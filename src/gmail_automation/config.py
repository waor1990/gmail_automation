from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from dateutil import parser
from zoneinfo import ZoneInfo

from .ignored_rules import normalize_ignored_rules
from .logging_utils import get_logger

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "gmail_config-final.json"
DEFAULT_CONFIG_PATH_STR = str(DEFAULT_CONFIG_PATH)
DEFAULT_CLIENT_SECRET_NAME = "client_secret.json"

DEFAULT_LAST_RUN_ISO = "2000-01-01T00:00:00Z"
DEFAULT_LAST_RUN_TIME = datetime(2000, 1, 1, tzinfo=timezone.utc).timestamp()


def get_project_root() -> Path:
    """Return the repository root directory."""

    return PROJECT_ROOT


def get_config_dir() -> Path:
    """Return the directory storing configuration files."""

    return PROJECT_ROOT / "config"


def get_data_dir() -> Path:
    """Return the directory storing runtime data files."""

    return PROJECT_ROOT / "data"


def _ensure_directory(path: Path) -> Path:
    """Create ``path`` (and parents) if it does not exist and return it."""

    path.mkdir(parents=True, exist_ok=True)
    return path


def _coerce_bool(value: object, *, default: bool = False) -> bool:
    """Coerce commonly used truthy/falsey strings into booleans."""

    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y"}:
            return True
        if lowered in {"false", "0", "no", "n"}:
            return False
    return default


def _unique_preserve_order(values: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _normalise_string_list(raw: object) -> List[str]:
    """Return a list of stripped, non-empty strings from ``raw``."""

    if raw is None:
        return []
    if isinstance(raw, str):
        candidates: Sequence[object] = [raw]
    elif isinstance(raw, Sequence):
        candidates = raw
    else:
        raise ValueError("Expected a list of strings")

    cleaned: List[str] = []
    for item in candidates:
        if item is None:
            continue
        text = str(item).strip()
        if text:
            cleaned.append(text)
    return cleaned


def _normalise_protected_labels(raw: object) -> List[str]:
    """Return a normalised list for ``PROTECTED_LABELS``."""

    labels = _normalise_string_list(raw)
    return _unique_preserve_order(labels)


def _normalise_selected_email_deletions(raw: object) -> List[dict]:
    """Return normalised ``SELECTED_EMAIL_DELETIONS`` entries."""

    if raw is None:
        return []
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        entries = list(raw)
    else:
        raise ValueError(
            "SELECTED_EMAIL_DELETIONS must be a list of message definitions"
        )

    normalised: List[dict] = []
    for index, entry in enumerate(entries):
        normalised.append(_normalise_single_deletion(entry, index))
    return normalised


def _normalise_single_deletion(entry: object, index: int) -> dict:
    if isinstance(entry, str):
        message_id = entry.strip()
        if not message_id:
            raise ValueError("SELECTED_EMAIL_DELETIONS entries cannot be empty strings")
        return {
            "id": message_id,
            "label": None,
            "require_read": False,
            "actor": None,
            "reason": None,
            "rule": None,
            "thread_id": None,
        }

    if not isinstance(entry, dict):
        raise ValueError(
            "SELECTED_EMAIL_DELETIONS entries must be dictionaries or strings; "
            f"received {type(entry).__name__} at index {index}"
        )

    data = dict(entry)
    message_id = str(data.get("id") or data.get("message_id") or "").strip()
    if not message_id:
        raise ValueError(
            "SELECTED_EMAIL_DELETIONS entries must include an 'id' or 'message_id'"
        )

    label_value = data.get("label")
    label = str(label_value).strip() if label_value not in (None, "") else None

    # Some legacy configs store labels in a list; prefer the first one.
    label_list = data.get("labels")
    if label is None and isinstance(label_list, Sequence) and label_list:
        label = str(label_list[0]).strip() or None

    require_read = _coerce_bool(data.get("require_read"), default=False)

    thread_raw = data.get("thread_id")
    thread_id = str(thread_raw).strip() if thread_raw not in (None, "") else None

    actor_raw = data.get("actor")
    actor = str(actor_raw).strip() if actor_raw not in (None, "") else None

    reason_raw = data.get("reason")
    reason = str(reason_raw).strip() if reason_raw not in (None, "") else None

    rule_raw = data.get("rule")
    rule = str(rule_raw).strip() if rule_raw not in (None, "") else None

    return {
        "id": message_id,
        "thread_id": thread_id,
        "label": label,
        "require_read": require_read,
        "actor": actor,
        "reason": reason,
        "rule": rule,
    }


def validate_and_normalize_config(config: dict) -> dict:
    """Validate and normalize configuration values."""

    config = dict(config or {})

    sender_to_labels = config.get("SENDER_TO_LABELS", {})
    if not isinstance(sender_to_labels, dict):
        raise ValueError("SENDER_TO_LABELS must be a dictionary")

    for category, rules in sender_to_labels.items():
        if not isinstance(rules, list):
            raise ValueError("SENDER_TO_LABELS entries must be lists of rules")
        for rule in rules:
            if not isinstance(rule, dict):
                raise ValueError("Sender rules must be dictionaries")
            if isinstance(rule.get("read_status"), str):
                value = rule["read_status"].strip().lower()
                if value == "true":
                    rule["read_status"] = True
                elif value == "false":
                    rule["read_status"] = False
            if "delete_after_days" not in rule or rule["delete_after_days"] in (
                None,
                "",
            ):
                rule["delete_after_days"] = float("inf")
            else:
                try:
                    rule["delete_after_days"] = int(rule["delete_after_days"])
                except (ValueError, TypeError):
                    logger.warning(
                        "Invalid delete_after_days for %s: %s", category, rule
                    )
                    rule["delete_after_days"] = float("inf")

    ignored_raw = config.get("IGNORED_EMAILS")
    try:
        config["IGNORED_EMAILS"] = normalize_ignored_rules(
            [] if ignored_raw is None else ignored_raw
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid IGNORED_EMAILS configuration: {exc}") from exc

    if "PROTECTED_LABELS" in config:
        try:
            config["PROTECTED_LABELS"] = _normalise_protected_labels(
                config.get("PROTECTED_LABELS")
            )
        except ValueError as exc:
            raise ValueError(f"Invalid PROTECTED_LABELS configuration: {exc}") from exc

    if "SELECTED_EMAIL_DELETIONS" in config:
        try:
            config["SELECTED_EMAIL_DELETIONS"] = _normalise_selected_email_deletions(
                config.get("SELECTED_EMAIL_DELETIONS")
            )
        except ValueError as exc:
            raise ValueError(
                f"Invalid SELECTED_EMAIL_DELETIONS configuration: {exc}"
            ) from exc

    return config


def load_configuration(config_path: str | None = None) -> dict:
    if config_path:
        path_str = os.path.expanduser(str(config_path))
    else:
        path_str = DEFAULT_CONFIG_PATH_STR

    logger.info("Loading configuration from: %s", path_str)

    if not os.path.exists(path_str):
        logger.error("Configuration file: '%s' does not exist.", path_str)
        return {}

    with open(path_str, encoding="utf-8") as fh:
        config = json.load(fh)
    required_keys = ["SENDER_TO_LABELS"]
    missing = [key for key in required_keys if key not in config]
    if missing:
        logger.error(
            "Missing required configuration keys: %s in %s",
            ", ".join(missing),
            path_str,
        )
        return {}
    logger.debug("Configuration loaded successfully.")
    try:
        return validate_and_normalize_config(config)
    except ValueError as exc:
        logger.error("Configuration validation failed: %s", exc)
        return {}


def check_files_existence(client_secret_file: str | None = None):
    config_dir = _ensure_directory(get_config_dir())
    data_dir = _ensure_directory(get_data_dir())

    if client_secret_file is None:
        candidates = sorted(config_dir.glob("client_secret*.json"))
        if candidates:
            client_secret_path = candidates[0]
        else:
            client_secret_path = config_dir / DEFAULT_CLIENT_SECRET_NAME
    else:
        client_secret_path = Path(client_secret_file)

    last_run = data_dir / "last_run.txt"

    if not client_secret_path.exists():
        logger.error("Client secret file: '%s' does not exist.", client_secret_path)
    else:
        logger.debug("Found client secret file: '%s'.", client_secret_path)

    if not last_run.exists():
        logger.debug(
            "Last run file: '%s' does not exist. Will use default time.", last_run
        )
    else:
        logger.debug("Found last run file: '%s'.", last_run)
    return str(client_secret_path), str(last_run)


def unix_to_readable(unix_timestamp: float) -> str:
    """Convert a Unix timestamp to a Pacific time string."""

    try:
        unix_timestamp = float(unix_timestamp)
        dt = datetime.fromtimestamp(unix_timestamp, tz=ZoneInfo("UTC")).astimezone(
            ZoneInfo("America/Los_Angeles")
        )
        return dt.strftime("%m/%d/%Y, %I:%M %p %Z")
    except (ValueError, TypeError, OSError) as exc:
        logger.error(
            "Error converting timestamp %s: %s", unix_timestamp, exc, exc_info=True
        )
        return "Invalid timestamp"


def get_last_run_time() -> float:
    data_dir = _ensure_directory(get_data_dir())
    last_run_file = data_dir / "last_run.txt"

    if not last_run_file.exists():
        logger.info(
            "No last run file found. Using default last run time: %s",
            unix_to_readable(DEFAULT_LAST_RUN_TIME),
        )
        return DEFAULT_LAST_RUN_TIME

    try:
        content = last_run_file.read_text(encoding="utf-8").strip()
        try:
            return float(content)
        except ValueError:
            return parser.isoparse(content).timestamp()
    except (ValueError, TypeError) as exc:
        logger.error(
            "Error parsing last run time: %s. Using default last run time instead.",
            exc,
            exc_info=True,
        )
        return DEFAULT_LAST_RUN_TIME


def update_last_run_time(current_time: float) -> None:
    data_dir = _ensure_directory(get_data_dir())
    last_run_file = data_dir / "last_run.txt"
    last_run_file.write_text(str(current_time), encoding="utf-8")
    logger.debug("Updated last run time: %s", unix_to_readable(current_time))


def get_sender_last_run_times(senders: Iterable[str]) -> Dict[str, float]:
    data_dir = _ensure_directory(get_data_dir())
    sender_file = data_dir / "sender_last_run.json"

    if sender_file.exists():
        try:
            data = json.loads(sender_file.read_text(encoding="utf-8"))
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
                    else parser.isoparse(str(value)).timestamp()
                )
        return result

    global_time = get_last_run_time()
    return {sender: global_time for sender in senders}


def update_sender_last_run_times(times: Dict[str, float]) -> None:
    data_dir = _ensure_directory(get_data_dir())
    sender_file = data_dir / "sender_last_run.json"

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
    sender_file.write_text(
        json.dumps(serializable, indent=2, sort_keys=True), encoding="utf-8"
    )
