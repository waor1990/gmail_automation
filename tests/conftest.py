"""Pytest configuration and fixtures for the test suite."""

from __future__ import annotations

import sys
from pathlib import Path


# Ensure that the application source directory is importable during tests.
SRC_PATH = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_PATH))
