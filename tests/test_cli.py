"""
Unit tests for the CLI module
"""

import unittest
import warnings
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime
from zoneinfo import ZoneInfo
from dateutil.parser import UnknownTimezoneWarning
from gmail_automation.cli import (
    parse_email_date,
    parse_header,
    validate_details,
    setup_logging,
    remove_old_logs,
    load_processed_email_ids,
    save_processed_email_ids,
    process_email,
)


class TestCLI(unittest.TestCase):
    """Test cases for CLI functionality"""

    def test_parse_email_date_valid_date(self):
        """Test parsing a valid email date string"""
        date_str = "Wed, 01 Jan 2023 12:00:00 +0000"
        result = parse_email_date(date_str)

        self.assertIsNotNone(result)
        if result is not None:
            self.assertEqual(result.year, 2023)
            self.assertEqual(result.month, 1)
            self.assertEqual(result.day, 1)
            self.assertEqual(result.tzinfo, ZoneInfo("America/Los_Angeles"))
            self.assertEqual(result.hour, 4)

    def test_parse_email_date_invalid_date(self):
        """Test parsing an invalid email date string"""
        date_str = "invalid date string"
        result = parse_email_date(date_str)

        self.assertIsNone(result)

    def test_parse_email_date_no_timezone(self):
        """Test parsing a date string without timezone info"""
        date_str = "Wed, 01 Jan 2023 12:00:00"
        result = parse_email_date(date_str)

        self.assertIsNotNone(result)
        if result is not None:
            self.assertEqual(result.tzinfo, ZoneInfo("America/Los_Angeles"))
            self.assertEqual(result.hour, 12)

    def test_parse_email_date_with_timezone_abbreviation(self):
        """Test parsing a date string with timezone abbreviation"""
        date_str = "Wed, 01 Jan 2023 12:00:00 EDT"
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", UnknownTimezoneWarning)
            result = parse_email_date(date_str)
        self.assertIsNotNone(result)
        if result is not None:
            self.assertEqual(result.tzinfo, ZoneInfo("America/Los_Angeles"))
            self.assertEqual(result.hour, 9)
        self.assertEqual(len(caught), 0)

    def test_parse_header_found(self):
        """Test parsing header when the header is found"""
        headers = [
            {"name": "Subject", "value": "Test Subject"},
            {"name": "From", "value": "test@example.com"},
            {"name": "Date", "value": "Wed, 01 Jan 2023 12:00:00 +0000"},
        ]

        result = parse_header(headers, "subject")
        self.assertEqual(result, "Test Subject")

        result = parse_header(headers, "FROM")  # Test case insensitive
        self.assertEqual(result, "test@example.com")

    def test_parse_header_not_found(self):
        """Test parsing header when the header is not found"""
        headers = [
            {"name": "Subject", "value": "Test Subject"},
            {"name": "From", "value": "test@example.com"},
        ]

        result = parse_header(headers, "Date")
        self.assertIsNone(result)

    def test_validate_details_all_present(self):
        """Test validation when all expected details are present"""
        details = {
            "subject": "Test Subject",
            "date": "2023-01-01",
            "sender": "test@example.com",
        }
        expected_keys = ["subject", "date", "sender"]

        result = validate_details(details, expected_keys)

        self.assertEqual(result["missing_details"], [])
        self.assertEqual(result["available_details"], details)

    def test_validate_details_missing_some(self):
        """Test validation when some details are missing"""
        details = {
            "subject": "Test Subject",
            "date": None,
            "sender": "test@example.com",
        }
        expected_keys = ["subject", "date", "sender"]

        result = validate_details(details, expected_keys)

        self.assertEqual(result["missing_details"], ["date"])
        self.assertEqual(
            result["available_details"],
            {"subject": "Test Subject", "sender": "test@example.com"},
        )

    def test_validate_details_missing_key(self):
        """Test validation when a key is completely missing"""
        details = {"subject": "Test Subject", "sender": "test@example.com"}
        expected_keys = ["subject", "date", "sender"]

        result = validate_details(details, expected_keys)

        self.assertEqual(result["missing_details"], ["date"])
        self.assertEqual(
            result["available_details"],
            {"subject": "Test Subject", "sender": "test@example.com"},
        )

    @patch("gmail_automation.cli.os.path.exists")
    def test_load_processed_email_ids_file_exists(self, mock_exists):
        """Test loading processed email IDs when file exists"""
        mock_exists.return_value = True
        test_ids = ["id1", "id2", "id3"]

        with patch("builtins.open", create=True) as mock_file:
            mock_file.return_value.__enter__.return_value.read.return_value = "\n".join(
                test_ids
            )

            result = load_processed_email_ids("test_path")
            self.assertEqual(result, set(test_ids))

    @patch("gmail_automation.cli.os.path.exists")
    def test_load_processed_email_ids_file_not_exists(self, mock_exists):
        """Test loading processed email IDs when file doesn't exist"""
        mock_exists.return_value = False

        result = load_processed_email_ids("test_path")
        self.assertEqual(result, set())

    def test_save_processed_email_ids(self):
        """Test saving processed email IDs"""
        test_ids = {"id1", "id2", "id3"}

        with patch("builtins.open", create=True) as mock_file:
            mock_write = mock_file.return_value.__enter__.return_value.write

            save_processed_email_ids("test_path", test_ids)

            # Verify that write was called for each ID
            self.assertEqual(mock_write.call_count, len(test_ids))

    @patch("gmail_automation.cli.os.makedirs")
    @patch("logging.FileHandler")
    @patch("logging.StreamHandler")
    @patch("logging.getLogger")
    def test_setup_logging(
        self, mock_get_logger, mock_stream_handler, mock_file_handler, mock_makedirs
    ):
        """Test logging setup"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_logger.hasHandlers.return_value = False

        setup_logging()

        # Verify that logging directory is created
        mock_makedirs.assert_called()

        # Verify that handlers are added to logger
        self.assertEqual(mock_logger.addHandler.call_count, 3)  # info, debug, stream

    @patch("gmail_automation.cli.os.path.exists")
    @patch("builtins.open", create=True)
    @patch("gmail_automation.cli.parser.parse")
    @patch("gmail_automation.cli.datetime")
    def test_remove_old_logs(self, mock_datetime, mock_parse, mock_open, mock_exists):
        """Test removal of old log entries"""
        mock_exists.return_value = True
        mock_now = datetime(2023, 12, 1, tzinfo=ZoneInfo("UTC"))
        mock_datetime.now.return_value = mock_now

        # Mock log content with one old entry and one recent entry
        old_date = datetime(2023, 9, 1, tzinfo=ZoneInfo("UTC"))
        recent_date = datetime(2023, 11, 15, tzinfo=ZoneInfo("UTC"))

        log_lines = [
            f"{old_date.isoformat()} - INFO - Old log entry\n",
            f"{recent_date.isoformat()} - INFO - Recent log entry\n",
        ]

        mock_parse.side_effect = [old_date, recent_date]

        mock_file = mock_open.return_value.__enter__.return_value
        mock_file.readlines.return_value = log_lines

        remove_old_logs("test_log.log")

        # Verify that only the recent entry is written back
        write_calls = [call[0][0] for call in mock_file.write.call_args_list]
        self.assertNotIn(log_lines[0], write_calls)
        self.assertIn(log_lines[1], write_calls)


class TestProcessEmail(unittest.TestCase):
    """Tests for the process_email function"""

    @patch("gmail_automation.cli.modify_message")
    @patch("gmail_automation.cli.get_message_details_cached")
    def test_delete_skip_modify(self, mock_get_details, mock_modify):
        """Emails older than the threshold should be deleted without modification"""
        service = MagicMock()
        users = service.users.return_value
        messages = users.messages.return_value
        messages.delete.return_value.execute.return_value = None

        mock_get_details.return_value = (
            "Old Subject",
            "01/01/2000, 12:00 AM PST",
            "sender@example.com",
            False,
        )

        with patch("logging.info") as mock_logging_info:
            result = process_email(
                service,
                "me",
                "123",
                None,
                None,
                None,
                None,
                "Streaming",
                True,
                30,
                {"Streaming": "label_id"},
                set(),
                set(),
                {},
                {},
                dry_run=False,
            )

        self.assertTrue(result)
        messages.get.assert_not_called()
        mock_modify.assert_not_called()
        messages.delete.assert_called_once_with(userId="me", id="123")
        mock_logging_info.assert_any_call(
            (
                "Deleting email from '%s' with subject '%s' dated '%s' "
                "as it is older than %s days."
            ),
            "sender@example.com",
            "Old Subject",
            "01/01/2000, 12:00 AM PST",
            30,
        )


if __name__ == "__main__":
    unittest.main()
