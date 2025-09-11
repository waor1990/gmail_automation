#!/usr/bin/env python3
import os
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


def main(host: str | None = None, port: int | None = None, debug: bool | None = None):
    cfg, stl_rows, analysis, diff, pending = _prepare_initial_data()
    # Allow callbacks that reference components created dynamically
    app = Dash(__name__, suppress_callback_exceptions=True)
    app.title = "Gmail Config Dashboard"
    app.layout = make_layout(stl_rows, analysis, diff, cfg, pending)
    register_callbacks(app)

    # Resolve host/port/debug from parameters, env vars, then defaults
    # Environment variables supported: DASH_HOST, DASH_PORT, PORT (fallback)
    resolved_host = (
        host or os.environ.get("DASH_HOST") or os.environ.get("HOST") or "127.0.0.1"
    )
    env_port = os.environ.get("DASH_PORT") or os.environ.get("PORT")
    resolved_port = port if port is not None else int(env_port) if env_port else 8050
    resolved_debug = bool(debug) if debug is not None else False

    app.run(host=resolved_host, port=resolved_port, debug=resolved_debug)


if __name__ == "__main__":
    main()
