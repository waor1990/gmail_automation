"""Tests for the grouped tree rendering helpers."""

from typing import List

from dash import html

from scripts.dashboard.grouped_tree import render_grouped_tree, toggle_expanded_label


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def test_render_grouped_tree_collapsed_by_default():
    grouped = {"Inbox": {0: ["alice@example.com"]}}

    tree = render_grouped_tree(grouped, expanded_labels=[])

    assert isinstance(tree, html.Ul)
    label_node = _as_list(tree.children)[0]
    header, content = _as_list(label_node.children)

    caret_span = _as_list(header.children)[0]
    assert caret_span.children == "\u25b6"  # ▶
    assert content.style["display"] == "none"


def test_render_grouped_tree_expanded_shows_emails():
    grouped = {
        "Inbox": {
            0: ["alice@example.com", "bob@example.com"],
            1: ["carol@example.com"],
        }
    }

    tree = render_grouped_tree(grouped, expanded_labels=["Inbox"])

    label_node = _as_list(tree.children)[0]
    header, content = _as_list(label_node.children)

    caret_span = _as_list(header.children)[0]
    assert caret_span.children == "\u25bc"  # ▼
    assert content.style["display"] == "block"

    group_list = content.children
    groups = _as_list(group_list.children)
    assert len(groups) == 2

    first_group = groups[0]
    email_list = _as_list(first_group.children)[1]
    emails = _as_list(email_list.children)
    assert len(emails) == 2


def test_toggle_expanded_label_adds_and_removes():
    available = ["Inbox", "Work"]
    expanded: List[str] = []

    expanded = toggle_expanded_label("Inbox", expanded, available)
    assert expanded == ["Inbox"]

    expanded = toggle_expanded_label("Inbox", expanded, available)
    assert expanded == []


def test_toggle_expanded_label_filters_invalid_entries():
    available = ["Inbox"]
    expanded = ["Inbox", "Archive"]

    updated = toggle_expanded_label("Archive", expanded, available)
    assert updated == ["Inbox"]
