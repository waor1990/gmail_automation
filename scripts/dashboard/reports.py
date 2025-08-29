#!/usr/bin/env python3
from datetime import datetime
import argparse

from .constants import LABELS_JSON, REPORT_TXT, DIFF_JSON
from .utils_io import write_json
from .analysis import load_config
from .analysis_helpers import run_full_analysis


def generate_report_text(cfg: dict) -> str:
    analysis = run_full_analysis(cfg)
    sort_issues = analysis["sorting"]
    cd = analysis["case_dups"]
    proj_changes = analysis["projected_changes"]

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
    if cd["cross_label_duplicates"]:
        msg = f"SENDERS IN MULTIPLE LABELS ({len(cd['cross_label_duplicates'])}): "
        lines += [msg, ""]
        for item in cd["cross_label_duplicates"]:
            lines.append(f"- {item['email']}")
            for loc in item["locations"]:
                lines.append(f"  • {loc}")
        lines.append("")
    all_good = (
        not sort_issues
        and not cd["case_issues"]
        and not cd["duplicate_issues"]
        and not cd["cross_label_duplicates"]
    )
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
    analysis = run_full_analysis(cfg)
    diff = analysis["diff"]
    proj_changes = analysis["projected_changes"]
    proj_diff = analysis["projected_diff"]
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
