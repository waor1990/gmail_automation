import time
from scripts.dashboard import analysis
from gmail_automation.config import DEFAULT_LAST_RUN_TIME


def test_find_unprocessed_senders(monkeypatch):
    cfg = {
        "SENDER_TO_LABELS": {
            "LabelA": [{"emails": ["new@example.com", "old@example.com"]}]
        }
    }

    def fake_get_sender_last_run_times(senders):
        assert set(senders) == {"new@example.com", "old@example.com"}
        return {
            "new@example.com": DEFAULT_LAST_RUN_TIME,
            "old@example.com": time.time(),
        }

    monkeypatch.setattr(
        analysis, "get_sender_last_run_times", fake_get_sender_last_run_times
    )

    result = analysis.find_unprocessed_senders(cfg)
    assert result == [{"email": "new@example.com", "labels": "LabelA"}]
