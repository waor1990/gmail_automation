"""Tests for the dashboard logging configuration helper."""

from __future__ import annotations

import importlib
from pathlib import Path


def test_configure_dashboard_logging_creates_transcript(tmp_path):
    module = importlib.import_module("scripts.dashboard.logging_setup")
    module = importlib.reload(module)
    module._reset_dashboard_logging_for_tests()

    log_file = module.configure_dashboard_logging(log_dir=tmp_path)

    assert log_file.parent == Path(tmp_path)
    assert log_file.suffix == ".log"
    assert log_file.exists()

    content = log_file.read_text(encoding="utf-8")
    assert "Dashboard session started" in content
    assert "Saving dashboard logs to" in content
    assert "--------------------" in content  # hyphen delimiter is recorded

    same_file = module.configure_dashboard_logging(log_dir=tmp_path)
    assert same_file == log_file

    module._reset_dashboard_logging_for_tests()
