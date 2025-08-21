"""
Unit tests for the config module
"""

import unittest
import json
import time
from unittest.mock import patch, mock_open
from gmail_automation.config import (
    validate_and_normalize_config,
    load_configuration,
    unix_to_readable,
    get_last_run_time,
    update_last_run_time,
)


class TestConfig(unittest.TestCase):
    """Test cases for configuration handling"""

    def test_validate_and_normalize_config_boolean_normalization(self):
        """Test that string boolean values are normalized to actual booleans"""
        config = {
            "SENDER_TO_LABELS": {
                "test_category": [
                    {"read_status": "true", "delete_after_days": "30"},
                    {"read_status": "false", "delete_after_days": None},
                    {"read_status": "True", "delete_after_days": "invalid"},
                ]
            }
        }

        normalized = validate_and_normalize_config(config)

        rules = normalized["SENDER_TO_LABELS"]["test_category"]
        self.assertTrue(rules[0]["read_status"])
        self.assertFalse(rules[1]["read_status"])
        self.assertTrue(rules[2]["read_status"])

        # Check delete_after_days normalization
        self.assertEqual(rules[0]["delete_after_days"], 30)
        self.assertEqual(rules[1]["delete_after_days"], float("inf"))
        self.assertEqual(rules[2]["delete_after_days"], float("inf"))

    def test_validate_and_normalize_config_empty_config(self):
        """Test handling of empty configuration"""
        config = {}
        normalized = validate_and_normalize_config(config)
        self.assertEqual(normalized, {})

    def test_unix_to_readable(self):
        """Test conversion of Unix timestamp to readable format"""
        # Test with a known timestamp (2023-01-01 00:00:00 UTC)
        timestamp = 1672531200
        readable = unix_to_readable(timestamp)
        self.assertIsInstance(readable, str)
        self.assertIn("2023", readable)

    def test_unix_to_readable_invalid_timestamp(self):
        """Test handling of invalid timestamp"""
        result = unix_to_readable("invalid")
        self.assertEqual(result, "Invalid timestamp")

        result = unix_to_readable(None)
        self.assertEqual(result, "Invalid timestamp")

    @patch("gmail_automation.config.os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_get_last_run_time_file_exists(self, mock_file, mock_exists):
        """Test getting last run time when file exists"""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = "1672531200"

        result = get_last_run_time()
        self.assertEqual(result, 1672531200.0)

    @patch("gmail_automation.config.os.path.exists")
    def test_get_last_run_time_file_not_exists(self, mock_exists):
        """Test getting last run time when file doesn't exist"""
        mock_exists.return_value = False

        result = get_last_run_time()
        expected = time.time() - (365 * 24 * 60 * 60)
        self.assertAlmostEqual(result, expected, delta=5)

    @patch("builtins.open", new_callable=mock_open)
    @patch("gmail_automation.config.os.makedirs")
    def test_update_last_run_time(self, mock_makedirs, mock_file):
        """Test updating last run time"""
        timestamp = 1672531200.0

        update_last_run_time(timestamp)

        mock_makedirs.assert_called_once()
        mock_file.assert_called_once()
        mock_file().write.assert_called_once_with(str(timestamp))

    @patch("gmail_automation.config.os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_configuration_success(self, mock_file, mock_exists):
        """Test successful configuration loading"""
        mock_exists.return_value = True
        test_config = {"SENDER_TO_LABELS": {"test": []}}
        mock_file.return_value.read.return_value = json.dumps(test_config)

        with patch("json.load", return_value=test_config):
            result = load_configuration()
            self.assertEqual(result, test_config)

    @patch("gmail_automation.config.os.path.exists")
    def test_load_configuration_file_not_exists(self, mock_exists):
        """Test configuration loading when file doesn't exist"""
        mock_exists.return_value = False

        result = load_configuration()
        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()
