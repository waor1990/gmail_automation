from scripts.dashboard.transforms import (
    config_to_table,
    table_to_config,
    rows_to_grouped,
    ignored_rules_to_rows,
    rows_to_ignored_rules,
)


def test_config_to_table_sanitizes_types():
    cfg = {
        "SENDER_TO_LABELS": {
            "Label": [
                {
                    "emails": ["a@example.com"],
                    "read_status": "true",
                    "delete_after_days": "30",
                }
            ]
        }
    }
    rows = config_to_table(cfg)
    assert rows == [
        {
            "label": "Label",
            "group_index": 0,
            "email": "a@example.com",
            "read_status": True,
            "delete_after_days": 30,
        }
    ]


def test_table_to_config_sanitizes_types():
    rows = [
        {
            "label": "Label",
            "group_index": 0,
            "email": "a@example.com",
            "read_status": "true",
            "delete_after_days": "30",
        },
        {
            "label": "Label",
            "group_index": 1,
            "email": "b@example.com",
            "read_status": "false",
            "delete_after_days": None,
        },
    ]
    cfg = table_to_config(rows)
    assert cfg == {
        "SENDER_TO_LABELS": {
            "Label": [
                {
                    "read_status": True,
                    "delete_after_days": 30,
                    "emails": ["a@example.com"],
                },
                {
                    "read_status": False,
                    "delete_after_days": None,
                    "emails": ["b@example.com"],
                },
            ]
        },
        "IGNORED_EMAILS": [],
    }


def test_rows_to_grouped_groups_by_label_and_index():
    rows = [
        {"label": "L1", "group_index": 0, "email": "a@example.com"},
        {"label": "L1", "group_index": 0, "email": "b@example.com"},
        {"label": "L1", "group_index": 1, "email": "c@example.com"},
        {"label": "L2", "group_index": 0, "email": "d@example.com"},
    ]
    grouped = rows_to_grouped(rows)
    assert grouped == {
        "L1": {0: ["a@example.com", "b@example.com"], 1: ["c@example.com"]},
        "L2": {0: ["d@example.com"]},
    }


def test_ignored_rules_round_trip():
    cfg = {
        "IGNORED_EMAILS": [
            {
                "name": "Legacy",
                "senders": ["skip@example.com"],
                "domains": [],
                "subject_contains": [],
                "actions": {
                    "skip_analysis": True,
                    "skip_import": True,
                    "mark_as_read": False,
                    "apply_labels": [],
                    "archive": False,
                    "delete_after_days": None,
                },
            }
        ]
    }
    rows = ignored_rules_to_rows(cfg)
    assert rows[0]["name"] == "Legacy"
    assert rows_to_ignored_rules(rows) == cfg["IGNORED_EMAILS"]
