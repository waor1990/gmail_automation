#!/usr/bin/env python3
"""Unified entry point for dashboard, reports, and development tasks."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from .reports import write_esaq_report, write_diff_json


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
        subprocess.run(
            [sys.executable, "-m", "flake8", "src/", "tests/", "gmail_automation.py"],
            check=True,
        )
        return

    if action == "format":
        subprocess.run(
            [sys.executable, "-m", "black", "src/", "tests/", "gmail_automation.py"],
            check=True,
        )
        return

    if action == "format-check":
        subprocess.run(
            [
                sys.executable,
                "-m",
                "black",
                "--check",
                "--diff",
                "src/",
                "tests/",
                "gmail_automation.py",
            ],
            check=True,
        )
        return

    if action == "mypy":
        subprocess.run(
            [sys.executable, "-m", "mypy", "src/", "gmail_automation.py"],
            check=True,
        )
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
    # Default behavior: launch the dashboard if no options provided.
    if not args.report and not args.launch and not args.refresh and not args.dev:
        args.launch = True

    if args.refresh:
        root = Path(__file__).resolve().parents[2]
        script = root / "gmail_automation.py"
        subprocess.run([sys.executable, str(script)], check=True)
        if not args.report and not args.launch and not args.dev:
            return

    if args.dev:
        run_dev(args.dev)
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
