import json
import os
import random
import ssl
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen
from xml.etree import ElementTree

# Placeholders
ENTSOE_API_KEY_FILE = "entsoe_api_key.json"
AREA_CODE = "10YNL----------L"  # For Netherlands
BUY_FEE = 0.05  # Additional fee for buy rate in EUR/kWh (adjust as needed, e.g., taxes)
SELL_FEE = -0.05  # Adjustment for sell rate in EUR/kWh (e.g., -fee)


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
        print(f"ENTSOE Rates xml_str: {xml_str}")
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
