#!/usr/bin/env python3
"""Create GitHub issues from markdown files."""

from __future__ import annotations

import argparse
import logging
import subprocess
from pathlib import Path
import json
import shlex

LOGGER = logging.getLogger(__name__)


def run(cmd: list[str], dry_run: bool) -> subprocess.CompletedProcess[str] | None:
    if dry_run:
        LOGGER.debug("dry-run: %s", " ".join(shlex.quote(c) for c in cmd))
        return None
    return subprocess.run(cmd, check=True, text=True, capture_output=True)


def parse_issue_file(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8").splitlines()
    title = text[0].lstrip("# ") if text else path.stem
    body = "\n".join(text[1:])
    return title, body


def issue_exists(title: str, dry_run: bool) -> bool:
    if dry_run:
        return False
    out = run(["gh", "issue", "list", "--state", "open", "--json", "title"], dry_run)
    if out is None:
        return False
    data = json.loads(out.stdout)
    return any(item["title"] == title for item in data)


def create_issue(title: str, body: str, dry_run: bool) -> str | None:
    out = run(
        ["gh", "issue", "create", "--title", title, "--body", body, "--json", "number"],
        dry_run,
    )
    if out is None:
        return None
    data = json.loads(out.stdout)
    return str(data.get("number"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create GitHub issues from files")
    parser.add_argument("--issues-dir", default="issues")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    issues_path = Path(args.issues_dir)
    files = list(issues_path.glob("*.md")) + list(issues_path.glob("*.txt"))
    for file in sorted(files):
        if file.parent.name == "solved":
            continue
        title, body = parse_issue_file(file)
        if issue_exists(title, args.dry_run):
            LOGGER.info("skipping existing issue %s", title)
            continue
        number = create_issue(title, body, args.dry_run)
        if number:
            LOGGER.info("created issue #%s from %s", number, file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
