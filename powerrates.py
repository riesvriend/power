import base64
import hashlib
import random
import webbrowser
import urllib.parse
import requests
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen
from xml.etree import ElementTree
import json
import os

# Require pip install pytz requests
import pytz

# Placeholders
ENTSOE_API_KEY = "your_entsoe_api_key_here"  # Register at https://transparency.entsoe.eu/ for a security token
AREA_CODE = "10YNL----------L"  # For Netherlands
LOCAL_TZ = "Europe/Amsterdam"  # Local timezone for tariff times
BUY_FEE = 0.05  # Additional fee for buy rate in EUR/kWh (adjust as needed, e.g., taxes)
SELL_FEE = -0.05  # Adjustment for sell rate in EUR/kWh (e.g., -fee)
REFRESH_TOKEN_FILE = "tesla_refresh_token.json"

def get_dayahead_prices(api_key: str, area_code: str, start: datetime = None, end: datetime = None):
    # Use stub implementation if API key is placeholder
    # https://transparencyplatform.zendesk.com/hc/en-us/articles/12845911031188-How-to-get-security-token
    if api_key == "your_entsoe_api_key_here":
        print("Using stub ENTSOE API implementation with dummy rates")
        if not start:
            start = datetime.now().astimezone(timezone.utc)
        elif start.tzinfo and start.tzinfo != timezone.utc:
            start = start.astimezone(timezone.utc)
        if not end:
            end = start + timedelta(days=1)
        elif end.tzinfo and end.tzinfo != timezone.utc:
            end = end.astimezone(timezone.utc)

        # Generate dummy prices for each hour (EUR/MWh)
        result = {}
        current_time = start.replace(minute=0, second=0, microsecond=0)
        while current_time < end:
            # Generate realistic electricity prices with some variation
            # Base price around 80-120 EUR/MWh, with daily pattern
            hour = current_time.hour
            if 6 <= hour <= 9 or 17 <= hour <= 20:  # Peak hours
                base_price = 120.0
            elif 10 <= hour <= 16:  # Mid-day
                base_price = 90.0
            else:  # Off-peak (night)
                base_price = 60.0

            # Add some random variation (±10 EUR/MWh)
            price = base_price + random.uniform(-10, 10)

            result[current_time] = round(price, 2)
            current_time += timedelta(hours=1)

        return result

    # Original ENTSOE API implementation
    if not start:
        start = datetime.now().astimezone(timezone.utc)
    elif start.tzinfo and start.tzinfo != timezone.utc:
        start = start.astimezone(timezone.utc)
    if not end:
        end = start + timedelta(days=1)
    elif end.tzinfo and end.tzinfo != timezone.utc:
        end = end.astimezone(timezone.utc)
    fmt = '%Y%m%d%H00'
    url = f'https://web-api.tp.entsoe.eu/api?securityToken={api_key}&documentType=A44&in_Domain={area_code}' \
          f'&out_Domain={area_code}&periodStart={start.strftime(fmt)}&periodEnd={end.strftime(fmt)}'
    with urlopen(url) as response:
        if response.status != 200:
            raise Exception(f"{response.status=}")
        xml_str = response.read().decode()
        result = {}
        for child in ElementTree.fromstring(xml_str):
            if child.tag.endswith("TimeSeries"):
                for ts_child in child:
                    if ts_child.tag.endswith("Period"):
                        for pe_child in ts_child:
                            if pe_child.tag.endswith("timeInterval"):
                                for ti_child in pe_child:
                                    if ti_child.tag.endswith("start"):
                                        start_time = datetime.strptime(ti_child.text, '%Y-%m-%dT%H:%MZ').replace(tzinfo=timezone.utc)
                            elif pe_child.tag.endswith("Point"):
                                for po_child in pe_child:
                                    if po_child.tag.endswith("position"):
                                        delta = int(po_child.text) - 1
                                        time = start_time + timedelta(hours=delta)
                                    elif po_child.tag.endswith("price.amount"):
                                        price = float(po_child.text)
                                        result[time] = price
        return result

def get_tesla_tokens():
    if os.path.exists(REFRESH_TOKEN_FILE):
        with open(REFRESH_TOKEN_FILE, 'r') as f:
            data = json.load(f)
            refresh_token = data.get('refresh_token')
            if refresh_token:
                print("Using saved refresh token.")
                return refresh_access_token(refresh_token)
    print("No saved refresh token. Performing full login.")
    code_verifier = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8').rstrip('=')
    code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode('utf-8')).digest()).decode('utf-8').rstrip('=')
    state = base64.urlsafe_b64encode(os.urandom(16)).decode('utf-8').rstrip('=')
    client_id = 'ownerapi'
    redirect_uri = 'https://auth.tesla.com/void/callback'
    scope = 'openid email offline_access'
    url = (f'https://auth.tesla.com/oauth2/v3/authorize?client_id={client_id}&code_challenge={code_challenge}'
           f'&code_challenge_method=S256&redirect_uri={redirect_uri}&response_type=code&scope={scope}&state={state}')
    webbrowser.open(url)
    callback_url = input("After logging in (including MFA if enabled), copy the full redirect URL from the browser address bar and paste it here: ")
    parsed = urllib.parse.urlparse(callback_url)
    query = urllib.parse.parse_qs(parsed.query)
    code = query.get('code', [None])[0]
    if not code:
        raise ValueError("No code found in the URL.")
    token_url = 'https://auth.tesla.com/oauth2/v3/token'
    data = {
        'grant_type': 'authorization_code',
        'client_id': client_id,
        'code': code,
        'code_verifier': code_verifier,
        'redirect_uri': redirect_uri
    }
    response = requests.post(token_url, json=data)
    response.raise_for_status()
    tokens = response.json()
    with open(REFRESH_TOKEN_FILE, 'w') as f:
        json.dump({'refresh_token': tokens['refresh_token']}, f)
    return tokens['access_token'], tokens['refresh_token']

def refresh_access_token(refresh_token):
    client_id = 'ownerapi'
    token_url = 'https://auth.tesla.com/oauth2/v3/token'
    data = {
        'grant_type': 'refresh_token',
        'client_id': client_id,
        'refresh_token': refresh_token,
        'scope': 'openid email offline_access'
    }
    response = requests.post(token_url, json=data)
    response.raise_for_status()
    tokens = response.json()
    with open(REFRESH_TOKEN_FILE, 'w') as f:
        json.dump({'refresh_token': tokens['refresh_token']}, f)
    return tokens['access_token'], tokens['refresh_token']

def print_current_rate_plan(base_url: str, energy_site_id: int, headers: dict):
    """Print the current rate plan details from the Powerwall.
    
    example response below. T
    
    The example response shows how the rate plan is structured.

    - There are max 4 rates, named     "OFF_PEAK", "ON_PEAK", "PARTIAL_PEAK", "SUPER_OFF_PEAK"
    - The goal of this script is to set the buy rates for the next day based on the entsoe market prices+energy tax of about 15 cent per kWh+additional fee of 5 cent per kWh
    - The sell rates should be set to the buy rates, also including tax. The user will get the full amount of the sell rate, including the energy tax.
    - In order to set the rates for today and tomorrow, we could configure the rate plan seasons so that winter is for all dates up today, and summer is for all dates after today (tomorrow).

=== Current Rate Plan Details (from /api/1/energy_sites/1689507072890170/tariff_rate) ===
{
  "name": "Test",
  "utility": "Per hour",
  "daily_charges": [
    {
      "amount": 0,
      "name": "Charge"
    }
  ],
  "demand_charges": {
    "ALL": {
      "ALL": 0
    },
    "Summer": {},
    "Winter": {}
  },
  "energy_charges": {
    "ALL": {
      "ALL": 0
    },
    "Summer": {
        "OFF_PEAK": 0.2,
        "ON_PEAK": 0.35,
        "PARTIAL_PEAK": 0.27,
        "SUPER_OFF_PEAK": 0.17
    },
    "Winter": {}
  },
  "seasons": {
    "Summer": {
      "fromDay": 1,
      "toDay": 31,
      "fromMonth": 1,
      "toMonth": 12,
      "tou_periods": {
        "OFF_PEAK": [
          {
            "fromDayOfWeek": 0,
            "toDayOfWeek": 6,
            "fromHour": 10,
            "fromMinute": 0,
            "toHour": 16,
            "toMinute": 0
          },
          {
            "fromDayOfWeek": 0,
            "toDayOfWeek": 6,
            "fromHour": 21,
            "fromMinute": 0,
            "toHour": 0,
            "toMinute": 0
          }
        ],
        "ON_PEAK": [
          {
            "fromDayOfWeek": 0,
            "toDayOfWeek": 6,
            "fromHour": 16,
            "fromMinute": 0,
            "toHour": 21,
            "toMinute": 0
          }
        ],
        "PARTIAL_PEAK": [
          {
            "fromDayOfWeek": 0,
            "toDayOfWeek": 6,
            "fromHour": 6,
            "fromMinute": 0,
            "toHour": 10,
            "toMinute": 0
          }
        ],
        "SUPER_OFF_PEAK": [
          {
            "fromDayOfWeek": 0,
            "toDayOfWeek": 6,
            "fromHour": 0,
            "fromMinute": 0,
            "toHour": 6,
            "toMinute": 0
          }
        ]
      }
    },
    "Winter": {
      "fromDay": 0,
      "toDay": 0,
      "fromMonth": 0,
      "toMonth": 0,
      "tou_periods": {}
    }
  },
  "sell_tariff": {
    "name": "Test",
    "utility": "Per hour",
    "daily_charges": [
      {
        "amount": 0,
        "name": "Charge"
      }
    ],
    "demand_charges": {
      "ALL": {
        "ALL": 0
      },
      "Summer": {},
      "Winter": {}
    },
    "energy_charges": {
      "ALL": {
        "ALL": 0
      },
      "Summer": {
        "OFF_PEAK": 0.05,
        "ON_PEAK": 0.2,
        "PARTIAL_PEAK": 0.12,
        "SUPER_OFF_PEAK": 0.02
      },
      "Winter": {}
    },
    "seasons": {
      "Summer": {
        "fromDay": 1,
        "toDay": 31,
        "fromMonth": 1,
        "toMonth": 12,
        "tou_periods": {
          "OFF_PEAK": [
            {
              "fromDayOfWeek": 0,
              "toDayOfWeek": 6,
              "fromHour": 10,
              "fromMinute": 0,
              "toHour": 16,
              "toMinute": 0
            },
            {
              "fromDayOfWeek": 0,
              "toDayOfWeek": 6,
              "fromHour": 21,
              "fromMinute": 0,
              "toHour": 0,
              "toMinute": 0
            }
          ],
          "ON_PEAK": [
            {
              "fromDayOfWeek": 0,
              "toDayOfWeek": 6,
              "fromHour": 16,
              "fromMinute": 0,
              "toHour": 21,
              "toMinute": 0
            }
          ],
          "PARTIAL_PEAK": [
            {
              "fromDayOfWeek": 0,
              "toDayOfWeek": 6,
              "fromHour": 6,
              "fromMinute": 0,
              "toHour": 10,
              "toMinute": 0
            }
          ],
          "SUPER_OFF_PEAK": [
            {
              "fromDayOfWeek": 0,
              "toDayOfWeek": 6,
              "fromHour": 0,
              "fromMinute": 0,
              "toHour": 6,
              "toMinute": 0
            }
          ]
        }
      },
      "Winter": {
        "fromDay": 0,
        "toDay": 0,
        "fromMonth": 0,
        "toMonth": 0,
        "tou_periods": {}
      }
    }
  }
}

    
    """
    try:
        # Use single endpoint for getting TOU settings
        endpoint = f'/api/1/energy_sites/{energy_site_id}/tariff_rate'
        url = base_url + endpoint
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()['response']
            successful_endpoint = endpoint
        else:
            data = None
            successful_endpoint = None

        if not data:
            print(f"Could not retrieve current rate plan from endpoint {endpoint}.")
            print(f"Response status: {response.status_code}")

            # Try to get rate information from site_info as a fallback
            print("\nTrying to get rate information from site_info...")
            try:
                site_info_url = base_url + f'/api/1/energy_sites/{energy_site_id}/site_info'
                site_info_response = requests.get(site_info_url, headers=headers)
                if site_info_response.status_code == 200:
                    site_info_data = site_info_response.json()['response']
                    print("Site info retrieved. Checking for rate information...")

                    # Look for rate-related fields in site_info
                    rate_fields = ['tariff', 'rates', 'pricing', 'tou', 'time_of_use']
                    found_rates = {}
                    for field in rate_fields:
                        if field in site_info_data:
                            found_rates[field] = site_info_data[field]

                    if found_rates:
                        print(f"Found rate information in site_info: {list(found_rates.keys())}")
                        import json
                        print(f"Rate data: {json.dumps(found_rates, indent=2)[:300]}...")
                    else:
                        print("No rate information found in site_info response.")
                        print(f"Available site_info keys: {list(site_info_data.keys())}")
                else:
                    print(f"Site info endpoint returned status {site_info_response.status_code}")
            except Exception as e:
                print(f"Error checking site_info: {e}")

            return

        print(f"\n=== Current Rate Plan Details (from {successful_endpoint}) ===")

        # Pretty print the complete JSON response
        import json
        print(json.dumps(data, indent=2))

        print("=" * 40)

    except requests.exceptions.RequestException as e:
        print(f"Error fetching current rate plan: {e}")
    except KeyError as e:
        print(f"Unexpected response format: {e}")

def main():
    access_token, refresh_token = get_tesla_tokens()
    headers = {'Authorization': f'Bearer {access_token}'}
    base_url = 'https://owner-api.teslamotors.com'
    # Get energy_site_id
    products_resp = requests.get(base_url + '/api/1/products', headers=headers)
    products_resp.raise_for_status()
    products = products_resp.json()['response']
    energy_site_id = None
    for p in products:
        if p.get('resource_type', '') == 'battery':
            energy_site_id = p['energy_site_id']
            break
    if not energy_site_id:
        raise ValueError("No Powerwall found in your account.")

    # Print current rate plan details
    print_current_rate_plan(base_url, energy_site_id, headers)

    # Set to Time-Based Control if not already
    site_info_url = base_url + f'/api/1/energy_sites/{energy_site_id}/site_info'
    site_info_resp = requests.get(site_info_url, headers=headers)
    site_info_resp.raise_for_status()
    if site_info_resp.json()['response']['default_real_mode'] != 'self_consumption':
        operation_url = base_url + f'/api/1/energy_sites/{energy_site_id}/operation'
        requests.post(operation_url, headers=headers, json={'default_real_mode': 'self_consumption'})
    # Fetch prices for today and tomorrow
    now_utc = datetime.now(timezone.utc)
    start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=0)  # Today
    end = start + timedelta(days=2)  # To cover tomorrow
    prices = get_dayahead_prices(ENTSOE_API_KEY, AREA_CODE, start, end)
    # Get current local time
    local_tz = pytz.timezone(LOCAL_TZ)
    now_local = now_utc.astimezone(local_tz)
    current_hour = now_local.hour
    # Build periods using the trick
    periods = []
    today_start = start
    tomorrow_start = start + timedelta(days=1)
    for i in range(24):
        start_time_str = f"{i:02d}:00"
        end_time_str = f"{(i + 1) % 24:02d}:00"
        if i < current_hour:
            # Use tomorrow's price
            dt = tomorrow_start + timedelta(hours=i)
        else:
            # Use today's price
            dt = today_start + timedelta(hours=i)
        price_mwh = prices.get(dt, 0.0)
        price_kwh = price_mwh / 1000
        buy_rate = price_kwh + BUY_FEE
        sell_rate = price_kwh + SELL_FEE
        periods.append({
            "label": f"hour_{i:02d}",
            "start_time": start_time_str,
            "end_time": end_time_str,
            "buy_rate": buy_rate,
            "sell_rate": sell_rate
        })
    # Build tariff body - try simpler format
    tariff_body = {
        "tou_settings": {
            "currency": "EUR",
            "seasons": {
                "default": {
                    "fromMonth": 1,
                    "fromDay": 1,
                    "toMonth": 12,
                    "toDay": 31,
                    "tou_periods": periods
                }
            }
        }
    }
    # Set the tariff
    tariff_url = base_url + f'/api/1/energy_sites/{energy_site_id}/time_of_use_settings'
    response = requests.post(tariff_url, headers=headers, json=tariff_body)
    response.raise_for_status()
    print("Tariff updated successfully.")
    print(f"Tariff update response: {response.json()}")

    # Print updated rate plan details
    print("\n=== Updated Rate Plan Details ===")
    print_current_rate_plan(base_url, energy_site_id, headers)

if __name__ == "__main__":
    main()