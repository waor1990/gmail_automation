"""
Unit tests for the CLI module
"""

import unittest
import warnings
from unittest.mock import patch, MagicMock
from zoneinfo import ZoneInfo
from dateutil.parser import UnknownTimezoneWarning
from gmail_automation.cli import (
    parse_email_date,
    parse_header,
    validate_details,
    load_processed_email_ids,
    save_processed_email_ids,
    process_email,
    delete_selected_emails,
)
from gmail_automation.ignored_rules import IgnoredRulesEngine, normalize_ignored_rules


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

    def test_load_processed_email_ids_file_exists(self):
        """Test loading processed email IDs when file exists"""
        test_ids = ["id1", "id2", "id3"]

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.read_text", return_value="\n".join(test_ids)),
        ):
            result = load_processed_email_ids("test_path")

        self.assertEqual(result, set(test_ids))

    def test_load_processed_email_ids_file_not_exists(self):
        """Test loading processed email IDs when file doesn't exist"""

        with patch("pathlib.Path.exists", return_value=False):
            result = load_processed_email_ids("test_path")

        self.assertEqual(result, set())

    def test_save_processed_email_ids(self):
        """Test saving processed email IDs"""
        test_ids = {"id1", "id2", "id3"}

        mock_handle = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_handle

        with (
            patch("pathlib.Path.open", return_value=mock_context) as mock_open,
            patch("pathlib.Path.mkdir") as mock_mkdir,
        ):
            save_processed_email_ids("test_path", test_ids)

        mock_mkdir.assert_called_once()
        mock_open.assert_called_once()
        self.assertEqual(mock_handle.write.call_count, len(test_ids))


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

        with patch("gmail_automation.cli.logger.info") as mock_logging_info:
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
                IgnoredRulesEngine.from_config([]),
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


class TestSelectedDeletions(unittest.TestCase):
    def _make_service(self, message_data):
        service = MagicMock()
        users = service.users.return_value
        messages = users.messages.return_value
        get_call = MagicMock()
        get_call.execute.return_value = message_data
        messages.get.return_value = get_call
        delete_call = MagicMock()
        delete_call.execute.return_value = None
        messages.delete.return_value = delete_call
        return service, messages

    def test_delete_selected_requires_confirm(self):
        message = {"labelIds": [], "payload": {"headers": []}}
        service, messages = self._make_service(message)
        engine = IgnoredRulesEngine.from_config([])
        config = {"SELECTED_EMAIL_DELETIONS": [{"id": "msg1"}], "PROTECTED_LABELS": []}

        deleted = delete_selected_emails(
            service,
            "me",
            {},
            config,
            engine,
            dry_run=False,
            confirm=False,
        )

        self.assertFalse(deleted)
        messages.delete.assert_not_called()

    def test_delete_selected_dry_run(self):
        message = {"labelIds": [], "payload": {"headers": []}}
        service, messages = self._make_service(message)
        engine = IgnoredRulesEngine.from_config([])
        config = {"SELECTED_EMAIL_DELETIONS": [{"id": "msg1"}]}

        deleted = delete_selected_emails(
            service,
            "me",
            {},
            config,
            engine,
            dry_run=True,
            confirm=False,
        )

        self.assertTrue(deleted)
        messages.delete.assert_not_called()

    def test_delete_selected_respects_protected_label(self):
        message = {"labelIds": ["Label_Important"], "payload": {"headers": []}}
        service, messages = self._make_service(message)
        engine = IgnoredRulesEngine.from_config([])
        config = {
            "SELECTED_EMAIL_DELETIONS": [{"id": "msg1"}],
            "PROTECTED_LABELS": ["Important"],
        }
        existing_labels = {"Important": "Label_Important"}

        deleted = delete_selected_emails(
            service,
            "me",
            existing_labels,
            config,
            engine,
            dry_run=False,
            confirm=True,
        )

        self.assertFalse(deleted)
        messages.delete.assert_not_called()

    def test_delete_selected_skips_unread_when_required(self):
        message = {"labelIds": ["UNREAD"], "payload": {"headers": []}}
        service, messages = self._make_service(message)
        engine = IgnoredRulesEngine.from_config([])
        config = {"SELECTED_EMAIL_DELETIONS": [{"id": "msg1", "require_read": True}]}

        deleted = delete_selected_emails(
            service,
            "me",
            {},
            config,
            engine,
            dry_run=False,
            confirm=True,
        )

        self.assertFalse(deleted)
        messages.delete.assert_not_called()

    def test_delete_selected_with_rule_and_confirm(self):
        headers = [
            {"name": "Subject", "value": "Ignore me"},
            {"name": "From", "value": "skip@example.com"},
            {"name": "Date", "value": "Wed, 01 Jan 2020 12:00:00 +0000"},
        ]
        message = {"labelIds": [], "payload": {"headers": headers}}
        service, messages = self._make_service(message)
        engine = IgnoredRulesEngine.from_config(
            normalize_ignored_rules(
                [
                    {
                        "name": "Ignore",
                        "senders": ["skip@example.com"],
                        "actions": {
                            "skip_analysis": True,
                            "skip_import": True,
                            "mark_as_read": True,
                            "apply_labels": ["Ignored"],
                        },
                    }
                ]
            )
        )
        config = {
            "SELECTED_EMAIL_DELETIONS": [
                {
                    "id": "msg1",
                    "rule": "Ignore",
                    "reason": "cleanup",
                    "actor": "tester",
                }
            ]
        }
        existing_labels = {"Ignored": "LBL_IGNORED"}

        with patch("gmail_automation.cli.modify_message") as mock_modify:
            deleted = delete_selected_emails(
                service,
                "me",
                existing_labels,
                config,
                engine,
                dry_run=False,
                confirm=True,
            )

        self.assertTrue(deleted)
        mock_modify.assert_called_once()
        messages.delete.assert_called_once()


if __name__ == "__main__":
    unittest.main()
