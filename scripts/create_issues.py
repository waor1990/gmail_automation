#!/usr/bin/env python3
"""Create GitHub issues from markdown files."""

from __future__ import annotations
from typing import TypedDict, Optional
import argparse
import subprocess
from pathlib import Path
import json
import shlex
import re

from gmail_automation.logging_utils import get_logger, setup_logging

LOGGER = get_logger(__name__)
EXCLUDED_FILES = {"AGENTS.md"}


class IssueMeta(TypedDict):
    labels: list[str]
    assignees: list[str]
    projects: list[str]
    milestone: Optional[str]


def run(cmd: list[str], dry_run: bool) -> subprocess.CompletedProcess[str] | None:
    LOGGER.debug("running command: %s", " ".join(shlex.quote(c) for c in cmd))
    if dry_run:
        LOGGER.debug("dry-run mode active")
        return None
    try:
        return subprocess.run(
            cmd, check=True, text=True, capture_output=True, encoding="utf-8"
        )
    except subprocess.CalledProcessError as e:
        LOGGER.error(f"Error running command: {e.cmd}")
        LOGGER.error(f"Exit code: {e.returncode}")
        LOGGER.error(f"stdout: {e.stdout}")
        LOGGER.error(f"stderr: {e.stderr}")
        raise


def parse_issue_file(path: Path) -> tuple[str, str, IssueMeta]:
    text = path.read_text(encoding="utf-8").splitlines()
    title = text[0].lstrip("# ") if text else path.stem
    body_lines = []

    issue_meta: IssueMeta = {
        "labels": [],
        "assignees": [],
        "projects": [],
        "milestone": None,
    }

    for line in text[1:]:
        clean_line = line.lstrip("- ").strip()
        lower = clean_line.lower()

        if lower.startswith("**labels**:"):
            issue_meta["labels"] = [
                v.strip() for v in clean_line.split(":", 1)[1].split(",") if v.strip()
            ]

        elif lower.startswith("**priority**:"):
            priority = clean_line.split(":", 1)[1].strip()
            issue_meta["labels"].append(priority)
        elif lower.startswith("**assignees**:"):
            issue_meta["assignees"] = [
                v.strip() for v in clean_line.split(":", 1)[1].split(",")
            ]
        elif lower.startswith("**milestone**:"):
            issue_meta["milestone"] = clean_line.split(":", 1)[1].strip()
        elif lower.startswith("**projects**:"):
            issue_meta["projects"] = [
                v.strip() for v in clean_line.split(":", 1)[1].split(",")
            ]
        else:
            body_lines.append(line)

    body = "\n".join(body_lines).strip()
    return title, body, issue_meta


def issue_exists(title: str, dry_run: bool) -> bool:
    if dry_run:
        return False
    out = run(["gh", "issue", "list", "--state", "open", "--json", "title"], dry_run)
    if out is None:
        return False
    data = json.loads(out.stdout)
    return any(item["title"] == title for item in data)


def create_issue(
    title: str, body: str, issue_meta: IssueMeta, dry_run: bool
) -> str | None:
    cmd = ["gh", "issue", "create", "--title", title, "--body", body]

    # Deduplicate labels while preserving order
    labels_unique: list[str] = []
    for label in issue_meta["labels"]:
        if label not in labels_unique:
            labels_unique.append(label)
    for label in labels_unique:
        cmd += ["--label", label]

    for assignee in issue_meta["assignees"]:
        cmd += ["--assignee", assignee]

    for project in issue_meta["projects"]:
        cmd += ["--project", project]

    if issue_meta["milestone"]:
        cmd += ["--milestone", issue_meta["milestone"]]

    out = run(cmd, dry_run)
    if out is None:
        return None
    match = re.search(r"/issues/(\d+)", out.stdout)
    return match.group(1) if match else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=("Create GitHub issues from local .md/.txt files."),
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 scripts/create_issues.py --dry-run\n"
            "  python3 scripts/create_issues.py --issues-dir my_issues\n"
        ),
    )
    parser.add_argument(
        "--issues-dir",
        default=None,
        metavar="ISSUES_DIR",
        help=(
            "Directory with issue files. Default: 'issues' if it exists,\n"
            "otherwise the current directory."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=("Preview actions; do not create or move files."),
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        help=("Logging level (default: INFO)."),
    )
    args = parser.parse_args(argv)

    logs_path = Path("logs")
    logs_path.mkdir(exist_ok=True)
    log_file_path = logs_path / "create_issues.log"

    # Set up both console and file logging
    setup_logging(level=args.log_level, log_file=log_file_path)

    # Determine issues directory: prefer explicit flag; otherwise use 'issues' if it
    # exists, else fall back to the current directory (useful when running from
    # within the issues/ folder).
    if args.issues_dir is None:
        issues_path = Path("issues") if Path("issues").is_dir() else Path.cwd()
    else:
        issues_path = Path(args.issues_dir)
    generated_path = issues_path / "generated"
    generated_path.mkdir(exist_ok=True)

    issue_files = [
        f for f in issues_path.iterdir() if f.suffix in {".md", ".txt"} and f.is_file()
    ]

    for file in sorted(issue_files):
        if file.name in EXCLUDED_FILES or file.parent.name in {"solved", "generated"}:
            continue

        title, body, issue_meta = parse_issue_file(file)

        if args.dry_run:
            meta_bits = []
            if issue_meta["labels"]:
                meta_bits.append(f"labels={issue_meta['labels']}")
            if issue_meta["assignees"]:
                meta_bits.append(f"assignees={issue_meta['assignees']}")
            if issue_meta["projects"]:
                meta_bits.append(f"projects={issue_meta['projects']}")
            if issue_meta["milestone"]:
                meta_bits.append(f"milestone={issue_meta['milestone']}")
            meta_str = f" ({', '.join(meta_bits)})" if meta_bits else ""
            LOGGER.info(
                "dry-run: would create issue '%s' from %s%s", title, file, meta_str
            )

        if issue_exists(title, args.dry_run):
            LOGGER.info("skipping existing issue %s", title)
            continue

        number = create_issue(title, body, issue_meta, args.dry_run)

        if number:
            LOGGER.info("created issue #%s from %s", number, file)
            destination = generated_path / file.name
            if destination.exists():
                LOGGER.warning("destination file %s already exists", destination)
                continue
            if args.dry_run:
                LOGGER.info("dry-run: would move %s to %s", file, destination)
            else:
                file.rename(destination)
                LOGGER.info("moved %s to %s", file, destination)

        elif args.dry_run:
            # Preview the move that would occur after successful creation
            destination = generated_path / file.name
            LOGGER.info("dry-run: would move %s to %s", file, destination)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
