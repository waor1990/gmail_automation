#!/usr/bin/env python3
"""
Gmail Labels Extraction Script

This script replicates the functionality of the Google Apps Script (saveLabelsToJSON.gs)
but runs locally using the Gmail API through Python.

This is a standalone script that extracts Gmail labels and associated email addresses
to generate a configuration file. It runs completely separate from the main
`gmail_automation` package.

Usage:
    python scripts/extract_gmail_labels.py [--output OUTPUT_FILE]
    [--batch-size BATCH_SIZE]

Example:
    python scripts/extract_gmail_labels.py --output config/my_labels.json \
        --batch-size 10
"""

import sys
import os
import argparse
import logging
import json
import re
import time
import random
from typing import Any

# Add the src directory to Python path so we can import our modules
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
src_dir = os.path.join(root_dir, "src")
sys.path.insert(0, src_dir)

# Import required modules
from gmail_automation.gmail_service import get_credentials, build_service  # noqa: E402
from gmail_automation.config import check_files_existence  # noqa: E402
from googleapiclient.errors import HttpError  # noqa: E402


def setup_logging(verbose=False):
    """Setup logging for the extraction script."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def retry_api_call(func, max_retries=3, base_delay=2):
    """
    Retry an API call with exponential backoff for temporary errors.

    Args:
        func: Function to call
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries (seconds)

    Returns:
        Function result or raises the last exception
    """
    for attempt in range(max_retries + 1):
        try:
            return func()
        except HttpError as error:
            if attempt == max_retries:
                # Last attempt, re-raise the error
                raise

            # Check if it's a retryable error
            if error.resp.status in [500, 502, 503, 504]:
                delay = base_delay * (2**attempt) + random.uniform(0, 1)
                delay_str = "{:.1f}".format(delay)
                logging.warning(
                    f"API error {error.resp.status}"
                    f" (attempt {attempt + 1}/{max_retries + 1})."
                    f" Retrying in {delay_str} seconds..."
                )
                time.sleep(delay)
            else:
                # Non-retryable error, re-raise immediately
                raise
        except Exception:
            # Non-HTTP errors, re-raise immediately
            raise


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
    if output_file is None:
        output_file = os.path.join(root_dir, "config", "gmail_labels_data.json")

    logging.info("Starting Gmail labels extraction...")

    try:
        # Get all user labels (excluding system labels)
        logging.info("Fetching Gmail labels...")
        labels_result = retry_api_call(
            lambda: service.users().labels().list(userId=user_id).execute()
        )
        labels = labels_result.get("labels", []) if labels_result else []

        # Filter out system labels (those that start with CATEGORY_, CHAT, INBOX, etc.)
        user_labels = [
            label
            for label in labels
            if label["type"] == "user"
            and not label["name"].startswith(("CATEGORY_", "CHAT"))
        ]

        logging.info(f"Found {len(user_labels)} user labels to process")

        # Initialize the configuration structure
        config_data: dict[str, dict[str, list[dict[str, Any]]]] = {
            "SENDER_TO_LABELS": {}
        }

        # Process labels in batches
        for i in range(0, len(user_labels), batch_size):
            batch = user_labels[i : i + batch_size]
            logging.info(
                f"Processing batch {i//batch_size + 1}/"
                f"{(len(user_labels) + batch_size - 1)//batch_size}"
            )

            for label in batch:
                label_name = label["name"]
                label_id = label["id"]

                logging.info(f"Processing label: {label_name}")

                try:
                    # Get all threads with this label (with retry logic)
                    threads_result = retry_api_call(
                        lambda: service.users()
                        .threads()
                        .list(
                            userId=user_id,
                            labelIds=[label_id],
                            maxResults=500,  # Adjust as needed
                        )
                        .execute()
                    )

                    threads = (
                        threads_result.get("threads", []) if threads_result else []
                    )
                    email_addresses = set()

                    # Process threads to extract sender email addresses
                    for thread in threads:
                        try:
                            # Get thread details (with retry logic)
                            thread_detail = retry_api_call(
                                lambda: service.users()
                                .threads()
                                .get(userId=user_id, id=thread["id"])
                                .execute()
                            )

                            if not thread_detail:
                                continue

                            # Extract email addresses from each message in the thread
                            for message in thread_detail.get("messages", []):
                                headers = message.get("payload", {}).get("headers", [])

                                # Find the 'From' header
                                for header in headers:
                                    if header["name"].lower() == "from":
                                        from_value = header["value"]

                                        # Extract email address from "Name <email>"
                                        email_match = re.search(
                                            r"<([^>]+)>", from_value
                                        )
                                        if email_match:
                                            email_address = email_match.group(1)
                                        else:
                                            # Handle emails like "email@domain.com"
                                            email_address = from_value.strip()

                                        if email_address and "@" in email_address:
                                            email_addresses.add(email_address)
                                        break
                        except HttpError as thread_error:
                            logging.warning(
                                f"Skipping thread {thread['id']} due to error: "
                                f"{thread_error}"
                            )
                            continue

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
                        logging.info(
                            f"Label '{label_name}': {len(email_addresses)} unique "
                            "emails"
                        )
                    else:
                        logging.info(f"Label '{label_name}': no emails found")

                except HttpError as label_error:
                    logging.warning(
                        f"Skipping label '{label_name}' due to error: {label_error}"
                    )
                    continue

            # Add a small delay between batches to be nice to the API
            if i + batch_size < len(user_labels):
                logging.debug("Waiting between batches...")
                time.sleep(2)  # Increased delay for better API compliance

        # Save the configuration to file
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)

        logging.info(f"Configuration saved to: {output_file}")
        logging.info(
            f"Total labels with emails: {len(config_data['SENDER_TO_LABELS'])}"
        )

        return config_data

    except HttpError as error:
        logging.error(f"An error occurred while extracting labels: {error}")
        return None
    except Exception as error:
        logging.error(f"Unexpected error during label extraction: {error}")
        return None


def main():
    """Main function for the standalone label extraction script."""
    parser = argparse.ArgumentParser(
        description="Extract Gmail labels to configuration file"
    )
    parser.add_argument(
        "--output",
        "-o",
        help=(
            "Output file path for the extracted configuration "
            "(default: config/gmail_labels_data.json)"
        ),
        default=None,
    )
    parser.add_argument(
        "--batch-size",
        "-b",
        type=int,
        default=5,
        help="Number of labels to process in each batch (default: 5)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(verbose=args.verbose)

    logging.info("Gmail Labels Extraction Script")
    logging.info("=" * 40)

    try:
        # Check that required files exist
        check_files_existence()

        # Get credentials and build service
        logging.info("Authenticating with Gmail API...")
        credentials = get_credentials()
        service = build_service(credentials)

        # Extract labels
        result = extract_labels_to_config(
            service=service,
            user_id="me",
            output_file=args.output,
            batch_size=args.batch_size,
        )

        if result:
            logging.info("=" * 40)
            logging.info("Label extraction completed successfully!")
            total_labels = len(result.get("SENDER_TO_LABELS", {}))
            logging.info(
                f"Extracted {total_labels} labels with associated email addresses."
            )

            output_path = args.output or os.path.join(
                root_dir, "config", "gmail_labels_data.json"
            )
            logging.info(f"Configuration saved to: {output_path}")
            logging.info(
                "\nYou can now use this configuration file with your Gmail automation."
            )
            return 0
        else:
            logging.error("Label extraction failed.")
            return 1

    except Exception as error:
        logging.error(f"Script failed: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
