from __future__ import annotations

from dash import dcc

from scripts.dashboard.callbacks import (
    _build_diff_tree_figure,
    _prepare_diff_tree_nodes,
)
from scripts.dashboard.layout import make_layout


def _find_component(component, target_id: str):
    """Recursively search Dash component children by id."""

    if isinstance(component, (list, tuple)):
        for child in component:
            found = _find_component(child, target_id)
            if found is not None:
                return found
        return None

    if getattr(component, "id", None) == target_id:
        return component

    children = getattr(component, "children", None)
    if not children:
        return None

    return _find_component(children, target_id)


def test_prepare_diff_tree_nodes_groups_by_status():
    diff = {
        "comparison_summary": {"total_missing_emails": 3},
        "missing_emails_by_label": {
            "Work": {
                "label_exists_in_target": True,
                "missing_emails": ["a@example.com", "b@example.com"],
                "total_emails_in_source": 4,
            },
            "Personal": {
                "label_exists_in_target": False,
                "missing_emails": ["c@example.com"],
                "total_emails_in_source": 1,
            },
        },
    }

    nodes = _prepare_diff_tree_nodes(diff)
    labels = {n["label"] for n in nodes}

    assert "All Labels" in labels
    assert "Existing Labels" in labels
    assert "Missing Labels" in labels
    assert any(n["parent"] == "Existing Labels" and n["label"] == "Work" for n in nodes)
    assert any(
        n["parent"] == "Missing Labels" and n["label"] == "Personal" for n in nodes
    )

    personal_node = next(n for n in nodes if n["label"] == "Personal")
    assert "Label missing from config." in personal_node["tooltip"]


def test_build_diff_tree_figure_handles_empty_diff():
    fig = _build_diff_tree_figure(None)
    assert len(fig.data) == 0

    fig = _build_diff_tree_figure({"missing_emails_by_label": {}})
    assert len(fig.data) == 0


def test_layout_includes_diff_tree_toggle():
    layout = make_layout([], {}, {}, {}, [])
    toggle = _find_component(layout, "diff-view-toggle")
    assert isinstance(toggle, dcc.RadioItems)
    table_view = _find_component(layout, "diff-table-view")
    tree_view = _find_component(layout, "diff-tree-view")
    assert table_view is not None
    assert tree_view is not None
