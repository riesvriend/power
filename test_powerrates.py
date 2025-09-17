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

    def test_get_entsoe_api_key_file_exists_with_valid_key(self):
        """Test loading API key when file exists with valid key."""
        test_data = {"api_key": self.test_api_key}

        with patch("builtins.open", mock_open(read_data=json.dumps(test_data))):
            with patch("os.path.exists", return_value=True):
                result = get_entsoe_api_key()
                self.assertEqual(result, self.test_api_key)

    def test_get_entsoe_api_key_file_exists_with_empty_key(self):
        """Test loading API key when file exists but key is empty."""
        test_data = {"api_key": ""}

        with patch("builtins.open", mock_open(read_data=json.dumps(test_data))):
            with patch("os.path.exists", return_value=True):
                result = get_entsoe_api_key()
                self.assertEqual(result, "your_entsoe_api_key_here")  # Should fallback

    def test_get_entsoe_api_key_file_exists_without_api_key_field(self):
        """Test loading API key when file exists but no api_key field."""
        test_data = {"other_field": "value"}

        with patch("builtins.open", mock_open(read_data=json.dumps(test_data))):
            with patch("os.path.exists", return_value=True):
                result = get_entsoe_api_key()
                self.assertEqual(result, "your_entsoe_api_key_here")  # Should fallback

    def test_get_entsoe_api_key_file_does_not_exist(self):
        """Test loading API key when file does not exist."""
        with patch("os.path.exists", return_value=False):
            result = get_entsoe_api_key()
            self.assertEqual(result, "your_entsoe_api_key_here")  # Should fallback

    def test_get_entsoe_api_key_invalid_json(self):
        """Test loading API key when file contains invalid JSON."""
        with patch("builtins.open", mock_open(read_data="invalid json")):
            with patch("os.path.exists", return_value=True):
                with patch(
                    "json.load", side_effect=json.JSONDecodeError("Invalid JSON", "", 0)
                ):
                    result = get_entsoe_api_key()
                    self.assertEqual(
                        result, "your_entsoe_api_key_here"
                    )  # Should fallback

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

    @unittest.skipUnless(
        os.path.exists("entsoe_api_key.json"), "ENTSOE API key file not found"
    )
    def test_entsoe_api_key_format_validation(self):
        """Test that the actual API key has reasonable format."""
        actual_api_key = get_entsoe_api_key()

        # Skip if using placeholder
        if actual_api_key == "your_entsoe_api_key_here":
            self.skipTest("Using placeholder API key - skipping format validation")

        # Basic format validation for ENTSOE API keys
        # ENTSOE API keys are typically UUIDs or long alphanumeric strings
        self.assertIsInstance(actual_api_key, str)
        self.assertGreater(len(actual_api_key), 10, "API key seems too short")
        self.assertLess(len(actual_api_key), 200, "API key seems too long")

        # Should contain only valid characters (alphanumeric, hyphens, underscores)
        import re

        valid_pattern = re.compile(r"^[a-zA-Z0-9\-_]+$")
        self.assertRegex(
            actual_api_key, valid_pattern, "API key contains invalid characters"
        )


class TestDayaheadPrices(unittest.TestCase):
    """Test cases for day-ahead price fetching functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_api_key = "valid_api_key"
        self.test_area_code = AREA_CODE

    def test_get_dayahead_prices_with_placeholder_key(self):
        """Test that placeholder key triggers stub implementation."""
        start = datetime.now(timezone.utc)
        result = get_dayahead_prices(
            "your_entsoe_api_key_here", self.test_area_code, start
        )

        # Should return a dictionary with hourly prices
        self.assertIsInstance(result, dict)
        self.assertGreater(len(result), 0)

        # Check that all values are floats
        for price in result.values():
            self.assertIsInstance(price, float)
            self.assertGreater(price, 0)  # Prices should be positive

    @patch("powerrates.urlopen")
    def test_get_dayahead_prices_with_real_key(self, mock_urlopen):
        """Test the real API call path (mocked)."""
        # Mock the URL response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'<?xml version="1.0"?><Publication_MarketDocument></Publication_MarketDocument>'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        start = datetime.now(timezone.utc)
        end = start + timedelta(hours=2)

        with patch("powerrates.ElementTree") as mock_et:
            mock_root = MagicMock()
            mock_et.fromstring.return_value = mock_root

            # Mock empty XML structure
            mock_root.__iter__.return_value = []

            result = get_dayahead_prices(
                self.test_api_key, self.test_area_code, start, end
            )
            self.assertIsInstance(result, dict)

    def test_get_dayahead_prices_datetime_conversion(self):
        """Test datetime parameter handling."""
        # Test with naive datetime (should convert to UTC)
        naive_dt = datetime(2024, 1, 1, 12, 0, 0)
        result = get_dayahead_prices(
            "your_entsoe_api_key_here", self.test_area_code, naive_dt
        )

        self.assertIsInstance(result, dict)
        self.assertGreater(len(result), 0)

    def test_get_dayahead_prices_none_parameters(self):
        """Test with None start/end parameters."""
        result = get_dayahead_prices(
            "your_entsoe_api_key_here", self.test_area_code, None, None
        )

        self.assertIsInstance(result, dict)
        self.assertGreater(len(result), 0)


class TestUtilityFunctions(unittest.TestCase):
    """Test cases for utility functions."""

    def test_detect_overlapping_periods_no_overlaps(self):
        """Test overlap detection with non-overlapping periods."""
        schedule = [
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
        ]

        result = detect_overlapping_periods(schedule)
        self.assertFalse(result)

    def test_detect_overlapping_periods_with_overlaps(self):
        """Test overlap detection with overlapping periods."""
        schedule = [
            {
                "target": "off_peak",
                "start_seconds": 0,
                "end_seconds": 3600,
                "week_days": [0, 1, 2, 3, 4, 5, 6],
            },
            {
                "target": "peak",
                "start_seconds": 3500,
                "end_seconds": 4000,
                "week_days": [0, 1, 2, 3, 4, 5, 6],
            },  # Overlaps!
        ]

        result = detect_overlapping_periods(schedule)
        self.assertTrue(result)

    def test_convert_to_schedule_format(self):
        """Test TOU periods to schedule format conversion."""
        tou_periods = {
            "OFF_PEAK": [
                {"fromHour": 0, "fromMinute": 0, "toHour": 6, "toMinute": 0},
                {"fromHour": 22, "fromMinute": 0, "toHour": 24, "toMinute": 0},
            ],
            "ON_PEAK": [{"fromHour": 6, "fromMinute": 0, "toHour": 22, "toMinute": 0}],
        }

        result = convert_to_schedule_format(tou_periods)

        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

        for entry in result:
            self.assertIn("target", entry)
            self.assertIn("start_seconds", entry)
            self.assertIn("end_seconds", entry)
            self.assertIn("week_days", entry)


class TestDataValidation(unittest.TestCase):
    """Test cases for data validation and error handling."""

    def test_api_key_file_format_validation(self):
        """Test that API key file follows expected JSON format."""
        # Create a temporary file with valid format
        test_data = {"api_key": "test_key_123"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            temp_file = f.name

        try:
            # Test loading from the temp file
            with patch("powerrates.ENTSOE_API_KEY_FILE", temp_file):
                with patch("os.path.exists", return_value=True):
                    with patch(
                        "builtins.open", mock_open(read_data=json.dumps(test_data))
                    ):
                        result = get_entsoe_api_key()
                        self.assertEqual(result, "test_key_123")
        finally:
            os.unlink(temp_file)

    def test_schedule_format_validation(self):
        """Test that schedule data follows expected format."""
        valid_schedule = [
            {
                "target": "off_peak",
                "start_seconds": 0,
                "end_seconds": 3600,
                "week_days": [0, 1, 2, 3, 4, 5, 6],
            }
        ]

        # Should not raise any exceptions
        result = detect_overlapping_periods(valid_schedule)
        self.assertIsInstance(result, bool)


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)
