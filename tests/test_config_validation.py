import pytest

from gmail_automation.config import validate_and_normalize_config


def test_validate_config_rejects_invalid_ignored_rule():
    config = {"SENDER_TO_LABELS": {}, "IGNORED_EMAILS": [{"name": "bad"}]}
    with pytest.raises(ValueError):
        validate_and_normalize_config(config)


def test_validate_config_normalizes_ignored_rules():
    config = {
        "SENDER_TO_LABELS": {},
        "IGNORED_EMAILS": [
            {
                "name": "Alerts",
                "senders": ["alert@example.com"],
                "actions": {"mark_as_read": True, "archive": True},
            }
        ],
    }
    normalized = validate_and_normalize_config(config)
    assert normalized["IGNORED_EMAILS"][0]["actions"]["skip_analysis"] is False
    assert normalized["IGNORED_EMAILS"][0]["actions"]["archive"] is True


def test_validate_config_normalizes_protected_labels():
    config = {
        "SENDER_TO_LABELS": {},
        "PROTECTED_LABELS": ["  Keep ", "Keep", "Starred"],
    }
    normalized = validate_and_normalize_config(config)
    assert normalized["PROTECTED_LABELS"] == ["Keep", "Starred"]


def test_validate_config_normalizes_selected_deletions():
    config = {
        "SENDER_TO_LABELS": {},
        "SELECTED_EMAIL_DELETIONS": [
            {
                "id": " msg1 ",
                "require_read": "true",
                "label": "Inbox",
                "reason": " cleanup ",
                "actor": " tester ",
            },
            "msg2",
        ],
    }
    normalized = validate_and_normalize_config(config)
    first = normalized["SELECTED_EMAIL_DELETIONS"][0]
    assert first == {
        "id": "msg1",
        "thread_id": None,
        "label": "Inbox",
        "require_read": True,
        "actor": "tester",
        "reason": "cleanup",
        "rule": None,
    }
    second = normalized["SELECTED_EMAIL_DELETIONS"][1]
    assert second["id"] == "msg2"


def test_validate_config_rejects_selected_deletion_without_id():
    config = {"SENDER_TO_LABELS": {}, "SELECTED_EMAIL_DELETIONS": [{}]}
    with pytest.raises(ValueError):
        validate_and_normalize_config(config)
