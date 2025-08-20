#!/usr/bin/env python3
from datetime import datetime
import argparse

from .constants import LABELS_JSON, REPORT_TXT, DIFF_JSON
from .utils_io import read_json, write_json
from .analysis import (
    load_config,
    analyze_email_consistency,
    check_alphabetization,
    check_case_and_duplicates,
    compute_label_differences,
)


def generate_report_text(cfg: dict) -> str:
    cons = analyze_email_consistency(cfg)
    sort_issues = check_alphabetization(cfg)
    cd = check_case_and_duplicates(cfg)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "=" * 70,
        "EMAIL STRUCTURE AND QUALITY (ESAQ) REPORT",
        "=" * 70,
        f"Generated: {ts}",
        "Target: config/gmail_config-final.json",
        "",
        "CONSISTENCY SUMMARY:",
        f"  EMAIL_LIST count: {cons['email_list_count']}",
        f"  SENDER_TO_LABELS email set: {cons['sender_labels_count']}",
        f"  Sets identical: {cons['are_identical']}",
        "",
    ]
    if cons["missing_in_sender"]:
        lines += [
            (
                "EMAILS IN EMAIL_LIST BUT NOT IN SENDER_TO_LABELS "
                f"({len(cons['missing_in_sender'])}):"
            ),
            "",
        ]
        lines += [f"- {e}" for e in cons["missing_in_sender"]]
        lines.append("")
    if cons["missing_in_list"]:
        lines += [
            (
                "EMAILS IN SENDER_TO_LABELS BUT NOT IN EMAIL_LIST "
                f"({len(cons['missing_in_list'])}):"
            ),
            "",
        ]
        for e in cons["missing_in_list"]:
            labels = cons["email_to_labels"].get(e, ["Unknown"])
            lines.append(f"- {e} (labels: {', '.join(labels)})")
        lines.append("")
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
    all_good = (
        cons["are_identical"]
        and not sort_issues
        and not cd["case_issues"]
        and not cd["duplicate_issues"]
    )
    if all_good:
        lines.append(
            "STATUS: CLEAN. All lists consistent, alphabetized, lowercase, unique."
        )
    else:
        lines += [
            "ISSUES FOUND - RECOMMENDATIONS:",
            "",
            "Use the dashboard tools or manually edit config/gmail_config-final.json",
            "to resolve the above issues, then regenerate this report.",
            "",
        ]
    return "\n".join(lines)


def write_esaq_report():
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
    DIFF_JSON.parent.mkdir(parents=True, exist_ok=True)
    write_json(diff, DIFF_JSON)
    return DIFF_JSON


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", choices=["esaq", "diff", "all"], required=True)
    args = ap.parse_args()

    if args.report in ("esaq", "all"):
        p = write_esaq_report()
        print(f"Report exported: {p}")
    if args.report in ("diff", "all"):
        p = write_diff_json()
        print(f"Differences JSON exported: {p}")


if __name__ == "__main__":
    main()
