#!/usr/bin/env python3
"""Close a GitHub issue and move its file to the solved directory."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

from gmail_automation.logging_utils import get_logger, setup_logging

LOGGER = get_logger(__name__)


def run(cmd: list[str], dry_run: bool) -> None:
    if dry_run:
        LOGGER.debug("dry-run: %s", " ".join(cmd))
        return
    subprocess.run(cmd, check=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolve GitHub issue")
    parser.add_argument("issue", help="issue number or file")
    parser.add_argument("--issues-dir", default="issues")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    setup_logging(level=args.log_level)
    issues_dir = Path(args.issues_dir)
    solved_dir = issues_dir / "solved"
    solved_dir.mkdir(exist_ok=True)

    issue_input = args.issue
    issue_number: str | None = None
    file_path: Path | None = None

    if issue_input.isdigit():
        issue_number = issue_input
        glob = f"{int(issue_input):03d}_*"  # noqa: E231
        matches = list(issues_dir.glob(glob)) + list(
            issues_dir.glob(f"{issue_input}_*")
        )
        file_path = matches[0] if matches else None
    else:
        path = issues_dir / issue_input
        if path.exists():
            issue_number = "".join(ch for ch in path.stem if ch.isdigit())
            file_path = path
    if not issue_number:
        LOGGER.error("could not determine issue number from %s", issue_input)
        return 1

    run(["gh", "issue", "close", issue_number, "--comment", "Resolved"], args.dry_run)
    if file_path and file_path.exists():
        LOGGER.info("moving %s to solved", file_path)
        if not args.dry_run:
            shutil.move(str(file_path), solved_dir / file_path.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
