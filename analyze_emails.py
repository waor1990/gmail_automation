#!/usr/bin/env python3
"""
Script to analyze email addresses in gmail_config-final.json
Compares EMAIL_LIST with emails in SENDER_TO_LABELS
Outputs results to config/email_analysis_report.txt
"""

import json
import sys
from pathlib import Path
from datetime import datetime


def load_config():
    """Load the configuration file"""
    config_path = Path("config/gmail_config-final.json")
    with open(config_path, "r") as f:
        return json.load(f)


def extract_sender_to_labels_emails(config):
    """Extract all email addresses from SENDER_TO_LABELS"""
    all_emails = set()
    email_to_labels = {}  # Track which labels each email belongs to

    for label, configurations in config["SENDER_TO_LABELS"].items():
        for config_group in configurations:
            emails = config_group.get("emails", [])
            for email in emails:
                # Strip whitespace (noticed "venmo@venmo.com " has trailing space)
                clean_email = email.strip()
                all_emails.add(clean_email)

                # Track label mapping
                if clean_email not in email_to_labels:
                    email_to_labels[clean_email] = []
                email_to_labels[clean_email].append(label)

    return all_emails, email_to_labels


def check_alphabetization(config):
    """Check if EMAIL_LIST and all emails lists in SENDER_TO_LABELS are alphabetized"""
    sorting_issues = []

    # Check EMAIL_LIST
    email_list = config["EMAIL_LIST"]
    sorted_email_list = sorted(email_list, key=str.lower)
    if email_list != sorted_email_list:
        sorting_issues.append(
            {
                "location": "EMAIL_LIST",
                "current": email_list,
                "sorted": sorted_email_list,
            }
        )

    # Check SENDER_TO_LABELS email lists
    for label, configurations in config["SENDER_TO_LABELS"].items():
        for i, config_group in enumerate(configurations):
            emails = config_group.get("emails", [])
            if emails:
                # Clean emails (strip whitespace) before sorting
                cleaned_emails = [email.strip() for email in emails]
                sorted_emails = sorted(cleaned_emails, key=str.lower)
                if cleaned_emails != sorted_emails:
                    sorting_issues.append(
                        {
                            "location": f"SENDER_TO_LABELS.{label}[{i}].emails",
                            "current": cleaned_emails,
                            "sorted": sorted_emails,
                        }
                    )

    return sorting_issues


def check_case_and_duplicates(config):
    """Check for case inconsistencies and duplicates in email lists"""
    issues = {"case_issues": [], "duplicate_issues": []}

    # Check EMAIL_LIST
    email_list = config["EMAIL_LIST"]

    # Check for case issues
    case_fixed_emails = [email.strip().lower() for email in email_list]
    if [email.strip() for email in email_list] != case_fixed_emails:
        issues["case_issues"].append(
            {
                "location": "EMAIL_LIST",
                "current": [email.strip() for email in email_list],
                "fixed": case_fixed_emails,
            }
        )

    # Check for duplicates
    seen = set()
    duplicates = set()
    for email in case_fixed_emails:
        if email in seen:
            duplicates.add(email)
        seen.add(email)

    if duplicates:
        issues["duplicate_issues"].append(
            {
                "location": "EMAIL_LIST",
                "duplicates": sorted(duplicates),
                "unique_count": len(seen),
                "original_count": len(case_fixed_emails),
            }
        )

    # Check SENDER_TO_LABELS email lists
    for label, configurations in config["SENDER_TO_LABELS"].items():
        for i, config_group in enumerate(configurations):
            emails = config_group.get("emails", [])
            if emails:
                location = f"SENDER_TO_LABELS.{label}[{i}].emails"

                # Check for case issues
                cleaned_emails = [email.strip() for email in emails]
                case_fixed_emails = [email.lower() for email in cleaned_emails]
                if cleaned_emails != case_fixed_emails:
                    issues["case_issues"].append(
                        {
                            "location": location,
                            "current": cleaned_emails,
                            "fixed": case_fixed_emails,
                        }
                    )

                # Check for duplicates
                seen = set()
                duplicates = set()
                for email in case_fixed_emails:
                    if email in seen:
                        duplicates.add(email)
                    seen.add(email)

                if duplicates:
                    issues["duplicate_issues"].append(
                        {
                            "location": location,
                            "duplicates": sorted(duplicates),
                            "unique_count": len(seen),
                            "original_count": len(case_fixed_emails),
                        }
                    )

    return issues


def fix_case_and_duplicates(config):
    """Fix case inconsistencies and remove duplicates in the config"""
    updated_config = json.loads(json.dumps(config))  # Deep copy
    changes_made = []

    # Fix EMAIL_LIST
    email_list = updated_config["EMAIL_LIST"]
    original_count = len(email_list)

    # Clean, lowercase, and remove duplicates while preserving order
    seen = set()
    fixed_emails = []
    for email in email_list:
        clean_email = email.strip().lower()
        if clean_email not in seen:
            fixed_emails.append(clean_email)
            seen.add(clean_email)

    if len(fixed_emails) != original_count or email_list != fixed_emails:
        updated_config["EMAIL_LIST"] = fixed_emails
        if len(fixed_emails) != original_count:
            changes_made.append(
                f"EMAIL_LIST (removed {original_count - len(fixed_emails)} duplicates)"
            )
        else:
            changes_made.append("EMAIL_LIST (fixed case)")

    # Fix SENDER_TO_LABELS email lists
    for label, configurations in updated_config["SENDER_TO_LABELS"].items():
        for i, config_group in enumerate(configurations):
            emails = config_group.get("emails", [])
            if emails:
                original_count = len(emails)

                # Clean, lowercase, and remove duplicates while preserving order
                seen = set()
                fixed_emails = []
                for email in emails:
                    clean_email = email.strip().lower()
                    if clean_email not in seen:
                        fixed_emails.append(clean_email)
                        seen.add(clean_email)

                if len(fixed_emails) != original_count or emails != fixed_emails:
                    config_group["emails"] = fixed_emails
                    location = f"SENDER_TO_LABELS.{label}[{i}].emails"
                    if len(fixed_emails) != original_count:
                        changes_made.append(
                            f"{location} (removed {original_count - len(fixed_emails)} duplicates)"
                        )
                    else:
                        changes_made.append(f"{location} (fixed case)")

    return updated_config, changes_made


def fix_alphabetization(config):
    """Fix alphabetization in the config and return the updated config"""
    updated_config = json.loads(json.dumps(config))  # Deep copy
    changes_made = []

    # Fix EMAIL_LIST
    email_list = updated_config["EMAIL_LIST"]
    sorted_email_list = sorted(email_list, key=str.lower)
    if email_list != sorted_email_list:
        updated_config["EMAIL_LIST"] = sorted_email_list
        changes_made.append("EMAIL_LIST")

    # Fix SENDER_TO_LABELS email lists
    for label, configurations in updated_config["SENDER_TO_LABELS"].items():
        for i, config_group in enumerate(configurations):
            emails = config_group.get("emails", [])
            if emails:
                # Clean and sort emails
                cleaned_emails = [email.strip() for email in emails]
                sorted_emails = sorted(cleaned_emails, key=str.lower)
                if cleaned_emails != sorted_emails:
                    config_group["emails"] = sorted_emails
                    changes_made.append(f"SENDER_TO_LABELS.{label}[{i}].emails")

    return updated_config, changes_made


def save_config(config, backup=True):
    """Save the updated config file with optional backup"""
    config_path = Path("config/gmail_config-final.json")

    if backup:
        # Create backup with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = Path(f"config/gmail_config-final.json.backup_{timestamp}")

        # Copy original to backup
        import shutil

        shutil.copy2(config_path, backup_path)
        print(f"📄 Backup created: {backup_path}")

    # Save updated config
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

    print(f"✅ Updated config saved: {config_path}")


def analyze_email_consistency(config):
    """Analyze consistency between EMAIL_LIST and SENDER_TO_LABELS"""
    email_list = set(config["EMAIL_LIST"])
    sender_emails, email_to_labels = extract_sender_to_labels_emails(config)

    # Find emails in EMAIL_LIST but not in SENDER_TO_LABELS
    missing_in_sender = email_list - sender_emails

    # Find emails in SENDER_TO_LABELS but not in EMAIL_LIST
    missing_in_list = sender_emails - email_list

    return {
        "email_list_count": len(email_list),
        "sender_labels_count": len(sender_emails),
        "missing_in_sender": sorted(missing_in_sender),
        "missing_in_list": sorted(missing_in_list),
        "are_identical": len(missing_in_sender) == 0 and len(missing_in_list) == 0,
        "email_to_labels": email_to_labels,
    }


def generate_report(analysis, sorting_issues, case_duplicate_issues, output_path):
    """Generate detailed report and save to file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    case_issues = case_duplicate_issues["case_issues"]
    duplicate_issues = case_duplicate_issues["duplicate_issues"]

    report_lines = [
        "=" * 70,
        "EMAIL CONSISTENCY, ALPHABETIZATION & QUALITY ANALYSIS REPORT",
        "=" * 70,
        f"Generated: {timestamp}",
        f"Analysis of: config/gmail_config-final.json",
        "",
        "CONSISTENCY SUMMARY:",
        f"  EMAIL_LIST contains: {analysis['email_list_count']} emails",
        f"  SENDER_TO_LABELS contains: {analysis['sender_labels_count']} emails",
        f"  Are they identical? {analysis['are_identical']}",
        "",
        "QUALITY SUMMARY:",
        f"  Lists that need sorting: {len(sorting_issues)}",
        f"  Lists with case issues: {len(case_issues)}",
        f"  Lists with duplicates: {len(duplicate_issues)}",
        "",
    ]

    # Consistency issues
    if analysis["missing_in_sender"]:
        report_lines.extend(
            [
                f"❌ EMAILS IN EMAIL_LIST BUT NOT IN SENDER_TO_LABELS ({len(analysis['missing_in_sender'])}):",
                "",
            ]
        )
        for email in analysis["missing_in_sender"]:
            report_lines.append(f"  - {email}")
        report_lines.append("")

    if analysis["missing_in_list"]:
        report_lines.extend(
            [
                f"❌ EMAILS IN SENDER_TO_LABELS BUT NOT IN EMAIL_LIST ({len(analysis['missing_in_list'])}):",
                "",
            ]
        )
        for email in analysis["missing_in_list"]:
            labels = analysis["email_to_labels"].get(email, ["Unknown"])
            report_lines.append(f"  - {email} (in labels: {', '.join(labels)})")
        report_lines.append("")

    # Alphabetization issues
    if sorting_issues:
        report_lines.extend(
            [f"📝 LISTS THAT ARE NOT ALPHABETIZED ({len(sorting_issues)}):", ""]
        )
        for issue in sorting_issues:
            report_lines.append(f"  - {issue['location']}")
        report_lines.append("")

    # Case issues
    if case_issues:
        report_lines.extend(
            [f"🔤 LISTS WITH CASE INCONSISTENCIES ({len(case_issues)}):", ""]
        )
        for issue in case_issues:
            report_lines.append(f"  - {issue['location']}")
        report_lines.append("")

    # Duplicate issues
    if duplicate_issues:
        report_lines.extend(
            [f"🔄 LISTS WITH DUPLICATE EMAILS ({len(duplicate_issues)}):", ""]
        )
        for issue in duplicate_issues:
            dup_count = issue["original_count"] - issue["unique_count"]
            report_lines.append(f"  - {issue['location']} ({dup_count} duplicates)")
            for dup in issue["duplicates"]:
                report_lines.append(f"    • {dup}")
        report_lines.append("")

    # Overall status
    all_good = (
        analysis["are_identical"]
        and not sorting_issues
        and not case_issues
        and not duplicate_issues
    )

    if all_good:
        report_lines.append(
            "🎉 PERFECT! ALL EMAILS ARE CONSISTENT, ALPHABETIZED, LOWERCASE & UNIQUE!"
        )
    else:
        report_lines.extend(["⚠️  ISSUES FOUND - RECOMMENDATIONS:", ""])
        if not analysis["are_identical"]:
            report_lines.extend(
                [
                    "CONSISTENCY ISSUES:",
                    "1. Fix case sensitivity issues (if any)",
                    "2. Add missing emails to appropriate SENDER_TO_LABELS categories",
                    "3. Remove unused emails from EMAIL_LIST (if no longer needed)",
                    "4. Check for trailing whitespace in email addresses",
                    "",
                ]
            )
        if sorting_issues or case_issues or duplicate_issues:
            report_lines.extend(
                [
                    "QUALITY ISSUES:",
                    "1. Run this script with --fix-all to automatically fix all issues",
                    "2. Or use individual flags: --fix-sorting, --fix-case, --fix-duplicates",
                    "3. Manually review and fix the identified issues",
                    "",
                ]
            )

    report_lines.extend(["", "=" * 70, "END OF REPORT", "=" * 70])

    # Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    return report_lines


def main():
    """Main analysis function"""
    try:
        import argparse

        # Parse command line arguments
        parser = argparse.ArgumentParser(
            description="Analyze and fix email configuration"
        )
        parser.add_argument(
            "--fix-sorting",
            action="store_true",
            help="Automatically fix alphabetization issues",
        )
        parser.add_argument(
            "--fix-case", action="store_true", help="Convert all emails to lowercase"
        )
        parser.add_argument(
            "--fix-duplicates", action="store_true", help="Remove duplicate emails"
        )
        parser.add_argument(
            "--fix-all",
            action="store_true",
            help="Fix all issues (sorting, case, duplicates)",
        )
        parser.add_argument(
            "--no-backup", action="store_true", help="Skip creating backup when fixing"
        )
        args = parser.parse_args()

        # Handle --fix-all flag
        if args.fix_all:
            args.fix_sorting = True
            args.fix_case = True
            args.fix_duplicates = True

        # Ensure config directory exists
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)

        # Load and analyze
        config = load_config()
        analysis = analyze_email_consistency(config)
        sorting_issues = check_alphabetization(config)
        case_duplicate_issues = check_case_and_duplicates(config)

        # Handle fixing if requested
        changes_made = []

        # Fix case and duplicates first (affects sorting)
        if (args.fix_case or args.fix_duplicates) and (
            case_duplicate_issues["case_issues"]
            or case_duplicate_issues["duplicate_issues"]
        ):
            print("🔧 Fixing case and duplicate issues...")
            updated_config, case_changes = fix_case_and_duplicates(config)

            if case_changes:
                # Save the fixed config
                save_config(updated_config, backup=not args.no_backup)

                print(f"✅ Fixed case/duplicate issues in {len(case_changes)} lists:")
                for change in case_changes:
                    print(f"   - {change}")
                print()

                changes_made.extend(case_changes)

                # Re-analyze with fixed config
                config = updated_config
                analysis = analyze_email_consistency(config)
                sorting_issues = check_alphabetization(config)
                case_duplicate_issues = check_case_and_duplicates(config)

        # Fix sorting after case/duplicate fixes
        if args.fix_sorting and sorting_issues:
            print("🔧 Fixing alphabetization issues...")
            updated_config, sort_changes = fix_alphabetization(config)

            if sort_changes:
                # Save the fixed config (backup only if not already created)
                save_config(
                    updated_config, backup=not args.no_backup and not changes_made
                )

                print(f"✅ Fixed alphabetization in {len(sort_changes)} lists:")
                for change in sort_changes:
                    print(f"   - {change}")
                print()

                changes_made.extend(sort_changes)

                # Re-analyze with fixed config
                config = updated_config
                analysis = analyze_email_consistency(config)
                sorting_issues = check_alphabetization(config)
                case_duplicate_issues = check_case_and_duplicates(config)

        # Generate report
        output_path = config_dir / "email_analysis_report.txt"
        report_lines = generate_report(
            analysis, sorting_issues, case_duplicate_issues, output_path
        )

        # Print to console
        for line in report_lines:
            print(line)

        print(f"\n📄 Detailed report saved to: {output_path}")

        # Provide helpful tips
        total_issues = (
            len(sorting_issues)
            + len(case_duplicate_issues["case_issues"])
            + len(case_duplicate_issues["duplicate_issues"])
        )

        if total_issues > 0 and not any(
            [args.fix_sorting, args.fix_case, args.fix_duplicates]
        ):
            print(
                f"\n💡 TIP: Run with --fix-all to automatically fix all {total_issues} issues"
            )
            print(
                "   Or use individual flags: --fix-sorting, --fix-case, --fix-duplicates"
            )

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
