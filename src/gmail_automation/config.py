import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Iterable

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


def load_configuration(config_path: str | None = None):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(script_dir))
    if config_path is None:
        config_path = f"{root_dir}/config/gmail_config-final.json"
    config_path = os.path.abspath(config_path)
    logging.debug(f"Attempting to load configuration from: {config_path}")
    if not os.path.exists(config_path):
        logging.error(f"Configuration file: '{config_path}' does not exist.")
        return {}
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)
    required_keys = ["SENDER_TO_LABELS"]
    missing = [key for key in required_keys if key not in config]
    if missing:
        logging.error(
            "Missing required configuration keys: %s in %s",
            ", ".join(missing),
            config_path,
        )
        return {}
    logging.debug("Configuration loaded successfully.")
    return validate_and_normalize_config(config)


def check_files_existence(client_secret_file: str | None = None):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(script_dir, os.pardir, os.pardir))
    config_dir = os.path.join(root_dir, "config")
    data_dir = os.path.join(root_dir, "data")
    os.makedirs(config_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)

    if client_secret_file is None:
        # Find client secret files and prioritize ones with actual credentials
        client_secret_files = [
            f
            for f in os.listdir(config_dir)
            if f.startswith("client_secret") and f.endswith(".json")
        ]

        # Sort to put specific named files (with actual client IDs) first
        client_secret_files.sort(key=lambda x: (x == "client_secret.json", x))

        client_secret_file = next(
            (os.path.join(config_dir, f) for f in client_secret_files),
            os.path.join(config_dir, "client_secret.json"),
        )
    last_run = os.path.join(data_dir, "last_run.txt")

    if not os.path.exists(client_secret_file):
        logging.error(f"Client secret file: '{client_secret_file}' does not exist.")
    else:
        logging.debug(f"Found client secret file: '{client_secret_file}'.")

    if not os.path.exists(last_run):
        logging.debug(
            f"Last run file: '{last_run}' does not exist. Will use default time."
        )
    else:
        logging.debug(f"Found last run file: '{last_run}'.")
    return client_secret_file, last_run


def unix_to_readable(unix_timestamp: float) -> str:
    """Convert a Unix timestamp to a Pacific time string.

    Args:
        unix_timestamp: Seconds since the Unix epoch.

    Returns:
        Formatted timestamp in the ``America/Los_Angeles`` timezone. If the
        conversion fails, ``"Invalid timestamp"`` is returned.
    """

    try:
        unix_timestamp = float(unix_timestamp)
        dt = datetime.fromtimestamp(unix_timestamp, tz=ZoneInfo("UTC")).astimezone(
            ZoneInfo("America/Los_Angeles")
        )
        return dt.strftime("%m/%d/%Y, %I:%M %p %Z")
    except (ValueError, TypeError, OSError) as e:
        logging.error(f"Error converting timestamp {unix_timestamp}: {e}")
        return "Invalid timestamp"


DEFAULT_LAST_RUN_ISO = "2000-01-01T00:00:00Z"
DEFAULT_LAST_RUN_TIME = datetime(2000, 1, 1, tzinfo=timezone.utc).timestamp()


def get_last_run_time():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(script_dir, os.pardir, os.pardir))
    data_dir = os.path.join(root_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    last_run_file = os.path.join(data_dir, "last_run.txt")

    if not os.path.exists(last_run_file):
        logging.info(
            "No last run file found. Using default last run time: %s",
            unix_to_readable(DEFAULT_LAST_RUN_TIME),
        )
        return DEFAULT_LAST_RUN_TIME

    try:
        with open(last_run_file, "r", encoding="utf-8") as f:
            last_run_time_str = f.read().strip()
            try:
                last_run_timestamp = float(last_run_time_str)
            except ValueError:
                last_run_timestamp = parser.isoparse(last_run_time_str).timestamp()
            logging.info(f"Got last run time: {unix_to_readable(last_run_timestamp)}")
            return last_run_timestamp
    except (ValueError, TypeError) as e:
        logging.error(
            f"Error parsing last run time: {e}. Using default last run time instead."
        )
        return DEFAULT_LAST_RUN_TIME


def update_last_run_time(current_time):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(script_dir, os.pardir, os.pardir))
    data_dir = os.path.join(root_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    last_run_file = os.path.join(data_dir, "last_run.txt")
    with open(last_run_file, "w", encoding="utf-8") as f:
        f.write(str(current_time))
    logging.debug(f"Updated last run time: {unix_to_readable(current_time)}")


def get_sender_last_run_times(senders: Iterable[str]) -> Dict[str, float]:
    """Return last run timestamps for each sender.

    Args:
        senders: Iterable of sender email addresses.

    Returns:
        Mapping from sender to Unix timestamp of the last processed message.
    """

    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(script_dir, os.pardir, os.pardir))
    data_dir = os.path.join(root_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    sender_file = os.path.join(data_dir, "sender_last_run.json")

    if os.path.exists(sender_file):
        with open(sender_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {}
        result: Dict[str, float] = {}
        for sender in senders:
            value = data.get(sender)
            if value is None:
                result[sender] = DEFAULT_LAST_RUN_TIME
            else:
                result[sender] = (
                    float(value)
                    if isinstance(value, (int, float))
                    else parser.isoparse(value).timestamp()
                )
        return result

    # Fallback to legacy global last run file
    global_time = get_last_run_time()
    return {sender: global_time for sender in senders}


def update_sender_last_run_times(times: Dict[str, float]) -> None:
    """Persist last run timestamps for senders.

    Args:
        times: Mapping from sender to Unix timestamp.
    """

    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(script_dir, os.pardir, os.pardir))
    data_dir = os.path.join(root_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    sender_file = os.path.join(data_dir, "sender_last_run.json")

    serializable: Dict[str, str] = {}
    for sender, ts in times.items():
        if ts == DEFAULT_LAST_RUN_TIME:
            serializable[sender] = DEFAULT_LAST_RUN_ISO
        else:
            serializable[sender] = (
                datetime.fromtimestamp(ts, tz=timezone.utc)
                .isoformat()
                .replace("+00:00", "Z")
            )
    with open(sender_file, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2, sort_keys=True)
