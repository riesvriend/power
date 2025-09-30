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
from energy_zero_prices import fetch_energy_prices

"""

- The goal of this script is to set the buy and sell rates for the next day into the Tesla Powerwall, using the
  ANWB energie API, which uses hourly rates for electricity
- The sell rates should be set to the Marktprijs from ANWB, the buy price should be the AllInPrijs from the ABWB api.
- We should reference the @tesla_specs.md file for the correct rate plan structure and API endpoints, as well as the
  tester TestPowerwallConnectivity in  @test_powerrates.py.
These sources are validated, the current code in this file is not and has some incorrect APIs and schema's potentially
"""


# Placeholders
LOCAL_TZ = "Europe/Amsterdam"  # Local timezone for tariff times. MUST be an IANA-compliant name.
REFRESH_TOKEN_FILE = "tesla_refresh_token.json"
OVERHEAD_COST_KWH = 0.15  # EUR per kWh
BOOST_SALES_PRICES = False


def get_prices_today_and_tomorrow():
    """
    Fetch day-ahead prices from Energy Zero API for today and tomorrow.
    Prices are returned in EUR/MWh for buy and sell.
    """
    local_tz = pytz.timezone(LOCAL_TZ)
    now_local = datetime.now(local_tz)
    today_local = now_local.date()
    tomorrow_local = today_local + timedelta(days=1)

    all_prices = {}

    def fetch_prices_for_day(target_date):
        # Create a timezone-aware datetime for the beginning of the target day
        start_local = local_tz.localize(
            datetime.combine(target_date, datetime.min.time())
        )
        # The end of the day is 23 hours after the start to get 24 hourly slots (0-23)
        # as the EnergyZero API is inclusive of the end date.
        end_local = start_local + timedelta(hours=23)

        # Convert to UTC for the API and format as required
        start_utc = start_local.astimezone(pytz.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        end_utc = end_local.astimezone(pytz.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

        print(
            f"Fetching Energy Zero prices for {target_date.strftime('%Y-%m-%d')} from {start_utc} to {end_utc}"
        )
        # Fetch sell prices from Energy Zero (usageType=1 for return / electricity base price)
        energy_zero_data = fetch_energy_prices(start_utc, end_utc, 1)

        day_prices = {}
        if energy_zero_data and "Prices" in energy_zero_data:
            print(
                f"API returned {len(energy_zero_data['Prices'])} price points for {target_date.strftime('%Y-%m-%d')}."
            )
            for item in energy_zero_data["Prices"]:
                utc_dt = datetime.fromisoformat(
                    item["readingDate"].replace("Z", "+00:00")
                )
                # Energy Zero prices are in EUR/kWh.
                sell_price_kwh = item["price"]
                buy_price_kwh = sell_price_kwh + OVERHEAD_COST_KWH

                # Convert to EUR/MWh for the rest of the script
                sell_price_mwh = sell_price_kwh * 1000.0
                buy_price_mwh = buy_price_kwh * 1000.0

                day_prices[utc_dt] = {"buy": buy_price_mwh, "sell": sell_price_mwh}
        print(
            f"Processed {len(day_prices)} prices for {target_date.strftime('%Y-%m-%d')}."
        )
        return day_prices

    today_prices = fetch_prices_for_day(today_local)
    all_prices.update(today_prices)

    tomorrow_prices = fetch_prices_for_day(tomorrow_local)

    # If tomorrow's prices are not fully available, use today's as a fallback
    if len(tomorrow_prices) < 24 and len(today_prices) == 24:
        print(
            "Warning: Tomorrow's prices not fully available. Using today's prices as a fallback."
        )
        fallback_prices = {
            dt + timedelta(days=1): prices for dt, prices in today_prices.items()
        }
        all_prices.update(fallback_prices)
    else:
        all_prices.update(tomorrow_prices)

    return all_prices


def _request_tesla_tokens(data):
    """Helper function to handle common Tesla token request logic."""
    client_id = "ownerapi"
    token_url = "https://auth.tesla.com/oauth2/v3/token"
    data["client_id"] = client_id

    response = requests.post(token_url, json=data)
    response.raise_for_status()
    tokens = response.json()

    # Save the new refresh token
    with open(REFRESH_TOKEN_FILE, "w") as f:
        json.dump({"refresh_token": tokens["refresh_token"]}, f)

    return tokens["access_token"], tokens["refresh_token"]


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
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "code_verifier": code_verifier,
        "redirect_uri": redirect_uri,
    }
    return _request_tesla_tokens(data)


def refresh_access_token(refresh_token):
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "scope": "openid email offline_access",
    }
    return _request_tesla_tokens(data)


def get_yearly_grid_import_export(base_url, energy_site_id, headers):
    """Fetch total grid import and export for the current year."""
    local_tz = pytz.timezone(LOCAL_TZ)
    now_local = datetime.now(local_tz)
    start_of_year_local = now_local.replace(
        month=1, day=1, hour=0, minute=0, second=0, microsecond=0
    )

    start_date_utc = start_of_year_local.astimezone(pytz.UTC).strftime(
        "%Y-%m-%dT%H:%M:%S.000Z"
    )
    end_date_utc = now_local.astimezone(pytz.UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    endpoint = f"/api/1/energy_sites/{energy_site_id}/calendar_history"
    params = {
        "kind": "energy",
        "start_date": start_date_utc,
        "end_date": end_date_utc,
        "period": "year",
        "time_zone": LOCAL_TZ,
    }
    url = base_url + endpoint

    print(f"\nFetching yearly energy history from: {endpoint}")
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json().get("response", {})

        # print(f"Full API Response for Yearly History: {json.dumps(data)}")

        total_imported_wh = 0
        total_exported_wh = 0
        for entry in data.get("time_series", []):
            total_imported_wh += entry.get("grid_energy_imported", 0)
            total_exported_wh += entry.get("grid_energy_exported_from_solar", 0)
            total_exported_wh += entry.get("grid_energy_exported_from_generator", 0)
            total_exported_wh += entry.get("grid_energy_exported_from_battery", 0)

        # Convert from Wh to kWh
        total_imported_kwh = total_imported_wh / 1000.0
        total_exported_kwh = total_exported_wh / 1000.0

        # if current year is 2025, then add 5000 imported KwH; the value from before the install of the powerwall
        if now_local.year == 2025:
            total_imported_kwh += 5000

        print(
            f"Yearly grid summary: Imported={total_imported_kwh:.2f} kWh, Exported={total_exported_kwh:.2f} kWh"
        )
        return total_imported_kwh, total_exported_kwh

    except requests.exceptions.RequestException as e:
        print(f"Error fetching yearly energy history: {e}")
        return 0, 0


def print_current_rate_plan(base_url: str, energy_site_id: int, headers: dict):
    """Print the current rate plan details from the Powerwall."""
    try:
        endpoint = f"/api/1/energy_sites/{energy_site_id}/site_info"
        url = base_url + endpoint
        print(f"\nFetching current rate plan from: {endpoint}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        site_info_data = response.json().get("response", {})

        print("\n=== Current Site Info ===")
        print(json.dumps(site_info_data, indent=2))

        if "tou_settings" in site_info_data:
            print("\n=== Current TOU Settings ===")
            print(json.dumps(site_info_data["tou_settings"], indent=2))
        else:
            print("\nNo 'tou_settings' found in site_info.")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching current rate plan: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response text: {e.response.text}")
    except KeyError as e:
        print(f"Unexpected response format: {e}")


def configure_rate_plan_from_prices(today_tomorrow_prices, use_market_sell_price: bool):
    """
    Configure a rate plan for today and tomorrow using a single season.
    Today's rates are assigned to today's weekday, tomorrow's rates to all other weekdays.
    This allows the Powerwall algorithm to optimize properly within a single season.
    """
    local_tz = pytz.timezone(LOCAL_TZ)
    now_local = datetime.now(local_tz)
    today_local_date = now_local.date()
    tomorrow_local_date = today_local_date + timedelta(days=1)

    # Get weekday numbers (0=Monday, 6=Sunday in Python's weekday())
    # But Tesla uses 0=Sunday, 6=Saturday, so we need to convert:
    # Python: Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
    # Tesla:  Sun=0, Mon=1, Tue=2, Wed=3, Thu=4, Fri=5, Sat=6
    today_weekday_python = today_local_date.weekday()
    tomorrow_weekday_python = tomorrow_local_date.weekday()

    # Convert to Tesla's weekday numbering
    today_weekday_tesla = (today_weekday_python + 1) % 7
    tomorrow_weekday_tesla = (tomorrow_weekday_python + 1) % 7

    today_prices = {}
    tomorrow_prices = {}
    for utc_dt, price_mwh in today_tomorrow_prices.items():
        local_dt = utc_dt.astimezone(local_tz)
        if local_dt.date() == today_local_date:
            today_prices[local_dt.hour] = {
                "buy": round(price_mwh["buy"] / 1000.0, 4),
                "sell": round(price_mwh["sell"] / 1000.0, 4),
            }
        elif local_dt.date() == tomorrow_local_date:
            tomorrow_prices[local_dt.hour] = {
                "buy": round(price_mwh["buy"] / 1000.0, 4),
                "sell": round(price_mwh["sell"] / 1000.0, 4),
            }

    if len(today_prices) < 24:
        print(
            f"Warning: Missing some hourly prices for today. Found {len(today_prices)}/24 rates."
        )
    if len(tomorrow_prices) < 24:
        print(
            f"Warning: Missing some hourly prices for tomorrow. Found {len(tomorrow_prices)}/24 rates."
        )

    def boost_sales_price(buy_energy_charges, sell_energy_charges):
        """We want to force the powerwall to start selling to the grid, in case we still have
        an excess amount of energy purchages vs sold to the grid. If we bring the balance to
        to 0 by selling back, we get a kick-back value equal to the overhead costs that was paid
        on the purchased amount during the year.

        Find 12 of the rate items with the highest hourly rates and boost both the buy
        and the sell prices by the overhead amount. This will incentify the powerwalls algorithm
        to start selling to the grid during those high-price hours; even if there is a mostly flat rate during the day.
        """
        if not BOOST_SALES_PRICES:
            return

        # Create a list of (hour_name, buy_price) tuples to find the top 12
        hour_prices = []
        for hour_name, buy_price in buy_energy_charges.items():
            hour_prices.append((hour_name, buy_price))

        # Sort by buy price in descending order and take top 12
        hour_prices.sort(key=lambda x: x[1], reverse=True)
        top_12_hours = hour_prices[:12]

        # Boost both buy and sell prices for the top 12 hours
        for hour_name, _ in top_12_hours:
            buy_energy_charges[hour_name] += OVERHEAD_COST_KWH
            sell_energy_charges[hour_name] += OVERHEAD_COST_KWH

    # Create combined rate structure with weekday-based periods
    buy_energy_charges = {}
    sell_energy_charges = {}
    tou_periods = {}

    for hour in range(24):
        if hour not in today_prices or hour not in tomorrow_prices:
            continue

        # Create rate names for today and tomorrow
        today_rate_name = f"TODAY_HOUR_{hour}"
        tomorrow_rate_name = f"TOMORROW_HOUR_{hour}"

        # Get prices for this hour
        today_buy_price = today_prices[hour]["buy"]
        today_sell_price_raw = today_prices[hour]["sell"]
        tomorrow_buy_price = tomorrow_prices[hour]["buy"]
        tomorrow_sell_price_raw = tomorrow_prices[hour]["sell"]

        # Apply sell price logic (saldering)
        if use_market_sell_price:
            today_sell_price = today_sell_price_raw
            tomorrow_sell_price = tomorrow_sell_price_raw
        else:
            # Per ANWB, the sell price for consumers is the same as the buy price
            # until they sell more than they buy in a year. IE, we get the overhead back or prior purchases in the
            # year. This the 'salderingsregeling' in Netherlands, valid until 2026-12-31
            today_sell_price = today_buy_price
            tomorrow_sell_price = tomorrow_buy_price

        # Ensure buy >= sell
        if today_buy_price < today_sell_price:
            today_buy_price = today_sell_price
        if tomorrow_buy_price < tomorrow_sell_price:
            tomorrow_buy_price = tomorrow_sell_price

        # Add today's rates (applies only to today's weekday)
        buy_energy_charges[today_rate_name] = today_buy_price
        sell_energy_charges[today_rate_name] = today_sell_price
        tou_periods[today_rate_name] = {
            "periods": [
                {
                    "fromDayOfWeek": today_weekday_tesla,
                    "toDayOfWeek": today_weekday_tesla,
                    "fromHour": hour,
                    "fromMinute": 0,
                    "toHour": hour + 1 if hour < 23 else 0,
                    "toMinute": 0,
                }
            ]
        }

        # Add tomorrow's rates (applies to all days except today's weekday)
        buy_energy_charges[tomorrow_rate_name] = tomorrow_buy_price
        sell_energy_charges[tomorrow_rate_name] = tomorrow_sell_price

        # Create periods for all days except today's weekday
        periods = []
        for weekday in range(7):
            if weekday != today_weekday_tesla:
                periods.append(
                    {
                        "fromDayOfWeek": weekday,
                        "toDayOfWeek": weekday,
                        "fromHour": hour,
                        "fromMinute": 0,
                        "toHour": hour + 1 if hour < 23 else 0,
                        "toMinute": 0,
                    }
                )

        tou_periods[tomorrow_rate_name] = {"periods": periods}

    if not use_market_sell_price:
        boost_sales_price(buy_energy_charges, sell_energy_charges)

    rate_plan_name = "Dynamic Hourly Rates"

    # Create a single season covering the entire year
    single_season = {
        "fromDay": 1,
        "toDay": 31,
        "fromMonth": 1,
        "toMonth": 12,
        "tou_periods": tou_periods,
    }

    def create_tariff_structure(name, energy_charges, seasons):
        """Create a tariff structure with common fields."""
        return {
            "name": name,
            "utility": "Per hour",
            "currency": "EUR",
            "daily_charges": [{"amount": 0, "name": "Charge"}],
            "demand_charges": {
                "ALL": {"rates": {"ALL": 0}},
                "AllYear": {"rates": {}},
            },
            "energy_charges": {
                "ALL": {"rates": {"ALL": 0}},
                "AllYear": {"rates": energy_charges},
            },
            "seasons": seasons,
        }

    # Create seasons structure with single season
    seasons = {
        "AllYear": single_season,
    }

    rate_plan = {
        "version": 1,
        "name": rate_plan_name,
        "utility": "Per hour",
        "currency": "EUR",
        "daily_charges": [{"amount": 0, "name": "Charge"}],
        "demand_charges": {
            "ALL": {"rates": {"ALL": 0}},
            "AllYear": {"rates": {}},
        },
        "energy_charges": {
            "ALL": {"rates": {"ALL": 0}},
            "AllYear": {"rates": buy_energy_charges},
        },
        "seasons": seasons,
        "sell_tariff": create_tariff_structure(
            rate_plan_name, sell_energy_charges, seasons
        ),
    }
    return rate_plan, today_prices, tomorrow_prices


def convert_to_schedule_format(tou_periods):
    # print("TOU Periods:")
    # print(json.dumps(tou_periods, indent=2))
    schedule = []

    # Sort by fromHour to ensure correct processing
    sorted_periods = sorted(
        tou_periods.items(), key=lambda item: item[1]["periods"][0]["fromHour"]
    )

    for period_name, period_details in sorted_periods:
        # The API expects specific, case-sensitive names for the rate bands
        # For dynamic hourly rates, we can create a mapping or use a convention
        target_name = period_name.lower()  # e.g., "hour_0"

        for period in period_details.get("periods", []):
            start_seconds = period["fromHour"] * 3600 + period["fromMinute"] * 60

            # For a period ending at midnight (00:00 next day), toHour is 0.
            if period["toHour"] == 0 and period["fromHour"] == 23:
                end_seconds = 86400  # End of the day
            else:
                end_seconds = period["toHour"] * 3600 + period["toMinute"] * 60

            schedule.append(
                {
                    "target": target_name,
                    "start_seconds": start_seconds,
                    "end_seconds": end_seconds,
                    "week_days": list(range(7)),  # All days of the week
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

    # Get yearly import/export stats to determine sell price strategy
    total_imported, total_exported = get_yearly_grid_import_export(
        base_url, energy_site_id, headers
    )
    use_market_sell_price = total_exported > total_imported
    if use_market_sell_price:
        print("Annual export exceeds import. Using market rate for sell price.")
    else:
        print(
            "Annual import exceeds export. Using buy price for sell price (salderen)."
        )

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
    prices_today_and_tomorrow = get_prices_today_and_tomorrow()

    print("🌙 Applying rates to Powerwall")

    # Configure rate plan based on day-ahead prices
    rate_plan, today_prices, tomorrow_prices = configure_rate_plan_from_prices(
        prices_today_and_tomorrow, use_market_sell_price
    )

    # Check if we have a full set of prices before proceeding
    if len(today_prices) < 24 or len(tomorrow_prices) < 24:
        print("❌ Critical: Missing full 24-hour price data for today or tomorrow.")
        print("Aborting Powerwall schedule update to prevent invalid data upload.")
        return  # Exit the main function

    # Print rate band assignments for debugging
    print("\n=== Today's Hourly Rate Assignments (EUR/kWh) ===")
    for hour in sorted(today_prices.keys()):
        buy_price = today_prices[hour]["buy"]
        sell_price = today_prices[hour]["sell"]
        print(f"  Hour {hour:02d}: Buy @ {buy_price:.4f}, Sell @ {sell_price:.4f}")

    print("\n=== Tomorrow's Hourly Rate Assignments (EUR/kWh) ===")
    for hour in sorted(tomorrow_prices.keys()):
        buy_price = tomorrow_prices[hour]["buy"]
        sell_price = tomorrow_prices[hour]["sell"]
        print(f"  Hour {hour:02d}: Buy @ {buy_price:.4f}, Sell @ {sell_price:.4f}")

    schedule = convert_to_schedule_format(
        rate_plan["seasons"]["AllYear"]["tou_periods"]
    )
    tou_payload = {
        "tou_settings": {"schedule": schedule, "tariff_content_v2": rate_plan}
    }

    # Set the complete rate plan
    tariff_url = base_url + f"/api/1/energy_sites/{energy_site_id}/time_of_use_settings"

    # print("\n=== Payload for POST to /time_of_use_settings ===")
    # print(json.dumps(tou_payload, indent=2))

    try:
        print(f"\n--- Making API call to: {tariff_url} ---")
        response = requests.post(tariff_url, headers=headers, json=tou_payload)
        print(f"API Response Status: {response.status_code}")

        if response.status_code == 200 or response.status_code == 201:
            response_data = response.json()
            print("✅ Rate plan updated successfully.")
            # print(f"Response: {json.dumps(response_data, indent=2)}")
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
