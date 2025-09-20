"""Tests for dashboard group operations."""

from scripts.dashboard.group_ops import (
    merge_selected,
    remove_email_from_group,
    split_selected,
)


def test_merge_selected_merges_to_lowest_index():
    rows = [
        {"label": "A", "group_index": 0, "email": "a@example.com"},
        {"label": "A", "group_index": 1, "email": "b@example.com"},
        {"label": "B", "group_index": 0, "email": "c@example.com"},
    ]
    merged = merge_selected(rows, [0, 1])
    assert merged[0]["group_index"] == 0
    assert merged[1]["group_index"] == 0
    assert merged[2]["group_index"] == 0


def test_split_selected_assigns_unique_indices():
    rows = [
        {"label": "A", "group_index": 0, "email": "a@example.com"},
        {"label": "A", "group_index": 0, "email": "b@example.com"},
    ]
    split = split_selected(rows, [0, 1])
    indices = {r["group_index"] for r in split}
    assert indices == {0, 1}


def test_remove_email_from_group_detaches_selected_email():
    rows = [
        {"label": "Work", "group_index": 0, "email": "keep@example.com"},
        {"label": "Work", "group_index": 0, "email": "remove@example.com"},
        {"label": "Personal", "group_index": 1, "email": "friend@example.com"},
    ]

    updated, removed = remove_email_from_group(rows, "Work", 0, "remove@example.com")

    assert removed is True
    assert len(updated) == 2
    assert len(rows) == 3  # original untouched
    emails = [r["email"] for r in updated]
    assert "remove@example.com" not in emails
    assert "keep@example.com" in emails
    assert "friend@example.com" in emails


def test_remove_email_from_group_ignores_non_matching_rows():
    rows = [
        {"label": "Work", "group_index": 0, "email": "keep@example.com"},
        {"label": "Work", "group_index": 0, "email": "remove@example.com"},
    ]

    updated, removed = remove_email_from_group(rows, "Work", 1, "remove@example.com")

    assert removed is False
    assert updated == rows
    assert updated is not rows
