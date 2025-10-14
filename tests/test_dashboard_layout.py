"""Assertions covering the Dash layout composition."""

from __future__ import annotations

from scripts.dashboard.layout import make_layout


def _find_component_by_id(component, target_id: str):
    """Recursively search a Dash component tree for the given ``target_id``."""

    if getattr(component, "id", None) == target_id:
        return component

    children = getattr(component, "children", None)
    if not children:
        return None

    if not isinstance(children, (list, tuple)):
        children = [children]

    for child in children:
        found = _find_component_by_id(child, target_id)
        if found is not None:
            return found
    return None


def _collect_text(content):
    """Return all text nodes contained within ``content`` as a list."""

    if content is None:
        return []
    if isinstance(content, str):
        return [content]
    if isinstance(content, (list, tuple)):
        text_items = []
        for item in content:
            text_items.extend(_collect_text(item))
        return text_items
    if hasattr(content, "children"):
        return _collect_text(content.children)
    return []


def test_pending_help_notice_is_prominent():
    """The pending senders notice should surface as a highlighted alert."""

    layout_component = make_layout([], {}, {}, {}, [])
    pending_help = _find_component_by_id(layout_component, "pending-help")
    assert pending_help is not None, "Pending notice should exist in the layout"

    style = pending_help.style or {}
    assert style.get("backgroundColor") == "#fff4db"
    assert style.get("borderLeft") == "4px solid #ffa940"
    assert style.get("fontWeight") == "600"
    assert style.get("fontSize") == "14px"

    text_content = " ".join(
        item.strip()
        for item in _collect_text(pending_help.children)
        if isinstance(item, str) and item.strip()
    )
    assert "Senders not yet processed by Gmail automation." in text_content
