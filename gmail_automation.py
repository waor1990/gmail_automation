import httplib2
import json
import logging
import os
import random
import sys
import time
from datetime import datetime, timedelta
from dateutil import parser
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from time import time
from oauth2client import client, file, tools
from zoneinfo import ZoneInfo

SCOPES = 'https://www.googleapis.com/auth/gmail.modify'
APPLICATION_NAME = 'Email Automation'
CACHE_TTL = 3600
#Add cache dictionary
message_details_cache = {}
processed_queries = set()
    
def setup_logging():
    #Determine the directory of the script
    logging.debug("Setting up logging")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    #Set up logging to file for INFO level 
    info_log_file_path = os.path.join(script_dir, 'gmail_automation_info.log')
    remove_old_logs(info_log_file_path)
    
    #Set up logging to file for DEBUG level 
    debug_log_file_path = os.path.join(script_dir, 'gmail_automation_debug.log')
    remove_old_logs_debug(debug_log_file_path)
    
    #Create a file handler that logs debug and higher level messages
    info_file_handler = logging.FileHandler(info_log_file_path, encoding='utf-8')
    info_file_handler.setLevel(logging.INFO) 
    info_file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    info_file_handler.setFormatter(info_file_formatter)
    
    #Create a file handler that logs debug and higher level messages
    debug_file_handler = logging.FileHandler(debug_log_file_path, encoding='utf-8')
    debug_file_handler.setLevel(logging.DEBUG) 
    debug_file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    debug_file_handler.setFormatter(debug_file_formatter)
    
    #Create a stream handler for the console/terminal
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO) 
    stream_formatter = logging.Formatter('%(message)s')
    stream_handler.setFormatter(stream_formatter)
    
    #Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG) 
    
    #Remove any existing handlers from the root logger
    if logger.hasHandlers():
        logger.handlers.clear()

    #Add handlers to the logger
    logger.addHandler(info_file_handler)
    logger.addHandler(debug_file_handler)
    logger.addHandler(stream_handler)
    
    logging.debug("Logging setup completed")
    
def remove_old_logs(log_file_path):
    if not os.path.exists(log_file_path):
        return
    
    #Define the cutoff date (Over 60 days)
    cutoff_date = datetime.now(ZoneInfo("UTC")) - timedelta(days=60)
    
    with open(log_file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        
    with open(log_file_path, 'w', encoding='utf-8') as file:
        for line in lines:
            #Attempt to parse the date from the log line
            try:
                log_date_str = line.split(' - ')[0]
                log_date = parser.parse(log_date_str)
                #Ensure log_date is timezone-aware
                if log_date.tzinfo is None: 
                    log_date = log_date.replace(tzinfo=ZoneInfo("UTC"))
                #Write lines if log_date is after the cutoff_date
                if log_date >= cutoff_date:
                    file.write(line)
            except (ValueError, IndexError):
                #If parsing fails, keep the line
                file.write(line)    
                
def remove_old_logs_debug(log_file_path):
    if not os.path.exists(log_file_path):
        return
    
    #Define the cutoff date (Over 7 days)
    cutoff_date = datetime.now(ZoneInfo("UTC")) - timedelta(days=7)
    
    with open(log_file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        
    with open(log_file_path, 'w', encoding='utf-8') as file:
        for line in lines:
            #Attempt to parse the date from the log line
            try:
                log_date_str = line.split(' - ')[0]
                log_date = parser.parse(log_date_str)
                #Ensure log_date is timezone-aware
                if log_date.tzinfo is None: 
                    log_date = log_date.replace(tzinfo=ZoneInfo("UTC"))
                #Write lines if log_date is after the cutoff_date
                if log_date >= cutoff_date:
                    file.write(line)
            except (ValueError, IndexError):
                #If parsing fails, keep the line
                file.write(line)    

def validate_and_normalize_config(config):
    #Validate and ensures all configuration fields are correctly set
    for category, rules in config.get('SENDER_TO_LABELS', {}).items():
        for rule in rules:
            if 'delete_after_dats' not in rule or rule['delete_after_days'] is None:
                rule['delete_after_days'] = float('inf')
            else:
                try:
                    rule['delete_after_days'] = int(rule['delete_after_days'])
                except ValueError:
                    logging.warning(f"Invalid delete_after_days for {category}: {rule}")
                    rule['delete_after_days'] = float('inf')
        return config

def load_configuration():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    #Load the configuration from JSON file
    config_path = os.path.join(script_dir, 'gmail_config-final.json')
    logging.debug(f'Attempting to load configuration from: {config_path}')
    if os.path.exists(config_path):
        with open(config_path, encoding='utf-8') as f:
            config = json.load(f)
            logging.debug(f"Configuration loaded successfully.")
            return validate_and_normalize_config(config)
    else: 
        logging.error(f"Configuration file: '{config_path}' does not exist.")
        return {}
    
def check_files_existence():    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    CLIENT_SECRET_FILE = os.path.join(script_dir, 'client_secret_717954459613-8f8k3mc7diq2h6rtkujvrjc2cbq6plh7.apps.googleusercontent.com.json')
    LAST_RUN_FILE = os.path.join(script_dir, 'last_run.txt')
    
    logging.debug(f"Checking existence of '{CLIENT_SECRET_FILE} and {LAST_RUN_FILE}.")
    client_secret_exists = os.path.exists(CLIENT_SECRET_FILE)
    last_run_file_exists = os.path.exists(LAST_RUN_FILE)
    
    #Ensure the client secret file exists
    if not client_secret_exists:
        logging.error(f"Client secret file: '{CLIENT_SECRET_FILE}' does not exist.")
    else: 
        logging.debug(f"Found client secret file: '{CLIENT_SECRET_FILE}'.")
    
    if not last_run_file_exists:
        logging.debug(f"Last run file: '{LAST_RUN_FILE}' does not exist. Will use default time.")
    else: 
        logging.debug(f"Found last run file: '{LAST_RUN_FILE}'.")
        
    return CLIENT_SECRET_FILE, LAST_RUN_FILE

def parse_email_date(date_str):
    #Parses email date and ensures timezone consistency
    try:
        date = parser.parse(date_str)
        if date.tzinfo is None:
            date = date.replace(tzinfo=ZoneInfo('US/Pacific'))
        return date
    except Exception as e:
        logging.error(f"Error parsing date string '{date_str}': {e}")
        return None


def unix_to_readable(unix_timestamp):
    #Convert Unix timestamp to datetime object
    unix_timestamp = int(unix_timestamp)
    PDT = ZoneInfo('US/Pacific')
    dt = datetime.fromtimestamp(unix_timestamp, tz=PDT)
    #Format the datetime into a readable string
    return dt.strftime('%m/%d/%Y, %I:%M %p %Z')

def get_credentials():
    #Gets valid user credentials from storage.
    logging.debug(f'Getting credentials.')
    script_dir = os.path.dirname(os.path.abspath(__file__))
    credential_path = os.path.join(script_dir, 'gmail-python-email.json')
    logging.debug(f'Credential path: {credential_path}')
    
    #Extract CLIENT_SECRET_FILE from the tuple returned by checking file's existence
    CLIENT_SECRET_FILE, _ = check_files_existence()

    store = file.Storage(credential_path)
    credentials = store.get()
    
    if not credentials or credentials.invalid:
        logging.warning(f'No valid credentials, initiating OAuth flow.')
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        credentials = tools.run_flow(flow, store)
        logging.info(f'New credentials obtained via OAuth flow.')
    else: 
        try: 
            logging.debug(f'Refreshing credentials...')
            credentials.refresh(httplib2.Http())
            logging.info(f'Credentials successfully refreshed.')
        except client.HttpAccessTokenRefreshError as e:
            logging.error(f'Failed to refresh token: {e}. Re-initiating OAuth flow.')
            flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
            flow.user_agent = APPLICATION_NAME
            credentials = tools.run_flow(flow, store)
            logging.info('New credentials obtained after refresh failure.')
            
    logging.debug(f"Final Credentials Status: Invalid = {credentials.invalid}")
    return credentials

def list_labels(service):
    #Lists all labels in the user's Gmail account
    logging.debug(f'Listing labels.')
    try:
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        return {label['name']: label['id'] for label in labels}
    except HttpError as error:
        logging.error(f'An error occurred while listing labels: {error}')
        return {}
    
def get_existing_labels_cached(service):
    if not hasattr(get_existing_labels_cached, "cache"):
        #Cache the labels if not already done so
        get_existing_labels_cached.cache = list_labels(service)
    return get_existing_labels_cached.cache

    
def execute_request_with_backoff(request, max_retries=5):
    #Executes a request with exponential backoff.
    for retry in range(max_retries):
        try: 
            return request.execute()
        except HttpError as error:
            if error.resp.status in [429, 403]: #429: Rate limit, 403: Forbidden
                wait_time = min((2 ** retry) + random.uniform(0,1), 64) #Cap wait time to a max of 46 secs
                logging.warning(f'Rate limit exceeded. Retrying in {wait_time:.2f} seconds...')
                time.sleep(wait_time)
            elif error.resp.status == 400 and error._get_reason() == 'failedPrecondition':
                logging.error(f'Precondition check failed: {error}')
                return None
            else:
                logging.error(f'An error occurred: {error}')
                raise
    logging.error(f'Max number of retries exceeded.')
    raise HttpError("Max retries exceeded", content="Max retries exceeded")

def parse_header(headers, header_name):
    #Extracts the value of a specific header from a list of headers
    return next((header['value'] for header in headers if header['name'].lower() == header_name.lower()), None)

def validate_details(details, expected_keys):
    #Validates the presence of expected keys in the details
    missing_details = [key for key in expected_keys if key not in details or details[key] is None]
    available_details = {key: value for key, value in details.items() if key in expected_keys and value is not None}
    
    return {
        "missing_details": missing_details,
        "available_details": available_details
    }

def get_message_details(service, userId, msg_id):
    #Fetches the email's subject, date, and sender
    try:
        message = execute_request_with_backoff(service.users().messages().get(userId=userId, id=msg_id))
        if not message or 'payload' not in message or 'headers' not in message['payload']:
            logging.error(f"Invalid message structure for ID {msg_id}: {message}")
            return None, None, None, None

        headers = message['payload']['headers']

        subject = parse_header(headers, 'subject')
        date_str = parse_header(headers, 'date')
        sender = parse_header(headers, 'from')
        is_unread = 'UNREAD' in message['labelIds']
        
        #Validate the expected details
        details = {"subject": subject, "date": date_str, "sender": sender}
        validation = validate_details(details, ["subject", "date", "sender"])
        
        if validation["missing_details"]:
            logging.error(f"Missing details for message ID {msg_id}: {validation['missing_details']}")
            logging.info(f"Available details for message ID {msg_id}: {validation['available_details']}")
            return None, None, None, None
        
        #Parse the date if present
        date = parse_email_date(date_str)
        formatted_date = date.strftime('%m/%d/%Y, %I:%M %p %Z') if date else None
        
        return subject, formatted_date, sender, is_unread
    
    except Exception as e:
        logging.error(f'Error getting message details for ID {msg_id}: {e}')
        return None, None, None, None  

def get_message_details_cached(service, userId, msg_id):
    # Check if the message details are already cached
    if msg_id in message_details_cache:
        cached_value = message_details_cache.get(msg_id)
        # Validate the cached value format
        if isinstance(cached_value, tuple) and len(cached_value) == 4:
            # Return only essential parts of the cached value
            return cached_value
        else:
            logging.warning(f"Invalid cache format for message ID {msg_id}: {cached_value}")

    # Fetch and cache details if not present or invalid
    subject, date, sender, is_unread = get_message_details(service, userId, msg_id)
    if subject is not None and date is not None and sender is not None:
        message_details_cache[msg_id] = (subject, date, sender, is_unread)
        return subject, date, sender, is_unread
    else:
        # Cache the failure to avoid retrying during the same session
        logging.error(f"Caching incomplete details for message ID {msg_id}: (subject={subject}, date={date}, sender={sender})")
        message_details_cache[msg_id] = (None, None, None, None)
        return (None, None, None, None)
    

def load_processed_email_ids(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return set(f.read().splitlines())
    return set()

def save_processed_email_ids(file_path, email_ids):
    with open(file_path, 'w', encoding='utf-8') as f:
        for email_id in email_ids:
            f.write(email_id + '\n')

def get_last_run_time():
    #Define default initial run time (in UTC)
    default_time = datetime(2000, 1, 1, tzinfo=ZoneInfo('UTC')).timestamp()
    _, LAST_RUN_FILE = check_files_existence()
    
    if not os.path.exists(LAST_RUN_FILE):
        logging.info(f'No last run file found. Using default last run time: {unix_to_readable(default_time)}')
        return default_time
        
    #Try reading the last run time from file
    try:
        with open(LAST_RUN_FILE, 'r', encoding='utf-8') as f:
            last_run_time_str = f.read().strip()
            last_run_time = parser.isoparse(last_run_time_str).astimezone(ZoneInfo('US/Pacific'))
            last_run_timestamp = last_run_time.timestamp()
            logging.info(f'Got last run time: {unix_to_readable(last_run_timestamp)}')
            return last_run_timestamp
    except (ValueError, TypeError) as e:
        logging.error(f'Error parsing last run time: {e}. Using default last run time instead.')
        return default_time
    
def update_last_run_time(current_time):
    PDT = ZoneInfo('US/Pacific')
    _, LAST_RUN_FILE = check_files_existence()
    last_run_time = datetime.fromtimestamp(current_time, tz=PDT).isoformat()
    with open(LAST_RUN_FILE, 'w', encoding='utf-8') as f:
        f.write(datetime.fromtimestamp(current_time, tz=ZoneInfo('US/Pacific')).isoformat())
    readable_time = unix_to_readable(current_time)
    
def batch_fetch_messages(service, userId, msg_ids):
    batched_messages = {}
    for msg_id in msg_ids:
        if msg_id in message_details_cache:
            batched_messages[msg_id] = message_details_cache[msg_id]
        else:
            try:
                message = service.users().messages().get(userId=userId, id=msg_id).execute()
                batched_messages[msg_id] = message
                message_details_cache[msg_id] = message
            except HttpError as error:
                logging.error(f'Error during batch fetch: {error}')
    return batched_messages

def fetch_emails_to_label(service, userId, query):
    #Use the defined query to fetch emails with pagination support
    logging.debug(f"Fetching emails with query: {query}")
    try:
        messages = []
        response = service.users().messages().list(userId=userId, q=query).execute()
        logging.debug(f"API Response: {response}")
        if 'messages' in response:
            messages.extend(response['messages'])
            
        while 'nextPageToken' in response:
            page_token = response['nextPageToken']
            response = service.users().messages().list(userId=userId, q=query, pageToken=page_token).execute()
            logging.debug(f"API Response for next page: {response}")
            if 'messages' in response:
                messages.extend(response['messages'])
                
        return messages
    
    except HttpError as error:
        logging.error(f"An error occurred while fetching emails: {error}")
        return []

def fetch_emails_to_label_optimized(service, userId, query):
    if query in processed_queries:
        logging.debug(f"Query already processed: {query}")
        return []
    processed_queries.add(query)
    return fetch_emails_to_label(service, userId, query)


def modify_message(service, userId, msg_id, label_ids, remove_ids, mark_read):
    modify_body = {
        'addLabelIds': label_ids,
        'removeLabelIds': remove_ids
    }
    try:
        message = execute_request_with_backoff(service.users().messages().modify(
          userId=userId,
          id=msg_id,
          body=modify_body
        ))
        if mark_read:
            execute_request_with_backoff(service.users().messages().modify(
                userId=userId,
                id=msg_id,
                body={'removeLabelIds': ['UNREAD']}
            ))
        return message
    except HttpError as error:
        logging.error(f'An error occurred while modifying message {msg_id}: {error}')
        return None
    
def process_email(service, userId, msg_id, subject, date, sender, is_unread, label, mark_read, delete_after_days, existing_labels, current_run_processed_ids, processed_email_ids, expected_labels, config):
    logging.debug(f'Processing message ID: {msg_id} with subject: {subject}, date: {date}, sender: {sender}')
    
    #Fetch details using caching
    subject, date, sender, is_unread = get_message_details_cached(service, userId, msg_id)
    
    #Handle missing details
    if not subject or not date or not sender:
        logging.debug(f'Missing details for message ID: {msg_id}. Skipping')
        return False
    
    #Fetch current labels of the email
    current_labels = service.users().messages().get(userId=userId, id=msg_id).execute().get('labelIds',[])
    
    #Avoid processing if the email already has been processed in this run
    if msg_id in current_run_processed_ids:
        logging.debug(f'Email ID {msg_id} already processed in this run. Skipping.')
        return False
    
    #Check if the required label is already applied
    label_id_to_add = existing_labels.get(label)
    
    #Apply the new label if necessary
    if label_id_to_add not in current_labels:
        modify_message(service, userId, msg_id, [label_id_to_add], ['INBOX'], mark_read)
        #Only mark the email as processed if it was successfully labeled
        processed_email_ids.add(msg_id)
        logging.info(f'Email from: "{sender}" dated: "{date}", and with subject: "{subject}" was modified with label "{label}", marked as read: "{mark_read}" and removed from Inbox.')
        
    #Check if the email should be deleted after a certain amount of days
    if delete_after_days is not None:
        logging.debug(f"Attempting to parse date: '{date}' for message ID: {msg_id}")
        try: 
            #Parse the email's date and make it timezone-aware if it isn't already
            email_date = parse_email_date(date)
            if email_date.tzinfo is None: #If date is naive, set to Pacific time
                email_date = email_date.replace(tzinfo=ZoneInfo('US/Pacific'))
            #Set current_time to the same timezone
            current_time = datetime.now(ZoneInfo('US/Pacific'))
            days_diff = (current_time - email_date).days
        
            if days_diff >= delete_after_days:
                logging.info(f"Deleting email from: '{sender}' with subject: '{subject}' as it is older than {delete_after_days} days.")
                service.users().messages().delete(userId=userId, id=msg_id).execute()
                return True
        except Exception as e:
            logging.error(f"Error parsing date for message ID {msg_id}: {e}")
            return False
    return True


def process_emails_by_criteria(service, userId, query, label, mark_read, delete_after_days, existing_labels, current_run_processed_ids, processed_email_ids, expected_labels, config, criterion_type='keyword', criterion_value=''):
    #Fetch emails matching the query
    messages = fetch_emails_to_label_optimized(service, userId, query)
    
    #Counters to track the number of skipped and processed emails
    skipped_emails_count = 0
    modified_emails_count = 0
    any_emails_processed  = False

    if not messages: 
        logging.info(f'No emails found for {criterion_type}: "{criterion_value}" for label: "{label}".')
        return False
    
    logging.debug(f'Query "{query}" resulted in: "{messages}"')
    
    #Fetch messages in a batch
    msg_ids = [msg['id'] for msg in messages]
    batched_messages = batch_fetch_messages(service, userId, msg_ids)
    
    for msg_id in msg_ids:
        #Access fetched data from batched messages
        message_data = batched_messages.get(msg_id)
        if not message_data:
            logging.error(f"Message ID {msg_id} not found in batch fetch.")
            skipped_emails_count += 1
            continue
        
        #Get message details from batch data 
        subject, date, sender, is_unread = get_message_details_cached(service, userId, msg_id)
        
        if not subject or not date or not sender: 
            logging.debug(f'Missing details for message ID: {msg_id}. Skipping.')
            skipped_emails_count += 1
            continue
        
        if msg_id in processed_email_ids or msg_id in current_run_processed_ids:
            logging.debug(f"Skipping already processed email ID: {msg_id}")
            skipped_emails_count += 1
            continue
        
        #Process the email (if it meets the criteria for modification)
        if process_email(service, userId, msg_id, subject, date, sender, is_unread, label, mark_read, delete_after_days, existing_labels, current_run_processed_ids, processed_email_ids, expected_labels, config):
            modified_emails_count += 1
            any_emails_processed = True
        else: 
            skipped_emails_count += 1
            
    #Summarize logging after processing all emails for a particular query
    logging.debug(f'Processed {modified_emails_count} emails and skipped {skipped_emails_count} emails for {criterion_type}: "{criterion_value}" with label "{label}".')
    
    return any_emails_processed
        
def process_emails_for_labeling(service, userId, existing_labels, config, last_run_time):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    processed_ids_file = os.path.join(script_dir, 'processed_email_ids.txt')
    processed_email_ids = load_processed_email_ids(processed_ids_file)
    current_run_processed_ids = set()
    expected_labels = {}
    
    logging.debug(f"Loaded processed email IDs: {processed_email_ids}")
    
    any_emails_processed = False
    
    #Process keywords to labels first
    logging.info(f"Processing keywords to labels:")
    for keyword, label_info in config['KEYWORDS_TO_LABELS'].items():
        label, mark_read = label_info
        if label not in existing_labels:
            logging.warning(f"The label '{label}' does not exist. Existing labels: {list(existing_labels.keys())}")
            continue
        
        query = f'subject:"{keyword}" label:inbox after:{int(last_run_time)}'
        #Set delete_after_days to None for keywords
        emails_processed = process_emails_by_criteria(service, userId, query, label, mark_read, None, existing_labels, current_run_processed_ids, processed_email_ids, expected_labels, config, criterion_type='keyword', criterion_value=keyword)
        
        if emails_processed:
            any_emails_processed = True
        
    #Then process sender categories for only emails that have not been processed
    logging.info(f"Processing sender categories:")
    for sender_category, sender_info in config['SENDER_TO_LABELS'].items():
        if sender_category not in existing_labels:
            logging.warning(f"The label '{sender_category}' does not exist. Existing labels: {list(existing_labels.keys())}")
            continue

        for info in sender_info:
            mark_read = info['read_status']
            delete_after_days = info.get('delete_after_days', None)
            emails = info['emails']
            for email in emails:
                query = f'from:{email} label:inbox after:{int(last_run_time)}'
                emails_processed = process_emails_by_criteria(service, userId, query, sender_category, mark_read, delete_after_days, existing_labels, current_run_processed_ids, processed_email_ids, expected_labels, config, criterion_type='sender', criterion_value=email)
                
                if emails_processed:
                    any_emails_processed = True
            
    #Save the processed email IDs
    logging.debug(f"Saving processed email IDs.")
    save_processed_email_ids(processed_ids_file, processed_email_ids)
    return any_emails_processed
    

def reprocess_unlabeled_emails(service, userId, existing_labels, config, processed_email_ids):
    logging.info("Rechecking labels for previously processed emails.")
    
    emails_to_reprocess = set()
    current_run_processed_ids = set()
    expected_labels = {}
    
    for msg_id in processed_email_ids:
        subject, date, sender, is_unread = get_message_details_cached(service, userId, msg_id)
        
        if not subject or not sender: 
            continue
        
        #Check if the email has the expected labels
        message = service.users().messages().get(userId=userId, id=msg_id).execute()
        labels_applied = message.get('labelIds', [])
        
        #Process keywords to labels
        logging.debug(f"Processing keywords to labels")
        for keyword, label_info in config['KEYWORDS_TO_LABELS'].items():
            label, mark_read = label_info
            if subject.lower().find(keyword.lower()) != -1 and existing_labels[label] not in labels_applied:
                emails_to_reprocess.add(msg_id)
                
        logging.debug(f"Processing sender categories")
        for sender_category, sender_info in config['SENDER_TO_LABELS'].items():
            for info in sender_info:
                if sender in info['emails'] and existing_labels[sender_category] not in labels_applied:
                    emails_to_reprocess.add(msg_id)
        
        logging.debug(f"Found {len(emails_to_reprocess)} emails that need to be reprocessed.")
        
        #Reprocess those emails
        for msg_id in emails_to_reprocess:
            process_email(service, userId, msg_id, subject, date, sender, is_unread, label, mark_read, existing_labels, current_run_processed_ids, processed_email_ids, expected_labels, config)
            
        #Save the updated processed_email_ids
        save_processed_email_ids('processed_email_ids.txt', processed_email_ids)
    

def main():
    try:
        setup_logging()
        logging.info('-' * 72)
        logging.debug("Script started")
        logging.info('Starting Gmail_Automation.')
        
        config = load_configuration()
        CLIENT_SECRET_FILE, LAST_RUN_FILE = check_files_existence()
        
        PDT = ZoneInfo('US/Pacific')
        current_time = datetime.now(PDT).timestamp()
        logging.info(f"Current Time: {unix_to_readable(current_time)}")
        
        #Get credentials
        credentials = get_credentials()
        service = build('gmail', 'v1', credentials=credentials, cache_discovery=False)

        userId = 'me'
        last_run_time = get_last_run_time()
        
        #Get all existing labels
        existing_labels = get_existing_labels_cached(service)
        
        #Track if any emails were processed
        emails_processed = process_emails_for_labeling(service, userId, existing_labels, config, last_run_time)
        
        #Only update the last run time if emails were processed
        if emails_processed:
            update_last_run_time(current_time)
            logging.info(f"Last run time updated: {unix_to_readable(current_time)}")
        else:
            logging.info("No emails processed, skipping last run time update.")
            
        logging.info(f"Script completed")
        
    except HttpError as error:
            logging.error(f'An error occured: {error}', exc_info=True)

if __name__ == '__main__':
    main()