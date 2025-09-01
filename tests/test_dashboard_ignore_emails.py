from scripts.dashboard.analysis import compute_label_differences


def test_ignored_emails_excluded_from_diff():
    cfg = {"SENDER_TO_LABELS": {}, "IGNORED_EMAILS": ["skip@example.com"]}
    labels = {
        "SENDER_TO_LABELS": {
            "Foo": [{"emails": ["skip@example.com", "keep@example.com"]}]
        }
    }
    diff = compute_label_differences(cfg, labels)
    missing = diff["missing_emails_by_label"]["Foo"]["missing_emails"]
    assert missing == ["keep@example.com"]
    assert diff["comparison_summary"]["total_missing_emails"] == 1
