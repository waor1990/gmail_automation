import logging
import random
import time
import os
import httplib2
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from oauth2client import client, file, tools

from .config import check_files_existence

SCOPES = "https://www.googleapis.com/auth/gmail.modify"
APPLICATION_NAME = "Email Automation"

# Cache dictionaries
message_details_cache = {}
processed_queries = set()


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
        logging.warning("No valid credentials, initiating OAuth flow.")
        flow = client.flow_from_clientsecrets(client_secret, SCOPES)
        flow.user_agent = APPLICATION_NAME
        credentials = tools.run_flow(flow, store)
        logging.info("New credentials obtained via OAuth flow.")
    else:
        try:
            credentials.refresh(httplib2.Http())
            logging.info("Credentials successfully refreshed.")
        except client.HttpAccessTokenRefreshError as e:
            logging.error(f"Failed to refresh token: {e}. Re-initiating OAuth flow.")
            flow = client.flow_from_clientsecrets(client_secret, SCOPES)
            flow.user_agent = APPLICATION_NAME
            credentials = tools.run_flow(flow, store)
            logging.info("New credentials obtained after refresh failure.")
    logging.debug(f"Final Credentials Status: Invalid = {credentials.invalid}")
    return credentials


def build_service(credentials):
    return build("gmail", "v1", credentials=credentials, cache_discovery=False)


def list_labels(service):
    logging.debug("Listing labels.")
    try:
        results = service.users().labels().list(userId="me").execute()
        labels = results.get("labels", [])
        return {label["name"]: label["id"] for label in labels}
    except HttpError as error:
        logging.error(f"An error occurred while listing labels: {error}")
        return {}


def get_existing_labels_cached(service):
    if not hasattr(get_existing_labels_cached, "cache"):
        get_existing_labels_cached.cache = list_labels(service)
    return get_existing_labels_cached.cache


def execute_request_with_backoff(request, max_retries=5):
    for retry in range(max_retries):
        try:
            return request.execute()
        except HttpError as error:
            if error.resp.status in [429, 403]:
                wait_time = min((2 ** retry) + random.uniform(0, 1), 64)
                logging.warning(f"Rate limit exceeded. Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
            elif error.resp.status == 400 and error._get_reason() == "failedPrecondition":
                logging.error(f"Precondition check failed: {error}")
                return None
            else:
                logging.error(f"An error occurred: {error}")
                raise
    logging.error("Max number of retries exceeded.")
    raise HttpError("Max retries exceeded", content="Max retries exceeded")


def batch_fetch_messages(service, user_id, msg_ids):
    batched_messages = {}
    for msg_id in msg_ids:
        if msg_id in message_details_cache:
            batched_messages[msg_id] = message_details_cache[msg_id]
        else:
            try:
                message = service.users().messages().get(userId=user_id, id=msg_id).execute()
                batched_messages[msg_id] = message
                message_details_cache[msg_id] = message
            except HttpError as error:
                logging.error(f"Error during batch fetch: {error}")
    return batched_messages


def fetch_emails_to_label(service, user_id, query):
    try:
        messages = []
        response = service.users().messages().list(userId=user_id, q=query).execute()
        logging.debug(f"API Response: {response}")
        if "messages" in response:
            messages.extend(response["messages"])
        while "nextPageToken" in response:
            page_token = response["nextPageToken"]
            response = service.users().messages().list(userId=user_id, q=query, pageToken=page_token).execute()
            logging.debug(f"API Response for next page: {response}")
            if "messages" in response:
                messages.extend(response["messages"])
        return messages
    except HttpError as error:
        logging.error(f"An error occurred while fetching emails: {error}")
        return []


def fetch_emails_to_label_optimized(service, user_id, query):
    if query in processed_queries:
        logging.debug(f"Query already processed: {query}")
        return []
    processed_queries.add(query)
    return fetch_emails_to_label(service, user_id, query)


def modify_message(service, user_id, msg_id, label_ids, remove_ids, mark_read):
    modify_body = {"addLabelIds": label_ids, "removeLabelIds": remove_ids}
    try:
        message = execute_request_with_backoff(
            service.users().messages().modify(userId=user_id, id=msg_id, body=modify_body)
        )
        if mark_read:
            execute_request_with_backoff(
                service.users().messages().modify(userId=user_id, id=msg_id, body={"removeLabelIds": ["UNREAD"]})
            )
        return message
    except HttpError as error:
        logging.error(f"An error occurred while modifying message {msg_id}: {error}")
        return None

