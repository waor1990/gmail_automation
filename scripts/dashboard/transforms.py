from __future__ import annotations

from typing import Any, Dict, List

from gmail_automation.ignored_rules import normalize_ignored_rules


def _to_clean_email(value: Any) -> str:
    """
    Return a trimmed string for email fields; empty string if not coercible.
    """
    if value is None:
        return ""
    s = str(value).strip()
    return s


def _to_bool(value: Any, default: bool | None = None) -> bool | None:
    """Coerce common string representations to booleans."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "1", "yes"}:
            return True
        if v in {"false", "0", "no"}:
            return False
    return default


def _to_nonneg_int(value: Any, default: int | None = 0) -> int | None:
    """
    Strictly coerce value to a non-negative int.
    Handles: int, str digits, other -> default.
    This avoids Optional/Unknown -> int complaints from type checkers.
    """
    if isinstance(value, int):
        return value if value >= 0 else default
    if isinstance(value, str):
        v = value.strip()
        if v.isdigit():
            return int(v)
        # allow negative-like strings to fall back to default
        return default
    # all other types (None, floats, objects) fall back to default
    return default


def _split_multi_field(value: Any) -> List[str]:
    """Split comma-separated strings or lists into clean tokens."""

    if value is None:
        return []
    if isinstance(value, list):
        values = value
    else:
        values = str(value).split(",")
    cleaned = [str(v).strip() for v in values]
    return [c for c in cleaned if c]


def config_to_table(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Flatten config into a table of sender-to-label mappings:
      - SENDER_TO_LABELS -> [
          {"label": str, "group_index": int, "email": str,
           "read_status": Any, "delete_after_days": Any}
        ]
    """
    stl = cfg.get("SENDER_TO_LABELS") or {}

    stl_rows: List[Dict[str, Any]] = []
    # stl is expected: Dict[label:str, List[{"emails": [str, ...], ...}, ...]]
    for label, groups in stl.items() if isinstance(stl, dict) else []:
        label_str = _to_clean_email(label)
        if not label_str:
            continue
        groups = groups or []
        if not isinstance(groups, list):
            continue
        for gi, group in enumerate(groups):
            # group_index is the index position in the list
            group_index = _to_nonneg_int(gi) or 0
            read_status = None
            delete_after_days = None
            emails = []
            if isinstance(group, dict):
                raw_emails = group.get("emails", [])
                if isinstance(raw_emails, list):
                    emails = [
                        _to_clean_email(e) for e in raw_emails if _to_clean_email(e)
                    ]
                read_status = _to_bool(group.get("read_status"))
                delete_after_days = _to_nonneg_int(
                    group.get("delete_after_days"), default=None
                )
            for email in emails:
                stl_rows.append(
                    {
                        "label": label_str,
                        "group_index": group_index,
                        "email": email,
                        "read_status": read_status,
                        "delete_after_days": delete_after_days,
                    }
                )

    return stl_rows


def ignored_rules_to_rows(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return Dash table rows for IGNORED_EMAILS rules."""

    rows: List[Dict[str, Any]] = []
    for index, rule in enumerate(cfg.get("IGNORED_EMAILS") or []):
        actions = rule.get("actions", {})
        rows.append(
            {
                "name": rule.get("name", f"Rule {index + 1}"),
                "senders": ", ".join(rule.get("senders", [])),
                "domains": ", ".join(rule.get("domains", [])),
                "subject_contains": ", ".join(rule.get("subject_contains", [])),
                "skip_analysis": bool(actions.get("skip_analysis", False)),
                "skip_import": bool(actions.get("skip_import", False)),
                "mark_as_read": bool(actions.get("mark_as_read", False)),
                "apply_labels": ", ".join(actions.get("apply_labels", [])),
                "archive": bool(actions.get("archive", False)),
                "delete_after_days": actions.get("delete_after_days"),
            }
        )
    return rows


def rows_to_ignored_rules(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalise table rows into IGNORED_EMAILS config entries."""

    raw_rules: List[Dict[str, Any]] = []
    for row in rows or []:
        raw_rules.append(
            {
                "name": row.get("name"),
                "senders": _split_multi_field(row.get("senders")),
                "domains": _split_multi_field(row.get("domains")),
                "subject_contains": _split_multi_field(row.get("subject_contains")),
                "actions": {
                    "skip_analysis": _to_bool(row.get("skip_analysis"), default=False),
                    "skip_import": _to_bool(row.get("skip_import"), default=False),
                    "mark_as_read": _to_bool(row.get("mark_as_read"), default=False),
                    "apply_labels": _split_multi_field(row.get("apply_labels")),
                    "archive": _to_bool(row.get("archive"), default=False),
                    "delete_after_days": _to_nonneg_int(
                        row.get("delete_after_days"), default=None
                    ),
                },
            }
        )
    return normalize_ignored_rules(raw_rules)


def table_to_config(
    stl_rows: List[Dict[str, Any]], cfg: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    """
    Rebuild config from edited table.
    Output structure:
      {
        "SENDER_TO_LABELS": {
            "<label>": [{"emails": [str, ...]}, ...],
            ...
        }
      }
    """

    # SENDER_TO_LABELS re-aggregate by label, group_index
    # stl_map[label][group_index] -> {
    #   "emails": [...], "read_status": Any, "delete_after_days": Any
    # }
    stl_map: Dict[str, Dict[int, Dict[str, Any]]] = {}

    for r in stl_rows or []:
        label = _to_clean_email(r.get("label"))
        if not label:
            continue
        group_index = _to_nonneg_int(r.get("group_index"), default=0) or 0
        email = _to_clean_email(r.get("email"))
        if not email:
            continue
        read_status = _to_bool(r.get("read_status"))
        delete_after_days = _to_nonneg_int(r.get("delete_after_days"), default=None)

        group_dict = stl_map.setdefault(label, {})
        group_data = group_dict.setdefault(
            group_index,
            {
                "emails": [],
                "read_status": read_status,
                "delete_after_days": delete_after_days,
            },
        )
        group_data["emails"].append(email)
        if group_data.get("read_status") is None and read_status is not None:
            group_data["read_status"] = read_status
        if (
            group_data.get("delete_after_days") is None
            and delete_after_days is not None
        ):
            group_data["delete_after_days"] = delete_after_days

    # Normalize into the expected list-of-groups form, filling only existing indices
    stl_out: Dict[str, List[Dict[str, Any]]] = {}

    for label, groups in stl_map.items():
        # ensure integer keys and non-negative
        safe_keys = [k for k in groups.keys() if isinstance(k, int) and k >= 0]
        if not safe_keys:
            continue
        max_index = max(safe_keys)
        out_groups: List[Dict[str, Any]] = []
        for i in range(0, max_index + 1):
            group_data = groups.get(i, {})
            emails = group_data.get("emails", [])
            # only emit groups that contain at least one email
            cleaned_emails = [_to_clean_email(e) for e in emails if _to_clean_email(e)]
            if cleaned_emails:
                out_groups.append(
                    {
                        "read_status": group_data.get("read_status"),
                        "delete_after_days": group_data.get("delete_after_days"),
                        "emails": cleaned_emails,
                    }
                )
        if out_groups:
            stl_out[label] = out_groups

    result = dict(cfg or {})
    result["SENDER_TO_LABELS"] = stl_out
    result.setdefault("IGNORED_EMAILS", [])
    return result


def rows_to_grouped(stl_rows: List[Dict[str, Any]]) -> Dict[str, Dict[int, List[str]]]:
    """Group table rows into a label → group_index → emails structure."""
    grouped: Dict[str, Dict[int, List[str]]] = {}
    for r in stl_rows or []:
        label = _to_clean_email(r.get("label"))
        email = _to_clean_email(r.get("email"))
        if not label or not email:
            continue
        group_index = _to_nonneg_int(r.get("group_index"), default=0) or 0
        grouped.setdefault(label, {}).setdefault(group_index, []).append(email)
    return grouped
