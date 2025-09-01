from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Tuple


def resolve_collisions(
    cfg: Dict[str, Any], resolutions: List[Dict[str, Any]]
) -> Tuple[Dict[str, Any], List[str]]:
    """Apply email collision resolutions to a configuration.

    Args:
        cfg: Existing Gmail configuration mapping.
        resolutions: A list of dictionaries with keys ``email``, ``labels``,
            and ``action``. ``labels`` should be the list of labels where the
            email currently resides. ``action`` may be one of
            ``reassign:<label>``, ``split``, or ``remove``.

    Returns:
        A tuple of ``(updated_config, changes)`` where ``changes`` is a list of
        human-readable descriptions of the operations performed.
    """

    updated = deepcopy(cfg)
    stl = updated.get("SENDER_TO_LABELS") or {}
    changes: List[str] = []

    for item in resolutions or []:
        email = item.get("email")
        labels = item.get("labels") or []
        action = item.get("action") or ""
        if not email or not labels or not action:
            continue

        if action.startswith("reassign:"):
            target = action.split(":", 1)[1]
            for label in labels:
                if label == target:
                    continue
                for group in stl.get(label, []) or []:
                    emails = group.get("emails") or []
                    if email in emails:
                        group["emails"] = [e for e in emails if e != email]
            changes.append(f"{email} reassigned to {target}")
        elif action == "remove":
            for label in labels:
                for group in stl.get(label, []) or []:
                    emails = group.get("emails") or []
                    if email in emails:
                        group["emails"] = [e for e in emails if e != email]
            changes.append(f"{email} removed")
        elif action == "split":
            # No structural change required; email remains in all labels
            changes.append(f"{email} left in all labels")

    return updated, changes
