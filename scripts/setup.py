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
import os
import shutil
import time
import subprocess
import sys
from pathlib import Path

from gmail_automation.logging_utils import get_logger, setup_logging

LOGGER = get_logger(__name__)


def run(cmd: list[str], dry_run: bool) -> None:
    if dry_run:
        LOGGER.debug("dry-run: %s", " ".join(cmd))
        return
    subprocess.run(cmd, check=True)


def _is_valid_venv(venv: Path) -> bool:
    cfg = venv / "pyvenv.cfg"
    py = venv_python(venv)
    return cfg.exists() and py.exists()


def _safe_rmtree(path: Path) -> None:
    if not path.exists():
        return

    def _onerror(func, p, exc_info):  # pragma: no cover - best-effort cleanup
        try:
            os.chmod(p, 0o700)
        except Exception:
            pass
        try:
            func(p)
        except Exception:
            pass

    shutil.rmtree(path, onerror=_onerror)


def create_venv(venv: Path, dry_run: bool) -> None:
    if venv.exists():
        if _is_valid_venv(venv):
            LOGGER.info("virtual environment exists at %s", venv)
            return
        LOGGER.warning("found invalid venv at %s; recreating", venv)
        if not dry_run:
            _safe_rmtree(venv)
    LOGGER.info("creating virtual environment at %s", venv)
    try:
        run([sys.executable, "-m", "venv", str(venv)], dry_run)
    except subprocess.CalledProcessError as exc:
        if os.name == "nt" and not dry_run:
            LOGGER.warning("venv creation failed (%s); retrying after cleanup", exc)
            _safe_rmtree(venv)
            time.sleep(0.5)
            run([sys.executable, "-m", "venv", str(venv)], dry_run)
        else:
            raise


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

    setup_logging(level=args.log_level)
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
