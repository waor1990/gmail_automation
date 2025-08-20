from dash import html, no_update, callback_context
from dash import Input, Output, State
from .analysis import (
    analyze_email_consistency, check_alphabetization, check_case_and_duplicates,
    normalize_case_and_dups, sort_lists
)
from .transforms import config_to_tables, tables_to_config
from .utils_io import write_json, backup_file, read_json
from .constants import CONFIG_JSON, LABELS_JSON
from .analysis import compute_label_differences

def register_callbacks(app):

    @app.callback(
        Output("store-config", "data"),
        Output("tbl-email-list", "data"),
        Output("tbl-stl", "data"),
        Output("store-analysis", "data"),
        Output("status", "children"),
        Input("btn-load", "n_clicks"),
        prevent_initial_call=True,
    )
    def on_load(_):
        from .analysis import load_config
        cfg = load_config()
        el_rows, stl_rows = config_to_tables(cfg)
        analysis = {
            "consistency": analyze_email_consistency(cfg),
            "sorting": check_alphabetization(cfg),
            "case_dups": check_case_and_duplicates(cfg),
        }
        return cfg, el_rows, stl_rows, analysis, "Loaded config."

    @app.callback(
        Output("tbl-email-list", "data", allow_duplicate=True),
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
            return no_update, no_update, no_update, no_update, "No config loaded."

        action = callback_context.triggered[0]["prop_id"].split(".")[0]
        tmp = cfg

        if action in ("btn-fix-case", "btn-fix-dups", "btn-fix-all"):
            tmp, _ = normalize_case_and_dups(tmp)
        if action in ("btn-fix-sort", "btn-fix-all"):
            tmp, _ = sort_lists(tmp)

        el_rows, stl_rows = config_to_tables(tmp)
        analysis = {
            "consistency": analyze_email_consistency(tmp),
            "sorting": check_alphabetization(tmp),
            "case_dups": check_case_and_duplicates(tmp),
        }
        return el_rows, stl_rows, tmp, analysis, f"Applied: {action.replace('btn-','').replace('-',' ')}"

    @app.callback(
        Output("store-config", "data", allow_duplicate=True),
        Output("store-analysis", "data", allow_duplicate=True),
        Output("status", "children", allow_duplicate=True),
        Input("btn-apply-edits", "n_clicks"),
        State("tbl-email-list", "data"),
        State("tbl-stl", "data"),
        prevent_initial_call=True,
    )
    def on_apply_edits(_n, el_rows, stl_rows):
        tmp = tables_to_config(el_rows, stl_rows)
        analysis = {
            "consistency": analyze_email_consistency(tmp),
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
                return f"Backup saved: {bkp.name}\nUpdated: config/gmail_config-final.json"
            else:
                write_json(cfg, CONFIG_JSON)
                return "Updated: config/gmail_config-final.json"
        else:
            write_json(cfg, CONFIG_JSON)
            return "Updated: config/gmail_config-final.json (no backup)"

    @app.callback(
        Output("metrics", "children"),
        Output("issues-block", "children"),
        Input("store-analysis", "data"),
    )
    def render_analysis(analysis):
        if not analysis:
            return "", ""

        cons = analysis["consistency"]
        sorting = analysis["sorting"]
        cd = analysis["case_dups"]

        def ul(items):
            from dash import html
            return html.Ul([html.Li(x) for x in items]) if items else html.Ul([html.Li("None")])

        metrics = html.Div([
            html.Div(f"EMAIL_LIST count: {cons['email_list_count']}"),
            html.Div(f"SENDER_TO_LABELS email set: {cons['sender_labels_count']}"),
            html.Div(f"Sets identical: {cons['are_identical']}"),
        ])

        missing_sender = ul(cons["missing_in_sender"])
        missing_list = ul([f"{e} (labels: {', '.join(cons['email_to_labels'].get(e, ['Unknown']))})"
                           for e in cons["missing_in_list"]])
        sort_list = ul([i["location"] for i in sorting])
        case_list = ul([i["location"] for i in cd["case_issues"]])

        dup_blocks = []
        for i in cd["duplicate_issues"]:
            dup_count = i["original_count"] - i["unique_count"]
            lines = [html.Div(f"{i['location']} ({dup_count} duplicates)")]
            lines.extend([html.Div(f"• {d}") for d in i["duplicates"]])
            dup_blocks.append(html.Div(lines, style={"marginLeft": "12px"}))
        dup_div = html.Div(dup_blocks) if dup_blocks else html.Div("None")

        issues = html.Div([
            html.H4("Emails in EMAIL_LIST but not in SENDER_TO_LABELS"),
            missing_sender,
            html.H4("Emails in SENDER_TO_LABELS but not in EMAIL_LIST"),
            missing_list,
            html.H4("Lists not alphabetized"),
            sort_list,
            html.H4("Case inconsistencies"),
            case_list,
            html.H4("Duplicate issues"),
            dup_div,
        ])
        return metrics, issues

    @app.callback(
        Output("diff-summary", "children"),
        Output("tbl-diff", "data"),
        Output("store-diff", "data"),
        Output("status", "children", allow_duplicate=True),
        Input("btn-diff", "n_clicks"),
        State("store-config", "data"),
        prevent_initial_call=True,
    )
    def on_diff(_n, cfg):
        from dash import html
        if not cfg:
            return "", [], None, "No config loaded."
        if not LABELS_JSON.exists():
            return "", [], None, "Missing config/gmail_labels_data.json"
        labels = read_json(LABELS_JSON)
        diff = compute_label_differences(cfg, labels)
        summary = diff["comparison_summary"]
        rows = []
        for label, info in diff["missing_emails_by_label"].items():
            rows.append({
                "label": label,
                "exists_in_target": info["label_exists_in_target"],
                "total_in_source": info["total_emails_in_source"],
                "missing_count": info["missing_emails_count"],
                "missing_emails": ", ".join(info["missing_emails"]),
            })
        return (
            html.Div([
                html.Div(f"Source labels: {summary['total_labels_in_source']}"),
                html.Div(f"Target labels: {summary['total_labels_in_target']}"),
                html.Div(f"Total missing emails: {summary['total_missing_emails']}"),
            ]),
            rows,
            diff,
            "Differences computed."
        )

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
        return "Report exported: config/ESAQ_Report.txt"

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