#!/usr/bin/env python3
"""Remove sensitive files from git history using git-filter-repo."""

from __future__ import annotations

import argparse
import subprocess

from gmail_automation.logging_utils import get_logger, setup_logging

PATTERNS = [
    "client_secret_*.json",
    "gmail-python-email.json",
    "data/gmail-python-email.json",
    "gmail_config-final.json",
    "config/gmail_config-final.json",
    "*.log",
    "logs/*.log",
    "gmail_automation.log",
    "gmail_automation_debug*.log",
    "last_run.txt",
    "data/last_run.txt",
    "processed_email_ids.txt",
    "data/processed_email_ids.txt",
]

LOGGER = get_logger(__name__)


def run(cmd: list[str], dry_run: bool) -> None:
    if dry_run:
        LOGGER.debug("dry-run: %s", " ".join(cmd))
        return
    subprocess.run(cmd, check=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Clean git history")
    parser.add_argument("--dry-run", action="store_true", help="show actions")
    parser.add_argument("--yes", action="store_true", help="confirm operation")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    setup_logging(level=args.log_level)
    if not args.dry_run and not args.yes:
        parser.error("Refusing to run without --yes (use --dry-run to preview)")

    for pattern in PATTERNS:
        LOGGER.info("removing pattern %s", pattern)
        run(
            ["git", "filter-repo", "--path-glob", pattern, "--invert-paths", "--force"],
            args.dry_run,
        )
    LOGGER.info("git history cleaned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
