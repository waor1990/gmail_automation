import json
from datetime import datetime, timezone
from pathlib import Path

from gmail_automation.config import (
    DEFAULT_LAST_RUN_ISO,
    DEFAULT_LAST_RUN_TIME,
    get_sender_last_run_times,
    update_sender_last_run_times,
)


def _data_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "data"


def _cleanup(*paths: Path) -> None:
    for path in paths:
        if path.exists():
            path.unlink()


def test_new_sender_defaults_to_standard_date() -> None:
    """New senders should use the standard epoch."""
    data_dir = _data_dir()
    data_dir.mkdir(exist_ok=True)
    sender_file = data_dir / "sender_last_run.json"
    last_run_file = data_dir / "last_run.txt"
    _cleanup(sender_file, last_run_file)

    existing_iso = (
        datetime(2023, 1, 1, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    )
    sender_file.write_text(json.dumps({"existing@example.com": existing_iso}))

    senders = {"existing@example.com", "new@example.com"}
    times = get_sender_last_run_times(senders)

    assert (
        times["existing@example.com"]
        == datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp()
    )
    assert times["new@example.com"] == DEFAULT_LAST_RUN_TIME

    _cleanup(sender_file, last_run_file)


def test_fallback_to_global_last_run() -> None:
    """When sender data is missing, fallback to the legacy global timestamp."""
    data_dir = _data_dir()
    data_dir.mkdir(exist_ok=True)
    sender_file = data_dir / "sender_last_run.json"
    last_run_file = data_dir / "last_run.txt"
    _cleanup(sender_file)
    last_run_file.write_text("1234567890")

    senders = {"any@example.com"}
    times = get_sender_last_run_times(senders)
    assert times["any@example.com"] == 1234567890

    _cleanup(sender_file, last_run_file)


def test_update_sender_times_writes_default_iso() -> None:
    """Persist default ISO for new senders when no emails processed."""
    data_dir = _data_dir()
    data_dir.mkdir(exist_ok=True)
    sender_file = data_dir / "sender_last_run.json"
    _cleanup(sender_file)

    times = {"new@example.com": DEFAULT_LAST_RUN_TIME}
    update_sender_last_run_times(times)

    written = json.loads(sender_file.read_text())
    assert written["new@example.com"] == DEFAULT_LAST_RUN_ISO

    _cleanup(sender_file)
