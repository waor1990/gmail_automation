#!/usr/bin/env python3
"""Create a virtual environment and install runtime and development dependencies."""

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


def install_requirements(venv: Path, dry_run: bool) -> None:
    if dry_run:
        LOGGER.info("skipping dependency installation")
        return
    python = (
        venv
        / ("Scripts" if os.name == "nt" else "bin")
        / ("python.exe" if os.name == "nt" else "python")
    )
    run(
        [str(python), "-m", "pip", "install", "-r", "requirements-dev.txt"],
        dry_run,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create project virtualenv")
    parser.add_argument("--venv", default=".venv", help="venv directory")
    parser.add_argument("--check", action="store_true", help="skip installs")
    parser.add_argument("--dry-run", action="store_true", help="show actions")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    venv = Path(args.venv)
    create_venv(venv, args.dry_run)
    if not args.check:
        install_requirements(venv, args.dry_run)
    LOGGER.info("setup complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
