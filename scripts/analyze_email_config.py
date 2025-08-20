#!/usr/bin/env python3
"""
scripts/analyze_email_config.py

Unified analyzer:
1) Validates EMAIL_LIST vs SENDER_TO_LABELS (consistency, alphabetization, case, duplicates).
2) Optional auto-fix (case, duplicates, sorting).
3) Generates config/ECAQ_Report.txt.
4) Compares config/gmail_labels_data.json vs config/gmail_config-final.json and outputs config/email_differences_by_label.json.

Exit codes: 0 success, 1 error.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Tuple

# ---------- I/O ----------

def _read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _write_json(obj: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

# ---------- Core ----------

def load_config() -> dict:
    cfg = Path("config/gmail_config-final.json")
    if not cfg.exists():
        raise FileNotFoundError("config/gmail_config-final.json not found")
    return _read_json(cfg)

def extract_sender_to_labels_emails(config: dict) -> Tuple[Set[str], Dict[str, List[str]]]:
    all_emails: Set[str] = set()
    email_to_labels: Dict[str, List[str]] = {}
    for label, configurations in (config.get("SENDER_TO_LABELS", {}) or {}).items():
        for config_group in configurations or []:
            for email in (config_group.get("emails") or []):
                clean = email.strip()
                all_emails.add(clean)
                email_to_labels.setdefault(clean, []).append(label)
    return all_emails, email_to_labels

def analyze_email_consistency(config: dict) -> dict:
    email_list = set(e.strip() for e in config.get("EMAIL_LIST", []) or [])
    sender_emails, email_to_labels = extract_sender_to_labels_emails(config)
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

def check_alphabetization(config: dict) -> List[dict]:
    issues: List[dict] = []
    elist = (config.get("EMAIL_LIST", []) or [])
    cleaned = [e.strip() for e in elist]
    if cleaned != sorted(cleaned, key=str.lower):
        issues.append({"location": "EMAIL_LIST"})
    for label, configurations in (config.get("SENDER_TO_LABELS", {}) or {}).items():
        for i, group in enumerate(configurations or []):
            emails = group.get("emails", []) or []
            c = [e.strip() for e in emails]
            if c != sorted(c, key=str.lower):
                issues.append({"location": f"SENDER_TO_LABELS.{label}[{i}].emails"})
    return issues

def check_case_and_duplicates(config: dict) -> dict:
    issues = {"case_issues": [], "duplicate_issues": []}

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

    elist = (config.get("EMAIL_LIST", []) or [])
    if [e.strip() for e in elist] != lowered(elist):
        issues["case_issues"].append({"location": "EMAIL_LIST"})
    d = duplicate_lowers(elist)
    if d:
        issues["duplicate_issues"].append({
            "location": "EMAIL_LIST",
            "duplicates": d,
            "original_count": len(elist),
            "unique_count": len(set(lowered(elist))),
        })

    for label, configurations in (config.get("SENDER_TO_LABELS", {}) or {}).items():
        for i, group in enumerate(configurations or []):
            emails = group.get("emails", []) or []
            if [e.strip() for e in emails] != lowered(emails):
                issues["case_issues"].append({"location": f"SENDER_TO_LABELS.{label}[{i}].emails"})
            d = duplicate_lowers(emails)
            if d:
                low = lowered(emails)
                issues["duplicate_issues"].append({
                    "location": f"SENDER_TO_LABELS.{label}[{i}].emails",
                    "duplicates": d,
                    "original_count": len(low),
                    "unique_count": len(set(low)),
                })
    return issues

def fix_case_and_duplicates(config: dict) -> Tuple[dict, List[str]]:
    updated = json.loads(json.dumps(config))
    changes: List[str] = []

    def normalize(seq: List[str]) -> Tuple[List[str], int, bool]:
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

    elist = (updated.get("EMAIL_LIST", []) or [])
    fixed, removed, cased = normalize(elist)
    if removed or cased or elist != fixed:
        updated["EMAIL_LIST"] = fixed
        if removed:
            changes.append(f"EMAIL_LIST (removed {removed} duplicates)")
        elif cased:
            changes.append("EMAIL_LIST (fixed case)")

    for label, configurations in (updated.get("SENDER_TO_LABELS", {}) or {}).items():
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

def fix_alphabetization(config: dict) -> Tuple[dict, List[str]]:
    updated = json.loads(json.dumps(config))
    changes: List[str] = []

    elist = (updated.get("EMAIL_LIST", []) or [])
    c = [e.strip() for e in elist]
    s = sorted(c, key=str.lower)
    if c != s:
        updated["EMAIL_LIST"] = s
        changes.append("EMAIL_LIST")

    for label, configurations in (updated.get("SENDER_TO_LABELS", {}) or {}).items():
        for i, group in enumerate(configurations or []):
            emails = group.get("emails", []) or []
            c = [e.strip() for e in emails]
            s = sorted(c, key=str.lower)
            if c != s:
                group["emails"] = s
                changes.append(f"SENDER_TO_LABELS.{label}[{i}].emails")
    return updated, changes

def save_config(config: dict, backup: bool = True) -> None:
    cfg = Path("config/gmail_config-final.json")
    if backup and cfg.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        bkp = cfg.with_suffix(cfg.suffix + f".backup_{ts}")
        import shutil
        shutil.copy2(cfg, bkp)
        print(f"Backup created: {bkp}")
    cfg.parent.mkdir(parents=True, exist_ok=True)
    with open(cfg, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    print(f"Updated config saved: {cfg}")

def generate_report(analysis: dict, sorting_issues: List[dict], case_dup: dict, out_path: Path) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: List[str] = [
        "=" * 70,
        "EMAIL STRUCTURE AND QUALITY (ESAQ) REPORT",
        "=" * 70,
        f"Generated: {ts}",
        "Target: config/gmail_config-final.json",
        "",
        "CONSISTENCY SUMMARY:",
        f"  EMAIL_LIST count          : {analysis['email_list_count']}",
        f"  SENDER_TO_LABELS email set: {analysis['sender_labels_count']}",
        f"  Sets identical            : {analysis['are_identical']}",
        "",
    ]

    if analysis["missing_in_sender"]:
        lines += [f"EMAILS IN EMAIL_LIST BUT NOT IN SENDER_TO_LABELS ({len(analysis['missing_in_sender'])}):", ""]
        lines += [f"  - {e}" for e in analysis["missing_in_sender"]]
        lines.append("")

    if analysis["missing_in_list"]:
        lines += [f"EMAILS IN SENDER_TO_LABELS BUT NOT IN EMAIL_LIST ({len(analysis['missing_in_list'])}):", ""]
        for e in analysis["missing_in_list"]:
            labels = analysis["email_to_labels"].get(e, ["Unknown"])
            lines.append(f"  - {e} (labels: {', '.join(labels)})")
        lines.append("")

    if sorting_issues:
        lines += [f"LISTS NOT ALPHABETIZED ({len(sorting_issues)}):", ""]
        lines += [f"  - {i['location']}" for i in sorting_issues]
        lines.append("")

    if case_dup["case_issues"]:
        lines += [f"LISTS WITH CASE INCONSISTENCIES ({len(case_dup['case_issues'])}):", ""]
        lines += [f"  - {i['location']}" for i in case_dup["case_issues"]]
        lines.append("")

    if case_dup["duplicate_issues"]:
        lines += [f"LISTS WITH DUPLICATES ({len(case_dup['duplicate_issues'])}):", ""]
        for i in case_dup["duplicate_issues"]:
            dup_count = i["original_count"] - i["unique_count"]
            lines.append(f"  - {i['location']} ({dup_count} duplicates)")
            for d in i["duplicates"]:
                lines.append(f"    • {d}")
        lines.append("")

    all_good = analysis["are_identical"] and not sorting_issues and not case_dup["case_issues"] and not case_dup["duplicate_issues"]
    if all_good:
        lines.append("STATUS: CLEAN. All lists consistent, alphabetized, lowercase, unique.")
    else:
        lines += [
            "ISSUES FOUND - RECOMMENDATIONS:",
            "",
            "Run from repo root. Backups are created unless --no-backup is used.",
            "",
            "1) Fix all issues in one pass (case, duplicates, sorting):",
            "   python scripts/analyze_email_config.py --fix-all",
            "   Use when: multiple categories appear in this report; you want an idempotent normalize-and-sort.",
            "",
            "2) Only fix case and whitespace (lowercase/trim) without touching order:",
            "   python scripts/analyze_email_config.py --fix-case",
            "   Use when: report shows ONLY case inconsistencies and you want to preserve current ordering.",
            "",
            "3) Only remove duplicates (case-insensitive) without changing case or order:",
            "   python scripts/analyze_email_config.py --fix-duplicates",
            "   Use when: duplicate entries exist but case and ordering are already correct.",
            "",
            "4) Only alphabetize lists (case-insensitive sort):",
            "   python scripts/analyze_email_config.py --fix-sorting",
            "   Use when: lists are correctly cased and deduped, but ordering is flagged.",
            "",
            "Compositions:",
            "   python scripts/analyze_email_config.py --fix-case --fix-duplicates",
            "   python scripts/analyze_email_config.py --fix-duplicates --fix-sorting",
            "   Add --no-backup to suppress backup creation.",
            "",
            "Re-run without flags to regenerate this report after fixes.",
            "",
        ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")

# ---------- Differences ----------

def compute_label_differences(labels_path: Path, config: dict) -> dict:
    labels_data = _read_json(labels_path)
    config_emails: Set[str] = set((config.get("EMAIL_LIST", []) or []))
    for _, entries in (config.get("SENDER_TO_LABELS", {}) or {}).items():
        for entry in entries or []:
            for e in (entry.get("emails") or []):
                config_emails.add(e)

    output = {
        "comparison_summary": {
            "source_file": labels_path.name,
            "target_file": "gmail_config-final.json",
            "total_labels_in_source": len((labels_data.get("SENDER_TO_LABELS") or {})),
            "total_labels_in_target": len((config.get("SENDER_TO_LABELS") or {})),
        },
        "missing_emails_by_label": {},
    }

    total_missing = 0
    for label_name, entries in (labels_data.get("SENDER_TO_LABELS") or {}).items():
        label_emails: Set[str] = set()
        for entry in entries or []:
            for e in (entry.get("emails") or []):
                label_emails.add(e)

        missing = sorted(label_emails - config_emails)
        exists_in_target = label_name in (config.get("SENDER_TO_LABELS") or {})
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

def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Analyze and reconcile Gmail email configuration.")
    p.add_argument("--fix-sorting", action="store_true", help="Fix alphabetization.")
    p.add_argument("--fix-case", action="store_true", help="Lowercase and trim emails.")
    p.add_argument("--fix-duplicates", action="store_true", help="Remove duplicates.")
    p.add_argument("--fix-all", action="store_true", help="Apply all fixes (case, dups, sorting).")
    p.add_argument("--no-backup", action="store_true", help="Skip backup when writing config.")
    p.add_argument("--skip-report", action="store_true", help="Skip generating ESAQ report.")
    p.add_argument("--skip-differences", action="store_true", help="Skip differences JSON.")
    p.add_argument("--labels-file", default="config/gmail_labels_data.json",
                   help="Path to labels source JSON used for differences check.")

    args = p.parse_args()
    if args.fix_all:
        args.fix_case = args.fix_duplicates = args.fix_sorting = True

    try:
        cfg = load_config()

        changed_once = False
        if args.fix_case or args.fix_duplicates:
            cfg2, changes = fix_case_and_duplicates(cfg)
            if changes:
                save_config(cfg2, backup=not args.no_backup)
                cfg = cfg2
                changed_once = True
                print("Case/Duplicate fixes applied:")
                for c in changes:
                    print(f"  - {c}")

        if args.fix_sorting:
            cfg2, changes = fix_alphabetization(cfg)
            if changes:
                save_config(cfg2, backup=not args.no_backup and not changed_once)
                cfg = cfg2
                print("Sorting fixes applied:")
                for c in changes:
                    print(f"  - {c}")

        if not args.skip_report:
            analysis = analyze_email_consistency(cfg)
            sort_issues = check_alphabetization(cfg)
            case_dup = check_case_and_duplicates(cfg)
            report_path = Path("config/ECAQ_Report.txt")
            generate_report(analysis, sort_issues, case_dup, report_path)
            print(f"Report saved: {report_path}")

        if not args.skip_differences:
            labels_path = Path(args.labels_file)
            if labels_path.exists():
                diff = compute_label_differences(labels_path, cfg)
                out = Path("config/email_differences_by_label.json")
                _write_json(diff, out)
                print(f"Differences JSON saved: {out}")
            else:
                print(f"Labels file not found, skipping differences: {labels_path}")

        sys.exit(0)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()