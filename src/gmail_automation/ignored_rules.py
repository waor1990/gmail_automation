"""Utilities for working with IGNORED_EMAILS configuration rules.

This module defines a structured representation for ignore rules along with
helpers to normalise configuration data and evaluate rule matches. The richer
rule schema enables deterministic processing in the email pipeline and shared
behaviour across analytics tooling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from email.utils import parseaddr
from typing import Any, Dict, Iterable, Iterator, List, Sequence


def _unique_preserve_order(values: Iterable[str]) -> List[str]:
    """Return values with duplicates removed while preserving order."""

    seen: set[str] = set()
    result: List[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _to_bool(value: object, default: bool = False) -> bool:
    """Coerce strings commonly used in configs to booleans."""

    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y"}:
            return True
        if lowered in {"false", "0", "no", "n"}:
            return False
    return default


def _clean_domain(value: str) -> str:
    """Normalise a domain string by stripping whitespace and leading '@'."""

    cleaned = value.strip()
    if cleaned.startswith("@"):
        cleaned = cleaned[1:]
    return cleaned.lower()


def _normalise_string_list(value: object) -> List[str]:
    """Coerce list-like config values into a list of non-empty strings."""

    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, Sequence):
        return []
    strings: List[str] = []
    for item in value:
        if item is None:
            continue
        text = str(item).strip()
        if text:
            strings.append(text)
    return strings


def _normalise_apply_labels(value: object) -> List[str]:
    """Return a list of label names suitable for API usage."""

    labels = _normalise_string_list(value)
    return [label for label in labels if label]


@dataclass(frozen=True)
class RuleActions:
    """Actions supported by an ignored-email rule."""

    skip_analysis: bool = False
    skip_import: bool = False
    mark_as_read: bool = False
    apply_labels: tuple[str, ...] = ()
    archive: bool = False
    delete_after_days: int | None = None

    def has_pipeline_actions(self) -> bool:
        """Return ``True`` if any actions affect the Gmail pipeline."""

        return bool(
            self.mark_as_read
            or self.apply_labels
            or self.archive
            or self.delete_after_days is not None
        )


@dataclass(frozen=True)
class IgnoredRule:
    """Represent a single IGNORED_EMAILS rule."""

    name: str
    senders: tuple[str, ...]
    domains: tuple[str, ...]
    subject_contains: tuple[str, ...]
    actions: RuleActions
    index: int = field(default=0)
    _senders_cf: tuple[str, ...] = field(init=False, repr=False)
    _domains_cf: tuple[str, ...] = field(init=False, repr=False)
    _subjects_cf: tuple[str, ...] = field(init=False, repr=False)

    def __post_init__(self) -> None:  # pragma: no cover - dataclass init code
        object.__setattr__(
            self, "_senders_cf", tuple(sender.casefold() for sender in self.senders)
        )
        object.__setattr__(
            self,
            "_domains_cf",
            tuple(_clean_domain(domain) for domain in self.domains),
        )
        object.__setattr__(
            self,
            "_subjects_cf",
            tuple(subject.casefold() for subject in self.subject_contains),
        )

    @staticmethod
    def _extract_address(sender: str | None) -> str | None:
        """Return the email address portion of a ``From`` header."""

        if not sender:
            return None
        _name, addr = parseaddr(sender)
        addr = addr.strip()
        return addr or None

    def matches_sender(self, sender: str | None) -> bool:
        """Return ``True`` if the sender matches rule senders or domains."""

        address = self._extract_address(sender)
        if not address:
            return False
        folded = address.casefold()
        if self._senders_cf and folded in self._senders_cf:
            return True
        if self._domains_cf:
            domain = address.split("@", 1)[-1].casefold()
            if domain in self._domains_cf:
                return True
        return False

    def matches_subject(self, subject: str | None) -> bool:
        """Return ``True`` if the subject matches configured substrings."""

        if not self._subjects_cf:
            return False
        if subject is None:
            return False
        folded = subject.casefold()
        return any(token in folded for token in self._subjects_cf)

    def matches(self, sender: str | None, subject: str | None) -> bool:
        """Return ``True`` if either sender or subject matches the rule."""

        return self.matches_sender(sender) or self.matches_subject(subject)

    def matches_address(self, address: str) -> bool:
        """Case-insensitive match against a plain email address."""

        folded = address.casefold()
        if self._senders_cf and folded in self._senders_cf:
            return True
        if self._domains_cf:
            domain = folded.split("@", 1)[-1]
            return domain in self._domains_cf
        return False


class IgnoredRulesEngine:
    """Evaluate IGNORED_EMAILS rules against messages."""

    def __init__(self, rules: Sequence[IgnoredRule]):
        self._rules = list(rules)

    @classmethod
    def from_config(cls, rules_config: Sequence[dict]) -> "IgnoredRulesEngine":
        """Build an engine from normalised rule dictionaries."""

        rules: List[IgnoredRule] = []
        for index, data in enumerate(rules_config):
            actions_dict = data.get("actions", {})
            actions = RuleActions(
                skip_analysis=_to_bool(actions_dict.get("skip_analysis")),
                skip_import=_to_bool(actions_dict.get("skip_import")),
                mark_as_read=_to_bool(actions_dict.get("mark_as_read")),
                apply_labels=tuple(actions_dict.get("apply_labels", [])),
                archive=_to_bool(actions_dict.get("archive")),
                delete_after_days=actions_dict.get("delete_after_days"),
            )
            rules.append(
                IgnoredRule(
                    name=str(data.get("name", f"Rule {index + 1}")),
                    senders=tuple(data.get("senders", [])),
                    domains=tuple(data.get("domains", [])),
                    subject_contains=tuple(data.get("subject_contains", [])),
                    actions=actions,
                    index=index,
                )
            )
        return cls(rules)

    @property
    def rules(self) -> Sequence[IgnoredRule]:
        """Return the ordered rule list."""

        return tuple(self._rules)

    def iter_matches(
        self, sender: str | None, subject: str | None
    ) -> Iterator[IgnoredRule]:
        """Yield rules that match the provided sender or subject."""

        for rule in self._rules:
            if rule.matches(sender, subject):
                yield rule

    def should_skip_analysis(self, email: str) -> bool:
        """Return ``True`` if any rule skips analysis for the email."""

        folded = email.strip()
        if not folded:
            return False
        for rule in self._rules:
            if rule.actions.skip_analysis and rule.matches_address(folded):
                return True
        return False

    def should_skip_import(self, email: str) -> bool:
        """Return ``True`` if any rule skips config import for the email."""

        folded = email.strip()
        if not folded:
            return False
        for rule in self._rules:
            if rule.actions.skip_import and rule.matches_address(folded):
                return True
        return False


def normalize_ignored_rules(rules: Sequence[object]) -> List[dict]:
    """Return canonical representations of IGNORED_EMAILS rules."""

    normalized: List[dict] = []
    for index, raw_rule in enumerate(rules or []):
        normalized.append(_normalize_single_rule(raw_rule, index))
    return normalized


def _normalize_single_rule(raw_rule: object, index: int) -> dict:
    if isinstance(raw_rule, str):
        sender = raw_rule.strip()
        if not sender:
            raise ValueError("IGNORED_EMAILS entries cannot be empty strings")
        return {
            "name": sender,
            "senders": [sender],
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

    if not isinstance(raw_rule, dict):
        raise ValueError(
            "IGNORED_EMAILS entries must be strings or dictionaries; "
            f"received type {type(raw_rule).__name__} at index {index}"
        )

    data: Dict[str, Any] = dict(raw_rule)  # shallow copy
    match_raw = data.get("match")
    match_section: Dict[str, Any]
    if isinstance(match_raw, dict):
        match_section = match_raw
    else:
        match_section = {}

    senders = _normalise_string_list(
        data.get("senders")
        or data.get("emails")
        or match_section.get("senders")
        or match_section.get("emails")
    )
    domains = [
        _clean_domain(d)
        for d in _normalise_string_list(
            data.get("domains")
            or match_section.get("domains")
            or data.get("domain")
            or match_section.get("domain")
        )
    ]
    subjects = _normalise_string_list(
        data.get("subject_contains")
        or match_section.get("subject_contains")
        or data.get("subjects")
        or match_section.get("subjects")
    )

    senders = _unique_preserve_order(senders)
    domains = _unique_preserve_order(domain for domain in domains if domain)
    subjects = _unique_preserve_order(subjects)

    if not (senders or domains or subjects):
        raise ValueError(
            "IGNORED_EMAILS rules must define senders, domains, or subject filters"
        )

    actions_src = data.get("actions")
    actions_dict: Dict[str, Any]
    if isinstance(actions_src, dict):
        actions_dict = actions_src
    else:
        actions_dict = {}

    def action_value(key: str) -> object:
        if key in data:
            return data[key]
        return actions_dict.get(key)

    skip_analysis = _to_bool(action_value("skip_analysis"))
    skip_import = _to_bool(action_value("skip_import"), default=False)
    mark_as_read = _to_bool(action_value("mark_as_read"))
    archive = _to_bool(action_value("archive"))
    apply_labels = _normalise_apply_labels(action_value("apply_labels"))

    delete_after_raw = action_value("delete_after_days")
    delete_after_days: int | None
    if delete_after_raw in (None, ""):
        delete_after_days = None
    else:
        if isinstance(delete_after_raw, (int, str)):
            try:
                delete_after_days = int(delete_after_raw)
            except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
                raise ValueError(
                    "delete_after_days must be an integer or null"
                ) from exc
        else:
            raise ValueError("delete_after_days must be an integer or null")
        if delete_after_days < 0:
            raise ValueError("delete_after_days must be zero or greater")

    if (skip_analysis or skip_import) and not (senders or domains):
        raise ValueError(
            "Rules that skip analysis or import must specify senders or domains"
        )

    name_value = data.get("name") or (
        senders[0] if senders else (f"@{domains[0]}" if domains else subjects[0])
    )

    return {
        "name": str(name_value),
        "senders": senders,
        "domains": domains,
        "subject_contains": subjects,
        "actions": {
            "skip_analysis": skip_analysis,
            "skip_import": skip_import,
            "mark_as_read": mark_as_read,
            "apply_labels": apply_labels,
            "archive": archive,
            "delete_after_days": delete_after_days,
        },
    }
