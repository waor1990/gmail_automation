"""Tests for dashboard group operations."""

from scripts.dashboard.group_ops import merge_selected, split_selected


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
