from scripts.dashboard.collisions import resolve_collisions


def test_resolve_collisions_reassign():
    cfg = {
        "SENDER_TO_LABELS": {
            "Work": [{"emails": ["a@example.com"]}],
            "Personal": [{"emails": ["a@example.com", "b@example.com"]}],
        }
    }
    resolutions = [
        {
            "email": "a@example.com",
            "labels": ["Work", "Personal"],
            "action": "reassign:Work",
        }
    ]
    updated, changes = resolve_collisions(cfg, resolutions)
    assert updated["SENDER_TO_LABELS"]["Work"][0]["emails"] == ["a@example.com"]
    assert updated["SENDER_TO_LABELS"]["Personal"][0]["emails"] == ["b@example.com"]
    assert "a@example.com reassigned to Work" in changes


def test_resolve_collisions_remove():
    cfg = {
        "SENDER_TO_LABELS": {
            "Work": [{"emails": ["a@example.com"]}],
            "Personal": [{"emails": ["a@example.com"]}],
        }
    }
    resolutions = [
        {"email": "a@example.com", "labels": ["Work", "Personal"], "action": "remove"}
    ]
    updated, changes = resolve_collisions(cfg, resolutions)
    assert updated["SENDER_TO_LABELS"]["Work"][0]["emails"] == []
    assert updated["SENDER_TO_LABELS"]["Personal"][0]["emails"] == []
    assert "a@example.com removed" in changes


def test_resolve_collisions_split_no_change():
    cfg = {
        "SENDER_TO_LABELS": {
            "Work": [{"emails": ["a@example.com"]}],
            "Personal": [{"emails": ["a@example.com"]}],
        }
    }
    resolutions = [
        {"email": "a@example.com", "labels": ["Work", "Personal"], "action": "split"}
    ]
    updated, changes = resolve_collisions(cfg, resolutions)
    assert updated == cfg
    assert "a@example.com left in all labels" in changes
