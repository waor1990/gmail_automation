"""Tests for configuration utilities."""

from datetime import datetime
from zoneinfo import ZoneInfo

from gmail_automation.config import unix_to_readable


def test_unix_to_readable_pacific_time():
    """unix_to_readable formats timestamps in Pacific time."""
    timestamp = datetime(2023, 1, 1, 12, 0, tzinfo=ZoneInfo("UTC")).timestamp()
    assert unix_to_readable(timestamp) == "01/01/2023, 04:00 AM PST"
