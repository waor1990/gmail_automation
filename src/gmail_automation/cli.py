import argparse
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from dateutil import parser
from zoneinfo import ZoneInfo
from googleapiclient.errors import HttpError

from . import __version__

from .config import (
    load_configuration,
    check_files_existence,
    unix_to_readable,
    get_sender_last_run_times,
    update_sender_last_run_times,
    update_last_run_time,
    DEFAULT_LAST_RUN_TIME,
)
from .gmail_service import (
    get_credentials,
    build_service,
    get_existing_labels_cached,
    batch_fetch_messages,
    fetch_emails_to_label_optimized,
    modify_message,
)
from .logging_utils import get_logger, setup_logging
from .ignored_rules import IgnoredRulesEngine, IgnoredRule

message_details_cache: Dict[
    str, Tuple[Optional[str], Optional[str], Optional[str], Optional[bool]]
] = {}
processed_queries: Set[str] = set()

TZINFOS: dict[str, ZoneInfo] = {
    "UTC": ZoneInfo("UTC"),
    "PST": ZoneInfo("America/Los_Angeles"),
    "PDT": ZoneInfo("America/Los_Angeles"),
    "MST": ZoneInfo("America/Denver"),
    "MDT": ZoneInfo("America/Denver"),
    "CST": ZoneInfo("America/Chicago"),
    "CDT": ZoneInfo("America/Chicago"),
    "EST": ZoneInfo("America/New_York"),
    "EDT": ZoneInfo("America/New_York"),
}


logger = get_logger(__name__)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Gmail automation script")
    parser.add_argument(
        "--config",
        "-c",
        help="Path to configuration file",
        default=None,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without modifying messages",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging (equivalent to --log-level DEBUG)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level (default: INFO)",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Optional path to a log file",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"gmail_automation {__version__}",
    )
    return parser.parse_args(argv)


def parse_email_date(date_str: str) -> Optional[datetime]:
    """Parse an email date string and return it in Pacific time.

    Args:
        date_str: Date string extracted from an email header.

    Returns:
        A timezone-aware ``datetime`` in the ``America/Los_Angeles`` timezone or
        ``None`` if parsing fails.
    """

    try:
        parsed_date = parser.parse(date_str, tzinfos=TZINFOS)
        if parsed_date.tzinfo is None:
            parsed_date = parsed_date.replace(tzinfo=ZoneInfo("America/Los_Angeles"))
        return parsed_date.astimezone(ZoneInfo("America/Los_Angeles"))
    except Exception as e:
        logger.error(
            f"Error parsing date string '{date_str}': {e}",
            exc_info=True,
        )
        return None


def parse_header(headers, header_name):
    return next(
        (
            header["value"]
            for header in headers
            if header["name"].lower() == header_name.lower()
        ),
        None,
    )


def validate_details(details, expected_keys):
    missing_details = [
        key for key in expected_keys if key not in details or details[key] is None
    ]
    available_details = {
        key: value
        for key, value in details.items()
        if key in expected_keys and value is not None
    }
    return {"missing_details": missing_details, "available_details": available_details}


def get_message_details(service, user_id, msg_id):
    try:
        message = service.users().messages().get(userId=user_id, id=msg_id).execute()
        if (
            not message
            or "payload" not in message
            or "headers" not in message["payload"]
        ):
            logger.error(f"Invalid message structure for ID {msg_id}: {message}")
            return None, None, None, None
        headers = message["payload"]["headers"]
        subject = parse_header(headers, "subject")
        date_str = parse_header(headers, "date")
        sender = parse_header(headers, "from")
        is_unread = "UNREAD" in message.get("labelIds", [])
        details = {"subject": subject, "date": date_str, "sender": sender}
        validation = validate_details(details, ["subject", "date", "sender"])
        if validation["missing_details"]:
            logger.error(
                "Missing details for message ID %s: %s",
                msg_id,
                validation["missing_details"],
            )
            logger.info(
                "Available details for message ID %s: %s",
                msg_id,
                validation["available_details"],
            )
            return None, None, None, None
        date = parse_email_date(date_str)
        formatted_date = date.strftime("%m/%d/%Y, %I:%M %p %Z") if date else None
        return subject, formatted_date, sender, is_unread
    except Exception as e:
        logger.error(
            f"Error getting message details for ID {msg_id}: {e}",
            exc_info=True,
        )
        return None, None, None, None


def get_message_details_cached(service, user_id, msg_id):
    if msg_id in message_details_cache:
        cached = message_details_cache.get(msg_id)
        if isinstance(cached, tuple) and len(cached) == 4:
            return cached
        logger.warning(f"Invalid cache format for message ID {msg_id}: {cached}")
    subject, date, sender, is_unread = get_message_details(service, user_id, msg_id)
    if subject is not None and date is not None and sender is not None:
        message_details_cache[msg_id] = (subject, date, sender, is_unread)
        return subject, date, sender, is_unread
    logger.error(
        (
            "Caching incomplete details for message ID %s: "
            "(subject=%s, date=%s, sender=%s)"
        ),
        msg_id,
        subject,
        date,
        sender,
    )
    message_details_cache[msg_id] = (None, None, None, None)
    return None, None, None, None


def load_processed_email_ids(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return set(f.read().splitlines())
    return set()


def save_processed_email_ids(file_path, email_ids):
    with open(file_path, "w", encoding="utf-8") as f:
        for email_id in email_ids:
            f.write(email_id + "\n")


def apply_ignored_rule_actions(
    service,
    user_id: str,
    msg_id: str,
    sender: str | None,
    subject: str | None,
    date: str | None,
    parsed_date: datetime | None,
    rule: IgnoredRule,
    existing_labels: Dict[str, str],
    dry_run: bool,
) -> tuple[List[str], bool]:
    """Apply pipeline actions for a matched ignored-email rule."""

    actions = rule.actions
    executed: List[str] = []
    deleted = False

    delete_after = actions.delete_after_days
    if delete_after is not None:
        should_delete = False
        if delete_after == 0:
            should_delete = True
        elif parsed_date is not None:
            current_time = datetime.now(ZoneInfo("America/Los_Angeles"))
            age_days = (current_time - parsed_date).days
            if age_days >= delete_after:
                should_delete = True
            else:
                logger.debug(
                    (
                        "Email %s is %s days old; below delete_after_days=%s "
                        "for rule '%s'."
                    ),
                    msg_id,
                    age_days,
                    delete_after,
                    rule.name,
                )
        else:
            logger.warning(
                (
                    "Unable to parse date '%s' for message %s; "
                    "skipping delete_after_days=%s for rule '%s'."
                ),
                date,
                msg_id,
                delete_after,
                rule.name,
            )

        if should_delete:
            summary = (
                f"delete (after {delete_after} days)"
                if delete_after > 0
                else "delete (immediate)"
            )
            if dry_run:
                executed.append(f"dry-run {summary}")
                logger.info(
                    "Dry run: would delete email %s from '%s' via rule '%s'",
                    msg_id,
                    sender,
                    rule.name,
                )
                deleted = True
            else:
                try:
                    service.users().messages().delete(
                        userId=user_id, id=msg_id
                    ).execute()
                    executed.append(summary)
                    deleted = True
                except HttpError as error:
                    if error.resp.status == 403:
                        logger.warning(
                            (
                                "Insufficient permissions to delete email %s; "
                                "rule '%s' requested delete_after_days=%s."
                            ),
                            msg_id,
                            rule.name,
                            delete_after,
                        )
                    else:
                        logger.error(
                            "Failed to delete email %s: %s",
                            msg_id,
                            error,
                            exc_info=True,
                        )
            if deleted:
                return executed, True

    label_ids: List[str] = []
    applied_labels: List[str] = []
    missing_labels: List[str] = []
    for label in actions.apply_labels:
        label_id = existing_labels.get(label)
        if label_id is None:
            missing_labels.append(label)
            continue
        label_ids.append(label_id)
        applied_labels.append(label)

    remove_ids: List[str] = []
    if actions.archive:
        remove_ids.append("INBOX")

    if missing_labels:
        logger.warning(
            "Rule '%s' requested labels %s which do not exist.",
            rule.name,
            ", ".join(missing_labels),
        )

    if not (label_ids or remove_ids or actions.mark_as_read):
        return executed, False

    if dry_run:
        if applied_labels:
            executed.append("dry-run applied labels: " + ", ".join(applied_labels))
        if actions.archive:
            executed.append("dry-run archived")
        if actions.mark_as_read:
            executed.append("dry-run marked as read")
        logger.info(
            "Dry run: would modify email %s for rule '%s' with actions: %s",
            msg_id,
            rule.name,
            ", ".join(executed) or "none",
        )
        return executed, False

    modify_message(
        service,
        user_id,
        msg_id,
        label_ids,
        remove_ids,
        actions.mark_as_read,
    )

    if applied_labels:
        executed.append("applied labels: " + ", ".join(applied_labels))
    if actions.archive:
        executed.append("archived")
    if actions.mark_as_read:
        executed.append("marked as read")

    return executed, False


def process_email(
    service,
    user_id,
    msg_id,
    subject,
    date,
    sender,
    is_unread,
    label,
    mark_read,
    delete_after_days,
    ignored_rules: IgnoredRulesEngine,
    existing_labels,
    current_run_processed_ids,
    processed_email_ids,
    expected_labels,
    config,
    dry_run=False,
):
    subject, date, sender, is_unread = get_message_details_cached(
        service, user_id, msg_id
    )
    if not subject or not date or not sender:
        logger.debug(f"Missing details for message ID: {msg_id}. Skipping")
        return False

    if msg_id in current_run_processed_ids:
        logger.debug(f"Email ID {msg_id} already processed in this run. Skipping.")
        return False

    parsed_date = parse_email_date(date) if date else None

    for rule in ignored_rules.iter_matches(sender, subject):
        if not rule.actions.has_pipeline_actions():
            logger.debug(
                "Ignored rule '%s' matched message %s without pipeline actions.",
                rule.name,
                msg_id,
            )
            continue
        executed_actions, _ = apply_ignored_rule_actions(
            service,
            user_id,
            msg_id,
            sender,
            subject,
            date,
            parsed_date,
            rule,
            existing_labels,
            dry_run,
        )
        skip_flags = [
            flag
            for flag, enabled in (
                ("skip_analysis", rule.actions.skip_analysis),
                ("skip_import", rule.actions.skip_import),
            )
            if enabled
        ]
        flag_suffix = f" (flags: {', '.join(skip_flags)})" if skip_flags else ""
        summary = (
            ", ".join(executed_actions) if executed_actions else "no pipeline actions"
        )
        logger.info(
            "Ignored rule '%s'%s applied to %s: %s",
            rule.name,
            flag_suffix,
            sender,
            summary,
        )
        current_run_processed_ids.add(msg_id)
        if not dry_run:
            processed_email_ids.add(msg_id)
        return True

    if delete_after_days is not None:
        if parsed_date is None:
            logger.debug(
                "Skipping delete_after_days for %s; unable to parse date '%s'",
                msg_id,
                date,
            )
        else:
            current_time = datetime.now(ZoneInfo("America/Los_Angeles"))
            days_diff = (current_time - parsed_date).days
            if days_diff >= delete_after_days:
                logger.info(
                    (
                        "Deleting email from '%s' with subject '%s' dated '%s' "
                        "as it is older than %s days."
                    ),
                    sender,
                    subject,
                    date,
                    delete_after_days,
                )
                if dry_run:
                    logger.info("Dry run enabled; email not deleted.")
                else:
                    try:
                        service.users().messages().delete(
                            userId=user_id, id=msg_id
                        ).execute()
                        logger.info(f"Email deleted successfully: {msg_id}")
                    except HttpError as delete_error:
                        if delete_error.resp.status == 403:
                            logger.warning(
                                (
                                    "Insufficient permissions to delete email %s. "
                                    "Email was labeled but not deleted. "
                                    "To enable deletion, re-authorize with broader "
                                    "Gmail permissions."
                                ),
                                msg_id,
                            )
                        else:
                            logger.error(
                                f"Failed to delete email {msg_id}: {delete_error}",
                                exc_info=True,
                            )
                return True
            logger.debug(
                (
                    "Email from '%s' is only %s days old, not deleting "
                    "(threshold: %s days)"
                ),
                sender,
                days_diff,
                delete_after_days,
            )

    current_labels = (
        service.users()
        .messages()
        .get(userId=user_id, id=msg_id)
        .execute()
        .get("labelIds", [])
    )

    label_id_to_add = existing_labels.get(label)
    if label_id_to_add not in current_labels:
        if dry_run:
            logger.info(
                "Dry run: would modify email from '%s' with label '%s'",
                sender,
                label,
            )
        else:
            modify_message(
                service, user_id, msg_id, [label_id_to_add], ["INBOX"], mark_read
            )
            processed_email_ids.add(msg_id)
            logger.info(
                (
                    "Email from '%s' dated '%s' with subject '%s' was modified "
                    "with label '%s', marked as read: '%s' "
                    "and removed from Inbox."
                ),
                sender,
                date,
                subject,
                label,
                mark_read,
            )

    return True


def process_emails_by_criteria(
    service,
    user_id,
    query,
    label,
    mark_read,
    delete_after_days,
    ignored_rules: IgnoredRulesEngine,
    existing_labels,
    current_run_processed_ids,
    processed_email_ids,
    expected_labels,
    config,
    dry_run=False,
    criterion_type="keyword",
    criterion_value="",
):
    messages = fetch_emails_to_label_optimized(service, user_id, query)
    skipped_emails_count = 0
    modified_emails_count = 0
    any_emails_processed = False

    if not messages:
        logger.info(
            "No emails found for %s: '%s' for label: '%s'.",
            criterion_type,
            criterion_value,
            label,
        )
        return False

    msg_ids = [msg["id"] for msg in messages]
    batched_messages = batch_fetch_messages(service, user_id, msg_ids)

    for msg_id in msg_ids:
        message_data = batched_messages.get(msg_id)
        if not message_data:
            logger.error(
                "Message ID %s was not located in batch fetch.",
                msg_id,
            )
            skipped_emails_count += 1
            continue
        subject, date, sender, is_unread = get_message_details_cached(
            service, user_id, msg_id
        )
        if not subject or not date or not sender:
            logger.debug(f"Missing details for message ID: {msg_id}. Skipping.")
            skipped_emails_count += 1
            continue
        if msg_id in processed_email_ids or msg_id in current_run_processed_ids:
            logger.debug(f"Skipping already processed email ID: {msg_id}")
            skipped_emails_count += 1
            continue
        if process_email(
            service,
            user_id,
            msg_id,
            subject,
            date,
            sender,
            is_unread,
            label,
            mark_read,
            delete_after_days,
            ignored_rules,
            existing_labels,
            current_run_processed_ids,
            processed_email_ids,
            expected_labels,
            config,
            dry_run=dry_run,
        ):
            modified_emails_count += 1
            any_emails_processed = True
        else:
            skipped_emails_count += 1

    logger.debug(
        "Processed %s emails and skipped %s emails for %s: '%s' with label '%s'.",
        modified_emails_count,
        skipped_emails_count,
        criterion_type,
        criterion_value,
        label,
    )
    return any_emails_processed


def process_emails_for_labeling(
    service,
    user_id,
    existing_labels,
    config,
    last_run_times: Dict[str, float],
    current_time: float,
    ignored_rules: IgnoredRulesEngine,
    dry_run: bool = False,
):
    """Process emails for all configured senders and apply labels.

    Args:
        service: Authorized Gmail API service instance.
        user_id: Gmail user identifier, usually ``"me"``.
        existing_labels: Mapping of label names to label IDs.
        config: Loaded configuration dictionary.
        last_run_times: Per-sender mapping of last processed timestamps.
        current_time: Timestamp to record as the new last run time.
        dry_run: When ``True``, fetch emails without modifying them.

    Returns:
        ``True`` if any emails were processed and modified.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(script_dir, os.pardir, os.pardir))
    data_dir = os.path.join(root_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    processed_ids_file = os.path.join(data_dir, "processed_email_ids.txt")
    processed_email_ids = load_processed_email_ids(processed_ids_file)
    current_run_processed_ids: Set[str] = set()
    expected_labels: Dict[str, str] = {}

    any_emails_processed = False

    logger.info("Processing sender categories:")
    for sender_category, sender_info in config.get("SENDER_TO_LABELS", {}).items():
        if sender_category not in existing_labels:
            logger.warning(
                (
                    f"The label '{sender_category}' does not exist. Existing labels: "
                    f"{list(existing_labels.keys())}"
                )
            )
            continue
        for info in sender_info:
            mark_read = info["read_status"]
            delete_after_days = info.get("delete_after_days", None)
            emails = info["emails"]
            for email in emails:
                sender_last_run = last_run_times.get(email, DEFAULT_LAST_RUN_TIME)
                query = "from:{sender} label:inbox after:{timestamp}".format(
                    sender=email, timestamp=int(sender_last_run)
                )
                emails_processed = process_emails_by_criteria(
                    service,
                    user_id,
                    query,
                    sender_category,
                    mark_read,
                    delete_after_days,
                    ignored_rules,
                    existing_labels,
                    current_run_processed_ids,
                    processed_email_ids,
                    expected_labels,
                    config,
                    dry_run=dry_run,
                    criterion_type="sender",
                    criterion_value=email,
                )
                if emails_processed:
                    any_emails_processed = True
                    last_run_times[email] = current_time

    save_processed_email_ids(processed_ids_file, processed_email_ids)
    return any_emails_processed


def main(argv=None):
    args = parse_args(argv)
    try:
        level = "DEBUG" if args.verbose else args.log_level
        log_file = Path(args.log_file) if args.log_file else None
        setup_logging(level=level, log_file=log_file)
        logger.info("-" * 72)
        logger.debug("Script started")
        logger.info("Starting Gmail_Automation.")

        config = load_configuration(args.config)
        check_files_existence()
        if not config:
            logger.error("Configuration could not be loaded. Exiting.")
            return

        current_time = datetime.now(ZoneInfo("America/Los_Angeles")).timestamp()
        logger.info(f"Current Time: {unix_to_readable(current_time)}")

        credentials = get_credentials()
        service = build_service(credentials)

        user_id = "me"

        # Collect all senders configured for labeling
        senders = {
            email
            for entries in config.get("SENDER_TO_LABELS", {}).values()
            for info in entries
            for email in info.get("emails", [])
        }
        last_run_times = get_sender_last_run_times(senders)

        existing_labels = get_existing_labels_cached(service)
        ignored_rules = IgnoredRulesEngine.from_config(config.get("IGNORED_EMAILS", []))

        emails_processed = process_emails_for_labeling(
            service,
            user_id,
            existing_labels,
            config,
            last_run_times,
            current_time,
            ignored_rules,
            dry_run=args.dry_run,
        )

        if not args.dry_run:
            update_sender_last_run_times(last_run_times)

        if emails_processed and not args.dry_run:
            update_last_run_time(current_time)
            logger.info(f"Last run time updated: {unix_to_readable(current_time)}")
        elif emails_processed:
            logger.info("Dry run enabled; last run time not updated.")
        else:
            logger.info("No emails processed, skipping last run time update.")

        logger.info("Script completed")

    except HttpError as error:
        logger.error(f"An error occured: {error}", exc_info=True)


if __name__ == "__main__":
    main()
