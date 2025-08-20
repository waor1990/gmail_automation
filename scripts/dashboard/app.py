#!/usr/bin/env python3
from dash import Dash
from .layout import make_layout
from .callbacks import register_callbacks

def main():
    app = Dash(__name__)
    app.title = "Gmail Config Dashboard"
    app.layout = make_layout()
    register_callbacks(app)
    app.run_server(host="127.0.0.1", port=8050, debug=False)

if __name__ == "__main__":
    main()