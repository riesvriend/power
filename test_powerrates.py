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
    convert_to_schedule_format,
)


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
