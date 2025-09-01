import json
import subprocess
import sys
from pathlib import Path


def test_cli_import_missing(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    config_dir = repo_root / "config"
    config_dir.mkdir(exist_ok=True)
    config_path = config_dir / "gmail_config-final.json"
    labels_path = config_dir / "gmail_labels_data.json"
    diff_path = config_dir / "email_differences_by_label.json"

    cfg = {
        "SENDER_TO_LABELS": {
            "Foo": [{"emails": ["a@example.com"], "read_status": True}]
        }
    }
    labels = {
        "SENDER_TO_LABELS": {
            "Foo": [{"emails": ["a@example.com", "b@example.com"], "read_status": True}]
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

    cmd = [sys.executable, "-m", "scripts.dashboard", "--import-missing", "Foo"]
    subprocess.run(cmd, cwd=repo_root, check=True)

    updated = json.loads(config_path.read_text(encoding="utf-8"))
    group = updated["SENDER_TO_LABELS"]["Foo"][0]
    assert "b@example.com" in group["emails"]
