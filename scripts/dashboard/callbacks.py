from dash import html, dcc, no_update, callback_context, ctx
from dash import Input, Output, State
import re
from typing import Dict, List
from .collisions import resolve_collisions
from .analysis import (
    load_config,
    normalize_case_and_dups,
    sort_lists,
    find_unprocessed_senders,
    import_missing_emails,
)
from .analysis_helpers import run_full_analysis
from .transforms import config_to_table, table_to_config, rows_to_grouped
from .utils_io import write_json, backup_file, read_json
from .constants import CONFIG_JSON, LABELS_JSON, LOGS_DIR
from .group_ops import merge_selected, split_selected


def _render_coverage(total: int, missing: int) -> str:
    """Return a small HTML progress bar for coverage."""
    pct = 100 if total == 0 else int(round((total - missing) / total * 100))
    if pct == 100:
        color = "#2e7d32"  # green
    elif pct >= 50:
        color = "#ed6c02"  # orange
    else:
        color = "#c62828"  # red
    bar = (
        "<div style='display:flex;align-items:center'>"
        "<div style='background:#eee;width:60px;height:8px'>"
        "<div style='background:{color};width:{pct}%;height:8px'></div>"
        "</div>"
        "<span style='margin-left:4px;font-size:10px'>{pct}%</span>"
        "</div>"
    ).format(color=color, pct=pct)
    return bar


def _group_changes_by_label(changes: List[str]) -> Dict[str, List[str]]:
    """Group projected change strings by label name.

    Args:
        changes: List of change descriptions from analysis.

    Returns:
        Mapping of label -> list of change strings.
    """

    groups: Dict[str, List[str]] = {}
    for c in changes:
        m = re.search(r"SENDER_TO_LABELS\.([^\.\[]+)", c)
        label = m.group(1) if m else "Unknown"
        groups.setdefault(label, []).append(c)
    return groups


def register_callbacks(app):
    def _render_grouped_tree(rows: List[Dict[str, str]]):
        grouped = rows_to_grouped(rows)
        items = []
        for label in sorted(grouped):
            group_items = []
            for gi in sorted(grouped[label]):
                emails = grouped[label][gi]
                email_items = [
                    html.Li(
                        [
                            html.Span(email),
                            # Hidden span to satisfy pattern-matching Output for remove
                            html.Span(
                                "",
                                id={
                                    "type": "grp-dummy",
                                    "label": label,
                                    "group": gi,
                                    "email": email,
                                },
                                style={"display": "none"},
                            ),
                            html.Button(
                                "Remove",
                                id={
                                    "type": "grp-remove",
                                    "label": label,
                                    "group": gi,
                                    "email": email,
                                },
                                n_clicks=0,
                                style={"marginLeft": "4px"},
                            ),
                        ]
                    )
                    for email in emails
                ]
                group_items.append(
                    html.Li(
                        [
                            html.Span(f"Group {gi}"),
                            html.Ul(email_items),
                            # Hidden span to satisfy pattern-matching Output for add
                            html.Span(
                                "",
                                id={"type": "grp-dummy", "label": label, "group": gi},
                                style={"display": "none"},
                            ),
                            dcc.Input(
                                id={"type": "grp-input", "label": label, "group": gi},
                                placeholder="new email",
                                style={"marginRight": "4px", "fontSize": "12px"},
                            ),
                            html.Button(
                                "Add",
                                id={"type": "grp-add", "label": label, "group": gi},
                                n_clicks=0,
                                style={"fontSize": "12px"},
                            ),
                        ]
                    )
                )
            items.append(html.Li([html.Strong(label), html.Ul(group_items)]))
        return html.Ul(items)

    def _recompute(rows):
        cfg = table_to_config(rows)
        analysis = run_full_analysis(cfg)
        return cfg, analysis

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

        # Determine which button fired
        action = ctx.triggered_id if ctx.triggered_id is not None else ""
        tmp = cfg

        if action in ("btn-fix-case", "btn-fix-dups", "btn-fix-all"):
            tmp, _ = normalize_case_and_dups(tmp)
        if action in ("btn-fix-sort", "btn-fix-all"):
            tmp, _ = sort_lists(tmp)

        stl_rows = config_to_table(tmp)
        analysis = run_full_analysis(tmp)
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
        analysis = run_full_analysis(tmp)
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
        action = ctx.triggered_id if ctx.triggered_id is not None else ""
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
        Output("stl-grouped", "children"),
        Input("tbl-stl", "data"),
    )
    def render_grouped(rows):
        return _render_grouped_tree(rows or [])

    @app.callback(
        Output("flat-view", "style"),
        Output("grouped-view", "style"),
        Input("stl-view-toggle", "value"),
    )
    def toggle_view(mode):
        if mode == "grouped":
            return {"display": "none"}, {"display": "block"}
        return {"display": "block"}, {"display": "none"}

    # Grouped-tree Add callback temporarily disabled due to Dash wildcard
    # constraints across multi-output callbacks. Controls are no-ops for now.

    # Grouped-tree Remove callback temporarily disabled due to Dash wildcard
    # constraints across multi-output callbacks. Controls are no-ops for now.

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
        analysis = run_full_analysis(cfg)
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
        Output("status", "children", allow_duplicate=True),
        Input("btn-export-pending", "n_clicks"),
        State("store-pending", "data"),
        prevent_initial_call=True,
    )
    def on_export_pending(_n, pending):
        if not pending:
            return "No pending senders to export."
        try:
            import csv
            from .constants import NEW_SENDERS_CSV

            NEW_SENDERS_CSV.parent.mkdir(parents=True, exist_ok=True)
            with NEW_SENDERS_CSV.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["status", "email", "labels"])
                writer.writeheader()
                for row in pending:
                    writer.writerow(
                        {
                            "status": row.get("status", ""),
                            "email": row.get("email", ""),
                            "labels": row.get("labels", ""),
                        }
                    )
            return "New Senders CSV exported: config/new_senders.csv"
        except Exception as exc:  # pragma: no cover - unexpected I/O errors
            return f"Failed to export New Senders CSV: {exc}"

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
        for i in cd.get("duplicate_issues", []):
            dup_count = i["original_count"] - i["unique_count"]
            items = [html.Li(d) for d in i["duplicates"]]
            dup_blocks.append(
                html.Div(
                    [
                        html.Div(f"{i['location']} ({dup_count} duplicates)"),
                        html.Ul(items) if items else html.Ul([html.Li("None")]),
                    ],
                    style={"marginLeft": "12px"},
                )
            )
        dup_div = html.Div(dup_blocks) if dup_blocks else html.Div("None")

        cross_blocks = []
        for item in cd.get("cross_label_duplicates", []):
            labels = [
                loc.split(".")[1].split("[")[0] for loc in item.get("locations", [])
            ]
            cross_blocks.append(
                html.Div(f"{item['email']}: {', '.join(sorted(set(labels)))}")
            )
        cross_div = html.Div(cross_blocks) if cross_blocks else html.Div("None")

        issues = html.Div(
            [
                html.H4("Lists not alphabetized"),
                sort_list,
                html.H4("Case inconsistencies"),
                case_list,
                html.H4("Duplicate issues"),
                dup_div,
                html.H4("Cross-label duplicates"),
                cross_div,
            ]
        )

        metrics = html.Div(
            [
                html.Div(f"Lists not alphabetized: {len(sorting)}"),
                html.Div(f"Case issues: {len(cd['case_issues'])}"),
                html.Div(f"Duplicate sets: {len(cd['duplicate_issues'])}"),
                html.Div(
                    f"Cross-label duplicates: {len(cd['cross_label_duplicates'])}"
                ),
            ]
        )

        changes = analysis.get("projected_changes") or []
        grouped = _group_changes_by_label(changes)
        proj_items = [
            html.Details(
                [
                    html.Summary(lbl, title="\n".join(items)),
                    html.Ul([html.Li(x) for x in items]),
                ],
                style={"marginBottom": "4px"},
            )
            for lbl, items in sorted(grouped.items())
        ]
        projected = html.Div(
            [
                html.H4("Projected Changes After Fix All"),
                html.Div(proj_items),
            ]
        )
        return metrics, issues, projected

    @app.callback(
        Output("tbl-collisions", "data"),
        Output("tbl-collisions", "dropdown_conditional"),
        Input("store-analysis", "data"),
    )
    def on_collisions(analysis):
        if not analysis:
            return [], []
        cd = analysis.get("case_dups", {})
        collisions = []
        dropdowns = []
        for i, item in enumerate(cd.get("cross_label_duplicates", [])):
            labels = sorted(
                {loc.split(".")[1].split("[")[0] for loc in item.get("locations", [])}
            )
            collisions.append(
                {
                    "email": item["email"],
                    "labels": ", ".join(labels),
                    "action": "",
                    "to_label": "",
                }
            )
            dropdowns.append(
                {
                    "if": {"row_index": i, "column_id": "to_label"},
                    "options": [{"label": lbl, "value": lbl} for lbl in labels],
                }
            )
        return collisions, dropdowns

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
        analysis = run_full_analysis(cfg)
        diff = analysis["diff"]
        assert diff is not None
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
            # Render a real button inside the cell
            # DataTable will still report clicks via active_cell
            action_btn = (
                '<button title="Import all missing emails for this label" '
                'style="padding:2px 6px; font-size:12px;">'
                "Import missing"
                "</button>"
            )
            total = info["total_emails_in_source"]
            missing = info["missing_emails_count"]
            coverage_html = _render_coverage(total, missing)
            exists_icon = "✅" if info["label_exists_in_target"] else "❌"

            rows.append(
                {
                    "label": label,
                    "exists_in_target": exists_icon,
                    "total_in_source": total,
                    "missing_count": missing,
                    "coverage": coverage_html,
                    "missing_emails": missing_html,
                    "actions": action_btn,
                }
            )

        changes = analysis.get("projected_changes") or []
        grouped = _group_changes_by_label(changes)
        proj_diff = analysis.get("projected_diff")
        assert proj_diff is not None

        # Build a richer projection summary
        import re

        case_fixes = sum(1 for c in changes if "(fixed case)" in c)
        removed_dup_counts = [
            int(m.group(1))
            for c in changes
            for m in [re.search(r"removed (\\d+) duplicates", c)]
            if m
        ]
        removed_dups_total = sum(removed_dup_counts)
        sorted_lists_count = sum(
            1 for c in changes if "(fixed case)" not in c and "duplicates" not in c
        )

        def extract_label(c: str) -> str | None:
            m = re.search(r"SENDER_TO_LABELS\\.([^\\[]+)\\[", c)
            return m.group(1) if m else None

        labels_affected = sorted({lbl for c in changes if (lbl := extract_label(c))})

        before_missing = summary["total_missing_emails"]
        after_missing = proj_diff["comparison_summary"]["total_missing_emails"]
        delta_missing = after_missing - before_missing

        # Top labels by remaining missing emails (limit to 10 for readability)
        items = list((proj_diff.get("missing_emails_by_label") or {}).items())
        items.sort(key=lambda kv: kv[1].get("missing_emails_count", 0), reverse=True)
        top_labels = [
            html.Li(
                f"{lbl}: {info['missing_emails_count']} remaining"
                + (" (new label)" if not info.get("label_exists_in_target") else "")
            )
            for lbl, info in items
            if info.get("missing_emails_count", 0) > 0
        ][:10]

        change_details = [
            html.Details(
                [
                    html.Summary(lbl, title="\n".join(items)),
                    html.Ul([html.Li(x) for x in items]),
                ],
                style={"marginBottom": "4px"},
            )
            for lbl, items in sorted(grouped.items())
        ]

        proj_div = html.Div(
            [
                html.H4("Projected Changes After Fix All"),
                html.Div(
                    [
                        html.Div(f"Before (missing emails): {before_missing}"),
                        html.Div(f"After (missing emails): {after_missing}"),
                        html.Div(f"Delta: {delta_missing:+d}"),  # noqa: E231
                    ],
                    style={"marginBottom": "6px"},
                ),
                html.Div(
                    [
                        html.Div(f"Case fixes: {case_fixes}"),
                        html.Div(f"Duplicates removed: {removed_dups_total}"),
                        html.Div(f"Sorted lists: {sorted_lists_count}"),
                        html.Div(f"Labels affected: {len(labels_affected)}"),
                    ],
                    style={"marginBottom": "6px"},
                ),
                html.Div(change_details),
                html.Details(
                    [
                        html.Summary("Top labels by remaining missing emails"),
                        html.Ul(top_labels or [html.Li("None")]),
                    ]
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
        analysis = run_full_analysis(updated)
        msg = f"Imported {len(added)} emails into {label}."
        return stl_rows, updated, analysis, None, msg

    @app.callback(
        Output("tbl-stl", "data", allow_duplicate=True),
        Output("store-config", "data", allow_duplicate=True),
        Output("store-analysis", "data", allow_duplicate=True),
        Output("status", "children", allow_duplicate=True),
        Input("btn-apply-collisions", "n_clicks"),
        State("tbl-collisions", "data"),
        State("store-config", "data"),
        prevent_initial_call=True,
    )
    def on_apply_collisions(_n, rows, cfg):
        if not cfg or not rows:
            return no_update, no_update, no_update, "No config loaded."
        resolutions = []
        for r in rows:
            act = r.get("action")
            if not act:
                continue
            if act == "reassign":
                target = r.get("to_label")
                if not target:
                    continue
                act = "reassign:" + target
            resolutions.append(
                {
                    "email": r["email"],
                    "labels": r["labels"].split(", "),
                    "action": act,
                }
            )
        if not resolutions:
            return (
                no_update,
                no_update,
                no_update,
                "No collision actions selected.",
            )
        updated, changes = resolve_collisions(cfg, resolutions)
        stl_rows = config_to_table(updated)
        analysis = run_full_analysis(updated)
        msg = "; ".join(changes) if changes else "No changes made."
        return stl_rows, updated, analysis, msg

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
        Output("ddl-log-files", "value"),
        Input("btn-load-logs", "n_clicks"),
        Input("store-log-selection", "data"),
    )
    def on_load_logs(_n, selection):
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        files = sorted(
            LOGS_DIR.glob("*.log"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:5]
        options = [{"label": f.name, "value": f.name} for f in files]
        value = None
        if selection:
            stored = selection.get("filename")
            if stored in {opt["value"] for opt in options}:
                value = stored
        return options, value

    @app.callback(
        Output("ddl-log-runs", "options"),
        Output("ddl-log-runs", "value"),
        Output("store-log-runs", "data"),
        Output("log-content", "children", allow_duplicate=True),
        Output("store-log-selection", "data", allow_duplicate=True),
        Input("btn-view-log", "n_clicks"),
        Input("store-log-selection", "data"),
        State("ddl-log-files", "value"),
        prevent_initial_call="initial_duplicate",
    )
    def on_view_log(_n, selection, filename):
        ctx = callback_context
        trigger = getattr(ctx, "triggered_id", None)
        if trigger == "store-log-selection" and selection:
            filename = selection.get("filename")
        if not filename:
            return [], None, {}, "No log file selected.", no_update
        path = LOGS_DIR / filename
        if not path.exists():
            return [], None, {}, f"Log file not found: {filename}", no_update
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:  # pragma: no cover - rare file errors
            return [], None, {}, f"Error reading log: {exc}", no_update

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
            return [], None, {}, "No runs found in log.", no_update

        first_id = options[0]["value"]
        run_id = first_id
        if selection and selection.get("run_id") in data:
            run_id = selection["run_id"]
        store_data = {"filename": filename, "run_id": run_id}
        return options, run_id, data, data[run_id], store_data

    @app.callback(
        Output("log-content", "children", allow_duplicate=True),
        Output("store-log-selection", "data", allow_duplicate=True),
        Input("ddl-log-runs", "value"),
        Input("store-log-selection", "data"),
        State("store-log-runs", "data"),
        State("ddl-log-files", "value"),
        prevent_initial_call="initial_duplicate",
    )
    def on_select_run(run_id, selection, runs, filename):
        ctx = callback_context
        trigger = getattr(ctx, "triggered_id", None)
        if trigger == "store-log-selection" and selection:
            run_id = selection.get("run_id")
        if not run_id or not runs:
            return "No run selected.", no_update
        store_data = {"filename": filename, "run_id": run_id}
        return runs.get(run_id, "Run not found."), store_data

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
