#!/usr/bin/env python3
"""Create a virtual environment and install runtime and development dependencies.

Enhancements:
- Upgrades ``pip`` inside the venv before installing dependencies.
- Installs from ``requirements-dev.txt`` (kept for tests and tooling).
- Optional pre-commit hook installation.
- Optional source compilation check for fast feedback.
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

LOGGER = logging.getLogger(__name__)


def run(cmd: list[str], dry_run: bool) -> None:
    if dry_run:
        LOGGER.debug("dry-run: %s", " ".join(cmd))
        return
    subprocess.run(cmd, check=True)


def create_venv(venv: Path, dry_run: bool) -> None:
    if venv.exists():
        LOGGER.info("virtual environment exists at %s", venv)
        return
    LOGGER.info("creating virtual environment at %s", venv)
    run([sys.executable, "-m", "venv", str(venv)], dry_run)


def venv_python(venv: Path) -> Path:
    return (
        venv
        / ("Scripts" if os.name == "nt" else "bin")
        / ("python.exe" if os.name == "nt" else "python")
    )


def upgrade_pip(venv: Path, dry_run: bool) -> None:
    LOGGER.info("upgrading pip inside the virtual environment")
    run([str(venv_python(venv)), "-m", "pip", "install", "--upgrade", "pip"], dry_run)


def install_requirements(venv: Path, dry_run: bool) -> None:
    if dry_run:
        LOGGER.info("skipping dependency installation")
        return
    run(
        [str(venv_python(venv)), "-m", "pip", "install", "-r", "requirements-dev.txt"],
        dry_run,
    )


def install_precommit_hooks(venv: Path, dry_run: bool) -> None:
    LOGGER.info("installing pre-commit hooks")
    run([str(venv_python(venv)), "-m", "pre_commit", "install"], dry_run)


def validate_compilation(venv: Path, dry_run: bool) -> None:
    """Quickly check the main package compiles.

    Uses py_compile on a few critical modules for immediate feedback.
    """
    if dry_run:
        LOGGER.info("skipping compilation validation (dry-run)")
        return
    LOGGER.info("validating gmail_automation package compiles")
    srcs = [
        Path("src/gmail_automation/__main__.py"),
        Path("src/gmail_automation/cli.py"),
    ]
    run([str(venv_python(venv)), "-m", "py_compile", *map(str, srcs)], dry_run)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create project virtualenv")
    parser.add_argument("--venv", default=".venv", help="venv directory")
    parser.add_argument("--check", action="store_true", help="skip installs")
    parser.add_argument("--dry-run", action="store_true", help="show actions")
    parser.add_argument(
        "--install-hooks",
        action="store_true",
        help="install pre-commit hooks after dependencies",
    )
    parser.add_argument(
        "--no-compile",
        action="store_true",
        help="skip compilation validation",
    )
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    venv = Path(args.venv)
    create_venv(venv, args.dry_run)
    if not args.check:
        upgrade_pip(venv, args.dry_run)
        install_requirements(venv, args.dry_run)
        if args.install_hooks:
            install_precommit_hooks(venv, args.dry_run)
        if not args.no_compile:
            validate_compilation(venv, args.dry_run)
    LOGGER.info("setup complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
