"""Tests for the command line entry point."""

from __future__ import annotations

import subprocess
import sys


def test_module_executes_help() -> None:
    """Ensure ``python -m gmail_automation --help`` runs successfully."""
    result = subprocess.run(
        [sys.executable, "-m", "gmail_automation", "--help"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert result.returncode == 0
    assert "usage" in result.stdout.lower()
