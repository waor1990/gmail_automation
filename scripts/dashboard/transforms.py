from __future__ import annotations

from typing import Dict, List, Any


def _to_clean_email(value: Any) -> str:
    """
    Return a trimmed string for email fields; empty string if not coercible.
    """
    if value is None:
        return ""
    s = str(value).strip()
    return s


def _to_nonneg_int(value: Any, default: int = 0) -> int:
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
            group_index = _to_nonneg_int(gi)
            read_status = None
            delete_after_days = None
            emails = []
            if isinstance(group, dict):
                raw_emails = group.get("emails", [])
                if isinstance(raw_emails, list):
                    emails = [
                        _to_clean_email(e) for e in raw_emails if _to_clean_email(e)
                    ]
                read_status = group.get("read_status")
                delete_after_days = group.get("delete_after_days")
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


def table_to_config(stl_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
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
        group_index = _to_nonneg_int(r.get("group_index"), default=0)
        email = _to_clean_email(r.get("email"))
        if not email:
            continue
        read_status = r.get("read_status")
        delete_after_days = r.get("delete_after_days")

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

    return {"SENDER_TO_LABELS": stl_out}
