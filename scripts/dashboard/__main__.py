#!/usr/bin/env python3
"""Unified entry point for dashboard, reports, and development tasks."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from gmail_automation.logging_utils import get_logger

from .analysis import load_config, import_missing_emails
from .constants import CONFIG_JSON, DIFF_JSON, LABELS_JSON
from .logging_setup import configure_dashboard_logging
from .reports import write_ECAQ_report, write_diff_json
from .utils_io import read_json, write_json


logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line options."""
    parser = argparse.ArgumentParser(
        description=(
            "Launch the dashboard, export configuration reports, "
            "run development helpers, or refresh automation data."
        ),
    )
    parser.add_argument(
        "--report",
        choices=["ECAQ", "diff", "all"],
        help="Generate a report and exit unless --launch is also provided.",
    )
    parser.add_argument(
        "--launch",
        action="store_true",
        help="Launch the interactive dashboard after running reports.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Run the Gmail automation module before other actions.",
    )
    parser.add_argument(
        "--import-missing",
        metavar="LABEL",
        help=(
            "Import missing emails for LABEL from the latest diff JSON and update "
            "the working config."
        ),
    )
    parser.add_argument(
        "--dev",
        choices=[
            "install",
            "test",
            "test-cov",
            "lint",
            "format",
            "format-check",
            "mypy",
            "all",
            "clean",
        ],
        help="Run development utility commands.",
    )
    parser.add_argument(
        "--host",
        default=None,
        help=(
            "Host interface for the dashboard (default: 127.0.0.1; env: DASH_HOST/HOST)"
        ),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help=("Port for the dashboard (default: 8050; env: DASH_PORT/PORT)"),
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable Dash debug mode when launching the dashboard.",
    )
    return parser.parse_args()


def run_dev(action: str) -> None:
    """Execute development helpers previously provided by dev scripts."""
    root = Path(__file__).resolve().parents[2]
    if action == "install":
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True
        )
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "-r",
                str(root / "requirements.txt"),
            ],
            check=True,
        )
        return

    if action == "test":
        subprocess.run([sys.executable, "-m", "pytest"], check=True)
        return

    if action == "test-cov":
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "--cov=src/gmail_automation",
                "--cov-report=term-missing",
            ],
            check=True,
        )
        return

    if action == "lint":
        subprocess.run([sys.executable, "-m", "flake8", "src/", "tests/"], check=True)
        return

    if action == "format":
        subprocess.run([sys.executable, "-m", "black", "src/", "tests/"], check=True)
        return

    if action == "format-check":
        subprocess.run(
            [sys.executable, "-m", "black", "--check", "--diff", "src/", "tests/"],
            check=True,
        )
        return

    if action == "mypy":
        subprocess.run([sys.executable, "-m", "mypy", "src/"], check=True)
        return

    if action == "all":
        for step in ["lint", "format-check", "mypy", "test"]:
            run_dev(step)
        return

    if action == "clean":
        for target in [
            root / ".pytest_cache",
            root / "htmlcov",
            root / "coverage.xml",
            root / ".coverage",
            root / ".mypy_cache",
        ]:
            if target.is_dir():
                shutil.rmtree(target, ignore_errors=True)
            else:
                target.unlink(missing_ok=True)
        for path in root.rglob("__pycache__"):
            shutil.rmtree(path, ignore_errors=True)
        for path in root.rglob("*.pyc"):
            path.unlink(missing_ok=True)
        return


def main() -> None:
    args = parse_args()
    log_file = configure_dashboard_logging()
    logger.info("CLI arguments: %s", args)
    logger.info("Dashboard log transcript will be saved to %s", log_file)
    # Default behavior: launch the dashboard only if no actionable options are provided.
    # Do NOT auto-launch when running non-interactive actions like --import-missing.
    if not any([args.report, args.launch, args.refresh, args.dev, args.import_missing]):
        args.launch = True

    if args.refresh:
        logger.info("Executing gmail_automation refresh prior to dashboard actions.")
        subprocess.run([sys.executable, "-m", "gmail_automation"], check=True)
        if not args.report and not args.launch and not args.dev:
            return

    if args.import_missing:
        logger.info(
            "Importing missing emails for label '%s' via dashboard CLI.",
            args.import_missing,
        )
        cfg = load_config()
        if not DIFF_JSON.exists() or not LABELS_JSON.exists():
            raise FileNotFoundError(
                "Missing diff or labels data. Run with --report diff first."
            )
        diff = read_json(DIFF_JSON)
        labels_data = read_json(LABELS_JSON)
        info = (diff.get("missing_emails_by_label") or {}).get(args.import_missing, {})
        emails = info.get("missing_emails") or []
        if not emails:
            print(f"No missing emails found for {args.import_missing}.")
            logger.info("No missing emails found for label '%s'.", args.import_missing)
        else:
            updated, added = import_missing_emails(
                cfg, labels_data, args.import_missing, emails
            )
            if added:
                write_json(updated, CONFIG_JSON)
                print(
                    f"Imported {len(added)} emails into {args.import_missing} "
                    "and updated config."
                )
                logger.info(
                    "Imported %s emails into %s and saved updated configuration.",
                    len(added),
                    args.import_missing,
                )
            else:
                print(f"No new emails imported for {args.import_missing}.")
                logger.info(
                    "Import completed for %s but no new emails were added.",
                    args.import_missing,
                )
        # If no further actions requested, exit after import.
        if not args.report and not args.launch and not args.dev:
            return

    if args.dev:
        logger.info("Running dashboard development helper: %s", args.dev)
        run_dev(args.dev)
        if not args.report and not args.launch:
            return

    if args.report:
        logger.info("Generating dashboard reports: %s", args.report)
        if args.report in ("ECAQ", "all"):
            path = write_ECAQ_report()
            print(f"ECAQ report exported: {path}")
            logger.info("ECAQ report exported to %s", path)
        if args.report in ("diff", "all"):
            path = write_diff_json()
            print(f"Differences JSON exported: {path}")
            logger.info("Diff report exported to %s", path)
        if not args.launch:
            return

    if args.launch:
        from .app import main as launch_dashboard

        logger.info(
            "Launching dashboard UI (host=%s, port=%s, debug=%s)",
            args.host,
            args.port,
            args.debug,
        )
        launch_dashboard(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":  # pragma: no cover - entry point
    main()
