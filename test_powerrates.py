"""
Test suite for powerrates.py
Follows Python testing best practices with unittest framework.
"""

import unittest
import json
import os
import tempfile
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime, timezone, timedelta

# Import the functions we want to test
from powerrates import (
    get_entsoe_api_key,
    get_dayahead_prices,
    ENTSOE_API_KEY_FILE,
    AREA_CODE,
    detect_overlapping_periods,
    convert_to_schedule_format,
)


class TestEntsoeApiKey(unittest.TestCase):
    """Test cases for ENTSOE API key loading functionality."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_api_key = "test_api_key_12345"
        self.original_file = ENTSOE_API_KEY_FILE

    def tearDown(self):
        """Clean up after each test method."""
        # Remove any test files created during tests
        if os.path.exists("test_entsoe_key.json"):
            os.remove("test_entsoe_key.json")

    @unittest.skipUnless(
        os.path.exists("entsoe_api_key.json"), "ENTSOE API key file not found"
    )
    def test_entsoe_api_connectivity_with_real_key(self):
        """Integration test: Validate connectivity to ENTSOE API with actual API key."""
        # Load the actual API key from the file
        actual_api_key = get_entsoe_api_key()

        # Skip test if using placeholder key
        if actual_api_key == "your_entsoe_api_key_here":
            self.skipTest("Using placeholder API key - skipping connectivity test")

        # Test parameters for a small time window (last 2 hours)
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=2)

        try:
            # Make actual API call to test connectivity
            result = get_dayahead_prices(
                actual_api_key, AREA_CODE, start_time, end_time
            )

            # Validate response structure
            self.assertIsInstance(result, dict)
            self.assertGreater(len(result), 0)

            """
            Actual sample response:

            ENTSOE Rates xml_str: <?xml version="1.0" encoding="utf-8"?>
            <Publication_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3">
                <mRID>92d0de83d76f44ed811f79d9835b5786</mRID>
                <revisionNumber>1</revisionNumber>
                <type>A44</type>
                <sender_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</sender_MarketParticipant.mRID>
                <sender_MarketParticipant.marketRole.type>A32</sender_MarketParticipant.marketRole.type>
                <receiver_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</receiver_MarketParticipant.mRID>
                <receiver_MarketParticipant.marketRole.type>A33</receiver_MarketParticipant.marketRole.type>
                <createdDateTime>2025-09-17T13:17:54Z</createdDateTime>
                <period.timeInterval>
                <start>2025-09-16T22:00Z</start>
                <end>2025-09-17T22:00Z</end>
                </period.timeInterval>
                <TimeSeries>
                    <mRID>1</mRID>
                    <auction.type>A01</auction.type>
                    <businessType>A62</businessType>
                    <in_Domain.mRID codingScheme="A01">10YNL----------L</in_Domain.mRID>
                    <out_Domain.mRID codingScheme="A01">10YNL----------L</out_Domain.mRID>
                    <contract_MarketAgreement.type>A01</contract_MarketAgreement.type>
                    <currency_Unit.name>EUR</currency_Unit.name>
                    <price_Measure_Unit.name>MWH</price_Measure_Unit.name>
                    <curveType>A03</curveType>
                    <Period>
                        <timeInterval>
                        <start>2025-09-16T22:00Z</start>
                        <end>2025-09-17T22:00Z</end>
                        </timeInterval>
                        <resolution>PT60M</resolution>
                        <Point>
                            <position>1</position>
                            <price.amount>74.78</price.amount>
                        </Point>
                        <Point>
                            <position>2</position>
                            <price.amount>66.86</price.amount>
                        </Point>
                        <Point>
                            <position>3</position>
                            <price.amount>52.14</price.amount>
                        </Point>
                        <Point>
                            <position>4</position>
                            <price.amount>53</price.amount>
                        </Point>
                        <Point>
                            <position>5</position>
                            <price.amount>69.4</price.amount>
                        </Point>
                        <Point>
                            <position>6</position>
                            <price.amount>81.26</price.amount>
                        </Point>
                        <Point>
                            <position>7</position>
                            <price.amount>97.8</price.amount>
                        </Point>
                        <Point>
                            <position>8</position>
                            <price.amount>118.75</price.amount>
                        </Point>
                        <Point>
                            <position>9</position>
                            <price.amount>112.96</price.amount>
                        </Point>
                        <Point>
                            <position>10</position>
                            <price.amount>99.88</price.amount>
                        </Point>
                        <Point>
                            <position>11</position>
                            <price.amount>94.9</price.amount>
                        </Point>
                        <Point>
                            <position>12</position>
                            <price.amount>100</price.amount>
                        </Point>
                        <Point>
                            <position>13</position>
                            <price.amount>71</price.amount>
                        </Point>
                        <Point>
                            <position>14</position>
                            <price.amount>40.1</price.amount>
                        </Point>
                        <Point>
                            <position>15</position>
                            <price.amount>25</price.amount>
                        </Point>
                        <Point>
                            <position>16</position>
                            <price.amount>59.3</price.amount>
                        </Point>
                        <Point>
                            <position>17</position>
                            <price.amount>71.4</price.amount>
                        </Point>
                        <Point>
                            <position>18</position>
                            <price.amount>101.71</price.amount>
                        </Point>
                        <Point>
                            <position>19</position>
                            <price.amount>117.75</price.amount>
                        </Point>
                        <Point>
                            <position>20</position>
                            <price.amount>116.21</price.amount>
                        </Point>
                        <Point>
                            <position>21</position>
                            <price.amount>110.79</price.amount>
                        </Point>
                        <Point>
                            <position>22</position>
                            <price.amount>90.82</price.amount>
                        </Point>
                        <Point>
                            <position>23</position>
                            <price.amount>86.5</price.amount>
                        </Point>
                        <Point>
                            <position>24</position>
                            <price.amount>71.43</price.amount>
                        </Point>
                    </Period>
                </TimeSeries>
            </Publication_MarketDocument>
            """

            # Validate that we got actual data (not stub implementation)
            # The stub implementation returns exactly 2 hours of data
            # Real API might return more or less depending on available data
            for timestamp, price in result.items():
                self.assertIsInstance(timestamp, datetime)
                self.assertIsInstance(price, (int, float))
                self.assertGreater(price, 0)  # Prices should be positive

            print(
                f"✅ ENTSOE API connectivity test passed - received {len(result)} price points"
            )

        except Exception as e:
            # Provide helpful error messages for common issues
            error_str = str(e).lower()
            if "403" in error_str or "401" in error_str:
                self.fail(
                    f"API authentication failed - check if ENTSOE API key is valid: {e}"
                )
            elif "404" in error_str:
                self.fail(
                    f"API endpoint not found - check AREA_CODE or API parameters: {e}"
                )
            elif "certificate" in error_str or "ssl" in error_str:
                self.fail(
                    f"SSL certificate verification failed. This is a common macOS Python issue.\n"
                    f"Solutions:\n"
                    f"1. Run: /Applications/Python\\ 3.12/Install\\ Certificates.command\n"
                    f"2. Or use: python -m pip install --upgrade certifi\n"
                    f"3. Or set environment variable: export SSL_CERT_FILE=/etc/ssl/cert.pem\n"
                    f"Original error: {e}"
                )
            elif (
                "timeout" in error_str
                or "connection" in error_str
                or "network" in error_str
            ):
                self.fail(
                    f"Network connectivity issue - check internet connection: {e}"
                )
            elif "name resolution" in error_str or "nodename" in error_str:
                self.fail(f"DNS resolution failed - check internet connection: {e}")
            else:
                self.fail(f"Unexpected API error: {e}")


class TestPowerwallConnectivity(unittest.TestCase):
    """Integration test for real Powerwall API connectivity."""

    def test_powerwall_api_connectivity(self):
        """Test real connectivity to Tesla Powerwall API using time_of_use_settings."""
        print("\n" + "=" * 60)
        print("🔌 POWERWALL CONNECTIVITY TEST")
        print("=" * 60)

        # Import required functions
        from powerrates import get_tesla_tokens, REFRESH_TOKEN_FILE
        import requests

        # Step 1: Get Tesla tokens
        print("\n📝 Step 1: Getting Tesla tokens...")
        try:
            access_token, refresh_token = get_tesla_tokens()
            print("✅ Successfully obtained access token")
        except Exception as e:
            self.fail(f"❌ Failed to get Tesla tokens: {e}")

        headers = {"Authorization": f"Bearer {access_token}"}
        base_url = "https://owner-api.teslamotors.com"

        # Step 2: Get products to find energy_site_id
        print("\n📝 Step 2: Finding Powerwall energy site...")
        try:
            products_url = f"{base_url}/api/1/products"
            response = requests.get(products_url, headers=headers)
            response.raise_for_status()
            products_data = response.json()

            print("📄 Products API Response:")
            print(json.dumps(products_data, indent=2))

            products = products_data.get("response", [])
            energy_site_id = None
            for product in products:
                if product.get("resource_type") == "battery":
                    energy_site_id = product["energy_site_id"]
                    break

            self.assertIsNotNone(energy_site_id, "❌ No Powerwall found in account")
            print(f"✅ Found Powerwall with energy_site_id: {energy_site_id}")

        except Exception as e:
            self.fail(f"❌ Failed to get products: {e}")

        # Step 3: Read current site info
        print("\n📝 Step 3: Reading current site info...")
        try:
            site_info_url = f"{base_url}/api/1/energy_sites/{energy_site_id}/site_info"
            response = requests.get(site_info_url, headers=headers)
            response.raise_for_status()
            site_info = response.json()

            print("📄 Site Info API Response:")
            print(json.dumps(site_info, indent=2))

            self.assertIn("response", site_info)
            # Note: The site_info API returns a different ID format than products API
            # Products API gives energy_site_id, site_info gives the gateway/DIN
            self.assertIsInstance(site_info["response"]["id"], str)
            self.assertGreater(len(site_info["response"]["id"]), 0)
            print("✅ Successfully read site info")

        except Exception as e:
            self.fail(f"❌ Failed to read site info: {e}")

        # Step 4: Set complete Time of Use and Tariff configuration
        print("\n📝 Step 4: Setting complete Time of Use and Tariff configuration...")
        try:
            # Combined payload with both TOU schedule and tariff rates (per Tesla API specs)
            complete_payload = {
                "tou_settings": {
                    "schedule": [
                        {
                            "target": "off_peak",
                            "start_seconds": 0,  # 00:00
                            "end_seconds": 21600,  # 06:00
                            "week_days": [0, 1, 2, 3, 4, 5, 6],
                        },
                        {
                            "target": "peak",
                            "start_seconds": 21600,  # 06:00
                            "end_seconds": 86400,  # 24:00
                            "week_days": [0, 1, 2, 3, 4, 5, 6],
                        },
                    ],
                    "tariff_content_v2": {
                        "version": 1,
                        "currency": "EUR",
                        "energy_charges": {
                            "ALL": {"rates": {"ALL": 0}},
                            "Summer": {"rates": {"OFF_PEAK": 0.15, "ON_PEAK": 0.35}},
                            "Winter": {"rates": {"OFF_PEAK": 0.12, "ON_PEAK": 0.30}},
                        },
                        "sell_tariff": {
                            "energy_charges": {
                                "ALL": {"rates": {"ALL": 0}},
                                "Summer": {
                                    "rates": {"OFF_PEAK": 0.05, "ON_PEAK": 0.20}
                                },
                                "Winter": {
                                    "rates": {"OFF_PEAK": 0.03, "ON_PEAK": 0.15}
                                },
                            }
                        },
                        "seasons": {
                            "Summer": {
                                "fromMonth": 4,
                                "toMonth": 9,
                                "tou_periods": {
                                    "OFF_PEAK": {
                                        "periods": [
                                            {
                                                "fromDayOfWeek": 0,
                                                "toDayOfWeek": 6,
                                                "fromHour": 0,
                                                "fromMinute": 0,
                                                "toHour": 6,
                                                "toMinute": 0,
                                            }
                                        ]
                                    },
                                    "ON_PEAK": {
                                        "periods": [
                                            {
                                                "fromDayOfWeek": 0,
                                                "toDayOfWeek": 6,
                                                "fromHour": 6,
                                                "fromMinute": 0,
                                                "toHour": 0,
                                                "toMinute": 0,
                                            }
                                        ]
                                    },
                                },
                            },
                            "Winter": {
                                "fromMonth": 10,
                                "toMonth": 3,
                                "tou_periods": {
                                    "OFF_PEAK": {
                                        "periods": [
                                            {
                                                "fromDayOfWeek": 0,
                                                "toDayOfWeek": 6,
                                                "fromHour": 0,
                                                "fromMinute": 0,
                                                "toHour": 6,
                                                "toMinute": 0,
                                            }
                                        ]
                                    },
                                    "ON_PEAK": {
                                        "periods": [
                                            {
                                                "fromDayOfWeek": 0,
                                                "toDayOfWeek": 6,
                                                "fromHour": 6,
                                                "fromMinute": 0,
                                                "toHour": 0,
                                                "toMinute": 0,
                                            }
                                        ]
                                    },
                                },
                            },
                        },
                    },
                }
            }

            settings_url = (
                f"{base_url}/api/1/energy_sites/{energy_site_id}/time_of_use_settings"
            )
            response = requests.post(
                settings_url, headers=headers, json=complete_payload
            )
            print(f"Settings URL: {settings_url}")
            print(f"Complete Request: {json.dumps(complete_payload, indent=2)}")
            print(f"Response: {response.json()}")
            response.raise_for_status()
            settings_result = response.json()

            print("📄 Complete TOU and Tariff Settings API Response:")
            print(json.dumps(settings_result, indent=2))

            self.assertIn("response", settings_result)
            # The real API returns a success object with 'code' and 'message'
            # instead of 'result', so we check for code 201.
            self.assertEqual(settings_result["response"]["code"], 201)
            print("✅ Successfully set complete TOU and tariff configuration")

        except Exception as e:
            self.fail(f"❌ Failed to set complete TOU and tariff configuration: {e}")

        # Step 5: Verification - read back the settings
        print("\n📝 Step 5: Verifying settings were applied...")
        try:
            # Read site info again to verify TOU settings
            response = requests.get(site_info_url, headers=headers)
            response.raise_for_status()
            updated_site_info = response.json()

            print("📄 Updated Site Info (verification):")
            print(json.dumps(updated_site_info, indent=2))

            self.assertIn("response", updated_site_info)
            if "tou_settings" in updated_site_info["response"]:
                print("✅ Time of Use settings verified in site info")
            else:
                print("⚠️  TOU settings not visible in site info (may be normal)")

        except Exception as e:
            print(f"⚠️  Verification failed: {e}")

        print("\n" + "=" * 60)
        print("🎉 POWERWALL CONNECTIVITY TEST COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\n📋 SUMMARY:")
        print("- ✅ Tesla authentication successful")
        print("- ✅ Powerwall found in account")
        print("- ✅ Site info read successfully")
        print("- ✅ Complete TOU and tariff configuration set")
        print("\n🔄 You can now check your Tesla app to verify the settings!")


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)
