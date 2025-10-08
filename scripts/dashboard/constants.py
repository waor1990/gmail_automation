from __future__ import annotations

import os
from pathlib import Path


def _expand(path: str) -> Path:
    """Return an absolute Path for ``path`` without requiring it to exist."""

    return Path(path).expanduser().resolve()


_root_override = os.getenv("GMAIL_AUTOMATION_DASHBOARD_ROOT")
ROOT = (
    _expand(_root_override) if _root_override else Path(__file__).resolve().parents[2]
)

_config_json_override = os.getenv("GMAIL_AUTOMATION_CONFIG_JSON")
_config_dir_override = os.getenv("GMAIL_AUTOMATION_CONFIG_DIR")

if _config_json_override:
    CONFIG_JSON = _expand(_config_json_override)
    CONFIG_DIR = CONFIG_JSON.parent
elif _config_dir_override:
    CONFIG_DIR = _expand(_config_dir_override)
    CONFIG_JSON = CONFIG_DIR / "gmail_config-final.json"
else:
    CONFIG_DIR = ROOT / "config"
    CONFIG_JSON = CONFIG_DIR / "gmail_config-final.json"

CONFIG_BACKUPS_DIR = CONFIG_DIR / "config-backups"

LOGS_DIR = ROOT / "logs"
LABELS_JSON = CONFIG_DIR / "gmail_labels_data.json"
REPORT_TXT = CONFIG_DIR / "ECAQ_Report.txt"
DIFF_JSON = CONFIG_DIR / "email_differences_by_label.json"
NEW_SENDERS_CSV = CONFIG_DIR / "new_senders.csv"
