#!/usr/bin/env python3
"""Unified entry point for dashboard and report generation."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from .reports import write_esaq_report, write_diff_json


def parse_args() -> argparse.Namespace:
    """Parse command line options."""
    parser = argparse.ArgumentParser(
        description="Launch the dashboard or export configuration reports."
    )
    parser.add_argument(
        "--report",
        choices=["esaq", "diff", "all"],
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
        help="Run gmail_automation.py before other actions.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    # Default behavior: launch the dashboard if no options provided.
    if not args.report and not args.launch and not args.refresh:
        args.launch = True

    if args.refresh:
        root = Path(__file__).resolve().parents[2]
        script = root / "gmail_automation.py"
        subprocess.run([sys.executable, str(script)], check=True)
        if not args.report and not args.launch:
            return

    if args.report:
        if args.report in ("esaq", "all"):
            path = write_esaq_report()
            print(f"ESAQ report exported: {path}")
        if args.report in ("diff", "all"):
            path = write_diff_json()
            print(f"Differences JSON exported: {path}")
        if not args.launch:
            return

    if args.launch:
        from .app import main as launch_dashboard

        launch_dashboard()


if __name__ == "__main__":  # pragma: no cover - entry point
    main()
