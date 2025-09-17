import base64
import hashlib
import webbrowser
import urllib.parse
import requests
from datetime import datetime, timedelta, timezone
import json
import os
import ssl

# Require pip install pytz requests
import pytz

# anwb_prices.py
from anwb_prices import fetch_anwb_prices

"""

- The goal of this script is to set the buy and sell rates for the next day into the Tesla Powerwall, using the ANWB energie API, which uses hourly rates for electricity
- The sell rates should be set to the Marktprijs from ANWB, the buy price should be the AllInPrijs from the ABWB api.
- We should reference the @tesla_specs.md file for the correct rate plan structure and API endpoints, as well as the tester TestPowerwallConnectivity in  @test_powerrates.py.
These sources are validated, the current code in this file is not and has some incorrect APIs and schema's potentially
"""


# Placeholders
LOCAL_TZ = "Europe/Amsterdam"  # Local timezone for tariff times
REFRESH_TOKEN_FILE = "tesla_refresh_token.json"


def get_dayahead_prices():
    """
    Fetch day-ahead prices from ANWB API for today and tomorrow.
    Prices are returned in EUR/MWh for buy and sell.
    """
    cest_tz = pytz.timezone(LOCAL_TZ)
    now_local = datetime.now(cest_tz)

    prices = {}

    for day_offset in range(2):  # Today and tomorrow
        target_date = now_local + timedelta(days=day_offset)
        start_local = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_local = start_local + timedelta(days=1)

        # Convert to UTC for API
        utc_tz = pytz.UTC
        start_date_utc = (
            start_local.astimezone(utc_tz).isoformat().replace("+00:00", "Z")
        )
        end_date_utc = end_local.astimezone(utc_tz).isoformat().replace("+00:00", "Z")

        print(
            f"Fetching ANWB prices for {start_local.strftime('%Y-%m-%d')} from {start_date_utc} to {end_date_utc}"
        )
        anwb_data = fetch_anwb_prices(
            start_date_utc, end_date_utc, "electricity", "HOUR"
        )

        if anwb_data and "data" in anwb_data:
            for item in anwb_data["data"]:
                utc_dt_str = item["date"]
                utc_dt = datetime.fromisoformat(utc_dt_str.replace("Z", "+00:00"))

                # Buy price is "AllInPrijs"
                buy_price_eur_kwh = (
                    item["values"].get("allInPrijs", 0) / 100.0
                )  # Convert cents to EUR
                buy_price_eur_mwh = buy_price_eur_kwh * 1000

                # Sell price is "marktprijs"
                sell_price_eur_kwh = (
                    item["values"].get("marktprijs", 0) / 100.0
                )  # Convert cents to EUR
                sell_price_eur_mwh = sell_price_eur_kwh * 1000

                prices[utc_dt] = {
                    "buy": buy_price_eur_mwh,
                    "sell": sell_price_eur_mwh,
                }
    return prices


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

    - The goal of this script is to set the buy and sell rates for the next day into the Tesla Powerwall
    - The sell rates should be set to the Marktprijs from ANWB, the buy price should be the AllInPrijs from the ABWB api.
    - We should reference the @tesla_specs.md file for the correct rate plan structure and API endpoints, as well as the tester TestPowerwallConnectivity in  @test_powerrates.py.
    These sources are validated, the current code in this file is not and has some incorrect APIs and schema's potentially
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
):
    """
    Configure a rate plan based on day-ahead prices for the next day.

    This function creates 4 dynamic rate bands based on price percentiles (25% each):
    - SUPER_OFF_PEAK: 25% lowest rates
    - OFF_PEAK: Next 25% rates
    - PARTIAL_PEAK: Next 25% rates
    - ON_PEAK: 25% highest rates

    Args:
        dayahead_prices: Dictionary mapping datetime to EUR/MWh prices from get_dayahead_prices

    Returns:
        Tuple of (rate_plan_dict, tomorrow_hour_assignments, active_tou_periods)
    """

    # Get today's date for processing tomorrow's data
    today = datetime.now()
    tomorrow = today + timedelta(days=1)

    # Process prices for tomorrow
    tomorrow_prices = {}

    for dt, price_mwh in dayahead_prices.items():
        buy_rate_kwh = price_mwh["buy"] / 1000.0
        sell_rate_kwh = price_mwh["sell"] / 1000.0

        if dt.date() == tomorrow.date():
            tomorrow_prices[dt.hour] = {
                "buy": round(buy_rate_kwh, 4),
                "sell": round(sell_rate_kwh, 4),
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

    # Create rate bands for tomorrow
    tomorrow_rate_bands, tomorrow_hour_assignments = create_rate_bands(tomorrow_prices)

    # Create TOU periods for tomorrow
    active_tou_periods = create_tou_periods(tomorrow_hour_assignments)
    rate_plan_name = "Dynamic Market Rates (Tomorrow)"

    # Create separate dictionaries for buy and sell energy charges
    buy_energy_charges = {
        band: rates["buy"] for band, rates in tomorrow_rate_bands.items()
    }
    sell_energy_charges = {
        band: rates["sell"] for band, rates in tomorrow_rate_bands.items()
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
        tomorrow_hour_assignments,
        active_tou_periods,
    )


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

    # Fetch prices for today and tomorrow
    prices = get_dayahead_prices()

    print("🌙 Applying TOMORROW'S rates to Powerwall")

    # Configure rate plan based on day-ahead prices
    rate_plan, tomorrow_hour_assignments, active_tou_periods = (
        configure_rate_plan_from_prices(prices)
    )

    # Print rate band assignments for debugging
    print("\n=== Dynamic Rate Band Assignments ===")
    for period, hours in tomorrow_hour_assignments.items():
        print(f"  {period}: Hours {sorted(hours)}")

    schedule = convert_to_schedule_format(active_tou_periods)
    tou_payload = {
        "tou_settings": {"optimization_strategy": "economics", "schedule": schedule}
    }

    # Set the complete rate plan
    tariff_url = base_url + f"/api/1/energy_sites/{energy_site_id}/time_of_use_settings"

    print("\n=== Payload for POST to /time_of_use_settings ===")
    print(json.dumps(tou_payload, indent=2))

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

    print("\n" + "=" * 60)
    print("UPDATE PROCESS COMPLETE")


if __name__ == "__main__":
    main()
