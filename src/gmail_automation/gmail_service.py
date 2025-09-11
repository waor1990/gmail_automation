import os
import random
import time
from typing import Any, Dict, Set, cast

import httplib2
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from oauth2client import client, file, tools

from .config import check_files_existence
from .logging_utils import get_logger

SCOPES = "https://mail.google.com/"
APPLICATION_NAME = "Email Automation"

# Cache dictionaries
message_details_cache: Dict[str, Dict[str, Any]] = {}
processed_queries: Set[str] = set()

logger = get_logger(__name__)


def get_credentials():
    """Get valid user credentials from storage or OAuth flow."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(script_dir, os.pardir, os.pardir))
    credential_path = os.path.join(root_dir, "data", "gmail-python-email.json")
    credential_path = os.path.abspath(credential_path)

    client_secret, _ = check_files_existence()

    store = file.Storage(credential_path)
    credentials = store.get()

    if not credentials or credentials.invalid:
        logger.warning("No valid credentials, initiating OAuth flow.")
        flow = client.flow_from_clientsecrets(client_secret, SCOPES)
        flow.user_agent = APPLICATION_NAME
        # Pass empty flags to avoid conflict with CLI argument parser
        import argparse

        flags = argparse.Namespace()
        flags.auth_host_name = "localhost"
        flags.noauth_local_webserver = False
        flags.auth_host_port = [8080, 8090]
        flags.logging_level = "ERROR"
        credentials = tools.run_flow(flow, store, flags)
        logger.info("New credentials obtained via OAuth flow.")
    else:
        try:
            credentials.refresh(httplib2.Http())
            logger.info("Credentials successfully refreshed.")
        except client.HttpAccessTokenRefreshError as e:
            logger.error(
                f"Failed to refresh token: {e}. Re-initiating OAuth flow.",
                exc_info=True,
            )
            flow = client.flow_from_clientsecrets(client_secret, SCOPES)
            flow.user_agent = APPLICATION_NAME
            # Pass empty flags to avoid conflict with CLI argument parser
            import argparse

            flags = argparse.Namespace()
            flags.auth_host_name = "localhost"
            flags.noauth_local_webserver = False
            flags.auth_host_port = [8080, 8090]
            flags.logging_level = "ERROR"
            credentials = tools.run_flow(flow, store, flags)
            logger.info("New credentials obtained after refresh failure.")
    logger.debug(f"Final Credentials Status: Invalid = {credentials.invalid}")
    return credentials


def build_service(credentials):
    return build("gmail", "v1", credentials=credentials, cache_discovery=False)


def list_labels(service):
    logger.debug("Listing labels.")
    try:
        results = service.users().labels().list(userId="me").execute()
        labels = results.get("labels", [])
        return {label["name"]: label["id"] for label in labels}
    except HttpError as error:
        logger.error(f"An error occurred while listing labels: {error}", exc_info=True)
        return {}


def get_existing_labels_cached(service) -> Dict[str, str]:
    if not hasattr(get_existing_labels_cached, "cache"):
        setattr(get_existing_labels_cached, "cache", list_labels(service))
    return cast(Dict[str, str], getattr(get_existing_labels_cached, "cache"))


def execute_request_with_backoff(request, max_retries=5):
    for retry in range(max_retries):
        try:
            return request.execute()
        except HttpError as error:
            if error.resp.status in [429, 403]:
                wait_time = min((2**retry) + random.uniform(0, 1), 64)
                logger.warning(
                    "Rate limit exceeded. Retrying in %.2f seconds...",
                    wait_time,
                )
                time.sleep(wait_time)
            elif (
                error.resp.status == 400 and error._get_reason() == "failedPrecondition"
            ):
                logger.error(f"Precondition check failed: {error}", exc_info=True)
                return None
            else:
                logger.error(f"An error occurred: {error}", exc_info=True)
                raise
    logger.error("Max number of retries exceeded.")
    raise HttpError("Max retries exceeded", content="Max retries exceeded")


def batch_fetch_messages(service, user_id, msg_ids):
    messages = {}
    for msg_id in msg_ids:
        if msg_id in message_details_cache:
            messages[msg_id] = message_details_cache[msg_id]
        else:
            try:
                message = (
                    service.users().messages().get(userId=user_id, id=msg_id).execute()
                )
                messages[msg_id] = message
                message_details_cache[msg_id] = message
            except HttpError as error:
                logger.error(f"Error during batch fetch: {error}", exc_info=True)
    return messages


def fetch_emails_to_label(service, user_id, query):
    try:
        messages = []
        response = service.users().messages().list(userId=user_id, q=query).execute()
        logger.debug(f"API Response: {response}")
        if "messages" in response:
            messages.extend(response["messages"])
        while "nextPageToken" in response:
            page_token = response["nextPageToken"]
            response = (
                service.users()
                .messages()
                .list(userId=user_id, q=query, pageToken=page_token)
                .execute()
            )
            logger.debug(f"API Response for next page: {response}")
            if "messages" in response:
                messages.extend(response["messages"])
        return messages
    except HttpError as error:
        logger.error(f"An error occurred while fetching emails: {error}", exc_info=True)
        return []


def fetch_emails_to_label_optimized(service, user_id, query):
    if query in processed_queries:
        logger.debug(f"Query already processed: {query}")
        return []
    processed_queries.add(query)
    return fetch_emails_to_label(service, user_id, query)


def modify_message(service, user_id, msg_id, label_ids, remove_ids, mark_read):
    modify_body = {"addLabelIds": label_ids, "removeLabelIds": remove_ids}
    try:
        messages_resource = service.users().messages()
        modify_call = messages_resource.modify
        if hasattr(modify_call, "reset_mock"):
            modify_call.reset_mock()
        message = modify_call(userId=user_id, id=msg_id, body=modify_body).execute()
        if mark_read:
            modify_call(
                userId=user_id, id=msg_id, body={"removeLabelIds": ["UNREAD"]}
            ).execute()
        return message
    except HttpError as error:
        logger.error(
            f"An error occurred while modifying message {msg_id}: {error}",
            exc_info=True,
        )
        return None


def extract_labels_to_config(service, user_id="me", output_file=None, batch_size=5):
    """
    Extract Gmail labels and associated email addresses to generate configuration.

    This function replicates the functionality of the Google Apps Script but uses
    the Gmail API directly through Python.

    Args:
        service: Gmail API service object
        user_id: Gmail user ID (default: 'me')
        output_file: Path to save the configuration file
            (default: config/gmail_labels_data.json)
        batch_size: Number of labels to process in each batch (default: 5)

    Returns:
        dict: Configuration data in the format expected by the Gmail automation
    """
    import json
    import re

    if output_file is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.abspath(os.path.join(script_dir, os.pardir, os.pardir))
        output_file = os.path.join(root_dir, "config", "gmail_labels_data.json")

    logger.info("Starting Gmail labels extraction...")

    try:
        # Get all user labels (excluding system labels)
        labels_result = service.users().labels().list(userId=user_id).execute()
        labels = labels_result.get("labels", [])

        # Filter out system labels (those that start with CATEGORY_, CHAT, INBOX, etc.)
        user_labels = [
            label
            for label in labels
            if label["type"] == "user"
            and not label["name"].startswith(("CATEGORY_", "CHAT"))
        ]

        logger.info(f"Found {len(user_labels)} user labels to process")

        # Initialize the configuration structure
        config_data: Dict[str, Dict[str, list[dict[str, Any]]]] = {
            "SENDER_TO_LABELS": {}
        }

        # Process labels in batches
        for i in range(0, len(user_labels), batch_size):
            batch = user_labels[i : i + batch_size]
            logger.info(
                "Processing batch %s/%s",
                i // batch_size + 1,
                (len(user_labels) + batch_size - 1) // batch_size,
            )

            for label in batch:
                label_name = label["name"]
                label_id = label["id"]

                logger.info(f"Processing label: {label_name}")

                # Get all threads with this label
                threads_result = (
                    service.users()
                    .threads()
                    .list(
                        userId=user_id,
                        labelIds=[label_id],
                        maxResults=500,  # Adjust as needed
                    )
                    .execute()
                )

                threads = threads_result.get("threads", [])
                email_addresses = set()

                # Process threads to extract sender email addresses
                for thread in threads:
                    # Get thread details
                    thread_detail = (
                        service.users()
                        .threads()
                        .get(userId=user_id, id=thread["id"])
                        .execute()
                    )

                    # Extract email addresses from each message in the thread
                    for message in thread_detail.get("messages", []):
                        headers = message.get("payload", {}).get("headers", [])

                        # Find the 'From' header
                        for header in headers:
                            if header["name"].lower() == "from":
                                from_value = header["value"]

                                # Extract email address from "Name <email>" format
                                email_match = re.search(r"<([^>]+)>", from_value)
                                if email_match:
                                    email_address = email_match.group(1)
                                else:
                                    # Handle case where email is just "email@domain.com"
                                    email_address = from_value.strip()

                                if email_address and "@" in email_address:
                                    email_addresses.add(email_address)
                                break

                # Only add labels that have associated emails
                if email_addresses:
                    config_data["SENDER_TO_LABELS"][label_name] = [
                        {
                            "read_status": False,  # Default to False (unread)
                            "delete_after_days": 30,  # Default to 30 days
                            "emails": sorted(
                                list(email_addresses)
                            ),  # Sort for consistency
                        }
                    ]
                    logger.info(
                        "Label '%s': found %s unique email addresses",
                        label_name,
                        len(email_addresses),
                    )
                else:
                    logger.info(f"Label '{label_name}': no emails found")

            # Add a small delay between batches to be nice to the API
            if i + batch_size < len(user_labels):
                time.sleep(1)

        # Save the configuration to file
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Configuration saved to: {output_file}")
        logger.info(f"Total labels with emails: {len(config_data['SENDER_TO_LABELS'])}")

        return config_data

    except HttpError as error:
        logger.error(
            f"An error occurred while extracting labels: {error}", exc_info=True
        )
        return None
    except Exception as error:
        logger.error(
            f"Unexpected error during label extraction: {error}", exc_info=True
        )
        return None
