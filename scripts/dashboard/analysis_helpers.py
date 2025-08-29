from __future__ import annotations

from typing import Any, Dict

from .analysis import (
    check_alphabetization,
    check_case_and_duplicates,
    normalize_case_and_dups,
    sort_lists,
    compute_label_differences,
)
from .constants import LABELS_JSON
from .utils_io import read_json


def run_full_analysis(
    cfg: Dict[str, Any], labels: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    """Run all config analyses and diff projections.

    Args:
        cfg: Current configuration mapping.
        labels: Optional pre-loaded labels data. If not provided, it will be
            read from ``LABELS_JSON`` when available.

    Returns:
        Dictionary with keys ``sorting``, ``case_dups``, ``projected_changes``,
        ``diff``, and ``projected_diff``.
    """

    sorting = check_alphabetization(cfg)
    case_dups = check_case_and_duplicates(cfg)

    if labels is None and LABELS_JSON.exists():
        labels = read_json(LABELS_JSON)

    diff = compute_label_differences(cfg, labels) if labels else None

    proj_cfg, changes = normalize_case_and_dups(cfg)
    proj_cfg, sort_changes = sort_lists(proj_cfg)
    changes.extend(sort_changes)
    proj_diff = compute_label_differences(proj_cfg, labels) if labels else None

    return {
        "sorting": sorting,
        "case_dups": case_dups,
        "projected_changes": changes,
        "diff": diff,
        "projected_diff": proj_diff,
    }
