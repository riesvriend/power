import requests
from datetime import datetime, timedelta
import pytz


def fetch_energy_prices(from_date, till_date, usage_type, incl_btw=True):
    """
    Fetch energy prices from EnergyZero API.
    - usage_type: 1 (electricity consumption), 2 (electricity return), 3 (gas)
    """
    base_url = "https://api.energyzero.nl/v1/energyprices"
    params = {
        "fromDate": from_date,
        "tillDate": till_date,
        "interval": 4,  # Hourly rates
        "usageType": usage_type,
        "inclBtw": str(incl_btw).lower(),
    }
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching data for usageType {usage_type}: {response.status_code}")
        return None


def utc_to_cest(utc_dt_str):
    """
    Convert UTC timestamp string (e.g., '2025-09-17T00:00:00Z') to CEST datetime string.
    """
    utc_dt = datetime.fromisoformat(utc_dt_str.replace("Z", "+00:00"))
    cest_tz = pytz.timezone("Europe/Amsterdam")
    cest_dt = utc_dt.astimezone(cest_tz)
    return cest_dt.strftime("%Y-%m-%dT%H:%M:%S%Z")


def main():
    # Define local timezone (Netherlands, CEST on Sep 17, 2025)
    cest_tz = pytz.timezone("Europe/Amsterdam")

    # Get today's start and end in local time (CEST)
    today_local = datetime.now(cest_tz).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    today_end_local = today_local.replace(
        hour=23, minute=59, second=59, microsecond=999999
    )

    # Convert local times to UTC for API
    utc_tz = pytz.UTC
    today_start_utc = today_local.astimezone(utc_tz).isoformat().replace("+00:00", "Z")
    today_end_utc = (
        today_end_local.astimezone(utc_tz).isoformat().replace("+00:00", "Z")
    )

    print(f"Fetching prices for {today_local.strftime('%Y-%m-%d')} (CEST)")

    # Fetch and print electricity consumption (usageType=1)
    elec_cons = fetch_energy_prices(today_start_utc, today_end_utc, 1)
    if elec_cons:
        print("\nElectricity Consumption Prices (CEST):")
        print(f"Average: {elec_cons.get('average', 'N/A'):.3f} EUR/kWh")
        for price in elec_cons.get("Prices", []):
            cest_time = utc_to_cest(price["readingDate"])
            print(f"{cest_time}: {price['price']:.3f} EUR/kWh")


if __name__ == "__main__":
    main()
