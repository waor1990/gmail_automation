#!/usr/bin/env python3
from datetime import datetime
import argparse

from .constants import LABELS_JSON, REPORT_TXT, DIFF_JSON
from .utils_io import read_json, write_json
from .analysis import (
    load_config,
    check_alphabetization,
    check_case_and_duplicates,
    compute_label_differences,
    normalize_case_and_dups,
    sort_lists,
)


def generate_report_text(cfg: dict) -> str:
    sort_issues = check_alphabetization(cfg)
    cd = check_case_and_duplicates(cfg)

    # Projected changes if developer actions (fix all) were applied
    proj_cfg, proj_changes = normalize_case_and_dups(cfg)
    proj_cfg, sort_changes = sort_lists(proj_cfg)
    proj_changes.extend(sort_changes)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "=" * 70,
        "EMAIL STRUCTURE AND QUALITY (ECAQ) REPORT",
        "=" * 70,
        f"Generated: {ts}",
        "Target: config/gmail_config-final.json",
        "",
    ]
    if sort_issues:
        msg = f"LISTS NOT ALPHABETIZED ({len(sort_issues)}): "
        lines += [msg, ""]
        lines += [f"- {i['location']}" for i in sort_issues]
        lines.append("")
    if cd["case_issues"]:
        msg = f"LISTS WITH CASE INCONSISTENCIES ({len(cd['case_issues'])}): "
        lines += [msg, ""]
        lines += [f"- {i['location']}" for i in cd["case_issues"]]
        lines.append("")
    if cd["duplicate_issues"]:
        msg = f"LISTS WITH DUPLICATES ({len(cd['duplicate_issues'])}): "
        lines += [msg, ""]
        for i in cd["duplicate_issues"]:
            dup_count = i["original_count"] - i["unique_count"]
            lines.append(f"- {i['location']} ({dup_count} duplicates)")
            for d in i["duplicates"]:
                lines.append(f"  • {d}")
        lines.append("")
    all_good = not sort_issues and not cd["case_issues"] and not cd["duplicate_issues"]
    if all_good:
        lines.append("STATUS: CLEAN. All lists alphabetized, lowercase, unique.")
    else:
        lines += [
            "ISSUES FOUND - RECOMMENDATIONS:",
            "",
            "Use the dashboard tools or manually edit config/gmail_config-final.json",
            "to resolve the above issues, then regenerate this report.",
            "",
        ]
    lines += [
        "PROJECTED CHANGES IF FIX ACTIONS APPLIED:",
        "",
    ]
    if proj_changes:
        lines += [f"- {c}" for c in proj_changes]
    else:
        lines.append("- None")
    return "\n".join(lines)


def write_ECAQ_report():
    cfg = load_config()
    text = generate_report_text(cfg)
    REPORT_TXT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_TXT.write_text(text, encoding="utf-8")
    return REPORT_TXT


def write_diff_json():
    cfg = load_config()
    if not LABELS_JSON.exists():
        raise FileNotFoundError("Missing config/gmail_labels_data.json")
    labels = read_json(LABELS_JSON)
    diff = compute_label_differences(cfg, labels)

    # Compute projected diff after applying developer actions
    proj_cfg, proj_changes = normalize_case_and_dups(cfg)
    proj_cfg, sort_changes = sort_lists(proj_cfg)
    proj_changes.extend(sort_changes)
    proj_diff = compute_label_differences(proj_cfg, labels)
    diff["projected_changes"] = {
        "config_actions": proj_changes,
        "diff_after_actions": proj_diff,
    }
    DIFF_JSON.parent.mkdir(parents=True, exist_ok=True)
    write_json(diff, DIFF_JSON)
    return DIFF_JSON


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", choices=["ECAQ", "diff", "all"], required=True)
    args = ap.parse_args()

    if args.report in ("ECAQ", "all"):
        p = write_ECAQ_report()
        print(f"Report exported: {p}")
    if args.report in ("diff", "all"):
        p = write_diff_json()
        print(f"Differences JSON exported: {p}")


if __name__ == "__main__":
    main()
