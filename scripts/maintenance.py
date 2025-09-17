#!/usr/bin/env python3
"""Repository maintenance utilities.

Provides convenient commands to keep the repo healthy:
- Validate there are no secrets checked in
- Install and/or update pre-commit hooks
- Run pre-commit across the codebase
- Run test suite
- Show outdated Python packages
- Check package compatibility

Use the project virtual environment for all actions when possible.
"""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path
import json
import sys
from typing import Any, cast

from importlib import metadata
from packaging.requirements import Requirement
from packaging.version import InvalidVersion, Version
from packaging.markers import default_environment

from gmail_automation.logging_utils import get_logger, setup_logging

LOGGER = get_logger(__name__)


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


def check_package_compatibility(python: str, dry_run: bool) -> bool:
    """Run ``pip check`` to verify installed packages are compatible.

    Returns ``True`` when all dependencies are satisfied, ``False`` otherwise.
    """
    LOGGER.info("checking package compatibility")
    cmd = [python, "-m", "pip", "check"]
    if dry_run:
        LOGGER.debug("dry-run: %s", " ".join(cmd))
        return True
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    output = result.stdout.strip()
    if result.returncode == 0:
        print("All packages are compatible.")
        return True
    if output:
        print(output)
    return False


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


def _normalize_name(name: str) -> str:
    return name.replace("-", "_").lower()


def collect_conflicting_requirements(
    info_by_name: dict[str, dict[str, Any]],
) -> dict[str, list[str]]:
    environment = dict(default_environment())
    if "extra" not in environment:
        environment["extra"] = ""
    conflicts: dict[str, list[str]] = {}
    latest_versions: dict[str, Version] = {}
    display_names: dict[str, str] = {}
    for display_name, metadata_info in info_by_name.items():
        latest = metadata_info.get("latest_version")
        if not latest:
            continue
        try:
            latest_versions[_normalize_name(display_name)] = Version(str(latest))
        except InvalidVersion:
            continue
        display_names[_normalize_name(display_name)] = display_name
    if not latest_versions:
        return conflicts
    for dist in metadata.distributions():
        requires = dist.requires or []
        metadata_obj = cast("Any", dist.metadata)
        dist_name = dist.name
        meta_get = getattr(metadata_obj, "get", None)
        if callable(meta_get):
            for key in ("Name", "Summary", "name"):
                value = meta_get(key)
                if isinstance(value, str) and value:
                    dist_name = value
                    break
        for req_str in requires:
            try:
                requirement = Requirement(req_str)
            except Exception:
                continue
            normalized = _normalize_name(requirement.name)
            if normalized not in latest_versions:
                continue
            marker = requirement.marker
            if marker is not None:
                try:
                    if not marker.evaluate(environment):
                        continue
                except Exception:
                    continue
            specifier = requirement.specifier
            if not specifier or specifier.contains(
                latest_versions[normalized], prereleases=True
            ):
                continue
            display = display_names[normalized]
            message = f"{dist_name} requires {requirement.name}{specifier}"
            existing = conflicts.setdefault(display, [])
            if message not in existing:
                existing.append(message)
    return conflicts


def upgrade_packages(
    python: str,
    names: list[str],
    details: dict[str, dict[str, Any]],
    dry_run: bool,
) -> tuple[list[str], list[str]]:
    upgraded: list[str] = []
    failed: list[str] = []
    if not names:
        return upgraded, failed
    LOGGER.info("upgrading %d package(s): %s", len(names), ", ".join(names))
    for name in names:
        info = details.get(name, {})
        current = info.get("version")
        latest = info.get("latest_version")
        if current and latest:
            LOGGER.info("upgrading %s from %s to %s", name, current, latest)
        else:
            LOGGER.info("upgrading %s", name)
        run([python, "-m", "pip", "install", "--upgrade", name], dry_run)
        if dry_run:
            continue
        if check_package_compatibility(python, dry_run):
            upgraded.append(name)
            continue
        LOGGER.error("compatibility issues detected after upgrading %s", name)
        if current:
            LOGGER.warning("reverting %s to %s", name, current)
            run([python, "-m", "pip", "install", f"{name}=={current}"], dry_run)
            check_package_compatibility(python, dry_run)
        else:
            LOGGER.warning(
                "previous version unknown; cannot automatically revert %s", name
            )
        failed.append(name)
    return upgraded, failed


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
        "--check-compat",
        action="store_true",
        help="verify installed packages have compatible dependencies",
    )
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
    setup_logging(level=args.log_level)

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
    if args.check_compat:
        check_package_compatibility(python, args.dry_run)
    if args.outdated:
        items = fetch_outdated(python, args.dry_run)
        print_outdated_table(items)

        # Decide upgrade behavior
        info_by_name: dict[str, dict[str, Any]] = {}
        for item in items:
            name = item.get("name")
            if name:
                info_by_name[name] = item
        names = list(info_by_name.keys())

        conflicts = collect_conflicting_requirements(info_by_name)
        if conflicts:
            print()
            print("Potential compatibility issues detected before upgrading:")
            for conflict_name, messages in conflicts.items():
                print(f"- {conflict_name}:")
                for message in messages:
                    print(f"    {message}")
            print()

        upgraded = False
        rolled_back: list[str] = []
        if args.upgrade is not None and len(args.upgrade) > 0:
            # Upgrade only the specified subset
            sel = [n for n in args.upgrade if n in names]
            missing = [n for n in args.upgrade if n not in names]
            if missing:
                LOGGER.warning(
                    "requested packages not listed as outdated: %s", ", ".join(missing)
                )
            successful, failed = upgrade_packages(
                python, sel, info_by_name, args.dry_run
            )
            rolled_back.extend(failed)
            upgraded = upgraded or bool(successful)
        elif args.upgrade_all:
            successful, failed = upgrade_packages(
                python, names, info_by_name, args.dry_run
            )
            rolled_back.extend(failed)
            upgraded = upgraded or bool(successful)
        elif not args.no_input and sys.stdin.isatty() and not args.dry_run and items:
            # Interactive prompt
            print()
            print("Update packages? [a]ll / [s]ome / [n]one:", end=" ")
            choice = input().strip().lower()
            if choice.startswith("a"):
                successful, failed = upgrade_packages(
                    python, names, info_by_name, args.dry_run
                )
                rolled_back.extend(failed)
                upgraded = upgraded or bool(successful)
            elif choice.startswith("s"):
                print("Enter package names to upgrade (space-separated):", end=" ")
                line = input().strip()
                sel = [n for n in line.split() if n in names]
                successful, failed = upgrade_packages(
                    python, sel, info_by_name, args.dry_run
                )
                rolled_back.extend(failed)
                upgraded = upgraded or bool(successful)
            else:
                print("No packages upgraded.")

        if rolled_back:
            unique_failures = list(dict.fromkeys(rolled_back))
            LOGGER.warning(
                "skipped upgrades due to compatibility errors: %s",
                ", ".join(unique_failures),
            )
        if upgraded:
            check_package_compatibility(python, args.dry_run)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
