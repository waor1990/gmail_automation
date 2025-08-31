#!/usr/bin/env python3
"""Repository maintenance utilities.

Provides convenient commands to keep the repo healthy:
- Validate there are no secrets checked in
- Install and/or update pre-commit hooks
- Run pre-commit across the codebase
- Run test suite
- Show outdated Python packages

Use the project virtual environment for all actions when possible.
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
from pathlib import Path
import json
import sys
from typing import Any, cast

LOGGER = logging.getLogger(__name__)


def run(cmd: list[str], dry_run: bool) -> None:
    if dry_run:
        LOGGER.debug("dry-run: %s", " ".join(cmd))
        return
    subprocess.run(cmd, check=True)


def venv_python(venv: Path) -> str:
    python = (
        venv
        / ("Scripts" if os.name == "nt" else "bin")
        / ("python.exe" if os.name == "nt" else "python")
    )
    return str(python if python.exists() else Path("python"))


def validate_no_secrets(python: str, dry_run: bool) -> None:
    LOGGER.info("validating no secrets are committed")
    run([python, "-m", "scripts.validate_no_secrets"], dry_run)


def precommit_install(python: str, dry_run: bool) -> None:
    LOGGER.info("installing pre-commit hooks")
    run([python, "-m", "pre_commit", "install"], dry_run)


def precommit_autoupdate(python: str, dry_run: bool) -> None:
    LOGGER.info("auto-updating pre-commit hooks")
    run([python, "-m", "pre_commit", "autoupdate"], dry_run)


def precommit_run_all(python: str, dry_run: bool) -> None:
    LOGGER.info("running pre-commit on all files")
    run([python, "-m", "pre_commit", "run", "--all-files"], dry_run)


def pytest_run(python: str, dry_run: bool) -> None:
    LOGGER.info("running test suite")
    run([python, "-m", "pytest"], dry_run)


def fetch_outdated(python: str, dry_run: bool) -> list[dict[str, Any]]:
    """Return a list of outdated packages via pip --format=json.

    Each item includes keys like: name, version, latest_version, latest_filetype.
    """
    if dry_run:
        LOGGER.info("skipping fetching outdated packages (dry-run)")
        return []
    result = subprocess.run(
        [python, "-m", "pip", "list", "--outdated", "--format", "json"],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        data = cast("list[dict[str, Any]]", json.loads(result.stdout or "[]"))
    except json.JSONDecodeError:
        data = []
    return data


def print_outdated_table(items: list[dict[str, Any]]) -> None:
    if not items:
        print("No outdated packages found.")
        return
    name_w = max(len(i.get("name", "")) for i in items)
    ver_w = max(len(i.get("version", "")) for i in items)
    lat_w = max(len(i.get("latest_version", "")) for i in items)
    header = (
        f"{'Package'.ljust(name_w)}  {'Current'.ljust(ver_w)}  {'Latest'.ljust(lat_w)}"
    )
    print(header)
    print("-" * len(header))
    for i in items:
        print(
            f"{i.get('name', '').ljust(name_w)}  "
            f"{i.get('version', '').ljust(ver_w)}  "
            f"{i.get('latest_version', '').ljust(lat_w)}"
        )


def upgrade_packages(python: str, names: list[str], dry_run: bool) -> None:
    if not names:
        return
    LOGGER.info("upgrading %d package(s): %s", len(names), ", ".join(names))
    run([python, "-m", "pip", "install", "--upgrade", *names], dry_run)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Repository maintenance utilities")
    parser.add_argument("--venv", default=".venv", help="venv directory")
    parser.add_argument("--dry-run", action="store_true", help="show actions")
    parser.add_argument("--log-level", default="INFO")

    group = parser.add_argument_group("actions")
    group.add_argument("--validate-secrets", action="store_true")
    group.add_argument("--install-hooks", action="store_true")
    group.add_argument("--autoupdate-hooks", action="store_true")
    group.add_argument("--run-hooks", action="store_true")
    group.add_argument("--tests", action="store_true")
    group.add_argument("--outdated", action="store_true")
    group.add_argument(
        "--upgrade-all",
        action="store_true",
        help="when listing outdated, upgrade all without prompting",
    )
    group.add_argument(
        "--upgrade",
        nargs="*",
        help="when listing outdated, upgrade only these packages",
    )
    group.add_argument(
        "--no-input",
        action="store_true",
        help="do not prompt; only list (unless --upgrade/--upgrade-all)",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="run: validate-secrets, install-hooks, run-hooks, tests",
    )

    args = parser.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))

    venv = Path(args.venv)
    python = venv_python(venv)

    if args.all:
        validate_no_secrets(python, args.dry_run)
        precommit_install(python, args.dry_run)
        precommit_run_all(python, args.dry_run)
        pytest_run(python, args.dry_run)
        return 0

    if args.validate_secrets:
        validate_no_secrets(python, args.dry_run)
    if args.install_hooks:
        precommit_install(python, args.dry_run)
    if args.autoupdate_hooks:
        precommit_autoupdate(python, args.dry_run)
    if args.run_hooks:
        precommit_run_all(python, args.dry_run)
    if args.tests:
        pytest_run(python, args.dry_run)
    if args.outdated:
        items = fetch_outdated(python, args.dry_run)
        print_outdated_table(items)

        # Decide upgrade behavior
        names = [i.get("name", "") for i in items]
        names = [n for n in names if n]

        if args.upgrade is not None and len(args.upgrade) > 0:
            # Upgrade only the specified subset
            sel = [n for n in args.upgrade if n in names]
            missing = [n for n in args.upgrade if n not in names]
            if missing:
                LOGGER.warning(
                    "requested packages not listed as outdated: %s", ", ".join(missing)
                )
            upgrade_packages(python, sel, args.dry_run)
        elif args.upgrade_all:
            upgrade_packages(python, names, args.dry_run)
        elif not args.no_input and sys.stdin.isatty() and not args.dry_run and items:
            # Interactive prompt
            print()
            print("Update packages? [a]ll / [s]ome / [n]one:", end=" ")
            choice = input().strip().lower()
            if choice.startswith("a"):
                upgrade_packages(python, names, args.dry_run)
            elif choice.startswith("s"):
                print("Enter package names to upgrade (space-separated):", end=" ")
                line = input().strip()
                sel = [n for n in line.split() if n in names]
                upgrade_packages(python, sel, args.dry_run)
            else:
                print("No packages upgraded.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
