#!/usr/bin/env python3
from dash import Dash
from .layout import make_layout
from .callbacks import register_callbacks
from .analysis import (
    load_config,
    check_alphabetization,
    check_case_and_duplicates,
    compute_label_differences,
    find_unprocessed_senders,
)
from .transforms import config_to_table
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

    stl_rows = config_to_table(cfg)
    analysis = {
        "sorting": check_alphabetization(cfg),
        "case_dups": check_case_and_duplicates(cfg),
    }
    diff = None
    if LABELS_JSON.exists():
        labels = read_json(LABELS_JSON)
        diff = compute_label_differences(cfg, labels)
    pending = find_unprocessed_senders(cfg)
    return cfg, stl_rows, analysis, diff, pending


def main():
    cfg, stl_rows, analysis, diff, pending = _prepare_initial_data()
    app = Dash(__name__)
    app.title = "Gmail Config Dashboard"
    app.layout = make_layout(stl_rows, analysis, diff, cfg, pending)
    register_callbacks(app)
    app.run(host="127.0.0.1", port=8050, debug=False)


if __name__ == "__main__":
    main()
