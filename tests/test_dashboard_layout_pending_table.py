from collections import deque

from scripts.dashboard.layout import make_layout


def _find_component(component, target_id):
    """Search the Dash component tree for a component with the given ID."""

    queue = deque([component])
    while queue:
        current = queue.popleft()
        if getattr(current, "id", None) == target_id:
            return current

        children = getattr(current, "children", None)
        if children is None:
            continue

        if isinstance(children, (list, tuple)):
            queue.extend(child for child in children if not isinstance(child, str))
        elif not isinstance(children, str):
            queue.append(children)

    return None


def test_pending_table_hides_filter_row_and_allows_sorting():
    layout = make_layout(
        stl_rows=[],
        analysis={},
        diff={},
        cfg={},
        pending=[{"status": "\N{LARGE RED CIRCLE}", "email": "foo", "labels": "Label"}],
    )

    pending_table = _find_component(layout, "tbl-new-senders")
    assert pending_table is not None
    assert pending_table.filter_action == "none"
    assert pending_table.sort_action == "native"
