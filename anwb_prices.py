import requests
from datetime import datetime
import pytz


def fetch_anwb_prices(
    start_date_utc, end_date_utc, energy_type="electricity", interval="HOUR"
):
    """
    Fetch prices from ANWB API.
    - energy_type: 'electricity' (buy), 'electricity-return' (return), 'gas' (use interval='DAY')
    """
    base_url = "https://api.anwb.nl/energy/energy-services/v1/tarieven/"
    url = f"{base_url}{energy_type}"
    params = {
        "startDate": start_date_utc,
        "endDate": end_date_utc,
        "interval": interval,
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9,nl;q=0.8",
        "Referer": "https://www.anwb.nl/energie/actuele-tarieven",
        # Add Authorization if found in browser console (e.g., 'Authorization: Bearer ...')
        # "Authorization": "Bearer YOUR_TOKEN_HERE",
    }
    print(
        f"Request URL: {url}?startDate={start_date_utc}&endDate={end_date_utc}&interval={interval}"
    )
    print(f"Headers: {headers}")
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {energy_type} data: {e}")
        return None


def utc_to_cest(utc_dt_str):
    """
    Convert UTC timestamp (e.g., '2025-09-17T00:00:00.000Z') to CEST string.
    """
    utc_dt_str = (
        utc_dt_str.replace(".000Z", "Z") if ".000Z" in utc_dt_str else utc_dt_str
    )
    utc_dt = datetime.fromisoformat(utc_dt_str.replace("Z", "+00:00"))
    cest_tz = pytz.timezone("Europe/Amsterdam")
    cest_dt = utc_dt.astimezone(cest_tz)
    return cest_dt.strftime("%Y-%m-%dT%H:%M:%S%Z")


def main():
    # Define local timezone (CEST on Sep 17, 2025, UTC+2)
    cest_tz = pytz.timezone("Europe/Amsterdam")

    # Get current time and today's start in local time (CEST)
    now_local = datetime.now(cest_tz)  # 04:16 PM CEST
    today_local = now_local.replace(
        hour=0, minute=0, second=0, microsecond=0
    )  # 2025-09-17 00:00:00 CEST

    # Set end time to last full hour (14:00:00 CEST = 12:00:00 UTC, since now is 16:16 CEST)
    end_local = now_local.replace(
        minute=0, second=0, microsecond=0
    )  # 2025-09-17 16:00:00 CEST

    # Convert to UTC for API
    utc_tz = pytz.UTC
    start_date_utc = (
        today_local.astimezone(utc_tz).isoformat()[:-6] + ".000Z"
    )  # 2025-09-16T22:00:00.000Z
    end_date_utc = (
        end_local.astimezone(utc_tz).isoformat()[:-6] + ".000Z"
    )  # 2025-09-17T14:00:00.000Z

    print(
        f"Fetching prices for {today_local.strftime('%Y-%m-%d')} (CEST) up to {end_local.strftime('%H:%M:%S CEST')}"
    )
    print(f"API startDate: {start_date_utc}, endDate: {end_date_utc}")

    # Fetch electricity buy prices
    elec_data = fetch_anwb_prices(start_date_utc, end_date_utc, "electricity", "HOUR")
    if elec_data:
        print("\nElectricity Consumption Prices (cents/kWh, CEST):")
        print(f"Interval: {elec_data.get('interval', 'N/A')}")
        for item in elec_data.get("data", []):
            cest_time = utc_to_cest(item["date"])
            markt = item["values"].get("marktprijs", "N/A")
            allin = item["values"].get("allInPrijs", "N/A")
            print(
                f"{cest_time}: Marktprijs = {markt:.2f} cents/kWh, AllInPrijs = {allin:.2f} cents/kWh"
            )


if __name__ == "__main__":
    main()
