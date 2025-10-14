from scripts.dashboard.analysis import import_missing_emails


def test_import_missing_emails_existing_label():
    cfg = {
        "SENDER_TO_LABELS": {
            "Foo": [{"emails": ["a@example.com"], "read_status": True}]
        }
    }
    labels = {
        "SENDER_TO_LABELS": {
            "Foo": [{"emails": ["a@example.com", "B@example.com"], "read_status": True}]
        }
    }
    updated, added = import_missing_emails(cfg, labels, "Foo", ["B@example.com"])
    group = updated["SENDER_TO_LABELS"]["Foo"][0]
    assert group["emails"] == ["a@example.com", "B@example.com"]
    assert group["read_status"] is True
    assert added == ["B@example.com"]


def test_import_missing_preserves_existing_metadata():
    cfg = {
        "SENDER_TO_LABELS": {
            "Foo": [
                {
                    "emails": ["existing@example.com"],
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
                    "emails": ["existing@example.com", "new@example.com"],
                    "read_status": False,
                    "delete_after_days": 30,
                }
            ]
        }
    }

    updated, added = import_missing_emails(cfg, labels, "Foo", ["new@example.com"])

    group = updated["SENDER_TO_LABELS"]["Foo"][0]
    assert group["read_status"] is True
    assert group["delete_after_days"] == 14
    assert "new@example.com" in group["emails"]
    assert added == ["new@example.com"]


def test_import_missing_applies_defaults_when_missing_metadata():
    cfg = {"SENDER_TO_LABELS": {"Foo": [{"emails": ["existing@example.com"]}]}}
    labels = {
        "SENDER_TO_LABELS": {
            "Foo": [
                {
                    "emails": ["existing@example.com", "new@example.com"],
                    "read_status": False,
                    "delete_after_days": 45,
                }
            ]
        }
    }

    updated, added = import_missing_emails(cfg, labels, "Foo", ["new@example.com"])

    group = updated["SENDER_TO_LABELS"]["Foo"][0]
    assert group["read_status"] is False
    assert group["delete_after_days"] == 45
    assert "new@example.com" in group["emails"]
    assert added == ["new@example.com"]


def test_import_missing_emails_creates_label_and_avoids_dups():
    cfg = {"SENDER_TO_LABELS": {}}
    labels = {
        "SENDER_TO_LABELS": {
            "Bar": [
                {
                    "emails": ["User@Example.com", "second@example.com"],
                    "read_status": False,
                    "delete_after_days": 7,
                }
            ]
        }
    }
    # include duplicate with different casing to ensure dedupe
    updated, added = import_missing_emails(
        cfg, labels, "Bar", ["user@example.com", "second@example.com"]
    )
    group = updated["SENDER_TO_LABELS"]["Bar"][0]
    assert group["emails"] == ["User@Example.com", "second@example.com"]
    assert group["read_status"] is False
    assert group["delete_after_days"] == 7
    assert added == ["second@example.com"]
