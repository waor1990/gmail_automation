from dash import html, no_update, callback_context
from dash import Input, Output, State
import re
from typing import Dict, List
from .analysis import (
    check_alphabetization,
    check_case_and_duplicates,
    load_config,
    normalize_case_and_dups,
    sort_lists,
    compute_label_differences,
    find_unprocessed_senders,
    import_missing_emails,
)
from .transforms import config_to_table, table_to_config
from .utils_io import write_json, backup_file, read_json
from .constants import CONFIG_JSON, LABELS_JSON, LOGS_DIR
from .group_ops import merge_selected, split_selected


def register_callbacks(app):
    @app.callback(
        Output("tbl-stl", "data", allow_duplicate=True),
        Output("store-config", "data", allow_duplicate=True),
        Output("store-analysis", "data", allow_duplicate=True),
        Output("status", "children", allow_duplicate=True),
        Input("btn-fix-case", "n_clicks"),
        Input("btn-fix-dups", "n_clicks"),
        Input("btn-fix-sort", "n_clicks"),
        Input("btn-fix-all", "n_clicks"),
        State("store-config", "data"),
        prevent_initial_call=True,
    )
    def on_fix(n_case, n_dups, n_sort, n_all, cfg):
        if not cfg:
            return no_update, no_update, no_update, "No config loaded."

        action = callback_context.triggered[0]["prop_id"].split(".")[0]
        tmp = cfg

        if action in ("btn-fix-case", "btn-fix-dups", "btn-fix-all"):
            tmp, _ = normalize_case_and_dups(tmp)
        if action in ("btn-fix-sort", "btn-fix-all"):
            tmp, _ = sort_lists(tmp)

        stl_rows = config_to_table(tmp)
        analysis = {
            "sorting": check_alphabetization(tmp),
            "case_dups": check_case_and_duplicates(tmp),
        }
        return (
            stl_rows,
            tmp,
            analysis,
            f"Applied: {action.replace('btn-', '').replace('-', ' ')}",
        )

    @app.callback(
        Output("store-config", "data", allow_duplicate=True),
        Output("store-analysis", "data", allow_duplicate=True),
        Output("status", "children", allow_duplicate=True),
        Input("btn-apply-edits", "n_clicks"),
        State("tbl-stl", "data"),
        prevent_initial_call=True,
    )
    def on_apply_edits(_n, stl_rows):
        tmp = table_to_config(stl_rows)
        analysis = {
            "sorting": check_alphabetization(tmp),
            "case_dups": check_case_and_duplicates(tmp),
        }
        return tmp, analysis, "Applied table edits to working config (not yet saved)."

    @app.callback(
        Output("status", "children", allow_duplicate=True),
        Input("btn-save", "n_clicks"),
        State("store-config", "data"),
        State("chk-backup", "value"),
        prevent_initial_call=True,
    )
    def on_save(_n, cfg, backup_flags):
        if not cfg:
            return "Nothing to save."
        if "backup" in (backup_flags or []):
            if CONFIG_JSON.exists():
                bkp = backup_file(CONFIG_JSON)
                write_json(cfg, CONFIG_JSON)
                return (
                    f"Backup saved: {bkp.name}\nUpdated: config/gmail_config-final.json"
                )
            else:
                write_json(cfg, CONFIG_JSON)
                return "Updated: config/gmail_config-final.json"
        else:
            write_json(cfg, CONFIG_JSON)
            return "Updated: config/gmail_config-final.json (no backup)"

    @app.callback(
        Output("tbl-stl", "data", allow_duplicate=True),
        Input("btn-add-stl-row", "n_clicks"),
        State("tbl-stl", "data"),
        prevent_initial_call=True,
    )
    def add_stl_row(_n, rows):
        rows = rows or []
        rows.append(
            {
                "label": "",
                "group_index": None,
                "email": "",
                "read_status": False,
                "delete_after_days": None,
            }
        )
        return rows

    @app.callback(
        Output("tbl-stl", "hidden_columns", allow_duplicate=True),
        Output("btn-toggle-advanced", "children"),
        Output("advanced-controls", "style"),
        Input("btn-toggle-advanced", "n_clicks"),
        State("tbl-stl", "hidden_columns"),
        prevent_initial_call=True,
    )
    def toggle_advanced_mode(_n, hidden):
        hidden = hidden or []
        if "group_index" in hidden:
            new_hidden = [c for c in hidden if c != "group_index"]
            return (
                new_hidden,
                "Hide Advanced Mode",
                {"display": "flex", "gap": "8px", "marginTop": "8px"},
            )
        new_hidden = hidden + ["group_index"]
        return new_hidden, "Show Advanced Mode", {"display": "none"}

    @app.callback(
        Output("tbl-stl", "data", allow_duplicate=True),
        Output("status", "children", allow_duplicate=True),
        Input("btn-merge-groups", "n_clicks"),
        Input("btn-split-groups", "n_clicks"),
        State("tbl-stl", "data"),
        State("tbl-stl", "selected_rows"),
        prevent_initial_call=True,
    )
    def on_group_actions(n_merge, n_split, rows, selected):
        if not rows or not selected:
            return no_update, "Select one or more rows first."
        action = callback_context.triggered[0]["prop_id"].split(".")[0]
        rows_str = ", ".join(str(i + 1) for i in selected)
        if action == "btn-merge-groups":
            return merge_selected(rows, selected), f"Merged rows {rows_str}"
        return split_selected(rows, selected), f"Split rows {rows_str}"

    @app.callback(
        Output("stl-selection", "children"),
        Input("tbl-stl", "selected_rows"),
    )
    def on_selection_change(selected):
        if not selected:
            return "No rows selected."
        rows = ", ".join(str(i + 1) for i in selected)
        return f"Selected rows: {rows}"

    @app.callback(
        Output("tbl-stl", "data", allow_duplicate=True),
        Output("store-config", "data", allow_duplicate=True),
        Output("store-analysis", "data", allow_duplicate=True),
        Output("status", "children", allow_duplicate=True),
        Input("btn-refresh-reports", "n_clicks"),
        prevent_initial_call=True,
    )
    def on_refresh(_n):
        try:
            cfg = load_config()
        except FileNotFoundError:
            return (
                no_update,
                no_update,
                no_update,
                "Missing config/gmail_config-final.json",
            )
        stl_rows = config_to_table(cfg)
        analysis = {
            "sorting": check_alphabetization(cfg),
            "case_dups": check_case_and_duplicates(cfg),
        }
        try:
            from .reports import write_ECAQ_report, write_diff_json

            write_ECAQ_report()
            write_diff_json()
        except Exception:
            pass
        return (
            stl_rows,
            cfg,
            analysis,
            "Reports refreshed.",
        )

    @app.callback(
        Output("metrics", "children"),
        Output("issues-block", "children"),
        Output("projected-changes", "children"),
        Input("store-analysis", "data"),
        State("store-config", "data"),
    )
    def render_analysis(analysis, cfg):
        if not analysis:
            return "", "", ""

        sorting = analysis["sorting"]
        cd = analysis["case_dups"]

        def ul(items):
            from dash import html

            return (
                html.Ul([html.Li(x) for x in items])
                if items
                else html.Ul([html.Li("None")])
            )

        sort_list = ul([i["location"] for i in sorting])
        case_list = ul([i["location"] for i in cd["case_issues"]])

        dup_blocks = []
        for i in cd["duplicate_issues"]:
            dup_count = i["original_count"] - i["unique_count"]
            lines = [html.Div(f"{i['location']} ({dup_count} duplicates)")]
            lines.extend([html.Div(f"• {d}") for d in i["duplicates"]])
            dup_blocks.append(html.Div(lines, style={"marginLeft": "12px"}))
        dup_div = html.Div(dup_blocks) if dup_blocks else html.Div("None")
        # Rebuild duplicates block using proper lists (replace placeholder bell char)
        if cd.get("duplicate_issues"):
            fixed_blocks = []
            for i in cd["duplicate_issues"]:
                dup_count = i["original_count"] - i["unique_count"]
                items = [html.Li(d) for d in i["duplicates"]]
                fixed_blocks.append(
                    html.Div(
                        [
                            html.Div(f"{i['location']} ({dup_count} duplicates)"),
                            html.Ul(items) if items else html.Ul([html.Li("None")]),
                        ],
                        style={"marginLeft": "12px"},
                    )
                )
            dup_div = html.Div(fixed_blocks)

        issues = html.Div(
            [
                html.H4("Lists not alphabetized"),
                sort_list,
                html.H4("Case inconsistencies"),
                case_list,
                html.H4("Duplicate issues"),
                dup_div,
            ]
        )

        metrics = html.Div(
            [
                html.Div(f"Lists not alphabetized: {len(sorting)}"),
                html.Div(f"Case issues: {len(cd['case_issues'])}"),
                html.Div(f"Duplicate sets: {len(cd['duplicate_issues'])}"),
            ]
        )

        proj_cfg, changes = normalize_case_and_dups(cfg)
        proj_cfg, sort_changes = sort_lists(proj_cfg)
        changes.extend(sort_changes)
        proj_list = ul(changes)
        projected = html.Div([html.H4("Projected Changes After Fix All"), proj_list])
        return metrics, issues, projected

    @app.callback(
        Output("diff-summary", "children"),
        Output("tbl-diff", "data"),
        Output("store-diff", "data"),
        Output("diff-projected", "children"),
        Output("status", "children", allow_duplicate=True),
        Input("store-config", "data"),
        prevent_initial_call="initial_duplicate",
    )
    def on_diff(cfg):
        from dash import html

        if not cfg:
            return "", [], None, "", "No config loaded."
        if not LABELS_JSON.exists():
            return "", [], None, "", "Missing config/gmail_labels_data.json"
        labels = read_json(LABELS_JSON)
        diff = compute_label_differences(cfg, labels)
        summary = diff["comparison_summary"]
        rows = []
        for label, info in diff["missing_emails_by_label"].items():
            missing_items = "".join(
                f"<li>{email}</li>" for email in info["missing_emails"]
            )
            missing_html = (
                "<details><summary>"
                f"{info['missing_emails_count']} missing emails"
                "</summary>"
                f"<ul>{missing_items}</ul></details>"
            )
            rows.append(
                {
                    "label": label,
                    "exists_in_target": info["label_exists_in_target"],
                    "total_in_source": info["total_emails_in_source"],
                    "missing_count": info["missing_emails_count"],
                    "missing_emails": missing_html,
                    "actions": "Import missing",
                }
            )

        proj_cfg, changes = normalize_case_and_dups(cfg)
        proj_cfg, sort_changes = sort_lists(proj_cfg)
        changes.extend(sort_changes)
        proj_diff = compute_label_differences(proj_cfg, labels)
        proj_div = html.Div(
            [
                html.H4("Projected Changes After Fix All"),
                html.Ul([html.Li(c) for c in changes] or [html.Li("None")]),
                html.Div(
                    "Total missing emails after fixes: "
                    f"{proj_diff['comparison_summary']['total_missing_emails']}"
                ),
            ]
        )

        return (
            html.Div(
                [
                    html.Div(f"Source labels: {summary['total_labels_in_source']}"),
                    html.Div(f"Target labels: {summary['total_labels_in_target']}"),
                    html.Div(
                        f"Total missing emails: {summary['total_missing_emails']}"
                    ),
                ]
            ),
            rows,
            diff,
            proj_div,
            "Differences computed.",
        )

    @app.callback(
        Output("tbl-stl", "data", allow_duplicate=True),
        Output("store-config", "data", allow_duplicate=True),
        Output("store-analysis", "data", allow_duplicate=True),
        Output("tbl-diff", "active_cell"),
        Output("status", "children", allow_duplicate=True),
        Input("tbl-diff", "active_cell"),
        State("tbl-diff", "data"),
        State("store-config", "data"),
        State("store-diff", "data"),
        prevent_initial_call=True,
    )
    def on_import_missing(active_cell, rows, cfg, diff):
        if not cfg or not diff or not active_cell:
            return no_update, no_update, no_update, no_update, no_update
        if active_cell.get("column_id") != "actions":
            return no_update, no_update, no_update, no_update, no_update

        label = rows[active_cell["row"]]["label"]
        info = (diff.get("missing_emails_by_label") or {}).get(label, {})
        emails = info.get("missing_emails") or []
        if not emails:
            return no_update, no_update, no_update, None, "No missing emails found."

        labels_data = read_json(LABELS_JSON)
        updated, added = import_missing_emails(cfg, labels_data, label, emails)

        if not added:
            return (
                no_update,
                cfg,
                no_update,
                None,
                f"No new emails imported for {label}.",
            )

        stl_rows = config_to_table(updated)
        analysis = {
            "sorting": check_alphabetization(updated),
            "case_dups": check_case_and_duplicates(updated),
        }
        msg = f"Imported {len(added)} emails into {label}."
        return stl_rows, updated, analysis, None, msg

    @app.callback(
        Output("status", "children", allow_duplicate=True),
        Input("btn-export-report", "n_clicks"),
        State("store-config", "data"),
        prevent_initial_call=True,
    )
    def on_export_report(_n, cfg):
        if not cfg:
            return "No config loaded."
        from .reports import generate_report_text

        text = generate_report_text(cfg)
        from .constants import REPORT_TXT

        REPORT_TXT.parent.mkdir(parents=True, exist_ok=True)
        REPORT_TXT.write_text(text, encoding="utf-8")
        return "Report exported: config/ECAQ_Report.txt"

    @app.callback(
        Output("status", "children", allow_duplicate=True),
        Input("btn-export-diff", "n_clicks"),
        State("store-diff", "data"),
        prevent_initial_call=True,
    )
    def on_export_diff(_n, diff):
        if not diff:
            return "No differences computed."
        from .constants import DIFF_JSON
        from .utils_io import write_json

        write_json(diff, DIFF_JSON)
        return "Differences JSON exported: config/email_differences_by_label.json"

    @app.callback(
        Output("ddl-log-files", "options"),
        Input("btn-load-logs", "n_clicks"),
        prevent_initial_call=True,
    )
    def on_load_logs(_n):
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        files = sorted(
            LOGS_DIR.glob("*.log"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:5]
        return [{"label": f.name, "value": f.name} for f in files]

    @app.callback(
        Output("ddl-log-runs", "options"),
        Output("ddl-log-runs", "value"),
        Output("store-log-runs", "data"),
        Output("log-content", "children", allow_duplicate=True),
        Input("btn-view-log", "n_clicks"),
        State("ddl-log-files", "value"),
        prevent_initial_call=True,
    )
    def on_view_log(_n, filename):
        if not filename:
            return [], None, {}, "No log file selected."
        path = LOGS_DIR / filename
        if not path.exists():
            return [], None, {}, f"Log file not found: {filename}"
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:  # pragma: no cover - rare file errors
            return [], None, {}, f"Error reading log: {exc}"

        runs: List[str] = []
        current: List[str] = []
        for line in text.splitlines():
            msg = line.split(" - ", 2)[-1]
            if re.fullmatch(r"-{10,}", msg.strip()):
                if current:
                    runs.append("\n".join(current))
                    current = []
                current.append(line)
            else:
                current.append(line)
        if current:
            runs.append("\n".join(current))

        options = []
        data: Dict[str, str] = {}
        for idx, segment in enumerate(runs):
            first_line = segment.splitlines()[0]
            ts = first_line.split(" - ", 1)[0]
            options.append({"label": f"Run {idx + 1} ({ts})", "value": str(idx)})
            data[str(idx)] = segment

        if not options:
            return [], None, {}, "No runs found in log."

        first_id = options[0]["value"]
        return options, first_id, data, data[first_id]

    @app.callback(
        Output("log-content", "children", allow_duplicate=True),
        Input("ddl-log-runs", "value"),
        State("store-log-runs", "data"),
        prevent_initial_call=True,
    )
    def on_select_run(run_id, runs):
        if not run_id or not runs:
            return "No run selected."
        return runs.get(run_id, "Run not found.")

    # Recompute and store pending senders whenever config changes
    @app.callback(
        Output("store-pending", "data"),
        Input("store-config", "data"),
        prevent_initial_call="initial_duplicate",
    )
    def on_config_change_pending(cfg):
        if not cfg:
            return []
        try:
            return find_unprocessed_senders(cfg)
        except Exception:
            return []

    # Populate dropdown options and filter the pending table by selected labels
    @app.callback(
        Output("ddl-pending-labels", "options"),
        Output("tbl-new-senders", "data"),
        Input("store-pending", "data"),
        Input("ddl-pending-labels", "value"),
    )
    def on_filter_pending(pending, selected_labels):
        pending = pending or []
        # Build label options from current pending dataset
        labels_set = set()
        for row in pending:
            lbls = (row.get("labels") or "").split(",")
            for lbl in lbls:
                clean = lbl.strip()
                if clean:
                    labels_set.add(clean)
        options = [
            {"label": label_value, "value": label_value}
            for label_value in sorted(labels_set, key=str.casefold)
        ]

        # Apply filter if any labels are selected
        if selected_labels:
            selected = set(
                selected_labels
                if isinstance(selected_labels, list)
                else [selected_labels]
            )
            filtered = []
            for row in pending:
                row_labels = set(
                    s.strip() for s in (row.get("labels") or "").split(",") if s.strip()
                )
                if row_labels & selected:
                    filtered.append(row)
            return options, filtered
        return options, pending
