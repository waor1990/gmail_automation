"""Layout definition for the Gmail Automation dashboard."""

from dash import dcc, dash_table, html

from .theme import get_theme_style


def make_layout(stl_rows, analysis, diff, cfg, pending):
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
            html.Button("Switch to Dark Mode", id="btn-toggle-theme", n_clicks=0),
        ],
    )

    defaults_panel = html.Div(
        id="defaults-panel",
        style={
            "display": "flex",
            "gap": "8px",
            "alignItems": "center",
            "marginBottom": "16px",
        },
        children=[
            html.Span("Defaults:"),
            dcc.Checklist(
                id="default-read-status",
                options=[{"label": "mark read", "value": "read"}],
                value=[],
            ),
            dcc.Input(
                id="default-delete-days",
                type="number",
                placeholder="delete_after_days",
                style={"width": "120px"},
            ),
        ],
    )

    return html.Div(
        id="app-root",
        style=get_theme_style("light"),
        children=[
            dcc.Store(id="store-theme", storage_type="local", data={"theme": "light"}),
            dcc.Store(
                id="store-defaults",
                storage_type="local",
                data={"read_status": False, "delete_after_days": None},
            ),
            html.H1("Gmail Email Configuration Dashboard"),
            control_row,
            defaults_panel,
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
                    html.H2("New Senders Pending Processing"),
                    html.Div(
                        "Senders not yet processed by Gmail automation.",
                        id="pending-help",
                        style={
                            "fontSize": "12px",
                            "color": "#a00",
                            "marginBottom": "4px",
                        },
                    ),
                    html.Button(
                        "Export New Senders CSV",
                        id="btn-export-pending",
                        n_clicks=0,
                        style={"marginBottom": "8px"},
                        title=(
                            "Save the current New Senders list to "
                            "config/new_senders.csv"
                        ),
                    ),
                    dcc.Dropdown(
                        id="ddl-pending-labels",
                        options=[],
                        multi=True,
                        placeholder="Filter by label...",
                        style={"marginBottom": "8px", "maxWidth": "400px"},
                    ),
                    dash_table.DataTable(
                        id="tbl-new-senders",
                        columns=[
                            {"name": "", "id": "status"},
                            {"name": "email", "id": "email"},
                            {"name": "labels", "id": "labels"},
                        ],
                        data=pending,
                        page_size=15,
                        style_table={"maxHeight": "200px", "overflowY": "auto"},
                        style_cell={"fontFamily": "monospace", "fontSize": "12px"},
                        sort_action="native",
                        filter_action="native",
                        style_data_conditional=[
                            {
                                "if": {"filter_query": "{status} = '🔴'"},
                                "style": {"backgroundColor": "#ffe5e5"},
                            },
                            {
                                "if": {"column_id": "status"},
                                "style": {
                                    "textAlign": "center",
                                    "width": "30px",
                                },
                            },
                        ],
                    ),
                ],
            ),
            html.Div(
                style=section_style,
                children=[
                    html.H2("Email Collision Viewer"),
                    html.Div(
                        "Emails assigned to multiple labels.",
                        style={
                            "fontSize": "12px",
                            "color": "#a00",
                            "marginBottom": "4px",
                        },
                    ),
                    html.Div(
                        (
                            "Select an action for each email. Choose 'Reassign' and "
                            "pick the target label, 'Remove' to delete it from all "
                            "labels, or 'Split' to keep it in all labels."
                        ),
                        style={
                            "fontSize": "12px",
                            "color": "#555",
                            "marginBottom": "4px",
                        },
                    ),
                    dash_table.DataTable(
                        id="tbl-collisions",
                        columns=[
                            {"name": "email", "id": "email"},
                            {"name": "labels", "id": "labels"},
                            {
                                "name": "action ▾",
                                "id": "action",
                                "presentation": "dropdown",
                            },
                            {
                                "name": "to label ▾",
                                "id": "to_label",
                                "presentation": "dropdown",
                            },
                        ],
                        data=[],
                        editable=True,
                        dropdown={
                            "action": {
                                "options": [
                                    {"label": "Reassign", "value": "reassign"},
                                    {"label": "Remove", "value": "remove"},
                                    {"label": "Split", "value": "split"},
                                ]
                            }
                        },
                        dropdown_conditional=[],
                        tooltip_header={
                            "action": (
                                "Reassign \u2192 move to one label; "
                                "Remove \u2192 delete from labels; "
                                "Split \u2192 keep in all labels"
                            )
                        },
                        tooltip_delay=0,
                        tooltip_duration=None,
                        page_size=15,
                        style_table={"maxHeight": "200px", "overflowY": "auto"},
                        style_cell={
                            "fontFamily": "monospace",
                            "fontSize": "12px",
                        },
                        style_data_conditional=[
                            {
                                "if": {"column_id": "action"},
                                "style": {"cursor": "pointer"},
                            },
                            {
                                "if": {"column_id": "to_label"},
                                "style": {"cursor": "pointer"},
                            },
                        ],
                    ),
                    html.Button(
                        "Apply Resolutions",
                        id="btn-apply-collisions",
                        n_clicks=0,
                        style={"marginTop": "8px"},
                    ),
                ],
            ),
            html.Div(
                style=section_style,
                children=[
                    html.H2("SENDER_TO_LABELS Editor"),
                    html.P(
                        [
                            (
                                "Edit mappings below. Use Advanced Mode to merge "
                                "or split rows, then apply edits and save."
                            ),
                        ],
                        id="stl-help",
                        style={"fontSize": "14px", "maxWidth": "800px"},
                    ),
                    dcc.RadioItems(
                        id="stl-view-toggle",
                        options=[
                            {"label": "Flat Table", "value": "flat"},
                            {"label": "Grouped Tree", "value": "grouped"},
                        ],
                        value="flat",
                        inline=True,
                        style={"marginBottom": "8px"},
                    ),
                    html.Div(
                        id="flat-view",
                        children=[
                            dash_table.DataTable(
                                id="tbl-stl",
                                columns=[
                                    {"name": "label", "id": "label"},
                                    {
                                        "name": "group (0=Mark Read, 1=Mark Unread)",
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
                                hidden_columns=[
                                    "group_index",
                                    "read_status",
                                    "delete_after_days",
                                ],
                                data=stl_rows,
                                editable=True,
                                row_deletable=True,
                                row_selectable="multi",
                                filter_action="native",
                                page_size=15,
                                style_table={"maxHeight": "400px", "overflowY": "auto"},
                                style_cell={
                                    "fontFamily": "monospace",
                                    "fontSize": "12px",
                                },
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
                                        "Show Advanced Mode",
                                        id="btn-toggle-advanced",
                                        n_clicks=0,
                                        title=(
                                            "Toggle visibility of grouping controls "
                                            "and the group column "
                                            "(0=Mark Read, 1=Mark Unread)"
                                        ),
                                    ),
                                    html.Button(
                                        "Apply table edits to config",
                                        id="btn-apply-edits",
                                        n_clicks=0,
                                        style={"background": "#e8f0ff"},
                                        title=(
                                            "Sync changes from the table to the "
                                            "working config. Use Save Config to "
                                            "write to file."
                                        ),
                                    ),
                                ],
                            ),
                            html.Div(
                                id="advanced-controls",
                                style={
                                    "display": "none",
                                    "gap": "8px",
                                    "marginTop": "8px",
                                },
                                children=[
                                    html.Button(
                                        "Merge Selected",
                                        id="btn-merge-groups",
                                        n_clicks=0,
                                        title=(
                                            "Merge selected rows into a single "
                                            "group per label"
                                        ),
                                    ),
                                    html.Button(
                                        "Split Selected",
                                        id="btn-split-groups",
                                        n_clicks=0,
                                        title=(
                                            "Move each selected row into its own group"
                                        ),
                                    ),
                                ],
                            ),
                            html.Div(
                                id="stl-selection",
                                style={"fontSize": "12px", "marginTop": "4px"},
                            ),
                            html.Span(
                                (
                                    "Applies edits from the table to the working "
                                    "config; remember to Save Config to persist."
                                ),
                                style={"fontSize": "12px", "color": "#555"},
                            ),
                        ],
                    ),
                    html.Div(
                        id="grouped-view",
                        style={"display": "none"},
                        children=[html.Div(id="stl-grouped")],
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
                            {
                                "name": "exists_in_target",
                                "id": "exists_in_target",
                                "presentation": "markdown",
                            },
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
                                "name": "coverage",
                                "id": "coverage",
                                "presentation": "markdown",
                            },
                            {
                                "name": "missing_emails",
                                "id": "missing_emails",
                                "presentation": "markdown",
                            },
                            {
                                "name": "actions",
                                "id": "actions",
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
            html.Div(
                style={"marginBottom": "24px"},
                children=[
                    html.Label(
                        "Filter SENDER_TO_LABELS by label",
                        htmlFor="ddl-stl-label-filter",
                        style={"display": "block", "fontWeight": "bold"},
                    ),
                    dcc.Dropdown(
                        id="ddl-stl-label-filter",
                        options=[],
                        placeholder="Select a label to filter the editor...",
                        clearable=True,
                        style={"marginTop": "4px", "maxWidth": "400px"},
                    ),
                ],
            ),
            html.Div(
                style=section_style,
                children=[
                    html.H2("Logs Viewer"),
                    html.Button("Load Log Files", id="btn-load-logs", n_clicks=0),
                    dcc.Dropdown(
                        id="ddl-log-files",
                        options=[],
                        placeholder="Select log file",
                        style={"marginTop": "8px"},
                    ),
                    html.Button(
                        "View Log",
                        id="btn-view-log",
                        n_clicks=0,
                        style={"marginTop": "8px"},
                    ),
                    dcc.Dropdown(
                        id="ddl-log-runs",
                        options=[],
                        placeholder="Select run instance",
                        style={"marginTop": "8px"},
                    ),
                    html.Div(
                        id="log-content",
                        style={
                            "whiteSpace": "pre",
                            "fontFamily": "monospace",
                            "fontSize": "12px",
                            "maxHeight": "400px",
                            "overflowY": "auto",
                            "border": "1px solid #ccc",
                            "padding": "8px",
                            "marginTop": "8px",
                        },
                    ),
                ],
            ),
            dcc.Store(id="store-config", data=cfg),
            dcc.Store(id="store-analysis", data=analysis),
            dcc.Store(id="store-diff", data=diff),
            dcc.Store(id="store-pending", data=pending),
            dcc.Store(id="store-log-runs"),
            dcc.Store(id="store-log-selection", storage_type="local"),
        ],
    )
