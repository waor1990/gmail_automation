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
