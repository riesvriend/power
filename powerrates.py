import base64
import hashlib
import random
import webbrowser
import urllib.parse
import requests
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen, Request
from xml.etree import ElementTree
import json
import os
import ssl

# Require pip install pytz requests
import pytz


def create_ssl_context():
    """Create SSL context that handles certificate verification issues on macOS."""
    try:
        # Try to create a context with default certificate verification
        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        return context
    except Exception:
        # Fallback: Create context that doesn't verify certificates
        # This is less secure but handles macOS certificate issues
        print("Warning: Using SSL context without certificate verification")
        print(
            "For better security, run: /Applications/Python 3.12/Install Certificates.command"
        )
        context = ssl._create_unverified_context()
        return context


# Placeholders
ENTSOE_API_KEY_FILE = "entsoe_api_key.json"
AREA_CODE = "10YNL----------L"  # For Netherlands
LOCAL_TZ = "Europe/Amsterdam"  # Local timezone for tariff times
BUY_FEE = 0.05  # Additional fee for buy rate in EUR/kWh (adjust as needed, e.g., taxes)
SELL_FEE = -0.05  # Adjustment for sell rate in EUR/kWh (e.g., -fee)
REFRESH_TOKEN_FILE = "tesla_refresh_token.json"


def get_dayahead_prices(
    api_key: str, area_code: str, start: datetime = None, end: datetime = None
):
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
    fmt = "%Y%m%d%H00"
    url = (
        f"https://web-api.tp.entsoe.eu/api?securityToken={api_key}&documentType=A44&in_Domain={area_code}"
        f"&out_Domain={area_code}&periodStart={start.strftime(fmt)}&periodEnd={end.strftime(fmt)}"
    )

    # Create request with proper SSL context for macOS compatibility
    ssl_context = create_ssl_context()
    request = Request(url)
    with urlopen(request, context=ssl_context) as response:
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
                                        start_time = datetime.strptime(
                                            ti_child.text, "%Y-%m-%dT%H:%MZ"
                                        ).replace(tzinfo=timezone.utc)
                            elif pe_child.tag.endswith("Point"):
                                for po_child in pe_child:
                                    if po_child.tag.endswith("position"):
                                        delta = int(po_child.text) - 1
                                        time = start_time + timedelta(hours=delta)
                                    elif po_child.tag.endswith("price.amount"):
                                        price = float(po_child.text)
                                        result[time] = price
        return result


def get_entsoe_api_key():
    """Load ENTSOE API key from local file"""
    if os.path.exists(ENTSOE_API_KEY_FILE):
        try:
            with open(ENTSOE_API_KEY_FILE, "r") as f:
                data = json.load(f)
                api_key = data.get("api_key")
                if api_key:
                    print("Using saved ENTSOE API key.")
                    return api_key
        except json.JSONDecodeError:
            print(
                "Warning: Invalid JSON in ENTSOE API key file. Using placeholder implementation."
            )
        except Exception as e:
            print(
                f"Warning: Error reading ENTSOE API key file: {e}. Using placeholder implementation."
            )
    print("No saved ENTSOE API key found. Using placeholder implementation.")
    return "your_entsoe_api_key_here"


def get_tesla_tokens():
    if os.path.exists(REFRESH_TOKEN_FILE):
        with open(REFRESH_TOKEN_FILE, "r") as f:
            data = json.load(f)
            refresh_token = data.get("refresh_token")
            if refresh_token:
                print("Using saved refresh token.")
                return refresh_access_token(refresh_token)
    print("No saved refresh token. Performing full login.")
    code_verifier = base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8").rstrip("=")
    code_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("utf-8")).digest())
        .decode("utf-8")
        .rstrip("=")
    )
    state = base64.urlsafe_b64encode(os.urandom(16)).decode("utf-8").rstrip("=")
    client_id = "ownerapi"
    redirect_uri = "https://auth.tesla.com/void/callback"
    scope = "openid email offline_access"
    url = (
        f"https://auth.tesla.com/oauth2/v3/authorize?client_id={client_id}&code_challenge={code_challenge}"
        f"&code_challenge_method=S256&redirect_uri={redirect_uri}&response_type=code&scope={scope}&state={state}"
    )
    webbrowser.open(url)
    callback_url = input(
        "After logging in (including MFA if enabled), copy the full redirect URL from the browser address bar and paste it here: "
    )
    parsed = urllib.parse.urlparse(callback_url)
    query = urllib.parse.parse_qs(parsed.query)
    code = query.get("code", [None])[0]
    if not code:
        raise ValueError("No code found in the URL.")
    token_url = "https://auth.tesla.com/oauth2/v3/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "code": code,
        "code_verifier": code_verifier,
        "redirect_uri": redirect_uri,
    }
    response = requests.post(token_url, json=data)
    response.raise_for_status()
    tokens = response.json()
    with open(REFRESH_TOKEN_FILE, "w") as f:
        json.dump({"refresh_token": tokens["refresh_token"]}, f)
    return tokens["access_token"], tokens["refresh_token"]


def refresh_access_token(refresh_token):
    client_id = "ownerapi"
    token_url = "https://auth.tesla.com/oauth2/v3/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token,
        "scope": "openid email offline_access",
    }
    response = requests.post(token_url, json=data)
    response.raise_for_status()
    tokens = response.json()
    with open(REFRESH_TOKEN_FILE, "w") as f:
        json.dump({"refresh_token": tokens["refresh_token"]}, f)
    return tokens["access_token"], tokens["refresh_token"]


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
        endpoint = f"/api/1/energy_sites/{energy_site_id}/tariff_rate"
        url = base_url + endpoint
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()["response"]
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
                site_info_url = (
                    base_url + f"/api/1/energy_sites/{energy_site_id}/site_info"
                )
                site_info_response = requests.get(site_info_url, headers=headers)
                if site_info_response.status_code == 200:
                    site_info_data = site_info_response.json()["response"]
                    print("Site info retrieved. Checking for rate information...")

                    # Look for rate-related fields in site_info
                    rate_fields = ["tariff", "rates", "pricing", "tou", "time_of_use"]
                    found_rates = {}
                    for field in rate_fields:
                        if field in site_info_data:
                            found_rates[field] = site_info_data[field]

                    if found_rates:
                        print(
                            f"Found rate information in site_info: {list(found_rates.keys())}"
                        )
                        print(
                            f"Rate data: {json.dumps(found_rates, indent=2)[:300]}..."
                        )
                    else:
                        print("No rate information found in site_info response.")
                        print(
                            f"Available site_info keys: {list(site_info_data.keys())}"
                        )
                else:
                    print(
                        f"Site info endpoint returned status {site_info_response.status_code}"
                    )
            except Exception as e:
                print(f"Error checking site_info: {e}")

            return

        print(f"\n=== Current Rate Plan Details (from {successful_endpoint}) ===")

        # Pretty print the complete JSON response
        print(json.dumps(data, indent=2))

        print("=" * 40)

    except requests.exceptions.RequestException as e:
        print(f"Error fetching current rate plan: {e}")
    except KeyError as e:
        print(f"Unexpected response format: {e}")


def configure_rate_plan_from_prices(
    dayahead_prices,
    buy_fee=BUY_FEE,
    sell_fee=SELL_FEE,
    energy_tax=0.15,
    apply_today=False,
):
    """
    Configure a rate plan based on day-ahead prices that matches the structure
    from the print_current_rate_plan example.

    This function creates 4 dynamic rate bands based on price percentiles (25% each):
    - SUPER_OFF_PEAK: 25% lowest rates
    - OFF_PEAK: Next 25% rates
    - PARTIAL_PEAK: Next 25% rates
    - ON_PEAK: 25% highest rates

    ✨ NEW: Can apply rates for today OR tomorrow during the current day!

    Args:
        dayahead_prices: Dictionary mapping datetime to EUR/MWh prices from get_dayahead_prices
        buy_fee: Additional fee for buy rate in EUR/kWh (default: BUY_FEE)
        sell_fee: Adjustment for sell rate in EUR/kWh (default: SELL_FEE)
        energy_tax: Energy tax in EUR/kWh (default: 0.15)
        apply_today: If True, applies today's rates instead of tomorrow's (for early morning execution)

    Returns:
        Tuple of (rate_plan_dict, today_hour_assignments, tomorrow_hour_assignments)
        Returns the rate plan for the selected day (today or tomorrow)

    Usage Examples:
        # Apply tomorrow's rates (default behavior)
        rate_plan, today_assign, tomorrow_assign = configure_rate_plan_from_prices(prices)

        # Apply today's rates (for early morning execution)
        rate_plan, today_assign, tomorrow_assign = configure_rate_plan_from_prices(prices, apply_today=True)
    """

    # Get today's date for processing today's and tomorrow's data
    today = datetime.now()
    tomorrow = today + timedelta(days=1)

    # Separate prices for today and tomorrow
    # We'll calculate rate bands for both days but only apply tomorrow's to the Powerwall
    today_prices = {}
    tomorrow_prices = {}

    for dt, price_mwh in dayahead_prices.items():
        price_kwh = price_mwh / 1000.0
        # Buy rate = market price + energy tax + additional fee
        buy_rate = price_kwh + energy_tax + buy_fee
        # Sell rate = market price + energy tax + sell fee adjustment
        sell_rate = price_kwh + energy_tax + sell_fee

        # Determine if this is today or tomorrow
        dt_date = dt.date()
        if dt_date == today.date():
            today_prices[dt.hour] = {
                "buy": round(buy_rate, 4),
                "sell": round(sell_rate, 4),
                "raw_price": price_kwh,
            }
        elif dt_date == tomorrow.date():
            tomorrow_prices[dt.hour] = {
                "buy": round(buy_rate, 4),
                "sell": round(sell_rate, 4),
                "raw_price": price_kwh,
            }

    def create_rate_bands(hourly_data):
        # Create 4 rate bands based on price percentiles for a given day's data
        if not hourly_data:
            return {}, {}

        # Sort hours by buy rate (ascending)
        sorted_hours = sorted(hourly_data.items(), key=lambda x: x[1]["buy"])

        total_hours = len(sorted_hours)
        hours_per_band = total_hours // 4

        # Create rate bands with percentile-based grouping
        rate_bands = {}
        hour_assignments = {}

        # SUPER_OFF_PEAK: 25% lowest rates
        band_hours = sorted_hours[:hours_per_band]
        if band_hours:
            avg_buy = sum(h[1]["buy"] for h in band_hours) / len(band_hours)
            avg_sell = sum(h[1]["sell"] for h in band_hours) / len(band_hours)
            rate_bands["SUPER_OFF_PEAK"] = {
                "buy": round(avg_buy, 4),
                "sell": round(avg_sell, 4),
            }
            hour_assignments["SUPER_OFF_PEAK"] = [h[0] for h in band_hours]

        # OFF_PEAK: Next 25%
        band_hours = sorted_hours[hours_per_band : 2 * hours_per_band]
        if band_hours:
            avg_buy = sum(h[1]["buy"] for h in band_hours) / len(band_hours)
            avg_sell = sum(h[1]["sell"] for h in band_hours) / len(band_hours)
            rate_bands["OFF_PEAK"] = {
                "buy": round(avg_buy, 4),
                "sell": round(avg_sell, 4),
            }
            hour_assignments["OFF_PEAK"] = [h[0] for h in band_hours]

        # PARTIAL_PEAK: Next 25%
        band_hours = sorted_hours[2 * hours_per_band : 3 * hours_per_band]
        if band_hours:
            avg_buy = sum(h[1]["buy"] for h in band_hours) / len(band_hours)
            avg_sell = sum(h[1]["sell"] for h in band_hours) / len(band_hours)
            rate_bands["PARTIAL_PEAK"] = {
                "buy": round(avg_buy, 4),
                "sell": round(avg_sell, 4),
            }
            hour_assignments["PARTIAL_PEAK"] = [h[0] for h in band_hours]

        # ON_PEAK: Highest 25%
        band_hours = sorted_hours[3 * hours_per_band :]
        if band_hours:
            avg_buy = sum(h[1]["buy"] for h in band_hours) / len(band_hours)
            avg_sell = sum(h[1]["sell"] for h in band_hours) / len(band_hours)
            rate_bands["ON_PEAK"] = {
                "buy": round(avg_buy, 4),
                "sell": round(avg_sell, 4),
            }
            hour_assignments["ON_PEAK"] = [h[0] for h in band_hours]

        return rate_bands, hour_assignments

    def create_tou_periods(hour_assignments):
        tou_periods = {}
        for period_name, hours in hour_assignments.items():
            if not hours:
                tou_periods[period_name] = []
                continue

            sorted_hours = sorted(hours)
            periods = []

            start_hour = sorted_hours[0]
            for i in range(1, len(sorted_hours)):
                # Check for a gap in hours.
                if sorted_hours[i] != sorted_hours[i - 1] + 1:
                    # End the current period
                    end_hour = sorted_hours[i - 1]
                    periods.append(
                        {
                            "fromDayOfWeek": 0,
                            "toDayOfWeek": 6,
                            "fromHour": start_hour,
                            "fromMinute": 0,
                            "toHour": end_hour + 1,
                            "toMinute": 0,
                        }
                    )
                    # Start a new period
                    start_hour = sorted_hours[i]

            # Add the last period
            periods.append(
                {
                    "fromDayOfWeek": 0,
                    "toDayOfWeek": 6,
                    "fromHour": start_hour,
                    "fromMinute": 0,
                    "toHour": sorted_hours[-1] + 1,
                    "toMinute": 0,
                }
            )

            tou_periods[period_name] = periods
        return tou_periods

    # Create rate bands for today and tomorrow
    today_rate_bands, today_hour_assignments = create_rate_bands(today_prices)
    tomorrow_rate_bands, tomorrow_hour_assignments = create_rate_bands(tomorrow_prices)

    # Create TOU periods for today and tomorrow
    today_tou_periods = create_tou_periods(today_hour_assignments)
    tomorrow_tou_periods = create_tou_periods(tomorrow_hour_assignments)

    # Choose which day's rates to apply based on apply_today parameter
    if apply_today:
        active_rate_bands = today_rate_bands
        active_tou_periods = today_tou_periods
        rate_plan_name = "Dynamic Market Rates (Today)"
    else:
        active_rate_bands = tomorrow_rate_bands
        active_tou_periods = tomorrow_tou_periods
        rate_plan_name = "Dynamic Market Rates (Tomorrow)"

    # Create separate dictionaries for buy and sell energy charges
    buy_energy_charges = {
        band: rates["buy"] for band, rates in active_rate_bands.items()
    }
    sell_energy_charges = {
        band: rates["sell"] for band, rates in active_rate_bands.items()
    }

    # Create a clean rate plan structure
    rate_plan = {
        "name": rate_plan_name,
        "utility": "Per hour",
        "currency": "EUR",
        "daily_charges": [{"amount": 0, "name": "Charge"}],
        "demand_charges": {"ALL": {"ALL": 0}, "Summer": {}},
        "energy_charges": {"ALL": {"ALL": 0}, "Summer": buy_energy_charges},
        "seasons": {
            "Summer": {  # This season contains the selected day's dynamic rates
                "fromDay": 1,
                "toDay": 31,
                "fromMonth": 1,
                "toMonth": 12,  # Covers entire year with selected day's rates
                "tou_periods": active_tou_periods,
            }
        },
        "sell_tariff": {
            "name": rate_plan_name,
            "utility": "Per hour",
            "currency": "EUR",
            "daily_charges": [{"amount": 0, "name": "Charge"}],
            "demand_charges": {"ALL": {"ALL": 0}, "Summer": {}},
            "energy_charges": {"ALL": {"ALL": 0}, "Summer": sell_energy_charges},
            "seasons": {
                "Summer": {  # This season contains the selected day's dynamic rates
                    "fromDay": 1,
                    "toDay": 31,
                    "fromMonth": 1,
                    "toMonth": 12,  # Covers entire year with selected day's rates
                    "tou_periods": active_tou_periods,
                }
            },
        },
    }

    # The Tesla API is very specific about midnight.
    # A period ending at 24:00 must be represented as toHour: 0.
    # We will iterate through the generated periods and adjust them.
    for season in rate_plan["seasons"]:
        if "tou_periods" in rate_plan["seasons"][season]:
            for period_name in rate_plan["seasons"][season]["tou_periods"]:
                periods = rate_plan["seasons"][season]["tou_periods"][period_name]
                for p in periods:
                    if p["toHour"] == 24:
                        p["toHour"] = 0

    for season in rate_plan["sell_tariff"]["seasons"]:
        if "tou_periods" in rate_plan["sell_tariff"]["seasons"][season]:
            for period_name in rate_plan["sell_tariff"]["seasons"][season][
                "tou_periods"
            ]:
                periods = rate_plan["sell_tariff"]["seasons"][season]["tou_periods"][
                    period_name
                ]
                for p in periods:
                    if p["toHour"] == 24:
                        p["toHour"] = 0

    return (
        rate_plan,
        today_hour_assignments,
        tomorrow_hour_assignments,
        active_tou_periods,
    )


def detect_overlapping_periods(schedule):
    """Check for overlapping time periods in the TOU schedule"""
    print("\n🔍 ANALYZING SCHEDULE FOR OVERLAPS...")

    overlaps_found = []

    for i, period1 in enumerate(schedule):
        start1 = period1["start_seconds"]
        end1 = period1["end_seconds"] if period1["end_seconds"] != 0 else 86400
        target1 = period1["target"]

        for j, period2 in enumerate(schedule):
            if i >= j:  # Don't compare with self or already compared pairs
                continue

            start2 = period2["start_seconds"]
            end2 = period2["end_seconds"] if period2["end_seconds"] != 0 else 86400
            target2 = period2["target"]

            # Check for overlap
            if start1 < end2 and start2 < end1:
                # Convert to readable times
                start1_h = start1 // 3600
                start1_m = (start1 % 3600) // 60
                end1_h = end1 // 3600 if end1 < 86400 else 0
                end1_m = (end1 % 3600) // 60 if end1 < 86400 else 0

                start2_h = start2 // 3600
                start2_m = (start2 % 3600) // 60
                end2_h = end2 // 3600 if end2 < 86400 else 0
                end2_m = (end2 % 3600) // 60 if end2 < 86400 else 0

                overlaps_found.append(
                    {
                        "period1": f"{target1}: {start1_h:02d}:{start1_m:02d}-{end1_h:02d}:{end1_m:02d}",
                        "period2": f"{target2}: {start2_h:02d}:{start2_m:02d}-{end2_h:02d}:{end2_m:02d}",
                    }
                )

    if overlaps_found:
        print("❌ OVERLAPS DETECTED:")
        for overlap in overlaps_found:
            print(f"  ⚠️  {overlap['period1']} overlaps with {overlap['period2']}")
        return True
    else:
        print("✅ No overlapping periods detected")
        return False


def convert_to_schedule_format_simplified(tou_periods):
    """
    Simplified version that creates only 2 TOU periods (off_peak and peak)
    to work around Tesla API limitations.
    """
    print("🔧 Using SIMPLIFIED TOU format (2 periods only)")

    # Group all off-peak periods together
    off_peak_periods = []
    peak_periods = []

    for period_name, periods in tou_periods.items():
        if period_name in ["SUPER_OFF_PEAK", "OFF_PEAK"]:
            off_peak_periods.extend(periods)
        elif period_name in ["PARTIAL_PEAK", "ON_PEAK"]:
            peak_periods.extend(periods)

    def fill_small_gaps(intervals, max_gap_seconds=3600):  # Default 1 hour
        """Fill small gaps between intervals to create larger merged blocks"""
        if len(intervals) <= 1:
            return intervals

        filled = [intervals[0]]
        for start, end in intervals[1:]:
            last_start, last_end = filled[-1]
            gap = start - last_end

            if gap <= max_gap_seconds:
                # Fill the gap by extending the previous interval
                filled[-1] = (last_start, end)
                print(
                    f"    🔗 Filled {gap//3600}h gap: {last_start//3600:2d}-{end//3600:2d}"
                )
            else:
                filled.append((start, end))

        return filled

    def merge_periods(periods_list, target_name):
        """Merge overlapping or adjacent periods of the same type"""
        if not periods_list:
            return []

        # Debug: show input periods
        print(f"  📊 Input {target_name} periods:")
        for period in periods_list:
            if isinstance(period, dict):
                start_h = period["fromHour"]
                end_h = period["toHour"]
                if end_h == 0:
                    end_h = 24
                print(f"    {start_h:2d}:00 - {end_h:2d}:00")

        # Convert to seconds and sort
        intervals = []
        for period in periods_list:
            if isinstance(period, dict):
                start_seconds = period["fromHour"] * 3600 + period["fromMinute"] * 60
                end_seconds = period["toHour"] * 3600 + period["toMinute"] * 60
                if end_seconds == 0:
                    end_seconds = 86400
                intervals.append((start_seconds, end_seconds))

        if not intervals:
            return []

        # Sort by start time
        intervals.sort(key=lambda x: x[0])

        print(f"  🔄 Merging {len(intervals)} intervals...")

        # Merge overlapping/adjacent intervals
        merged = [intervals[0]]
        for start, end in intervals[1:]:
            last_start, last_end = merged[-1]
            if start <= last_end:  # Overlapping or adjacent
                merged[-1] = (last_start, max(last_end, end))
                print(f"    ✅ Merged: {last_start//3600:2d}-{end//3600:2d}")
            else:
                merged.append((start, end))
                print(f"    ➕ Added separate: {start//3600:2d}-{end//3600:2d}")

        # Option 2: More aggressive merging with small gap filling
        print(f"  🔄 Attempting gap filling (≤ 2 hours)...")
        merged = fill_small_gaps(merged, max_gap_seconds=7200)  # 2 hours

        print(f"  ✅ Result: {len(merged)} merged {target_name} periods")

        # Convert back to schedule format
        schedule_entries = []
        for start_seconds, end_seconds in merged:
            schedule_entries.append(
                {
                    "target": target_name,
                    "start_seconds": start_seconds,
                    "end_seconds": end_seconds,
                    "week_days": [0, 1, 2, 3, 4, 5, 6],
                }
            )

        return schedule_entries

    # Create merged schedules
    schedule = []
    schedule.extend(merge_periods(off_peak_periods, "off_peak"))
    schedule.extend(merge_periods(peak_periods, "peak"))

    print(
        f"✅ Simplified {len(off_peak_periods)} off-peak + {len(peak_periods)} peak periods into {len(schedule)} merged entries"
    )
    print(
        "💡 Gap filling reduced schedule complexity for better Tesla API compatibility"
    )

    return schedule


def convert_to_schedule_format(tou_periods):
    print("TOU Periods:")
    print(json.dumps(tou_periods, indent=2))
    schedule = []
    for period_name, periods in tou_periods.items():
        # The API expects specific, case-sensitive names for the rate bands
        if period_name == "SUPER_OFF_PEAK":
            target_name = "super_off_peak"
        elif period_name == "OFF_PEAK":
            target_name = "off_peak"
        elif period_name == "PARTIAL_PEAK":
            target_name = "partial_peak"
        elif period_name == "ON_PEAK":
            target_name = "peak"
        else:
            continue  # Skip unknown period names

        if not isinstance(periods, list):
            continue
        for period in periods:
            start_seconds = period["fromHour"] * 3600 + period["fromMinute"] * 60
            end_seconds = period["toHour"] * 3600 + period["toMinute"] * 60

            # For periods ending at midnight, toHour will be 24.
            # The API expects this to be end_seconds = 86400 for a full 24-hour day.
            # However, if start_seconds > end_seconds for a midnight-crossing schedule,
            # it should also be valid. Let's try the explicit end-of-day value.
            if end_seconds == 0 and start_seconds > 0:
                # This handles periods like 22:00-00:00, which should end at the end of the day.
                # Let's check if 'toHour' was 24 and got converted somewhere, or if it's 0.
                if period["toHour"] == 0:
                    # This implies a period crossing into the next day, ending at 00:00.
                    # Example: 22:00 to 00:00 the next day.
                    # For the Tesla API, we should use 86400 for the end of the day.
                    if start_seconds > 0:  # like 22:00 - 00:00
                        pass  # end_seconds = 0 is correct for midnight crossing
                    else:  # 00:00 - X
                        pass
            if period["toHour"] == 24:
                end_seconds = 86400

            # The API expects week_days as 0-6 (Sun-Sat)
            # We are setting the same schedule for all days of the week.
            week_days = [0, 1, 2, 3, 4, 5, 6]

            schedule.append(
                {
                    "target": target_name,
                    "start_seconds": start_seconds,
                    "end_seconds": end_seconds,
                    "week_days": week_days,
                }
            )
    return schedule


def main():
    # Load ENTSOE API key from file
    entsoe_api_key = get_entsoe_api_key()

    access_token, refresh_token = get_tesla_tokens()
    headers = {"Authorization": f"Bearer {access_token}"}
    base_url = "https://owner-api.teslamotors.com"
    # Get energy_site_id
    products_resp = requests.get(base_url + "/api/1/products", headers=headers)
    products_resp.raise_for_status()
    products = products_resp.json()["response"]
    energy_site_id = None
    for p in products:
        if p.get("resource_type", "") == "battery":
            energy_site_id = p["energy_site_id"]
            break
    if not energy_site_id:
        raise ValueError("No Powerwall found in your account.")

    # Print current rate plan details
    print_current_rate_plan(base_url, energy_site_id, headers)

    # Set to Time-Based Control if not already
    site_info_url = base_url + f"/api/1/energy_sites/{energy_site_id}/site_info"
    site_info_resp = requests.get(site_info_url, headers=headers)
    site_info_resp.raise_for_status()
    if site_info_resp.json()["response"]["default_real_mode"] != "autonomous":
        operation_url = base_url + f"/api/1/energy_sites/{energy_site_id}/operation"
        requests.post(
            operation_url,
            headers=headers,
            json={"default_real_mode": "autonomous"},
        )

    # Print the tou_settings from site_info for debugging
    site_info_data = site_info_resp.json()["response"]
    print("\n=== BEFORE UPDATE: Current Powerwall Status ===")
    print(f"Current real mode: {site_info_data.get('default_real_mode', 'Unknown')}")
    if "tou_settings" in site_info_data:
        print("\n--- Current TOU Settings ---")
        print(json.dumps(site_info_data["tou_settings"], indent=2))

        # Extract and print current schedule details
        if "schedule" in site_info_data["tou_settings"]:
            print("\n--- Current Schedule Breakdown ---")
            for entry in site_info_data["tou_settings"]["schedule"]:
                target = entry.get("target", "Unknown")
                start_sec = entry.get("start_seconds", 0)
                end_sec = entry.get("end_seconds", 0)
                start_hour = start_sec // 3600
                start_min = (start_sec % 3600) // 60
                if end_sec == 0:
                    end_hour = 24
                    end_min = 0
                else:
                    end_hour = end_sec // 3600
                    end_min = (end_sec % 3600) // 60
                week_days = entry.get("week_days", [])
                print(
                    f"  {target.upper()}: {start_hour:02d}:{start_min:02d} - {end_hour:02d}:{end_min:02d} (Days: {week_days})"
                )
    else:
        print("No TOU settings found in current configuration.")

    # Try to get current rate plan for buy/sell rates
    try:
        tariff_url = base_url + f"/api/1/energy_sites/{energy_site_id}/tariff_rate"
        print(f"\n--- Attempting to fetch tariff rates from: {tariff_url} ---")
        tariff_resp = requests.get(tariff_url, headers=headers)
        print(f"Tariff API Response Status: {tariff_resp.status_code}")

        if tariff_resp.status_code == 200:
            tariff_data = tariff_resp.json()["response"]
            print("✅ Tariff data retrieved successfully")
            print("\n--- Current Buy Rates (EUR/kWh) ---")
            if (
                "energy_charges" in tariff_data
                and "Summer" in tariff_data["energy_charges"]
            ):
                for period, rate in tariff_data["energy_charges"]["Summer"].items():
                    print(f"  {period}: {rate}")
            else:
                print("  No Summer energy_charges found")

            print("\n--- Current Sell Rates (EUR/kWh) ---")
            if (
                "sell_tariff" in tariff_data
                and "energy_charges" in tariff_data["sell_tariff"]
                and "Summer" in tariff_data["sell_tariff"]["energy_charges"]
            ):
                for period, rate in tariff_data["sell_tariff"]["energy_charges"][
                    "Summer"
                ].items():
                    print(f"  {period}: {rate}")
            else:
                print("  No Summer sell_tariff energy_charges found")
        else:
            print(f"❌ Tariff API failed: {tariff_resp.status_code}")
            print(f"Response: {tariff_resp.text}")
            print("💡 This might be expected if you haven't set custom rates yet")
    except Exception as e:
        print(f"❌ Could not fetch current tariff rates: {e}")
        print("💡 This is likely normal if no custom tariff has been set")

    print("\n" + "=" * 60)

    # Fetch prices for today and tomorrow
    now_utc = datetime.now(timezone.utc)
    start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
        days=0
    )  # Today
    end = start + timedelta(days=2)  # To cover tomorrow
    prices = get_dayahead_prices(entsoe_api_key, AREA_CODE, start, end)

    # Determine whether to apply today's or tomorrow's rates
    # If it's before noon UTC (can vary by timezone), we can still apply today's rates
    # Otherwise, apply tomorrow's rates for the next day
    current_hour_utc = now_utc.hour
    apply_today_rates = (
        current_hour_utc < 12
    )  # Before noon UTC - can still set today's rates

    # Allow manual override via environment variable for testing
    manual_override = os.getenv("TESLA_APPLY_TODAY_RATES")
    if manual_override is not None:
        apply_today_rates = manual_override.lower() in ("true", "1", "yes")
        print(f"🔧 Manual override detected: apply_today_rates = {apply_today_rates}")

    if apply_today_rates:
        print("⏰ Early execution detected - applying TODAY'S rates to Powerwall")
        print("(This allows you to set rates during the current day)")
    else:
        print("🌙 Late execution - applying TOMORROW'S rates to Powerwall")
        print("(This is the standard before-midnight execution)")

    # Configure rate plan based on day-ahead prices
    rate_plan, today_hour_assignments, tomorrow_hour_assignments, active_tou_periods = (
        configure_rate_plan_from_prices(prices, apply_today=apply_today_rates)
    )

    # Determine debug message
    if apply_today_rates:
        applied_message = "Today's rates (applied via Summer season - early execution):"
        reference_message = "Tomorrow's rates (calculated for reference - not applied):"
        applied_assignments = today_hour_assignments
        reference_assignments = tomorrow_hour_assignments
        confirmation_message = "✅ Today's rates will be applied to your Powerwall."
    else:
        applied_message = (
            "Tomorrow's rates (applied via Summer season - standard execution):"
        )
        reference_message = "Today's rates (calculated for reference - not applied):"
        applied_assignments = tomorrow_hour_assignments
        reference_assignments = today_hour_assignments
        confirmation_message = "✅ Tomorrow's rates will be applied to your Powerwall."

    # Print rate band assignments for debugging
    print("\n=== Dynamic Rate Band Assignments ===")
    print(applied_message)
    for period, hours in applied_assignments.items():
        print(f"  {period}: Hours {sorted(hours)}")
    print(f"\n{reference_message}")
    for period, hours in reference_assignments.items():
        print(f"  {period}: Hours {sorted(hours)}")
    print(f"\n{confirmation_message}")

    # The payload for the /time_of_use_settings endpoint needs to be a valid TOU setting.
    # We will construct this using the `tou_settings` key.

    # Check if we should use simplified TOU format (workaround for API issues)
    use_simplified = os.getenv("TESLA_USE_SIMPLIFIED_TOU", "false").lower() in (
        "true",
        "1",
        "yes",
    )
    if use_simplified:
        print(
            "\n🔧 USING SIMPLIFIED TOU FORMAT (2 periods) - set TESLA_USE_SIMPLIFIED_TOU=false to use full 4 periods"
        )
        schedule = convert_to_schedule_format_simplified(active_tou_periods)
    else:
        print(
            "\n📊 USING FULL TOU FORMAT (4 periods) - set TESLA_USE_SIMPLIFIED_TOU=true to use simplified 2 periods"
        )
        schedule = convert_to_schedule_format(active_tou_periods)
    tou_payload = {
        "tou_settings": {"optimization_strategy": "economics", "schedule": schedule}
    }

    # Set the complete rate plan
    tariff_url = base_url + f"/api/1/energy_sites/{energy_site_id}/time_of_use_settings"

    print("\n=== Payload for POST to /time_of_use_settings ===")
    print(json.dumps(tou_payload, indent=2))

    # Additional debugging: show schedule breakdown that will be sent
    print("\n--- Schedule Breakdown Being Sent ---")
    for entry in tou_payload["tou_settings"]["schedule"]:
        target = entry.get("target", "Unknown")
        start_sec = entry.get("start_seconds", 0)
        end_sec = entry.get("end_seconds", 0)
        start_hour = start_sec // 3600
        start_min = (start_sec % 3600) // 60
        if end_sec == 0:
            end_hour = 24
            end_min = 0
        else:
            end_hour = end_sec // 3600
            end_min = (end_sec % 3600) // 60
        week_days = entry.get("week_days", [])
        print(
            f"  {target}: {start_hour:02d}:{start_min:02d} - {end_hour:02d}:{end_min:02d} (Days: {week_days})"
        )

    targets_sent = {
        entry.get("target") for entry in tou_payload["tou_settings"]["schedule"]
    }
    print(f"\nTargets being sent: {sorted(targets_sent)} (count: {len(targets_sent)})")

    # Check for overlapping periods
    detect_overlapping_periods(tou_payload["tou_settings"]["schedule"])

    try:
        print(f"\n--- Making API call to: {tariff_url} ---")
        response = requests.post(tariff_url, headers=headers, json=tou_payload)
        print(f"API Response Status: {response.status_code}")

        if response.status_code == 200 or response.status_code == 201:
            response_data = response.json()
            print("✅ Rate plan updated successfully.")
            print(f"Response: {json.dumps(response_data, indent=2)}")
        else:
            print(f"❌ API call failed with status: {response.status_code}")
            print(f"Response text: {response.text}")
            response.raise_for_status()

    except requests.exceptions.HTTPError as err:
        print(f"❌ HTTP Error Occurred: {err}")
        print(f"Response Text: {err.response.text}")
        raise
    except Exception as e:
        print(f"❌ Unexpected error during API call: {e}")
        raise

    # Print updated rate plan details by fetching the site_info again
    print("\n" + "=" * 60)
    print("=== AFTER UPDATE: Verification ===")

    # Fetch updated site_info
    site_info_resp = requests.get(site_info_url, headers=headers)
    if site_info_resp.status_code == 200:
        updated_site_info_data = site_info_resp.json()["response"]
        print(
            f"Updated real mode: {updated_site_info_data.get('default_real_mode', 'Unknown')}"
        )

        if "tou_settings" in updated_site_info_data:
            print("\n--- Updated TOU Settings ---")
            print(json.dumps(updated_site_info_data["tou_settings"], indent=2))

            # Extract and print updated schedule details
            if "schedule" in updated_site_info_data["tou_settings"]:
                print("\n--- Updated Schedule Breakdown ---")
                for entry in updated_site_info_data["tou_settings"]["schedule"]:
                    target = entry.get("target", "Unknown")
                    start_sec = entry.get("start_seconds", 0)
                    end_sec = entry.get("end_seconds", 0)
                    start_hour = start_sec // 3600
                    start_min = (start_sec % 3600) // 60
                    if end_sec == 0:
                        end_hour = 24
                        end_min = 0
                    else:
                        end_hour = end_sec // 3600
                        end_min = (end_sec % 3600) // 60
                    week_days = entry.get("week_days", [])
                    print(
                        f"  {target.upper()}: {start_hour:02d}:{start_min:02d} - {end_hour:02d}:{end_min:02d} (Days: {week_days})"
                    )
        else:
            print("No TOU settings found in updated configuration.")

        # Try to get updated rate plan for buy/sell rates
        try:
            tariff_url = base_url + f"/api/1/energy_sites/{energy_site_id}/tariff_rate"
            print(f"\n--- Checking updated tariff rates from: {tariff_url} ---")
            tariff_resp = requests.get(tariff_url, headers=headers)
            print(f"Updated Tariff API Response Status: {tariff_resp.status_code}")

            if tariff_resp.status_code == 200:
                updated_tariff_data = tariff_resp.json()["response"]
                print("✅ Updated tariff data retrieved successfully")
                print("\n--- Updated Buy Rates (EUR/kWh) ---")
                if (
                    "energy_charges" in updated_tariff_data
                    and "Summer" in updated_tariff_data["energy_charges"]
                ):
                    for period, rate in updated_tariff_data["energy_charges"][
                        "Summer"
                    ].items():
                        print(f"  {period}: {rate}")
                else:
                    print("  No Summer energy_charges found")

                print("\n--- Updated Sell Rates (EUR/kWh) ---")
                if (
                    "sell_tariff" in updated_tariff_data
                    and "energy_charges" in updated_tariff_data["sell_tariff"]
                    and "Summer" in updated_tariff_data["sell_tariff"]["energy_charges"]
                ):
                    for period, rate in updated_tariff_data["sell_tariff"][
                        "energy_charges"
                    ]["Summer"].items():
                        print(f"  {period}: {rate}")
                else:
                    print("  No Summer sell_tariff energy_charges found")

                # Show complete tariff structure for debugging
                print("\n--- Complete Tariff Structure ---")
                print(json.dumps(updated_tariff_data, indent=2))
            else:
                print(f"❌ Updated tariff API failed: {tariff_resp.status_code}")
                print(f"Response: {tariff_resp.text}")
                print(
                    "💡 This might indicate that TOU settings don't automatically set tariff rates"
                )
        except Exception as e:
            print(f"❌ Could not fetch updated tariff rates: {e}")
            print("💡 TOU settings and tariff rates are separate - this is expected")

    else:
        print(
            f"Could not fetch updated site_info. Status code: {site_info_resp.status_code}"
        )

    # Compare before and after
    print("\n--- COMPARISON SUMMARY ---")
    if "tou_settings" in site_info_data and "tou_settings" in updated_site_info_data:
        original_schedule = site_info_data["tou_settings"].get("schedule", [])
        updated_schedule = updated_site_info_data["tou_settings"].get("schedule", [])

        print(f"Original schedule entries: {len(original_schedule)}")
        print(f"Updated schedule entries: {len(updated_schedule)}")

        # Check if schedules are different
        if len(original_schedule) != len(updated_schedule):
            print("❌ Schedule length changed - potential issue")
        else:
            print("✅ Schedule length matches")

        # Check for specific issues seen in the output
        original_targets = {entry.get("target") for entry in original_schedule}
        updated_targets = {entry.get("target") for entry in updated_schedule}
        print(f"Original targets: {sorted(original_targets)}")
        print(f"Updated targets: {sorted(updated_targets)}")

        if original_targets != updated_targets:
            print("⚠️  Target types changed - this may indicate API processing issues")
            missing_targets = targets_sent - updated_targets
            extra_targets = updated_targets - targets_sent
            if missing_targets:
                print(f"   Missing from response: {sorted(missing_targets)}")
            if extra_targets:
                print(f"   Extra in response: {sorted(extra_targets)}")

            print("\n🔍 ANALYSIS OF POTENTIAL ISSUES:")
            print("1. Tesla API may consolidate similar TOU periods")
            print(
                "2. 'super_off_peak' and 'partial_peak' might be merged into 'off_peak' and 'peak'"
            )
            print("3. API may have limits on number of distinct TOU periods")
            print("4. Weekday restrictions might cause periods to be filtered")

    else:
        print("Could not compare schedules - missing TOU settings")

    print("\n" + "=" * 60)
    print("UPDATE PROCESS COMPLETE")

    # Additional analysis for the specific issue seen
    print("\n🔧 RECOMMENDED FIXES:")
    print("1. Try SIMPLIFIED mode: TESLA_USE_SIMPLIFIED_TOU=true python3 powerrates.py")
    print("2. Check for overlapping periods (see analysis above)")
    print("3. Verify actual rate values are being set (check Tesla app)")
    print("4. Test with fewer TOU periods to isolate the issue")
    print("=" * 60)


def test_overlap_detection():
    """Quick test function to check overlap detection"""
    test_schedule = [
        {
            "target": "off_peak",
            "start_seconds": 0,
            "end_seconds": 3600,
            "week_days": [0, 1, 2, 3, 4, 5, 6],
        },
        {
            "target": "peak",
            "start_seconds": 3600,
            "end_seconds": 7200,
            "week_days": [0, 1, 2, 3, 4, 5, 6],
        },
        {
            "target": "off_peak",
            "start_seconds": 7200,
            "end_seconds": 10800,
            "week_days": [0, 1, 2, 3, 4, 5, 6],
        },
        {
            "target": "peak",
            "start_seconds": 3500,
            "end_seconds": 4000,
            "week_days": [0, 1, 2, 3, 4, 5, 6],
        },  # This overlaps!
    ]

    print("Testing overlap detection with sample schedule...")
    detect_overlapping_periods(test_schedule)


def test_merge_logic():
    """Test the period merging logic"""
    print("\n" + "=" * 50)
    print("TESTING PERIOD MERGING LOGIC")
    print("=" * 50)

    # Test data similar to what the script generates
    test_tou_periods = {
        "SUPER_OFF_PEAK": [
            {"fromHour": 0, "fromMinute": 0, "toHour": 1, "toMinute": 0},
            {"fromHour": 2, "fromMinute": 0, "toHour": 4, "toMinute": 0},
            {"fromHour": 5, "fromMinute": 0, "toHour": 6, "toMinute": 0},
        ],
        "OFF_PEAK": [
            {"fromHour": 1, "fromMinute": 0, "toHour": 2, "toMinute": 0},
            {"fromHour": 4, "fromMinute": 0, "toHour": 5, "toMinute": 0},
        ],
        "PARTIAL_PEAK": [
            {"fromHour": 9, "fromMinute": 0, "toHour": 10, "toMinute": 0},
            {"fromHour": 11, "fromMinute": 0, "toHour": 12, "toMinute": 0},
        ],
        "ON_PEAK": [
            {"fromHour": 6, "fromMinute": 0, "toHour": 9, "toMinute": 0},
            {"fromHour": 10, "fromMinute": 0, "toHour": 11, "toMinute": 0},
        ],
    }

    merged_schedule = convert_to_schedule_format_simplified(test_tou_periods)

    print(f"\nMerged schedule has {len(merged_schedule)} entries:")
    for entry in merged_schedule:
        start_h = entry["start_seconds"] // 3600
        start_m = (entry["start_seconds"] % 3600) // 60
        end_h = entry["end_seconds"] // 3600
        end_m = (entry["end_seconds"] % 3600) // 60
        if entry["end_seconds"] == 86400:
            end_h, end_m = 24, 0
        print(
            f"  {entry['target']}: {start_h:02d}:{start_m:02d} - {end_h:02d}:{end_m:02d}"
        )

    print("\nExpected result: 2-4 merged periods (fewer is better)")
    print("=" * 50)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--test-overlaps":
        test_overlap_detection()
    elif len(sys.argv) > 1 and sys.argv[1] == "--test-merge":
        test_merge_logic()
    else:
        main()
