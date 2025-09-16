"""Utilities for manipulating group indices in the dashboard table."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


def merge_selected(
    rows: List[Dict[str, Any]], indices: List[int]
) -> List[Dict[str, Any]]:
    """Merge selected rows by label into the lowest ``group_index``.

    Args:
        rows: Current table rows.
        indices: Positions of selected rows.

    Returns:
        A new list with updated ``group_index`` values.
    """
    result = [dict(r) for r in rows]
    by_label: Dict[str, List[Tuple[int, int]]] = {}
    for idx in indices:
        row = result[idx]
        label = row.get("label", "")
        gi = row.get("group_index") or 0
        by_label.setdefault(label, []).append((idx, gi))
    for items in by_label.values():
        min_gi = min(gi for _, gi in items)
        for idx, _ in items:
            result[idx]["group_index"] = min_gi
    return result


def split_selected(
    rows: List[Dict[str, Any]], indices: List[int]
) -> List[Dict[str, Any]]:
    """Assign new ``group_index`` values to each selected row.

    Each row is moved to a unique group after the current maximum index for
    its label.

    Args:
        rows: Current table rows.
        indices: Positions of selected rows.

    Returns:
        A new list with updated ``group_index`` values.
    """
    result = [dict(r) for r in rows]
    max_gi: Dict[str, int] = {}
    for row in result:
        label = row.get("label", "")
        gi = row.get("group_index") or 0
        max_gi[label] = max(max_gi.get(label, -1), gi)
    first_seen: Dict[str, bool] = {}
    for idx in indices:
        row = result[idx]
        label = row.get("label", "")
        if first_seen.get(label):
            max_gi[label] += 1
            row["group_index"] = max_gi[label]
        else:
            first_seen[label] = True
    return result
