import pytest

from scripts.dashboard.analysis import compute_label_differences
from scripts.dashboard.callbacks import (
    _add_ignored_email,
    _remove_ignored_emails,
)


def test_ignored_emails_excluded_from_diff():
    cfg = {"SENDER_TO_LABELS": {}, "IGNORED_EMAILS": ["skip@example.com"]}
    labels = {
        "SENDER_TO_LABELS": {
            "Foo": [{"emails": ["skip@example.com", "keep@example.com"]}]
        }
    }
    diff = compute_label_differences(cfg, labels)
    missing = diff["missing_emails_by_label"]["Foo"]["missing_emails"]
    assert missing == ["keep@example.com"]
    assert diff["comparison_summary"]["total_missing_emails"] == 1


def test_add_ignored_email_appends_and_sorts():
    cfg = {
        "SENDER_TO_LABELS": {},
        "IGNORED_EMAILS": ["skip@example.com"],
    }
    updated, emails, added = _add_ignored_email(cfg, "New@Example.com ")
    assert added == "new@example.com"
    assert emails == ["new@example.com", "skip@example.com"]
    assert updated["IGNORED_EMAILS"] == emails
    # Original config should remain unchanged
    assert cfg["IGNORED_EMAILS"] == ["skip@example.com"]


def test_remove_ignored_email_deletes_selected_entries():
    cfg = {
        "SENDER_TO_LABELS": {},
        "IGNORED_EMAILS": ["keep@example.com", "skip@example.com"],
    }
    updated, remaining, removed = _remove_ignored_emails(cfg, ["skip@example.com"])
    assert removed == ["skip@example.com"]
    assert remaining == ["keep@example.com"]
    assert updated["IGNORED_EMAILS"] == ["keep@example.com"]


def test_add_ignored_email_rejects_invalid_entries():
    cfg = {"SENDER_TO_LABELS": {}, "IGNORED_EMAILS": []}
    with pytest.raises(ValueError):
        _add_ignored_email(cfg, "not-an-email")
