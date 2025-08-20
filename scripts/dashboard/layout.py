from dash import html, dcc, dash_table

def make_layout():
    return html.Div(
        style={"fontFamily": "Arial, sans-serif", "padding": "16px"},
        children=[
            html.H2("Gmail Email Configuration Dashboard"),
            html.Div(
                style={"display": "flex", "gap": "16px", "flexWrap": "wrap", "alignItems": "center"},
                children=[
                    html.Button("Load Config", id="btn-load", n_clicks=0),
                    html.Button("Fix Case", id="btn-fix-case", n_clicks=0),
                    html.Button("Remove Duplicates", id="btn-fix-dups", n_clicks=0),
                    html.Button("Alphabetize", id="btn-fix-sort", n_clicks=0),
                    html.Button("Fix All", id="btn-fix-all", n_clicks=0, style={"fontWeight": "bold"}),
                    dcc.Checklist(
                        id="chk-backup",
                        options=[{"label": "Create backup on save", "value": "backup"}],
                        value=["backup"],
                        style={"marginLeft": "8px"},
                    ),
                    html.Button("Save Config", id="btn-save", n_clicks=0, style={"background": "#e8ffe8"}),
                    html.Button("Export ECAQ Report", id="btn-export-report", n_clicks=0),
                    html.Button("Compute Differences", id="btn-diff", n_clicks=0),
                    html.Button("Export Differences JSON", id="btn-export-diff", n_clicks=0),
                    html.Div(id="status", style={"marginLeft": "8px", "whiteSpace": "pre-wrap"}),
                ]
            ),
            html.Hr(),
            html.H3("Overview"),
            html.Div(id="metrics"),
            html.Div(id="issues-block"),
            html.Hr(),
            html.H3("EMAIL_LIST Editor"),
            dash_table.DataTable(
                id="tbl-email-list",
                columns=[{"name": "email", "id": "email"}],
                data=[],
                editable=True,
                row_deletable=True,
                row_selectable="multi",
                page_size=15,
                style_table={"maxHeight": "350px", "overflowY": "auto"},
                style_cell={"fontFamily": "monospace", "fontSize": "12px"},
            ),
            html.Button("Add Row to EMAIL_LIST", id="btn-add-email-row", n_clicks=0),
            html.Hr(),
            html.H3("SENDER_TO_LABELS Editor"),
            dash_table.DataTable(
                id="tbl-stl",
                columns=[
                    {"name": "label", "id": "label"},
                    {"name": "group_index", "id": "group_index", "type": "numeric"},
                    {"name": "email", "id": "email"},
                ],
                data=[],
                editable=True,
                row_deletable=True,
                row_selectable="multi",
                page_size=15,
                style_table={"maxHeight": "400px", "overflowY": "auto"},
                style_cell={"fontFamily": "monospace", "fontSize": "12px"},
            ),
            html.Div(style={"display": "flex", "gap": "8px"}, children=[
                html.Button("Add Row to SENDER_TO_LABELS", id="btn-add-stl-row", n_clicks=0),
                html.Button("Apply Table Edits", id="btn-apply-edits", n_clicks=0, style={"background": "#e8f0ff"}),
            ]),
            html.Hr(),
            html.H3("Differences View (Source: config/gmail_labels_data.json)"),
            html.Div(id="diff-summary"),
            dash_table.DataTable(
                id="tbl-diff",
                columns=[
                    {"name": "label", "id": "label"},
                    {"name": "exists_in_target", "id": "exists_in_target"},
                    {"name": "total_in_source", "id": "total_in_source", "type": "numeric"},
                    {"name": "missing_count", "id": "missing_count", "type": "numeric"},
                    {"name": "missing_emails (comma-separated)", "id": "missing_emails"},
                ],
                data=[],
                page_size=15,
                style_table={"maxHeight": "400px", "overflowY": "auto"},
                style_cell={"fontFamily": "monospace", "fontSize": "12px"},
            ),
            dcc.Store(id="store-config"),
            dcc.Store(id="store-analysis"),
            dcc.Store(id="store-diff"),
        ]
    )
