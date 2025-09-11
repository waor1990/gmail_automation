#!/usr/bin/env python3
"""Check repository for sensitive files before committing."""

from __future__ import annotations

import argparse
import fnmatch
import subprocess

from gmail_automation.logging_utils import get_logger, setup_logging

PATTERNS = [
    "client_secret_*.json",
    "*token*.json",
    "gmail_config-final.json",
    "last_run.txt",
    "processed_email_ids.txt",
    "*.log",
]

LOGGER = get_logger(__name__)


def run_git(args: list[str]) -> list[str]:
    result = subprocess.run(["git", *args], check=False, text=True, capture_output=True)
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line]


def matches(path: str) -> bool:
    return any(fnmatch.fnmatch(path, pat) for pat in PATTERNS)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate repository for secrets")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    setup_logging(level=args.log_level)
    problems = False

    staged = run_git(["diff", "--cached", "--name-only"])
    for file in staged:
        if matches(file):
            LOGGER.error("staged sensitive file: %s", file)
            problems = True

    untracked = run_git(["ls-files", "--others", "--exclude-standard"])
    for file in untracked:
        if matches(file):
            LOGGER.error("untracked sensitive file: %s", file)
            problems = True

    if problems:
        return 1
    LOGGER.info("no sensitive files detected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
