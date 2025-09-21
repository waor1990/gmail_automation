import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Set, Tuple

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


ConfirmationProvider = Callable[[str, Dict[str, Any]], bool]

DEFERRED_DELETION_FILENAME = "deferred_deletions.json"


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
        "--confirm-delete",
        action="store_true",
        help=(
            "Confirm deletion actions for selected emails "
            "without an interactive prompt."
        ),
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


def get_data_directory() -> str:
    """Return the repository data directory, ensuring it exists."""

    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(script_dir, os.pardir, os.pardir))
    data_dir = os.path.join(root_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def get_deferred_deletion_path(data_dir: str) -> str:
    """Return the absolute path to the deferred deletions state file."""

    return os.path.join(data_dir, DEFERRED_DELETION_FILENAME)


def load_deferred_deletions(file_path: str) -> Dict[str, Dict[str, Any]]:
    """Load persisted deferred deletion requests from disk."""

    if not os.path.exists(file_path):
        return {}
    try:
        with open(file_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        logger.error(
            "Failed to load deferred deletions from %s: %s",
            file_path,
            error,
            exc_info=True,
        )
        return {}
    if not isinstance(data, dict):
        logger.error(
            "Deferred deletion file %s contained invalid structure. Starting fresh.",
            file_path,
        )
        return {}
    normalized: Dict[str, Dict[str, Any]] = {}
    for msg_id, metadata in data.items():
        if isinstance(metadata, dict):
            normalized[str(msg_id)] = metadata
        else:
            logger.warning(
                "Ignoring malformed deferred deletion entry for %s in %s.",
                msg_id,
                file_path,
            )
    return normalized


def save_deferred_deletions(file_path: str, state: Dict[str, Dict[str, Any]]) -> None:
    """Persist deferred deletion requests to disk."""

    try:
        with open(file_path, "w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, sort_keys=True)
    except OSError as error:
        logger.error(
            "Failed to persist deferred deletions to %s: %s",
            file_path,
            error,
            exc_info=True,
        )


def build_confirmation_provider(auto_confirm: bool) -> ConfirmationProvider:
    """Create a confirmation callback honoring the CLI configuration."""

    def provider(message_id: str, context: Dict[str, Any]) -> bool:
        prompt = context.get("prompt") or context.get("rule_name") or message_id
        confirmation_message = context.get(
            "confirmation_message",
            f"Delete message {message_id} ({prompt})? [y/N]: ",
        )
        if auto_confirm:
            logger.debug(
                "Auto-confirmation enabled for deletion of %s (rule: %s).",
                message_id,
                context.get("rule_name"),
            )
            return True
        try:
            response = input(confirmation_message)
        except EOFError:
            logger.error(
                "Failed to obtain confirmation for message %s due to EOF.",
                message_id,
            )
            return False
        if response.strip().lower() in {"y", "yes"}:
            return True
        logger.info("User declined deletion for message %s.", message_id)
        return False

    return provider


def is_message_protected(
    label_ids: Tuple[str, ...] | list[str],
    global_protected_labels: Tuple[str, ...] | list[str],
    rule_protected_labels: Tuple[str, ...] | list[str],
    label_id_to_name: Dict[str, str],
) -> bool:
    """Return ``True`` if the message has any protected labels."""

    protected = set(global_protected_labels or []) | set(rule_protected_labels or [])
    if not protected:
        return False
    message_labels = {label for label in label_ids}
    message_labels.update(label_id_to_name.get(label, label) for label in label_ids)
    return any(label in protected for label in message_labels)


def extract_message_metadata(
    message_id: str, message: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Extract normalized metadata from a Gmail message resource."""

    if not message or "payload" not in message or "headers" not in message["payload"]:
        logger.error(f"Invalid message structure for ID {message_id}: {message}")
        return None

    headers = message["payload"]["headers"]
    subject = parse_header(headers, "subject")
    date_str = parse_header(headers, "date")
    sender = parse_header(headers, "from")
    details = {"subject": subject, "date": date_str, "sender": sender}
    validation = validate_details(details, ["subject", "date", "sender"])
    if validation["missing_details"]:
        logger.error(
            "Missing details for message ID %s: %s",
            message_id,
            validation["missing_details"],
        )
        logger.info(
            "Available details for message ID %s: %s",
            message_id,
            validation["available_details"],
        )
        return None

    parsed_date = parse_email_date(date_str or "")
    formatted_date = (
        parsed_date.strftime("%m/%d/%Y, %I:%M %p %Z") if parsed_date else None
    )
    is_unread = "UNREAD" in message.get("labelIds", [])
    return {
        "subject": subject,
        "formatted_date": formatted_date,
        "sender": sender,
        "is_unread": is_unread,
        "label_ids": message.get("labelIds", []),
        "raw_date": date_str,
    }


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
        metadata = extract_message_metadata(msg_id, message)
        if metadata is None:
            return None, None, None, None
        return (
            metadata["subject"],
            metadata["formatted_date"],
            metadata["sender"],
            metadata["is_unread"],
        )
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
        logger.debug(f"Missing details for message ID: {msg_id}. Skipping")
        return False

    if msg_id in current_run_processed_ids:
        logger.debug(f"Email ID {msg_id} already processed in this run. Skipping.")
        return False

    if delete_after_days is not None:
        logger.debug(f"Attempting to parse date: '{date}' for message ID: {msg_id}")
        try:
            email_date = parse_email_date(date)
            if email_date is not None:
                current_time = datetime.now(ZoneInfo("America/Los_Angeles"))
                days_diff = (current_time - email_date).days
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
                else:
                    logger.debug(
                        (
                            "Email from '%s' is only %s days old, not deleting "
                            "(threshold: %s days)"
                        ),
                        sender,
                        days_diff,
                        delete_after_days,
                    )
        except Exception as e:
            logger.error(
                f"Error parsing date for message ID {msg_id}: {e}",
                exc_info=True,
            )
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
    data_dir = get_data_directory()
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


def process_selected_email_deletions(
    service,
    user_id: str,
    existing_labels: Dict[str, str],
    config: Dict[str, Any],
    data_dir: str,
    confirmation_provider: ConfirmationProvider,
    dry_run: bool = False,
    actor: str = "system",
) -> bool:
    """Delete emails selected via configuration rules."""

    rules = config.get("SELECTED_EMAIL_DELETIONS", [])
    if not rules:
        return False

    os.makedirs(data_dir, exist_ok=True)
    deferred_path = get_deferred_deletion_path(data_dir)
    existing_deferred = load_deferred_deletions(deferred_path)
    updated_deferred = dict(existing_deferred)
    state_changed = False
    any_action = False

    global_protected = config.get("PROTECTED_LABELS", []) or []
    label_id_to_name = {label_id: name for name, label_id in existing_labels.items()}

    for rule in rules:
        if not rule.get("enabled", True):
            logger.info("Skipping disabled deletion rule '%s'.", rule.get("name"))
            continue

        rule_name = rule.get("name", "Unnamed Rule")
        message_ids = set(rule.get("message_ids", []))
        query = rule.get("query")
        if query:
            try:
                messages = fetch_emails_to_label_optimized(service, user_id, query)
            except HttpError as error:
                logger.error(
                    "Failed to fetch messages for deletion rule '%s': %s",
                    rule_name,
                    error,
                    exc_info=True,
                )
                continue
            message_ids.update(message["id"] for message in messages or [])

        if not message_ids:
            logger.info(
                "No messages matched deletion rule '%s'.",
                rule_name,
            )
            continue

        for msg_id in sorted(message_ids):
            try:
                message = (
                    service.users().messages().get(userId=user_id, id=msg_id).execute()
                )
            except HttpError as error:
                logger.error(
                    "Error retrieving message %s for deletion rule '%s': %s",
                    msg_id,
                    rule_name,
                    error,
                    exc_info=True,
                )
                continue

            metadata = extract_message_metadata(msg_id, message)
            if metadata is None:
                continue

            if is_message_protected(
                tuple(metadata.get("label_ids", [])),
                tuple(global_protected),
                tuple(rule.get("protected_labels", [])),
                label_id_to_name,
            ):
                logger.info(
                    "Skipping deletion for message %s due to protected labels "
                    "(rule '%s').",
                    msg_id,
                    rule_name,
                )
                continue

            defer_until_read = bool(rule.get("defer_until_read", False))
            deletion_mode = "deferred" if defer_until_read else "instant"

            if defer_until_read and metadata.get("is_unread"):
                timestamp = datetime.now(timezone.utc).isoformat()
                if dry_run:
                    logger.info(
                        "Dry run: would defer deletion of message %s for rule '%s' "
                        "until it is read.",
                        msg_id,
                        rule_name,
                    )
                else:
                    updated_deferred[msg_id] = {
                        "rule_name": rule_name,
                        "protected_labels": rule.get("protected_labels", []),
                        "requested_at": timestamp,
                    }
                    state_changed = True
                    logger.info(
                        "Deferred deletion of message %s for rule '%s' until it "
                        "is read.",
                        msg_id,
                        rule_name,
                    )
                any_action = True
                continue

            prompt_value = f"{metadata.get('sender')} - {metadata.get('subject')}"
            context = {
                "rule_name": rule_name,
                "prompt": prompt_value,
                "mode": deletion_mode,
            }
            if not confirmation_provider(msg_id, context):
                logger.info(
                    "Deletion not confirmed for message %s under rule '%s'.",
                    msg_id,
                    rule_name,
                )
                continue

            timestamp = datetime.now(timezone.utc).isoformat()
            if dry_run:
                logger.info(
                    "Dry run: would delete message %s at %s by %s in %s mode "
                    "under rule '%s'.",
                    msg_id,
                    timestamp,
                    actor,
                    deletion_mode,
                    rule_name,
                )
                any_action = True
                continue

            try:
                service.users().messages().delete(userId=user_id, id=msg_id).execute()
                logger.info(
                    "Deleted message %s at %s by %s in %s mode under rule '%s'.",
                    msg_id,
                    timestamp,
                    actor,
                    deletion_mode,
                    rule_name,
                )
                any_action = True
            except HttpError as error:
                logger.error(
                    "Failed to delete message %s under rule '%s': %s",
                    msg_id,
                    rule_name,
                    error,
                    exc_info=True,
                )

    if not dry_run and state_changed:
        save_deferred_deletions(deferred_path, updated_deferred)

    return any_action


def process_deferred_selected_deletions(
    service,
    user_id: str,
    existing_labels: Dict[str, str],
    config: Dict[str, Any],
    data_dir: str,
    confirmation_provider: ConfirmationProvider,
    dry_run: bool = False,
    actor: str = "system",
) -> bool:
    """Process deferred deletion requests that are now eligible."""

    os.makedirs(data_dir, exist_ok=True)
    deferred_path = get_deferred_deletion_path(data_dir)
    deferred_state = load_deferred_deletions(deferred_path)
    if not deferred_state:
        return False

    label_id_to_name = {label_id: name for name, label_id in existing_labels.items()}
    global_protected = config.get("PROTECTED_LABELS", []) or []

    updated_state = dict(deferred_state)
    state_changed = False
    any_action = False

    for msg_id, metadata in deferred_state.items():
        rule_name = metadata.get("rule_name", "deferred")
        rule_protected = metadata.get("protected_labels", []) or []
        try:
            message = (
                service.users().messages().get(userId=user_id, id=msg_id).execute()
            )
        except HttpError as error:
            status = getattr(error, "resp", None)
            status_code = getattr(status, "status", None)
            if status_code == 404:
                logger.info(
                    "Deferred message %s no longer exists; removing from queue.",
                    msg_id,
                )
                if not dry_run:
                    updated_state.pop(msg_id, None)
                    state_changed = True
                any_action = True
                continue
            logger.error(
                "Failed to retrieve deferred message %s: %s",
                msg_id,
                error,
                exc_info=True,
            )
            continue

        message_metadata = extract_message_metadata(msg_id, message)
        if message_metadata is None:
            continue

        if message_metadata.get("is_unread"):
            logger.debug(
                "Message %s remains unread; deferring deletion (rule '%s').",
                msg_id,
                rule_name,
            )
            continue

        if is_message_protected(
            tuple(message_metadata.get("label_ids", [])),
            tuple(global_protected),
            tuple(rule_protected),
            label_id_to_name,
        ):
            logger.info(
                "Skipping deferred deletion for message %s due to protected "
                "labels (rule '%s').",
                msg_id,
                rule_name,
            )
            continue

        prompt_value = (
            f"{message_metadata.get('sender')} - " f"{message_metadata.get('subject')}"
        )
        context = {
            "rule_name": rule_name,
            "prompt": prompt_value,
            "mode": "deferred",
        }
        if not confirmation_provider(msg_id, context):
            logger.info(
                "Deferred deletion not confirmed for message %s (rule '%s').",
                msg_id,
                rule_name,
            )
            continue

        timestamp = datetime.now(timezone.utc).isoformat()
        if dry_run:
            logger.info(
                "Dry run: would delete deferred message %s at %s by %s in "
                "deferred mode (rule '%s').",
                msg_id,
                timestamp,
                actor,
                rule_name,
            )
            any_action = True
            continue

        try:
            service.users().messages().delete(userId=user_id, id=msg_id).execute()
            logger.info(
                "Deleted deferred message %s at %s by %s in deferred mode "
                "(rule '%s').",
                msg_id,
                timestamp,
                actor,
                rule_name,
            )
            updated_state.pop(msg_id, None)
            state_changed = True
            any_action = True
        except HttpError as error:
            logger.error(
                "Failed to delete deferred message %s (rule '%s'): %s",
                msg_id,
                rule_name,
                error,
                exc_info=True,
            )

    if not dry_run and state_changed:
        save_deferred_deletions(deferred_path, updated_state)

    return any_action


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

        data_dir = get_data_directory()
        confirmation_provider = build_confirmation_provider(args.confirm_delete)

        deferred_processed = process_deferred_selected_deletions(
            service,
            user_id,
            existing_labels,
            config,
            data_dir,
            confirmation_provider,
            dry_run=args.dry_run,
            actor=user_id,
        )

        emails_processed = process_emails_for_labeling(
            service,
            user_id,
            existing_labels,
            config,
            last_run_times,
            current_time,
            dry_run=args.dry_run,
        )

        selected_deletions_processed = process_selected_email_deletions(
            service,
            user_id,
            existing_labels,
            config,
            data_dir,
            confirmation_provider,
            dry_run=args.dry_run,
            actor=user_id,
        )

        if deferred_processed or selected_deletions_processed:
            logger.info(
                "Deletion workflows completed (deferred=%s, selected=%s).",
                deferred_processed,
                selected_deletions_processed,
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
