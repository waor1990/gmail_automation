"""Utilities for manipulating group indices in the dashboard table."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


def _coerce_group_index(value: Any) -> int:
    """Coerce a group index value into an integer."""

    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


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


def remove_email_from_group(
    rows: List[Dict[str, Any]],
    label: str,
    group_index: Any,
    email: str,
) -> Tuple[List[Dict[str, Any]], bool]:
    """Remove the first matching email from the provided rows.

    Args:
        rows: Current table rows.
        label: Target label for removal.
        group_index: Group index associated with the email.
        email: Email address to remove.

    Returns:
        Tuple of (updated_rows, removed_flag).
    """

    target_label = (label or "").strip()
    target_email = (email or "").strip()
    target_group = _coerce_group_index(group_index)

    updated: List[Dict[str, Any]] = []
    removed = False

    for row in rows or []:
        row_label = (row.get("label") or "").strip()
        row_email = (row.get("email") or "").strip()
        row_group = _coerce_group_index(row.get("group_index"))

        if (
            not removed
            and row_label == target_label
            and row_email == target_email
            and row_group == target_group
        ):
            removed = True
            continue

        updated.append(dict(row))

    return updated, removed
