import pytest

from scripts.dashboard import callbacks as dashboard_callbacks
from scripts.dashboard.analysis import compute_label_differences
from gmail_automation.ignored_rules import normalize_ignored_rules


def test_ignored_emails_excluded_from_diff():
    cfg = {
        "SENDER_TO_LABELS": {},
        "IGNORED_EMAILS": normalize_ignored_rules(
            [
                {
                    "name": "Skip",
                    "senders": ["skip@example.com"],
                    "actions": {"skip_analysis": True, "skip_import": True},
                }
            ]
        ),
    }
    labels = {
        "SENDER_TO_LABELS": {
            "Foo": [{"emails": ["skip@example.com", "keep@example.com"]}]
        }
    }
    diff = compute_label_differences(cfg, labels)
    missing = diff["missing_emails_by_label"]["Foo"]["missing_emails"]
    assert missing == ["keep@example.com"]
    assert diff["comparison_summary"]["total_missing_emails"] == 1


def test_group_helpers_add_and_remove_email():
    rows = [
        {
            "label": "Label",
            "group_index": 0,
            "email": "first@example.com",
            "read_status": True,
            "delete_after_days": None,
        }
    ]
    defaults = {"read_status": False, "delete_after_days": 30}
    updated = dashboard_callbacks._add_email_to_rows(
        rows,
        "Label",
        0,
        "second@example.com",
        defaults,
    )
    assert any(r["email"] == "second@example.com" for r in updated)
    assert updated[-1]["read_status"] is True  # inherited from existing group

    remaining = dashboard_callbacks._remove_email_from_rows(
        updated,
        "Label",
        0,
        "second@example.com",
    )
    assert all(r["email"] != "second@example.com" for r in remaining)


def test_ignored_email_helpers_manage_rows():
    rows = []
    rows = dashboard_callbacks._add_ignored_email(rows)
    assert len(rows) == 1
    with pytest.raises(ValueError):
        dashboard_callbacks._remove_ignored_email(None, 0)
    rows = dashboard_callbacks._remove_ignored_email(rows, 0)
    assert rows == []
