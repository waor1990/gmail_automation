import pytest

from gmail_automation.ignored_rules import (
    IgnoredRulesEngine,
    normalize_ignored_rules,
)


def test_normalize_legacy_string_rule():
    rules = normalize_ignored_rules(["skip@example.com"])
    assert len(rules) == 1
    rule = rules[0]
    assert rule["senders"] == ["skip@example.com"]
    actions = rule["actions"]
    assert actions["skip_analysis"] is True
    assert actions["skip_import"] is True
    assert actions["mark_as_read"] is False
    assert actions["apply_labels"] == []


def test_normalize_invalid_rule_requires_match():
    with pytest.raises(ValueError):
        normalize_ignored_rules(
            [{"name": "invalid", "actions": {"skip_analysis": True}}]
        )


def test_engine_matching_and_flags():
    config_rules = normalize_ignored_rules(
        [
            {
                "name": "Domain Skip",
                "domains": ["example.com"],
                "actions": {"skip_analysis": True, "skip_import": False},
            },
            {
                "name": "Subject Rule",
                "subject_contains": ["alert"],
                "actions": {"mark_as_read": True},
            },
        ]
    )
    engine = IgnoredRulesEngine.from_config(config_rules)

    assert engine.should_skip_analysis("foo@example.com") is True
    assert engine.should_skip_import("foo@example.com") is False

    matches = list(engine.iter_matches("Foo <foo@example.com>", "Weekly Alert"))
    assert [rule.name for rule in matches] == ["Domain Skip", "Subject Rule"]

    unmatched = list(engine.iter_matches("bar@other.com", "Hello"))
    assert unmatched == []
