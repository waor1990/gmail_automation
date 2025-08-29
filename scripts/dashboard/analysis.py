from typing import Any, Dict, List, Tuple, Set
from gmail_automation.config import (
    DEFAULT_LAST_RUN_TIME,
    get_sender_last_run_times,
)
from .utils_io import read_json
from .constants import CONFIG_JSON


def load_config() -> Dict[str, Any]:
    if not CONFIG_JSON.exists():
        raise FileNotFoundError("Missing config/gmail_config-final.json")
    data: Dict[str, Any] = read_json(CONFIG_JSON)
    data.setdefault("SENDER_TO_LABELS", {})
    return data


def extract_sender_to_labels_emails(cfg: dict) -> Tuple[Set[str], Dict[str, List[str]]]:
    all_emails: Set[str] = set()
    email_to_labels: Dict[str, List[str]] = {}
    for label, configurations in (cfg.get("SENDER_TO_LABELS") or {}).items():
        for config_group in configurations or []:
            for email in config_group.get("emails") or []:
                clean = email.strip()
                if clean:
                    all_emails.add(clean)
                    email_to_labels.setdefault(clean, []).append(label)
    return all_emails, email_to_labels


def find_unprocessed_senders(cfg: dict) -> List[dict]:
    """Return senders that have not been processed yet.

    Args:
        cfg: Loaded Gmail configuration.

    Returns:
        List of dictionaries with ``email``, associated ``labels``, and a
        ``status`` indicator for senders whose last run time matches the
        default epoch.
    """

    all_emails, email_to_labels = extract_sender_to_labels_emails(cfg)
    times = get_sender_last_run_times(all_emails)
    pending = []
    for sender, ts in times.items():
        if ts == DEFAULT_LAST_RUN_TIME:
            pending.append(
                {
                    "email": sender,
                    "labels": ", ".join(email_to_labels.get(sender, [])),
                    "status": "🔴",
                }
            )
    return sorted(pending, key=lambda r: r["email"])


def check_alphabetization(cfg: dict) -> List[dict]:
    issues: List[dict] = []
    for label, configurations in (cfg.get("SENDER_TO_LABELS") or {}).items():
        for i, group in enumerate(configurations or []):
            emails = group.get("emails", []) or []
            c = [e.strip() for e in emails]
            if c != sorted(c, key=str.casefold):
                issues.append({"location": f"SENDER_TO_LABELS.{label}[{i}].emails"})
    return issues


def check_case_and_duplicates(cfg: dict) -> Dict[str, List[dict]]:
    """Validate casing and locate duplicate senders.

    Returns a dictionary with keys:

    - ``case_issues``: locations where emails are not lowercase
    - ``duplicate_issues``: lists containing the same email multiple times
    - ``cross_label_duplicates``: emails appearing under more than one label
    """

    issues: Dict[str, List[dict]] = {
        "case_issues": [],
        "duplicate_issues": [],
        "cross_label_duplicates": [],
    }

    def folded(seq: List[str]) -> List[str]:
        """Return case-insensitive normalized strings."""
        return [s.strip().casefold() for s in seq]

    def duplicate_folds(seq: List[str]) -> List[str]:
        seen, dups = set(), []
        for s in folded(seq):
            if s in seen:
                dups.append(s)
            else:
                seen.add(s)
        return sorted(set(dups))

    # Track which labels each normalized email appears in
    email_locations: Dict[str, List[str]] = {}
    email_labels: Dict[str, Set[str]] = {}

    for label, configurations in (cfg.get("SENDER_TO_LABELS") or {}).items():
        for i, group in enumerate(configurations or []):
            emails = group.get("emails", []) or []
            if [e.strip() for e in emails] != folded(emails):
                issues["case_issues"].append(
                    {"location": f"SENDER_TO_LABELS.{label}[{i}].emails"}
                )
            d = duplicate_folds(emails)
            if d:
                low = folded(emails)
                issues["duplicate_issues"].append(
                    {
                        "location": f"SENDER_TO_LABELS.{label}[{i}].emails",
                        "duplicates": d,
                        "original_count": len(low),
                        "unique_count": len(set(low)),
                    }
                )

            loc = f"SENDER_TO_LABELS.{label}[{i}].emails"
            for e in emails:
                norm = e.strip().casefold()
                email_locations.setdefault(norm, []).append(loc)
                email_labels.setdefault(norm, set()).add(label)

    for email, labels in email_labels.items():
        if len(labels) > 1:
            issues["cross_label_duplicates"].append(
                {"email": email, "locations": email_locations[email]}
            )

    return issues


def normalize_case_and_dups(cfg: dict):
    import json

    updated = json.loads(json.dumps(cfg))
    changes = []

    def normalize(seq):
        seen = set()
        out = []
        removed = 0
        cased = False
        for s in seq:
            norm = s.strip().casefold()
            if norm != s:
                cased = True
            if norm in seen:
                removed += 1
            else:
                seen.add(norm)
                out.append(norm)
        return out, removed, cased

    for label, configurations in (updated.get("SENDER_TO_LABELS") or {}).items():
        for i, group in enumerate(configurations or []):
            emails = group.get("emails", []) or []
            fixed, removed, cased = normalize(emails)
            if removed or cased or emails != fixed:
                group["emails"] = fixed
                loc = f"SENDER_TO_LABELS.{label}[{i}].emails"
                if removed:
                    changes.append(f"{loc} (removed {removed} duplicates)")
                elif cased:
                    changes.append(f"{loc} (fixed case)")
    return updated, changes


def sort_lists(cfg: dict):
    import json

    updated = json.loads(json.dumps(cfg))
    changes = []

    for label, configurations in (updated.get("SENDER_TO_LABELS") or {}).items():
        for i, group in enumerate(configurations or []):
            emails = group.get("emails", []) or []
            c = [e.strip() for e in emails]
            s = sorted(c, key=str.casefold)
            if c != s:
                group["emails"] = s
                changes.append(f"SENDER_TO_LABELS.{label}[{i}].emails")
    return updated, changes


def compute_label_differences(cfg: dict, labels_data: dict) -> dict:
    cfg_emails: Set[str] = set()
    for _, entries in (cfg.get("SENDER_TO_LABELS") or {}).items():
        for entry in entries or []:
            for e in entry.get("emails") or []:
                cfg_emails.add(e.casefold())

    output: Dict[str, Any] = {
        "comparison_summary": {
            "source_file": "gmail_labels_data.json",
            "target_file": "gmail_config-final.json",
            "total_labels_in_source": len((labels_data.get("SENDER_TO_LABELS") or {})),
            "total_labels_in_target": len((cfg.get("SENDER_TO_LABELS") or {})),
        },
        "missing_emails_by_label": {},
    }

    total_missing = 0
    for label_name, entries in (labels_data.get("SENDER_TO_LABELS") or {}).items():
        label_emails_fold: Dict[str, str] = {}
        for entry in entries or []:
            for e in entry.get("emails") or []:
                cf = e.casefold()
                label_emails_fold.setdefault(cf, e)

        missing_folds = sorted(set(label_emails_fold) - cfg_emails)
        missing = [label_emails_fold[m] for m in missing_folds]
        exists_in_target = label_name in (cfg.get("SENDER_TO_LABELS") or {})
        if missing or not exists_in_target:
            output["missing_emails_by_label"][label_name] = {
                "label_exists_in_target": exists_in_target,
                "total_emails_in_source": len(label_emails_fold),
                "missing_emails_count": len(missing),
                "missing_emails": missing,
            }
            total_missing += len(missing)

    output["comparison_summary"]["total_missing_emails"] = total_missing
    return output


def import_missing_emails(
    cfg: dict, labels_data: dict, label: str, emails: List[str]
) -> Tuple[dict, List[str]]:
    """Merge missing emails for a label into the config.

    Args:
        cfg: Current working configuration.
        labels_data: Source labels data containing metadata.
        label: Label to import emails into.
        emails: Missing emails for the label.

    Returns:
        Tuple of updated configuration and list of added emails.
    """

    import json

    updated = json.loads(json.dumps(cfg))
    stl = updated.setdefault("SENDER_TO_LABELS", {})
    target_groups = stl.setdefault(label, [])

    existing = {
        e.casefold() for grp in target_groups for e in (grp.get("emails") or [])
    }
    added: List[str] = []

    source_groups = (labels_data.get("SENDER_TO_LABELS") or {}).get(label) or []

    for src in source_groups:
        meta = {k: src.get(k) for k in ("read_status", "delete_after_days") if k in src}
        to_add = [e for e in (src.get("emails") or []) if e in emails]
        to_add = [e for e in to_add if e.casefold() not in existing]
        if not to_add:
            continue

        for tgt in target_groups:
            if tgt.get("read_status") == meta.get("read_status") and tgt.get(
                "delete_after_days"
            ) == meta.get("delete_after_days"):
                tgt.setdefault("emails", []).extend(to_add)
                existing.update(e.casefold() for e in to_add)
                added.extend(to_add)
                break
        else:
            new_group = {"emails": to_add}
            new_group.update(meta)
            target_groups.append(new_group)
            existing.update(e.casefold() for e in to_add)
            added.extend(to_add)

    return updated, added
