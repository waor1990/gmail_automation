"""Logging helpers for gmail_automation.

Provides a consistent logging setup across the project.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional
import re


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger."""
    return logging.getLogger(name)


def setup_logging(level: str = "INFO", log_file: Optional[Path] = None) -> None:
    """Configure root logging.

    Parameters
    ----------
    level:
        Console logging level (default ``INFO``).
    log_file:
        When provided, a file handler logging at ``DEBUG`` level is attached.
    """
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    if root.handlers:
        root.handlers.clear()

    console_level = getattr(logging, level.upper(), logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(console_handler)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        root.addHandler(file_handler)


def redact(text: str) -> str:
    """Redact basic PII such as email addresses in ``text``."""
    return re.sub(r"([^@\s]+)@([^@\s]+)", r"***@\2", text)
