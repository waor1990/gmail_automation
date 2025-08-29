#!/usr/bin/env python3
from dash import Dash
from .layout import make_layout
from .callbacks import register_callbacks
from .analysis import load_config, find_unprocessed_senders
from .analysis_helpers import run_full_analysis
from .transforms import config_to_table
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
    analysis = run_full_analysis(cfg)
    diff = analysis["diff"]
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
