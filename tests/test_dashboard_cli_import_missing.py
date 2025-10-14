import json
import sys
import scripts.dashboard.analysis as dash_analysis
import scripts.dashboard.constants as dash_constants
import scripts.dashboard.__main__ as dash_main
from scripts.dashboard import logging_setup
from typing import Any


def test_cli_import_missing(monkeypatch, tmp_path):
    logging_setup._reset_dashboard_logging_for_tests()

    config_dir = tmp_path / "config"
    config_dir.mkdir(exist_ok=True)
    logs_dir = tmp_path / "logs"
    config_path = config_dir / "gmail_config-final.json"
    labels_path = config_dir / "gmail_labels_data.json"
    diff_path = config_dir / "email_differences_by_label.json"

    cfg: dict[str, Any] = {
        "SENDER_TO_LABELS": {
            "Foo": [
                {
                    "emails": ["a@example.com"],
                    "read_status": True,
                    "delete_after_days": 14,
                }
            ]
        }
    }
    labels = {
        "SENDER_TO_LABELS": {
            "Foo": [
                {
                    "emails": ["a@example.com", "b@example.com"],
                    "read_status": False,
                    "delete_after_days": 30,
                }
            ]
        }
    }
    diff = {
        "missing_emails_by_label": {
            "Foo": {
                "label_exists_in_target": True,
                "total_emails_in_source": 2,
                "missing_emails_count": 1,
                "missing_emails": ["b@example.com"],
            }
        },
        "comparison_summary": {"total_missing_emails": 1},
    }

    config_path.write_text(json.dumps(cfg), encoding="utf-8")
    labels_path.write_text(json.dumps(labels), encoding="utf-8")
    diff_path.write_text(json.dumps(diff), encoding="utf-8")

    monkeypatch.setattr(dash_constants, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(dash_constants, "CONFIG_JSON", config_path)
    monkeypatch.setattr(dash_constants, "LABELS_JSON", labels_path)
    monkeypatch.setattr(dash_constants, "DIFF_JSON", diff_path)
    monkeypatch.setattr(dash_constants, "LOGS_DIR", logs_dir)
    monkeypatch.setattr(dash_analysis, "CONFIG_JSON", config_path)
    monkeypatch.setattr(logging_setup, "LOGS_DIR", logs_dir)
    monkeypatch.setattr(dash_main, "CONFIG_JSON", config_path)
    monkeypatch.setattr(dash_main, "LABELS_JSON", labels_path)
    monkeypatch.setattr(dash_main, "DIFF_JSON", diff_path)

    monkeypatch.setattr(sys, "argv", ["scripts.dashboard", "--import-missing", "Foo"])
    dash_main.main()

    updated = json.loads(config_path.read_text(encoding="utf-8"))
    group = updated["SENDER_TO_LABELS"]["Foo"][0]
    assert "b@example.com" in group["emails"]
    assert group["read_status"] is True
    assert group["delete_after_days"] == 14


def test_cli_import_missing_creates_label_with_defaults(monkeypatch, tmp_path):
    logging_setup._reset_dashboard_logging_for_tests()

    config_dir = tmp_path / "config"
    config_dir.mkdir(exist_ok=True)
    logs_dir = tmp_path / "logs"
    config_path = config_dir / "gmail_config-final.json"
    labels_path = config_dir / "gmail_labels_data.json"
    diff_path = config_dir / "email_differences_by_label.json"

    cfg = {"SENDER_TO_LABELS": {}}
    labels = {
        "SENDER_TO_LABELS": {
            "Bar": [
                {
                    "emails": ["user@example.com", "second@example.com"],
                    "read_status": False,
                    "delete_after_days": 21,
                }
            ]
        }
    }
    diff = {
        "missing_emails_by_label": {
            "Bar": {
                "label_exists_in_target": False,
                "total_emails_in_source": 2,
                "missing_emails_count": 2,
                "missing_emails": ["user@example.com", "second@example.com"],
            }
        },
        "comparison_summary": {"total_missing_emails": 2},
    }

    config_path.write_text(json.dumps(cfg), encoding="utf-8")
    labels_path.write_text(json.dumps(labels), encoding="utf-8")
    diff_path.write_text(json.dumps(diff), encoding="utf-8")

    monkeypatch.setattr(dash_constants, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(dash_constants, "CONFIG_JSON", config_path)
    monkeypatch.setattr(dash_constants, "LABELS_JSON", labels_path)
    monkeypatch.setattr(dash_constants, "DIFF_JSON", diff_path)
    monkeypatch.setattr(dash_constants, "LOGS_DIR", logs_dir)
    monkeypatch.setattr(dash_analysis, "CONFIG_JSON", config_path)
    monkeypatch.setattr(logging_setup, "LOGS_DIR", logs_dir)
    monkeypatch.setattr(dash_main, "CONFIG_JSON", config_path)
    monkeypatch.setattr(dash_main, "LABELS_JSON", labels_path)
    monkeypatch.setattr(dash_main, "DIFF_JSON", diff_path)

    monkeypatch.setattr(
        sys,
        "argv",
        ["scripts.dashboard", "--import-missing", "Bar"],
    )
    dash_main.main()

    updated = json.loads(config_path.read_text(encoding="utf-8"))
    group = updated["SENDER_TO_LABELS"]["Bar"][0]
    assert group["emails"] == ["user@example.com", "second@example.com"]
    assert group["read_status"] is False
    assert group["delete_after_days"] == 21
