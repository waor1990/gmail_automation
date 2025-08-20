#!/usr/bin/env python3
from dash import Dash
from .layout import make_layout
from .callbacks import register_callbacks
from .analysis import (
    load_config,
    analyze_email_consistency,
    check_alphabetization,
    check_case_and_duplicates,
    compute_label_differences,
)
from .transforms import config_to_tables
from .utils_io import read_json
from .constants import LABELS_JSON
from .reports import write_ECAQ_report, write_diff_json


def _prepare_initial_data():
    cfg = load_config()
    # Execute reports automatically on load
    try:
        write_ECAQ_report()
    except Exception:
        pass
    try:
        write_diff_json()
    except Exception:
        pass

    el_rows, stl_rows = config_to_tables(cfg)
    analysis = {
        "consistency": analyze_email_consistency(cfg),
        "sorting": check_alphabetization(cfg),
        "case_dups": check_case_and_duplicates(cfg),
    }
    diff = None
    if LABELS_JSON.exists():
        labels = read_json(LABELS_JSON)
        diff = compute_label_differences(cfg, labels)
    return cfg, el_rows, stl_rows, analysis, diff


def main():
    cfg, el_rows, stl_rows, analysis, diff = _prepare_initial_data()
    app = Dash(__name__)
    app.title = "Gmail Config Dashboard"
    app.layout = make_layout(el_rows, stl_rows, analysis, diff, cfg)
    register_callbacks(app)
    app.run(host="127.0.0.1", port=8050, debug=False)


if __name__ == "__main__":
    main()
