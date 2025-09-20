"""Tests for the SENDER_TO_LABELS label filter helpers."""

from scripts.dashboard.callbacks import (
    _build_label_filter_query,
    _label_filter_options,
    _sanitize_label_filter_value,
)


def test_label_filter_options_sorted_and_unique():
    rows = [
        {"label": "Work", "email": "a@example.com"},
        {"label": "Personal", "email": "b@example.com"},
        {"label": "work", "email": "c@example.com"},
        {"label": "", "email": "d@example.com"},
        {"label": None, "email": "e@example.com"},
    ]

    options = _label_filter_options(rows)

    assert options == [
        {"label": "Personal", "value": "Personal"},
        {"label": "Work", "value": "Work"},
        {"label": "work", "value": "work"},
    ]


def test_label_filter_value_invalidated_when_missing():
    options = [
        {"label": "Work", "value": "Work"},
        {"label": "Personal", "value": "Personal"},
    ]

    assert _sanitize_label_filter_value(options, "Work") == "Work"
    assert _sanitize_label_filter_value(options, "Unknown") is None


def test_label_filter_query_generation():
    assert _build_label_filter_query("Work") == '{label} = "Work"'
    assert _build_label_filter_query(None) == ""
    assert _build_label_filter_query('Foo "Bar"') == '{label} = "Foo \\"Bar\\""'
