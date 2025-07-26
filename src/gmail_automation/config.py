import json
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from dateutil import parser


def validate_and_normalize_config(config):
    """Validate and normalize configuration values."""
    for category, rules in config.get("SENDER_TO_LABELS", {}).items():
        for rule in rules:
            if isinstance(rule.get("read_status"), str):
                value = rule["read_status"].strip().lower()
                if value == "true":
                    rule["read_status"] = True
                elif value == "false":
                    rule["read_status"] = False

            if "delete_after_days" not in rule or rule["delete_after_days"] is None:
                rule["delete_after_days"] = float("inf")
            else:
                try:
                    rule["delete_after_days"] = int(rule["delete_after_days"])
                except (ValueError, TypeError):
                    logging.warning(f"Invalid delete_after_days for {category}: {rule}")
                    rule["delete_after_days"] = float("inf")
    return config


def load_configuration():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(script_dir, os.pardir, os.pardir))
    config_path = os.path.join(root_dir, "config", "gmail_config-final.json")
    config_path = os.path.abspath(config_path)
    logging.debug(f"Attempting to load configuration from: {config_path}")
    if os.path.exists(config_path):
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
            logging.debug("Configuration loaded successfully.")
            return validate_and_normalize_config(config)
    logging.error(f"Configuration file: '{config_path}' does not exist.")
    return {}


def check_files_existence():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(script_dir, os.pardir, os.pardir))
    config_dir = os.path.join(root_dir, "config")
    data_dir = os.path.join(root_dir, "data")
    client_secret = os.path.join(
        config_dir,
        "client_secret_717954459613-8f8k3mc7diq2h6rtkujvrjc2cbq6plh7.apps.googleusercontent.com.json",
    )
    last_run = os.path.join(data_dir, "last_run.txt")

    client_secret_exists = os.path.exists(client_secret)
    last_run_exists = os.path.exists(last_run)

    if not client_secret_exists:
        logging.error(f"Client secret file: '{client_secret}' does not exist.")
    else:
        logging.debug(f"Found client secret file: '{client_secret}'.")

    if not last_run_exists:
        logging.debug(f"Last run file: '{last_run}' does not exist. Will use default time.")
    else:
        logging.debug(f"Found last run file: '{last_run}'.")
    return client_secret, last_run


def unix_to_readable(unix_timestamp):
    unix_timestamp = int(unix_timestamp)
    pdt = ZoneInfo("America/Los_Angeles")
    dt = datetime.fromtimestamp(unix_timestamp, tz=pdt)
    return dt.strftime("%m/%d/%Y, %I:%M %p %Z")


def get_last_run_time():
    default_time = datetime(2000, 1, 1, tzinfo=ZoneInfo("UTC")).timestamp()
    _, last_run_file = check_files_existence()

    if not os.path.exists(last_run_file):
        logging.info(f"No last run file found. Using default last run time: {unix_to_readable(default_time)}")
        return default_time

    try:
        with open(last_run_file, "r", encoding="utf-8") as f:
            last_run_time_str = f.read().strip()
            last_run_time = parser.isoparse(last_run_time_str).astimezone(ZoneInfo("America/Los_Angeles"))
            last_run_timestamp = last_run_time.timestamp()
            logging.info(f"Got last run time: {unix_to_readable(last_run_timestamp)}")
            return last_run_timestamp
    except (ValueError, TypeError) as e:
        logging.error(f"Error parsing last run time: {e}. Using default last run time instead.")
        return default_time


def update_last_run_time(current_time):
    _, last_run_file = check_files_existence()
    with open(last_run_file, "w", encoding="utf-8") as f:
        f.write(datetime.fromtimestamp(current_time, tz=ZoneInfo("America/Los_Angeles")).isoformat())
    logging.debug(f"Updated last run time: {unix_to_readable(current_time)}")

