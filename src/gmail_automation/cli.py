import argparse
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Set, Tuple

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


def setup_logging(verbose: bool = False, log_level: str = "INFO"):
    logging.debug("Setting up logging")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(script_dir, os.pardir, os.pardir))

    logs_dir = os.path.join(root_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    info_log_file_path = os.path.join(logs_dir, "gmail_automation_info.log")
    remove_old_logs(info_log_file_path)
    debug_log_file_path = os.path.join(logs_dir, "gmail_automation_debug.log")
    remove_old_logs_debug(debug_log_file_path)

    info_file_handler = logging.FileHandler(info_log_file_path, encoding="utf-8")
    info_file_handler.setLevel(logging.INFO)
    info_file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    pacific = ZoneInfo("America/Los_Angeles")

    def _to_pacific(ts: float | None) -> time.struct_time:
        return datetime.fromtimestamp(ts or 0.0, pacific).timetuple()

    info_file_formatter.converter = _to_pacific
    info_file_handler.setFormatter(info_file_formatter)

    debug_file_handler = logging.FileHandler(debug_log_file_path, encoding="utf-8")
    debug_file_handler.setLevel(logging.DEBUG)
    debug_file_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
    )
    debug_file_formatter.converter = _to_pacific
    debug_file_handler.setFormatter(debug_file_formatter)

    # Determine console logging level: verbose flag overrides log_level
    if verbose:
        console_level = logging.DEBUG
    else:
        console_level = getattr(logging, log_level.upper(), logging.INFO)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(console_level)
    stream_formatter = logging.Formatter("%(message)s")
    stream_handler.setFormatter(stream_formatter)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    if logger.hasHandlers():
        logger.handlers.clear()

    logger.addHandler(info_file_handler)
    logger.addHandler(debug_file_handler)
    logger.addHandler(stream_handler)

    logging.debug("Logging setup completed")


def remove_old_logs(log_file_path):
    if not os.path.exists(log_file_path):
        return

    cutoff_date = datetime.now(ZoneInfo("UTC")) - timedelta(days=60)
    with open(log_file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()
    with open(log_file_path, "w", encoding="utf-8") as file:
        for line in lines:
            try:
                log_date_str = line.split(" - ")[0]
                log_date = parser.parse(log_date_str, tzinfos=TZINFOS)
                if log_date.tzinfo is None:
                    log_date = log_date.replace(tzinfo=ZoneInfo("UTC"))
                if log_date >= cutoff_date:
                    file.write(line)
            except (ValueError, IndexError):
                file.write(line)


def remove_old_logs_debug(log_file_path):
    if not os.path.exists(log_file_path):
        return

    cutoff_date = datetime.now(ZoneInfo("UTC")) - timedelta(days=7)
    with open(log_file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()
    with open(log_file_path, "w", encoding="utf-8") as file:
        for line in lines:
            try:
                log_date_str = line.split(" - ")[0]
                log_date = parser.parse(log_date_str, tzinfos=TZINFOS)
                if log_date.tzinfo is None:
                    log_date = log_date.replace(tzinfo=ZoneInfo("UTC"))
                if log_date >= cutoff_date:
                    file.write(line)
            except (ValueError, IndexError):
                file.write(line)


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
        logging.error(f"Error parsing date string '{date_str}': {e}")
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
            logging.error(f"Invalid message structure for ID {msg_id}: {message}")
            return None, None, None, None
        headers = message["payload"]["headers"]
        subject = parse_header(headers, "subject")
        date_str = parse_header(headers, "date")
        sender = parse_header(headers, "from")
        is_unread = "UNREAD" in message.get("labelIds", [])
        details = {"subject": subject, "date": date_str, "sender": sender}
        validation = validate_details(details, ["subject", "date", "sender"])
        if validation["missing_details"]:
            logging.error(
                "Missing details for message ID %s: %s",
                msg_id,
                validation["missing_details"],
            )
            logging.info(
                "Available details for message ID %s: %s",
                msg_id,
                validation["available_details"],
            )
            return None, None, None, None
        date = parse_email_date(date_str)
        formatted_date = date.strftime("%m/%d/%Y, %I:%M %p %Z") if date else None
        return subject, formatted_date, sender, is_unread
    except Exception as e:
        logging.error(f"Error getting message details for ID {msg_id}: {e}")
        return None, None, None, None


def get_message_details_cached(service, user_id, msg_id):
    if msg_id in message_details_cache:
        cached = message_details_cache.get(msg_id)
        if isinstance(cached, tuple) and len(cached) == 4:
            return cached
        logging.warning(f"Invalid cache format for message ID {msg_id}: {cached}")
    subject, date, sender, is_unread = get_message_details(service, user_id, msg_id)
    if subject is not None and date is not None and sender is not None:
        message_details_cache[msg_id] = (subject, date, sender, is_unread)
        return subject, date, sender, is_unread
    logging.error(
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
        logging.debug(f"Missing details for message ID: {msg_id}. Skipping")
        return False

    if msg_id in current_run_processed_ids:
        logging.debug(f"Email ID {msg_id} already processed in this run. Skipping.")
        return False

    if delete_after_days is not None:
        logging.debug(f"Attempting to parse date: '{date}' for message ID: {msg_id}")
        try:
            email_date = parse_email_date(date)
            if email_date is not None:
                current_time = datetime.now(ZoneInfo("America/Los_Angeles"))
                days_diff = (current_time - email_date).days
                if days_diff >= delete_after_days:
                    logging.info(
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
                        logging.info("Dry run enabled; email not deleted.")
                    else:
                        try:
                            service.users().messages().delete(
                                userId=user_id, id=msg_id
                            ).execute()
                            logging.info(f"Email deleted successfully: {msg_id}")
                        except HttpError as delete_error:
                            if delete_error.resp.status == 403:
                                logging.warning(
                                    (
                                        "Insufficient permissions to delete email %s. "
                                        "Email was labeled but not deleted. "
                                        "To enable deletion, re-authorize with broader "
                                        "Gmail permissions."
                                    ),
                                    msg_id,
                                )
                            else:
                                logging.error(
                                    f"Failed to delete email {msg_id}: {delete_error}"
                                )
                    return True
                else:
                    logging.debug(
                        (
                            "Email from '%s' is only %s days old, not deleting "
                            "(threshold: %s days)"
                        ),
                        sender,
                        days_diff,
                        delete_after_days,
                    )
        except Exception as e:
            logging.error(f"Error parsing date for message ID {msg_id}: {e}")
            return False

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
            logging.info(
                "Dry run: would modify email from '%s' with label '%s'",
                sender,
                label,
            )
        else:
            modify_message(
                service, user_id, msg_id, [label_id_to_add], ["INBOX"], mark_read
            )
            processed_email_ids.add(msg_id)
            logging.info(
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
        logging.info(
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
            logging.error(
                "Message ID %s was not located in batch fetch.",
                msg_id,
            )
            skipped_emails_count += 1
            continue
        subject, date, sender, is_unread = get_message_details_cached(
            service, user_id, msg_id
        )
        if not subject or not date or not sender:
            logging.debug(f"Missing details for message ID: {msg_id}. Skipping.")
            skipped_emails_count += 1
            continue
        if msg_id in processed_email_ids or msg_id in current_run_processed_ids:
            logging.debug(f"Skipping already processed email ID: {msg_id}")
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

    logging.debug(
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

    logging.info("Processing sender categories:")
    for sender_category, sender_info in config.get("SENDER_TO_LABELS", {}).items():
        if sender_category not in existing_labels:
            logging.warning(
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
        setup_logging(verbose=args.verbose, log_level=args.log_level)
        logging.info("-" * 72)
        logging.debug("Script started")
        logging.info("Starting Gmail_Automation.")

        config = load_configuration(args.config)
        check_files_existence()
        if not config:
            logging.error("Configuration could not be loaded. Exiting.")
            return

        current_time = datetime.now(ZoneInfo("America/Los_Angeles")).timestamp()
        logging.info(f"Current Time: {unix_to_readable(current_time)}")

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

        emails_processed = process_emails_for_labeling(
            service,
            user_id,
            existing_labels,
            config,
            last_run_times,
            current_time,
            dry_run=args.dry_run,
        )

        if not args.dry_run:
            update_sender_last_run_times(last_run_times)

        if emails_processed and not args.dry_run:
            update_last_run_time(current_time)
            logging.info(f"Last run time updated: {unix_to_readable(current_time)}")
        elif emails_processed:
            logging.info("Dry run enabled; last run time not updated.")
        else:
            logging.info("No emails processed, skipping last run time update.")

        logging.info("Script completed")

    except HttpError as error:
        logging.error(f"An error occured: {error}", exc_info=True)


if __name__ == "__main__":
    main()
