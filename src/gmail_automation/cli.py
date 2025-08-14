import argparse
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from dateutil import parser
from zoneinfo import ZoneInfo
from googleapiclient.errors import HttpError

from . import __version__

from .config import (
    load_configuration,
    check_files_existence,
    unix_to_readable,
    get_last_run_time,
    update_last_run_time,
)
from .gmail_service import (
    get_credentials,
    build_service,
    get_existing_labels_cached,
    batch_fetch_messages,
    fetch_emails_to_label_optimized,
    modify_message,
)

message_details_cache = {}
processed_queries = set()


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
    info_file_handler.setFormatter(info_file_formatter)

    debug_file_handler = logging.FileHandler(debug_log_file_path, encoding="utf-8")
    debug_file_handler.setLevel(logging.DEBUG)
    debug_file_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )
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
                log_date = parser.parse(log_date_str)
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
                log_date = parser.parse(log_date_str)
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


def parse_email_date(date_str):
    try:
        date = parser.parse(date_str)
        if date.tzinfo is None:
            date = date.replace(tzinfo=ZoneInfo("America/Los_Angeles"))
        return date
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
                f"Missing details for message ID {msg_id}: {validation['missing_details']}"
            )
            logging.info(
                f"Available details for message ID {msg_id}: {validation['available_details']}"
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
        f"Caching incomplete details for message ID {msg_id}: (subject={subject}, date={date}, sender={sender})"
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

    current_labels = (
        service.users()
        .messages()
        .get(userId=user_id, id=msg_id)
        .execute()
        .get("labelIds", [])
    )
    if msg_id in current_run_processed_ids:
        logging.debug(f"Email ID {msg_id} already processed in this run. Skipping.")
        return False

    label_id_to_add = existing_labels.get(label)
    if label_id_to_add not in current_labels:
        if dry_run:
            logging.info(
                f"Dry run: would modify email from '{sender}' with label '{label}'"
            )
        else:
            modify_message(
                service, user_id, msg_id, [label_id_to_add], ["INBOX"], mark_read
            )
            processed_email_ids.add(msg_id)
            logging.info(
                f'Email from: "{sender}" dated: "{date}", and with subject: "{subject}" was modified with label "{label}", marked as read: "{mark_read}" and removed from Inbox.'
            )

    if delete_after_days is not None:
        logging.debug(f"Attempting to parse date: '{date}' for message ID: {msg_id}")
        try:
            email_date = parse_email_date(date)
            if email_date is not None:
                if email_date.tzinfo is None:
                    email_date = email_date.replace(tzinfo=ZoneInfo("America/Los_Angeles"))
                current_time = datetime.now(ZoneInfo("America/Los_Angeles"))
                days_diff = (current_time - email_date).days
                if days_diff >= delete_after_days:
                    logging.info(
                        f"Deleting email from: '{sender}' with subject: '{subject}' as it is older than {delete_after_days} days."
                    )
                if dry_run:
                    logging.info("Dry run enabled; email not deleted.")
                else:
                    service.users().messages().delete(
                        userId=user_id, id=msg_id
                    ).execute()
                return True
        except Exception as e:
            logging.error(f"Error parsing date for message ID {msg_id}: {e}")
            return False
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
            f'No emails found for {criterion_type}: "{criterion_value}" for label: "{label}".'
        )
        return False

    msg_ids = [msg["id"] for msg in messages]
    batched_messages = batch_fetch_messages(service, user_id, msg_ids)

    for msg_id in msg_ids:
        message_data = batched_messages.get(msg_id)
        if not message_data:
            logging.error(f"Message ID {msg_id} not found in batch fetch.")
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
        f'Processed {modified_emails_count} emails and skipped {skipped_emails_count} emails for {criterion_type}: "{criterion_value}" with label "{label}".'
    )
    return any_emails_processed


def process_emails_for_labeling(
    service, user_id, existing_labels, config, last_run_time, dry_run=False
):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(script_dir, os.pardir, os.pardir))
    data_dir = os.path.join(root_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    processed_ids_file = os.path.join(data_dir, "processed_email_ids.txt")
    processed_email_ids = load_processed_email_ids(processed_ids_file)
    current_run_processed_ids = set()
    expected_labels = {}

    any_emails_processed = False

    logging.info("Processing keywords to labels:")
    for keyword, label_info in config.get("KEYWORDS_TO_LABELS", {}).items():
        label, mark_read = label_info
        if label not in existing_labels:
            logging.warning(
                f"The label '{label}' does not exist. Existing labels: {list(existing_labels.keys())}"
            )
            continue
        query = f'subject:"{keyword}" label:inbox after:{int(last_run_time)}'
        emails_processed = process_emails_by_criteria(
            service,
            user_id,
            query,
            label,
            mark_read,
            None,
            existing_labels,
            current_run_processed_ids,
            processed_email_ids,
            expected_labels,
            config,
            dry_run=dry_run,
            criterion_type="keyword",
            criterion_value=keyword,
        )
        if emails_processed:
            any_emails_processed = True

    logging.info("Processing sender categories:")
    for sender_category, sender_info in config.get("SENDER_TO_LABELS", {}).items():
        if sender_category not in existing_labels:
            logging.warning(
                f"The label '{sender_category}' does not exist. Existing labels: {list(existing_labels.keys())}"
            )
            continue
        for info in sender_info:
            mark_read = info["read_status"]
            delete_after_days = info.get("delete_after_days", None)
            emails = info["emails"]
            for email in emails:
                query = f"from:{email} label:inbox after:{int(last_run_time)}"
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
        last_run_time = get_last_run_time()

        existing_labels = get_existing_labels_cached(service)

        emails_processed = process_emails_for_labeling(
            service,
            user_id,
            existing_labels,
            config,
            last_run_time,
            dry_run=args.dry_run,
        )

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
