from dash import html, dcc, dash_table


def make_layout(el_rows, stl_rows, analysis, diff, cfg):
    section_style = {"marginBottom": "24px"}
    control_row = html.Div(
        style={"display": "flex", "gap": "12px", "flexWrap": "wrap"},
        children=[
            html.Button("Fix Case", id="btn-fix-case", n_clicks=0),
            html.Button("Remove Duplicates", id="btn-fix-dups", n_clicks=0),
            html.Button("Alphabetize", id="btn-fix-sort", n_clicks=0),
            html.Button(
                "Fix All", id="btn-fix-all", n_clicks=0, style={"fontWeight": "bold"}
            ),
            dcc.Checklist(
                id="chk-backup",
                options=[{"label": "Create backup on save", "value": "backup"}],
                value=["backup"],
                style={"marginLeft": "8px"},
            ),
            html.Button(
                "Save Config",
                id="btn-save",
                n_clicks=0,
                style={"background": "#e8ffe8"},
            ),
            html.Button("Export ECAQ Report", id="btn-export-report", n_clicks=0),
            html.Button("Export Differences JSON", id="btn-export-diff", n_clicks=0),
            html.Button("Refresh Reports", id="btn-refresh-reports", n_clicks=0),
        ],
    )

    return html.Div(
        style={
            "fontFamily": "Arial, sans-serif",
            "padding": "20px",
            "maxWidth": "1200px",
            "margin": "0 auto",
        },
        children=[
            html.H1("Gmail Email Configuration Dashboard"),
            control_row,
            html.Div(
                id="status", style={"marginBottom": "16px", "whiteSpace": "pre-wrap"}
            ),
            html.Div(
                style=section_style,
                children=[
                    html.H2("Configuration Reports"),
                    html.Div(id="metrics", style={"marginBottom": "8px"}),
                    html.Div(id="issues-block", style={"marginBottom": "8px"}),
                    html.Div(id="projected-changes"),
                ],
            ),
            html.Div(
                style=section_style,
                children=[
                    html.H2("EMAIL_LIST Editor"),
                    dash_table.DataTable(
                        id="tbl-email-list",
                        columns=[{"name": "email", "id": "email"}],
                        data=el_rows,
                        editable=True,
                        row_deletable=True,
                        row_selectable="multi",
                        page_size=15,
                        style_table={"maxHeight": "350px", "overflowY": "auto"},
                        style_cell={"fontFamily": "monospace", "fontSize": "12px"},
                    ),
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "8px"},
                        children=[
                            html.Button(
                                "Add blank row to EMAIL_LIST",
                                id="btn-add-email-row",
                                n_clicks=0,
                                title="Append an empty row for a new email address",
                            ),
                            html.Span(
                                "Appends an empty row to the table for a new email.",
                                style={"fontSize": "12px", "color": "#555"},
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(
                style=section_style,
                children=[
                    html.H2("SENDER_TO_LABELS Editor"),
                    dash_table.DataTable(
                        id="tbl-stl",
                        columns=[
                            {"name": "label", "id": "label"},
                            {
                                "name": "group_index",
                                "id": "group_index",
                                "type": "numeric",
                            },
                            {"name": "email", "id": "email"},
                            {"name": "read_status", "id": "read_status"},
                            {
                                "name": "delete_after_days",
                                "id": "delete_after_days",
                                "type": "numeric",
                            },
                        ],
                        hidden_columns=["read_status", "delete_after_days"],
                        data=stl_rows,
                        editable=True,
                        row_deletable=True,
                        row_selectable="multi",
                        page_size=15,
                        style_table={"maxHeight": "400px", "overflowY": "auto"},
                        style_cell={"fontFamily": "monospace", "fontSize": "12px"},
                    ),
                    html.Div(
                        style={"display": "flex", "gap": "8px"},
                        children=[
                            html.Button(
                                "Add blank row to SENDER_TO_LABELS",
                                id="btn-add-stl-row",
                                n_clicks=0,
                                title=(
                                    "Append an empty row for a new "
                                    "label/email mapping"
                                ),
                            ),
                            html.Button(
                                "Apply table edits to config",
                                id="btn-apply-edits",
                                n_clicks=0,
                                style={"background": "#e8f0ff"},
                                title=(
                                    "Sync changes from both tables to the "
                                    "working config. Use Save Config to "
                                    "write to file."
                                ),
                            ),
                        ],
                    ),
                    html.Span(
                        (
                            "Applies edits from both tables to the working "
                            "config; remember to Save Config to persist."
                        ),
                        style={"fontSize": "12px", "color": "#555"},
                    ),
                ],
            ),
            html.Div(
                style=section_style,
                children=[
                    html.H2("Differences View (Source: config/gmail_labels_data.json)"),
                    html.Div(id="diff-summary", style={"marginBottom": "8px"}),
                    dash_table.DataTable(
                        id="tbl-diff",
                        columns=[
                            {"name": "label", "id": "label"},
                            {"name": "exists_in_target", "id": "exists_in_target"},
                            {
                                "name": "total_in_source",
                                "id": "total_in_source",
                                "type": "numeric",
                            },
                            {
                                "name": "missing_count",
                                "id": "missing_count",
                                "type": "numeric",
                            },
                            {
                                "name": "missing_emails",
                                "id": "missing_emails",
                                "presentation": "markdown",
                            },
                        ],
                        data=[],
                        page_size=15,
                        markdown_options={"html": True},
                        style_table={"maxHeight": "400px", "overflowY": "auto"},
                        style_cell={
                            "fontFamily": "monospace",
                            "fontSize": "12px",
                            "whiteSpace": "normal",
                            "height": "auto",
                        },
                    ),
                    html.Div(id="diff-projected", style={"marginTop": "8px"}),
                ],
            ),
            dcc.Store(id="store-config", data=cfg),
            dcc.Store(id="store-analysis", data=analysis),
            dcc.Store(id="store-diff", data=diff),
        ],
    )
