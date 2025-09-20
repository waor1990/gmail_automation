from unittest.mock import Mock, patch

import pytest

from gmail_automation.cli import process_email
from gmail_automation.ignored_rules import IgnoredRulesEngine, normalize_ignored_rules


def _make_service():
    service = Mock()
    users = Mock()
    messages = Mock()
    delete_call = Mock()
    delete_call.execute = Mock()
    messages.delete.return_value = delete_call
    get_call = Mock()
    get_call.execute.return_value = {"labelIds": []}
    messages.get.return_value = get_call
    users.messages.return_value = messages
    service.users.return_value = users
    return service, messages


@pytest.fixture
def message_details():
    return (
        "Subject",
        "01/01/2000, 12:00 AM PST",
        "Sender <skip@example.com>",
        True,
    )


def _run_process_email(
    service,
    ignored_rules,
    existing_labels,
    message_details,
    delete_after_days=None,
    dry_run=False,
):
    current_run = set()
    processed = set()
    with patch(
        "gmail_automation.cli.get_message_details_cached", return_value=message_details
    ):
        return (
            process_email(
                service,
                "me",
                "msg1",
                message_details[0],
                message_details[1],
                message_details[2],
                message_details[3],
                "Label",
                False,
                delete_after_days,
                ignored_rules,
                existing_labels,
                current_run,
                processed,
                {},
                {},
                dry_run=dry_run,
            ),
            current_run,
            processed,
        )


def test_ignore_rule_mark_read_apply_labels_archive(caplog, message_details):
    service, messages = _make_service()
    rules = normalize_ignored_rules(
        [
            {
                "name": "Ignore",
                "senders": ["skip@example.com"],
                "actions": {
                    "skip_analysis": True,
                    "skip_import": True,
                    "mark_as_read": True,
                    "apply_labels": ["Ignored"],
                    "archive": True,
                },
            }
        ]
    )
    engine = IgnoredRulesEngine.from_config(rules)
    existing_labels = {"Ignored": "LBL_IGNORED"}

    with (
        patch("gmail_automation.cli.modify_message") as mock_modify,
        caplog.at_level("INFO"),
    ):
        handled, current_run, processed = _run_process_email(
            service, engine, existing_labels, message_details
        )

    assert handled is True
    mock_modify.assert_called_once()
    args = mock_modify.call_args[0]
    assert args[3] == ["LBL_IGNORED"]
    assert args[4] == ["INBOX"]
    assert args[5] is True
    messages.delete.assert_not_called()
    assert processed == {"msg1"}
    assert "applied to" in caplog.text
    assert "applied labels" in caplog.text
    assert "archived" in caplog.text
    assert "marked as read" in caplog.text
    assert "flags: skip_analysis, skip_import" in caplog.text


def test_ignore_rule_delete_immediate(caplog, message_details):
    service, messages = _make_service()
    rules = normalize_ignored_rules(
        [
            {
                "name": "Delete",
                "senders": ["skip@example.com"],
                "actions": {"delete_after_days": 0},
            }
        ]
    )
    engine = IgnoredRulesEngine.from_config(rules)

    with (
        patch("gmail_automation.cli.modify_message") as mock_modify,
        caplog.at_level("INFO"),
    ):
        handled, current_run, processed = _run_process_email(
            service, engine, {}, message_details
        )

    assert handled is True
    mock_modify.assert_not_called()
    messages.delete.assert_called_once()
    messages.delete.return_value.execute.assert_called_once()
    assert processed == {"msg1"}
    assert "delete (immediate)" in caplog.text


def test_ignore_rule_delete_after_threshold(caplog):
    service, messages = _make_service()
    # Use a recent date to verify no deletion occurs
    fresh_details = ("Subject", "01/01/2099, 12:00 AM PST", "skip@example.com", True)
    rules = normalize_ignored_rules(
        [
            {
                "name": "Delete",
                "senders": ["skip@example.com"],
                "actions": {"delete_after_days": 30},
            }
        ]
    )
    engine = IgnoredRulesEngine.from_config(rules)

    with (
        patch("gmail_automation.cli.modify_message") as mock_modify,
        caplog.at_level("INFO"),
    ):
        handled, current_run, processed = _run_process_email(
            service,
            engine,
            {},
            fresh_details,
        )

    assert handled is True
    mock_modify.assert_not_called()
    messages.delete.assert_not_called()
    assert processed == {"msg1"}
    assert "no pipeline actions" in caplog.text
