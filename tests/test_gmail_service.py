"""
Unit tests for the Gmail service module
"""

import unittest
from unittest.mock import patch, Mock
from gmail_automation.gmail_service import (
    get_existing_labels_cached,
    batch_fetch_messages,
    modify_message,
)


class TestGmailService(unittest.TestCase):
    """Test cases for Gmail service functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_service = Mock()
        self.user_id = "test_user@example.com"

    def test_get_existing_labels_cached_first_call(self):
        """Test getting existing labels on first call (no cache)"""
        mock_labels_response = {
            "labels": [
                {"id": "INBOX", "name": "INBOX"},
                {"id": "SENT", "name": "SENT"},
                {"id": "Label_1", "name": "Test Label"},
            ]
        }

        self.mock_service.users().labels().list().execute.return_value = (
            mock_labels_response
        )

        result = get_existing_labels_cached(self.mock_service)

        expected = {"INBOX": "INBOX", "SENT": "SENT", "Test Label": "Label_1"}
        self.assertEqual(result, expected)

    def test_get_existing_labels_cached_subsequent_call(self):
        """Test getting existing labels on subsequent call (from cache)"""
        # First call to populate cache
        mock_labels_response = {
            "labels": [
                {"id": "INBOX", "name": "INBOX"},
                {"id": "Label_1", "name": "Test Label"},
            ]
        }

        self.mock_service.users().labels().list().execute.return_value = (
            mock_labels_response
        )

        # Clear any existing cache
        if hasattr(get_existing_labels_cached, "cache"):
            delattr(get_existing_labels_cached, "cache")

        # First call
        result1 = get_existing_labels_cached(self.mock_service)

        # Second call should use cache (service shouldn't be called again)
        result2 = get_existing_labels_cached(self.mock_service)

        self.assertEqual(result1, result2)
        # Service should only be called once
        self.assertEqual(
            self.mock_service.users().labels().list().execute.call_count, 1
        )

    def test_batch_fetch_messages(self):
        """Test batch fetching of messages"""
        message_ids = ["msg1", "msg2", "msg3"]

        # Mock responses for each message
        mock_responses = [
            {"id": "msg1", "payload": {"headers": []}},
            {"id": "msg2", "payload": {"headers": []}},
            {"id": "msg3", "payload": {"headers": []}},
        ]

        self.mock_service.users().messages().get().execute.side_effect = mock_responses

        result = batch_fetch_messages(self.mock_service, self.user_id, message_ids)

        self.assertEqual(len(result), 3)
        self.assertEqual(result["msg1"]["id"], "msg1")
        self.assertEqual(result["msg2"]["id"], "msg2")
        self.assertEqual(result["msg3"]["id"], "msg3")

    def test_batch_fetch_messages_with_error(self):
        """Test batch fetching messages when some requests fail"""
        message_ids = ["msg1", "msg2", "msg3"]

        # Mock responses where one fails
        def mock_execute():
            responses = [
                {"id": "msg1", "payload": {"headers": []}},
                Exception("API Error"),  # This will cause an error
                {"id": "msg3", "payload": {"headers": []}},
            ]
            for response in responses:
                if isinstance(response, Exception):
                    raise response
                yield response

        mock_gen = mock_execute()
        self.mock_service.users().messages().get().execute.side_effect = mock_gen

        # Should handle errors gracefully and continue with other messages
        with patch("logging.error"):  # Suppress error logging for test
            result = batch_fetch_messages(self.mock_service, self.user_id, message_ids)

        # Should return available messages, skipping the failed one
        self.assertIsInstance(result, dict)

    def test_modify_message_add_labels(self):
        """Test modifying message to add labels"""
        msg_id = "test_message"
        labels_to_add = ["LABEL1", "LABEL2"]
        labels_to_remove = []

        mock_response = {"id": msg_id, "labelIds": labels_to_add}
        self.mock_service.users().messages().modify().execute.return_value = (
            mock_response
        )

        result = modify_message(
            self.mock_service,
            self.user_id,
            msg_id,
            labels_to_add,
            labels_to_remove,
            False,  # mark_read
        )

        self.assertEqual(result, mock_response)

        # Verify the correct API call was made
        self.mock_service.users().messages().modify.assert_called_once_with(
            userId=self.user_id,
            id=msg_id,
            body={"addLabelIds": labels_to_add, "removeLabelIds": labels_to_remove},
        )

    def test_modify_message_remove_labels(self):
        """Test modifying message to remove labels"""
        msg_id = "test_message"
        labels_to_add = []
        labels_to_remove = ["UNREAD", "SPAM"]

        mock_response = {"id": msg_id, "labelIds": ["INBOX"]}
        self.mock_service.users().messages().modify().execute.return_value = (
            mock_response
        )

        result = modify_message(
            self.mock_service,
            self.user_id,
            msg_id,
            labels_to_add,
            labels_to_remove,
            False,  # mark_read
        )

        self.assertEqual(result, mock_response)

        # Verify the correct API call was made
        self.mock_service.users().messages().modify.assert_called_once_with(
            userId=self.user_id,
            id=msg_id,
            body={"addLabelIds": labels_to_add, "removeLabelIds": labels_to_remove},
        )

    def test_modify_message_api_error(self):
        """Test handling of API errors during message modification"""
        msg_id = "test_message"
        labels_to_add = ["LABEL1"]
        labels_to_remove = []

        # Mock an API error
        from googleapiclient.errors import HttpError

        mock_error = HttpError(Mock(status=400), b"Bad Request")
        self.mock_service.users().messages().modify().execute.side_effect = mock_error

        with patch("logging.error"):  # Suppress error logging for test
            result = modify_message(
                self.mock_service,
                self.user_id,
                msg_id,
                labels_to_add,
                labels_to_remove,
                False,  # mark_read
            )

        # Should return None on error
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
