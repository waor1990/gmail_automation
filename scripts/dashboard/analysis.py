from typing import Any, Dict, List, Tuple, Set, cast
from .utils_io import read_json
from .constants import CONFIG_JSON


def load_config() -> Dict[str, Any]:
    if not CONFIG_JSON.exists():
        raise FileNotFoundError("Missing config/gmail_config-final.json")
    data = cast(Dict[str, Any], read_json(CONFIG_JSON))
    data.setdefault("EMAIL_LIST", [])
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


def analyze_email_consistency(cfg: dict) -> dict:
    email_list = set(e.strip() for e in (cfg.get("EMAIL_LIST") or []) if e.strip())
    sender_emails, email_to_labels = extract_sender_to_labels_emails(cfg)
    missing_in_sender = sorted(email_list - sender_emails)
    missing_in_list = sorted(sender_emails - email_list)
    return {
        "email_list_count": len(email_list),
        "sender_labels_count": len(sender_emails),
        "missing_in_sender": missing_in_sender,
        "missing_in_list": missing_in_list,
        "are_identical": not missing_in_sender and not missing_in_list,
        "email_to_labels": email_to_labels,
    }


def check_alphabetization(cfg: dict) -> List[dict]:
    issues: List[dict] = []
    elist = cfg.get("EMAIL_LIST") or []
    cleaned = [e.strip() for e in elist]
    if cleaned != sorted(cleaned, key=str.lower):
        issues.append({"location": "EMAIL_LIST"})
    for label, configurations in (cfg.get("SENDER_TO_LABELS") or {}).items():
        for i, group in enumerate(configurations or []):
            emails = group.get("emails", []) or []
            c = [e.strip() for e in emails]
            if c != sorted(c, key=str.lower):
                issues.append({"location": f"SENDER_TO_LABELS.{label}[{i}].emails"})
    return issues


def check_case_and_duplicates(cfg: dict) -> Dict[str, List[dict]]:
    issues: Dict[str, List[dict]] = {"case_issues": [], "duplicate_issues": []}

    def lowered(seq: List[str]) -> List[str]:
        return [s.strip().lower() for s in seq]

    def duplicate_lowers(seq: List[str]) -> List[str]:
        seen, dups = set(), []
        for s in lowered(seq):
            if s in seen:
                dups.append(s)
            else:
                seen.add(s)
        return sorted(set(dups))

    elist = cfg.get("EMAIL_LIST") or []
    if [e.strip() for e in elist] != lowered(elist):
        issues["case_issues"].append({"location": "EMAIL_LIST"})
    d = duplicate_lowers(elist)
    if d:
        issues["duplicate_issues"].append(
            {
                "location": "EMAIL_LIST",
                "duplicates": d,
                "original_count": len(elist),
                "unique_count": len(set(lowered(elist))),
            }
        )

    for label, configurations in (cfg.get("SENDER_TO_LABELS") or {}).items():
        for i, group in enumerate(configurations or []):
            emails = group.get("emails", []) or []
            if [e.strip() for e in emails] != lowered(emails):
                issues["case_issues"].append(
                    {"location": f"SENDER_TO_LABELS.{label}[{i}].emails"}
                )
            d = duplicate_lowers(emails)
            if d:
                low = lowered(emails)
                issues["duplicate_issues"].append(
                    {
                        "location": f"SENDER_TO_LABELS.{label}[{i}].emails",
                        "duplicates": d,
                        "original_count": len(low),
                        "unique_count": len(set(low)),
                    }
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
            norm = s.strip().lower()
            if norm != s:
                cased = True
            if norm in seen:
                removed += 1
            else:
                seen.add(norm)
                out.append(norm)
        return out, removed, cased

    elist = updated.get("EMAIL_LIST") or []
    fixed, removed, cased = normalize(elist)
    if removed or cased or elist != fixed:
        updated["EMAIL_LIST"] = fixed
        if removed:
            changes.append(f"EMAIL_LIST (removed {removed} duplicates)")
        elif cased:
            changes.append("EMAIL_LIST (fixed case)")

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

    elist = updated.get("EMAIL_LIST") or []
    c = [e.strip() for e in elist]
    s = sorted(c, key=str.lower)
    if c != s:
        updated["EMAIL_LIST"] = s
        changes.append("EMAIL_LIST")

    for label, configurations in (updated.get("SENDER_TO_LABELS") or {}).items():
        for i, group in enumerate(configurations or []):
            emails = group.get("emails", []) or []
            c = [e.strip() for e in emails]
            s = sorted(c, key=str.lower)
            if c != s:
                group["emails"] = s
                changes.append(f"SENDER_TO_LABELS.{label}[{i}].emails")
    return updated, changes


def compute_label_differences(cfg: dict, labels_data: dict) -> dict:
    cfg_emails: Set[str] = set((cfg.get("EMAIL_LIST") or []))
    for _, entries in (cfg.get("SENDER_TO_LABELS") or {}).items():
        for entry in entries or []:
            for e in entry.get("emails") or []:
                cfg_emails.add(e)

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
        label_emails: Set[str] = set()
        for entry in entries or []:
            for e in entry.get("emails") or []:
                label_emails.add(e)

        missing = sorted(label_emails - cfg_emails)
        exists_in_target = label_name in (cfg.get("SENDER_TO_LABELS") or {})
        if missing or not exists_in_target:
            output["missing_emails_by_label"][label_name] = {
                "label_exists_in_target": exists_in_target,
                "total_emails_in_source": len(label_emails),
                "missing_emails_count": len(missing),
                "missing_emails": missing,
            }
            total_missing += len(missing)

    output["comparison_summary"]["total_missing_emails"] = total_missing
    return output
