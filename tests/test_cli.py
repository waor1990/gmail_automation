"""Unit tests for the CLI module."""

import json
import os
import tempfile
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
    process_selected_email_deletions,
    process_deferred_selected_deletions,
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


class TestSelectedEmailDeletions(unittest.TestCase):
    """Tests for selected email deletion workflows."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.data_dir = self.temp_dir.name
        self.existing_labels = {"INBOX": "INBOX", "Important": "Label_Important"}

    @staticmethod
    def _message(unread=True, labels=None):
        label_ids = (
            labels if labels is not None else ["INBOX"] + (["UNREAD"] if unread else [])
        )
        return {
            "id": "msg1",
            "payload": {
                "headers": [
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "Date", "value": "Wed, 01 Jan 2023 12:00:00 +0000"},
                ]
            },
            "labelIds": label_ids,
        }

    def _service_with_messages(self, *message_payloads):
        service = MagicMock()
        users = service.users.return_value
        messages_resource = users.messages.return_value
        messages_resource.get.return_value.execute = MagicMock(
            side_effect=list(message_payloads)
        )
        messages_resource.delete.return_value.execute.return_value = None
        return service

    def test_instant_delete_selected_emails(self):
        service = self._service_with_messages(self._message(unread=False))
        config = {
            "SELECTED_EMAIL_DELETIONS": [
                {
                    "name": "Immediate",
                    "message_ids": ["msg1"],
                    "defer_until_read": False,
                }
            ],
            "PROTECTED_LABELS": [],
        }

        result = process_selected_email_deletions(
            service,
            "me",
            self.existing_labels,
            config,
            self.data_dir,
            lambda *_args, **_kwargs: True,
            dry_run=False,
            actor="tester",
        )

        self.assertTrue(result)
        service.users().messages().delete.assert_called_once_with(
            userId="me", id="msg1"
        )

    def test_deferred_deletion_processed_after_read(self):
        unread_message = self._message(unread=True)
        read_message = self._message(unread=False)
        service = self._service_with_messages(unread_message, read_message)
        config = {
            "SELECTED_EMAIL_DELETIONS": [
                {"name": "Deferred", "message_ids": ["msg1"], "defer_until_read": True}
            ],
            "PROTECTED_LABELS": [],
        }

        result_defer = process_selected_email_deletions(
            service,
            "me",
            self.existing_labels,
            config,
            self.data_dir,
            lambda *_args, **_kwargs: True,
            dry_run=False,
            actor="tester",
        )
        self.assertTrue(result_defer)

        deferred_path = os.path.join(self.data_dir, "deferred_deletions.json")
        self.assertTrue(os.path.exists(deferred_path))
        with open(deferred_path, "r", encoding="utf-8") as handle:
            deferred_state = json.load(handle)
        self.assertIn("msg1", deferred_state)

        result_delete = process_deferred_selected_deletions(
            service,
            "me",
            self.existing_labels,
            config,
            self.data_dir,
            lambda *_args, **_kwargs: True,
            dry_run=False,
            actor="tester",
        )
        self.assertTrue(result_delete)
        service.users().messages().delete.assert_called_once_with(
            userId="me", id="msg1"
        )
        with open(deferred_path, "r", encoding="utf-8") as handle:
            remaining_state = json.load(handle)
        self.assertNotIn("msg1", remaining_state)

    def test_confirmation_required_for_deletion(self):
        service = self._service_with_messages(self._message(unread=False))
        config = {
            "SELECTED_EMAIL_DELETIONS": [
                {
                    "name": "Needs confirmation",
                    "message_ids": ["msg1"],
                    "defer_until_read": False,
                }
            ],
            "PROTECTED_LABELS": [],
        }

        with patch("gmail_automation.cli.logger") as mock_logger:
            result = process_selected_email_deletions(
                service,
                "me",
                self.existing_labels,
                config,
                self.data_dir,
                lambda *_args, **_kwargs: False,
                dry_run=False,
                actor="tester",
            )

        self.assertFalse(result)
        service.users().messages().delete.assert_not_called()
        mock_logger.info.assert_any_call(
            "Deletion not confirmed for message %s under rule '%s'.",
            "msg1",
            "Needs confirmation",
        )

    def test_dry_run_deletion_logs_without_action(self):
        service = self._service_with_messages(self._message(unread=False))
        config = {
            "SELECTED_EMAIL_DELETIONS": [
                {"name": "Dry run", "message_ids": ["msg1"], "defer_until_read": False}
            ],
            "PROTECTED_LABELS": [],
        }

        with patch("gmail_automation.cli.logger") as mock_logger:
            result = process_selected_email_deletions(
                service,
                "me",
                self.existing_labels,
                config,
                self.data_dir,
                lambda *_args, **_kwargs: True,
                dry_run=True,
                actor="tester",
            )

        self.assertTrue(result)
        service.users().messages().delete.assert_not_called()
        dry_run_logs = [
            call for call in mock_logger.info.call_args_list if "Dry run" in str(call)
        ]
        self.assertTrue(dry_run_logs)

    def test_protected_labels_prevent_deletion(self):
        protected_labels = ["Important"]
        service = self._service_with_messages(
            self._message(unread=False, labels=["INBOX", "Label_Important"])
        )
        config = {
            "SELECTED_EMAIL_DELETIONS": [
                {
                    "name": "Protected",
                    "message_ids": ["msg1"],
                    "defer_until_read": False,
                }
            ],
            "PROTECTED_LABELS": protected_labels,
        }

        result = process_selected_email_deletions(
            service,
            "me",
            self.existing_labels,
            config,
            self.data_dir,
            lambda *_args, **_kwargs: True,
            dry_run=False,
            actor="tester",
        )

        self.assertFalse(result)
        service.users().messages().delete.assert_not_called()
        deferred_path = os.path.join(self.data_dir, "deferred_deletions.json")
        self.assertFalse(os.path.exists(deferred_path))


if __name__ == "__main__":
    unittest.main()
