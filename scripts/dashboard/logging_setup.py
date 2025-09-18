"""Logging configuration helpers for the dashboard runtime."""

from __future__ import annotations

from datetime import datetime
import logging
from pathlib import Path
from typing import Optional

from gmail_automation.logging_utils import get_logger, setup_logging

from .constants import LOGS_DIR

_DASHBOARD_LOG_FILE: Optional[Path] = None


def configure_dashboard_logging(log_dir: Path | None = None) -> Path:
    """Ensure dashboard logs are written to logs/ and return the log path.

    Parameters
    ----------
    log_dir:
        Optional directory override used primarily for testing. When omitted,
        the default logs/ directory relative to the project root is used.

    Returns
    -------
    Path
        The path of the active dashboard log file.
    """

    global _DASHBOARD_LOG_FILE
    if _DASHBOARD_LOG_FILE is not None:
        return _DASHBOARD_LOG_FILE

    target_dir = Path(log_dir) if log_dir is not None else LOGS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = target_dir / f"dashboard_{timestamp}.log"

    setup_logging(level="INFO", log_file=log_file)
    logger = get_logger("scripts.dashboard")
    logger.info("-" * 40)
    logger.info("Dashboard session started at %s", timestamp)
    logger.info("Saving dashboard logs to %s", log_file)
    _DASHBOARD_LOG_FILE = log_file
    return log_file


def _reset_dashboard_logging_for_tests() -> None:
    """Reset cached log state. Intended for use in test suites only."""

    global _DASHBOARD_LOG_FILE
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        handler.close()
        root_logger.removeHandler(handler)
    root_logger.setLevel(logging.WARNING)
    _DASHBOARD_LOG_FILE = None
