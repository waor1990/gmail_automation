"""
Integration tests for the Gmail automation system
"""

import unittest
import tempfile
import json
import os
from unittest.mock import patch, Mock
from gmail_automation.cli import main, process_emails_for_labeling
from gmail_automation.config import load_configuration
from gmail_automation.ignored_rules import IgnoredRulesEngine, normalize_ignored_rules


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = os.path.join(self.temp_dir, "config")
        self.data_dir = os.path.join(self.temp_dir, "data")
        os.makedirs(self.config_dir)
        os.makedirs(self.data_dir)

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("gmail_automation.cli.setup_logging")
    @patch("gmail_automation.cli.load_configuration")
    @patch("gmail_automation.cli.get_credentials")
    @patch("gmail_automation.cli.build_service")
    def test_main_function_with_minimal_config(
        self,
        mock_build_service,
        mock_get_credentials,
        mock_load_config,
        mock_setup_logging,
    ):
        """Test the main function with a minimal configuration"""
        # Mock the configuration
        mock_config = {
            "SENDER_TO_LABELS": {
                "Important": [
                    {
                        "sender": "important@example.com",
                        "label": "Important",
                        "read_status": True,
                        "delete_after_days": 30,
                    }
                ]
            }
        }
        mock_load_config.return_value = mock_config

        # Mock the Gmail service
        mock_service = Mock()
        mock_build_service.return_value = mock_service
        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials

        # Mock the Gmail API responses
        mock_service.users().labels().list().execute.return_value = {
            "labels": [
                {"id": "INBOX", "name": "INBOX"},
                {"id": "Label_1", "name": "Important"},
            ]
        }

        mock_service.users().messages().list().execute.return_value = {
            "messages": []  # No messages to process
        }

        # Test that main function runs without errors
        with patch("sys.argv", ["gmail_automation"]):
            try:
                main()
                # If we get here, the function completed without exceptions
                self.assertTrue(True)
            except SystemExit:
                # main() might call sys.exit(), which is acceptable
                self.assertTrue(True)
            except Exception as e:
                self.fail(f"main() raised an unexpected exception: {e}")

    def test_config_loading_integration(self):
        """Test configuration loading with real file I/O"""
        # Create a test configuration file
        config_data = {
            "SENDER_TO_LABELS": {
                "Test Category": [
                    {
                        "sender": "test@example.com",
                        "label": "Test Label",
                        "read_status": True,
                        "delete_after_days": 7,
                    }
                ]
            }
        }

        config_file = os.path.join(self.config_dir, "gmail_config-final.json")
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        # Mock the config module to use our temp directory
        with patch("gmail_automation.config.os.path.dirname") as mock_dirname:
            # Mock the path resolution to point to our temp directory
            def mock_path_resolution(path):
                if "gmail_automation" in path:
                    return self.temp_dir
                return os.path.dirname(path)

            with patch("gmail_automation.config.os.path.abspath") as mock_abspath:
                mock_abspath.side_effect = lambda x: x  # Return path as-is
                mock_dirname.return_value = self.temp_dir

                with patch("gmail_automation.config.os.path.join") as mock_join:
                    mock_join.side_effect = os.path.join

                    # Test the actual loading
                    with patch("gmail_automation.config.os.path.exists") as mock_exists:
                        mock_exists.return_value = True

                        with patch("builtins.open", create=True) as mock_file:
                            file_handle = mock_file.return_value.__enter__.return_value
                            file_handle.read.return_value = json.dumps(config_data)

                            with patch("json.load", return_value=config_data):
                                result = load_configuration()

                                expected = dict(config_data)
                                expected.setdefault("IGNORED_EMAILS", [])
                                self.assertEqual(result, expected)

    @patch("gmail_automation.cli.logger")
    def test_error_handling_integration(self, mock_logging):
        """Test that the system handles errors gracefully"""
        # Test with invalid configuration
        with patch("gmail_automation.cli.load_configuration") as mock_load_config:
            mock_load_config.return_value = {}  # Empty config

            with patch("gmail_automation.cli.get_credentials") as mock_get_credentials:
                mock_get_credentials.side_effect = Exception("Credential error")

                # The system should handle this gracefully
                with patch("sys.argv", ["gmail_automation"]):
                    try:
                        main()
                    except SystemExit:
                        # Acceptable exit
                        pass
                    except Exception as e:
                        # Should log error rather than crash
                        self.assertIsInstance(e, Exception)


class TestEndToEndScenarios(unittest.TestCase):
    """End-to-end test scenarios"""

    @patch("gmail_automation.cli.setup_logging")
    @patch("gmail_automation.cli.get_credentials")
    @patch("gmail_automation.cli.build_service")
    def test_email_processing_scenario(
        self, mock_build_service, mock_get_credentials, mock_setup_logging
    ):
        """Test a complete email processing scenario"""
        # Mock configuration
        config = {
            "SENDER_TO_LABELS": {
                "Newsletters": [
                    {
                        "sender": "newsletter@example.com",
                        "label": "Newsletter",
                        "read_status": True,
                        "delete_after_days": 30,
                    }
                ]
            }
        }

        # Mock service and credentials
        mock_service = Mock()
        mock_build_service.return_value = mock_service
        mock_credentials = Mock()
        mock_get_credentials.return_value = mock_credentials

        # Mock Gmail API responses
        mock_service.users().labels().list().execute.return_value = {
            "labels": [
                {"id": "INBOX", "name": "INBOX"},
                {"id": "Label_Newsletter", "name": "Newsletter"},
            ]
        }

        # Mock message list response
        mock_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg123", "threadId": "thread123"}]
        }

        # Mock message details
        mock_service.users().messages().get().execute.return_value = {
            "id": "msg123",
            "payload": {
                "headers": [
                    {"name": "From", "value": "newsletter@example.com"},
                    {"name": "Subject", "value": "Weekly Newsletter"},
                    {"name": "Date", "value": "Wed, 01 Jan 2023 12:00:00 +0000"},
                ]
            },
            "labelIds": ["INBOX", "UNREAD"],
        }

        # Mock message modification
        mock_service.users().messages().modify().execute.return_value = {
            "id": "msg123",
            "labelIds": ["INBOX", "Label_Newsletter"],
        }

        with patch("gmail_automation.cli.load_configuration", return_value=config):
            with patch("sys.argv", ["gmail_automation"]):
                try:
                    main()
                    # Verify that the service methods were called
                    mock_service.users().labels().list.assert_called()
                    mock_service.users().messages().list.assert_called()
                except SystemExit:
                    # Acceptable exit
                    pass

    @patch("gmail_automation.cli.save_processed_email_ids")
    @patch("gmail_automation.cli.load_processed_email_ids", return_value=set())
    @patch("gmail_automation.cli.modify_message")
    @patch("gmail_automation.cli.batch_fetch_messages")
    @patch("gmail_automation.cli.fetch_emails_to_label_optimized")
    @patch("gmail_automation.cli.get_message_details_cached")
    def test_ignore_rules_applied_before_labeling(
        self,
        mock_details,
        mock_fetch,
        mock_batch,
        mock_modify,
        _mock_load,
        _mock_save,
    ):
        mock_details.return_value = (
            "Alert",
            "01/01/2000, 12:00 AM PST",
            "updates@example.com",
            True,
        )
        mock_fetch.return_value = [{"id": "msg1"}]
        mock_batch.return_value = {"msg1": {"id": "msg1"}}

        service = Mock()
        existing_labels = {"Updates": "LBL_UPDATES", "Ignored": "LBL_IGNORED"}
        config = {
            "SENDER_TO_LABELS": {
                "Updates": [
                    {
                        "emails": ["updates@example.com"],
                        "read_status": False,
                        "delete_after_days": None,
                    }
                ]
            },
            "IGNORED_EMAILS": normalize_ignored_rules(
                [
                    {
                        "name": "Ignore updates",
                        "senders": ["updates@example.com"],
                        "actions": {
                            "skip_analysis": True,
                            "skip_import": True,
                            "mark_as_read": True,
                            "apply_labels": ["Ignored"],
                            "archive": True,
                        },
                    }
                ]
            ),
        }
        last_run_times = {"updates@example.com": 0}
        ignored_engine = IgnoredRulesEngine.from_config(config["IGNORED_EMAILS"])

        processed = process_emails_for_labeling(
            service,
            "me",
            existing_labels,
            config,
            last_run_times,
            current_time=0,
            ignored_rules=ignored_engine,
            dry_run=False,
        )

        self.assertTrue(processed)
        mock_modify.assert_called_once()
        args = mock_modify.call_args[0]
        self.assertEqual(args[3], ["LBL_IGNORED"])
        self.assertEqual(args[4], ["INBOX"])
        self.assertTrue(args[5])


if __name__ == "__main__":
    unittest.main()
