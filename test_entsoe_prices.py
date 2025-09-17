import unittest
import os
from datetime import datetime, timezone, timedelta

# Import the functions we want to test
from entsoe_prices import (
    get_entsoe_api_key,
    get_dayahead_prices,
    ENTSOE_API_KEY_FILE,
    AREA_CODE,
)


class TestEntsoePrices(unittest.TestCase):
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

            # Validate that we got actual data (not stub implementation)
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


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)
