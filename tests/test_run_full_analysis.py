from scripts.dashboard.analysis_helpers import run_full_analysis


def test_run_full_analysis_returns_expected_structure():
    cfg = {
        "SENDER_TO_LABELS": {
            "Foo": [{"emails": ["b@example.com", "A@example.com", "A@example.com"]}]
        }
    }
    labels = {
        "SENDER_TO_LABELS": {"Foo": [{"emails": ["a@example.com", "c@example.com"]}]}
    }

    result = run_full_analysis(cfg, labels)

    assert set(result) >= {
        "sorting",
        "case_dups",
        "projected_changes",
        "diff",
        "projected_diff",
    }
    assert result["sorting"]
    assert result["case_dups"]["case_issues"]
    assert result["case_dups"]["duplicate_issues"]
    assert result["projected_changes"]
    assert result["diff"]["missing_emails_by_label"]["Foo"]["missing_emails"] == [
        "c@example.com"
    ]
    assert (
        result["projected_diff"]["comparison_summary"]["total_missing_emails"]
        == result["diff"]["comparison_summary"]["total_missing_emails"]
    )
