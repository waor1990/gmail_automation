from scripts.dashboard.analysis import compute_label_differences
from scripts.dashboard.reports import generate_report_text


def test_compute_label_differences_ignores_case():
    cfg = {"SENDER_TO_LABELS": {"Foo": [{"emails": ["user@example.com"]}]}}
    labels_data = {
        "SENDER_TO_LABELS": {
            "Foo": [{"emails": ["User@example.com", "other@example.com"]}]
        }
    }
    diff = compute_label_differences(cfg, labels_data)
    missing = diff["missing_emails_by_label"]["Foo"]["missing_emails"]
    assert missing == ["other@example.com"]


def test_ecaq_report_flags_case_insensitive_duplicates():
    cfg = {
        "SENDER_TO_LABELS": {
            "Foo": [{"emails": ["Dup@example.com", "dup@example.com"]}]
        }
    }
    text = generate_report_text(cfg)
    assert "LISTS WITH DUPLICATES (1):" in text
    assert "SENDER_TO_LABELS.Foo[0].emails (1 duplicates)" in text
    assert "dup@example.com" in text


def test_ecaq_report_flags_cross_label_duplicates():
    cfg = {
        "SENDER_TO_LABELS": {
            "Foo": [{"emails": ["dup@example.com"]}],
            "Bar": [{"emails": ["Dup@example.com"]}],
        }
    }
    text = generate_report_text(cfg)
    assert "SENDERS IN MULTIPLE LABELS (1):" in text
    assert "dup@example.com" in text
    assert "SENDER_TO_LABELS.Foo[0].emails" in text
    assert "SENDER_TO_LABELS.Bar[0].emails" in text
