from scripts.dashboard.callbacks import _group_changes_by_label


def test_group_changes_by_label_groups_strings():
    changes = [
        "SENDER_TO_LABELS.Work[0].emails (fixed case)",
        "SENDER_TO_LABELS.Work[1].emails (removed 2 duplicates)",
        "SENDER_TO_LABELS.Personal[0].emails",
        "Unrelated entry",
    ]
    grouped = _group_changes_by_label(changes)
    assert grouped["Work"] == [
        "SENDER_TO_LABELS.Work[0].emails (fixed case)",
        "SENDER_TO_LABELS.Work[1].emails (removed 2 duplicates)",
    ]
    assert grouped["Personal"] == ["SENDER_TO_LABELS.Personal[0].emails"]
    assert grouped["Unknown"] == ["Unrelated entry"]
