"""Dash callback definitions for the dashboard."""

from __future__ import annotations

from collections import OrderedDict
import json
import re
from typing import Any, Dict, List, Tuple

import plotly.graph_objects as go
from dash import (
    MATCH,
    Input,
    Output,
    State,
    callback_context,
    ctx,
    dcc,
    html,
    no_update,
)
from dash.exceptions import PreventUpdate
from gmail_automation.logging_utils import get_logger
from .collisions import resolve_collisions
from .analysis import (
    load_config,
    normalize_case_and_dups,
    sort_lists,
    find_unprocessed_senders,
    import_missing_emails,
)
from .analysis_helpers import run_full_analysis
from .transforms import (
    config_to_table,
    table_to_config,
    rows_to_grouped,
    ignored_rules_to_rows,
    rows_to_ignored_rules,
)
from .utils_io import backup_file, read_json, write_json
from .constants import CONFIG_JSON, LABELS_JSON, LOGS_DIR
from .group_ops import merge_selected, split_selected
from .theme import get_theme_style


logger = get_logger(__name__)

MIN_TREEMAP_VALUE = 0.1
MAX_EMAILS_IN_TOOLTIP = 30


def make_empty_stl_row(defaults: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Return a blank SENDER_TO_LABELS row using provided defaults."""

    defaults = defaults or {}
    return {
        "label": "",
        "group_index": None,
        "email": "",
        "read_status": defaults.get("read_status", False),
        "delete_after_days": defaults.get("delete_after_days"),
    }


def make_empty_ignored_row() -> Dict[str, Any]:
    """Return a blank IGNORED_EMAILS row."""

    return {
        "name": "",
        "senders": "",
        "domains": "",
        "subject_contains": "",
        "skip_analysis": True,
        "skip_import": True,
        "mark_as_read": False,
        "apply_labels": "",
        "archive": False,
        "delete_after_days": None,
    }


def _normalize_group_index(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _add_email_to_rows(
    rows: List[Dict[str, Any]] | None,
    label: str,
    group_index: Any,
    email: str,
    defaults: Dict[str, Any] | None,
) -> List[Dict[str, Any]]:
    label = (label or "").strip()
    email = (email or "").strip()
    if not label or not email:
        raise ValueError("label and email are required")

    normalized_group = _normalize_group_index(group_index)
    current_rows = list(rows or [])

    for row in current_rows:
        if (
            row.get("label") == label
            and _normalize_group_index(row.get("group_index")) == normalized_group
            and row.get("email") == email
        ):
            raise ValueError("email already exists in this group")

    read_status = None
    delete_after_days = None
    for row in current_rows:
        if (
            row.get("label") == label
            and _normalize_group_index(row.get("group_index")) == normalized_group
        ):
            if read_status is None:
                read_status = row.get("read_status")
            if delete_after_days is None:
                delete_after_days = row.get("delete_after_days")
            if read_status is not None and delete_after_days is not None:
                break

    defaults = defaults or {}
    if read_status is None:
        read_status = defaults.get("read_status")
    if delete_after_days is None:
        delete_after_days = defaults.get("delete_after_days")

    current_rows.append(
        {
            "label": label,
            "group_index": normalized_group,
            "email": email,
            "read_status": read_status,
            "delete_after_days": delete_after_days,
        }
    )
    return current_rows


def _remove_email_from_rows(
    rows: List[Dict[str, Any]] | None,
    label: str,
    group_index: Any,
    email: str,
) -> List[Dict[str, Any]]:
    normalized_group = _normalize_group_index(group_index)
    removed = False
    remaining: List[Dict[str, Any]] = []
    for row in rows or []:
        if (
            row.get("label") == label
            and _normalize_group_index(row.get("group_index")) == normalized_group
            and row.get("email") == email
        ):
            removed = True
            continue
        remaining.append(row)
    if not removed:
        raise ValueError("email not found in group")
    return remaining


def _add_ignored_email(rows: List[Dict[str, Any]] | None) -> List[Dict[str, Any]]:
    updated = list(rows or [])
    updated.append(make_empty_ignored_row())
    return updated


def _remove_ignored_email(
    rows: List[Dict[str, Any]] | None, index: int
) -> List[Dict[str, Any]]:
    if rows is None:
        raise ValueError("no ignored-email rows to remove")
    if index < 0 or index >= len(rows):
        raise ValueError("ignored-email index out of range")
    updated = list(rows)
    updated.pop(index)
    return updated


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


def _prepare_diff_tree_nodes(diff: Dict[str, Any] | None) -> List[Dict[str, Any]]:
    """Transform diff data into nodes for the grouped tree treemap."""

    if not diff:
        return []

    missing = diff.get("missing_emails_by_label") or {}
    if not missing:
        return []

    root_label = "All Labels"
    comparison = diff.get("comparison_summary") or {}
    total_missing = comparison.get("total_missing_emails", 0)

    nodes: List[Dict[str, Any]] = [
        {
            "label": root_label,
            "parent": "",
            "value": MIN_TREEMAP_VALUE,
            "missing_count": total_missing,
            "tooltip": (
                f"<b>{root_label}</b><br>Total missing emails: {total_missing}<br>"
                "Use the grouped tree to explore gaps by label."
            ),
            "text": f"{root_label}<br>{total_missing} missing",
            "type": "root",
        }
    ]

    status_map: Dict[str, Dict[str, Any]] = OrderedDict()

    def status_key(info: Dict[str, Any]) -> str:
        return (
            "Existing Labels"
            if info.get("label_exists_in_target")
            else "Missing Labels"
        )

    for label, info in sorted(missing.items(), key=lambda kv: kv[0].casefold()):
        key = status_key(info)
        entry = status_map.setdefault(
            key,
            {"items": [], "missing_total": 0, "value_total": 0.0},
        )
        missing_emails = info.get("missing_emails") or []
        missing_count = len(missing_emails)
        node_value = float(missing_count) if missing_count else MIN_TREEMAP_VALUE
        entry["items"].append(
            {
                "label": label,
                "missing_emails": missing_emails,
                "missing_count": missing_count,
                "total_in_source": info.get("total_emails_in_source", 0),
                "exists": info.get("label_exists_in_target", False),
                "value": node_value,
            }
        )
        entry["missing_total"] += missing_count
        entry["value_total"] += node_value

    status_order = {"Existing Labels": 0, "Missing Labels": 1}
    total_value = 0.0

    for _, status, entry in sorted(
        ((status_order.get(k, 99), k, v) for k, v in status_map.items()),
        key=lambda item: (item[0], item[1]),
    ):
        status_value = entry["value_total"] or MIN_TREEMAP_VALUE
        status_missing = entry["missing_total"]
        nodes.append(
            {
                "label": status,
                "parent": root_label,
                "value": status_value,
                "missing_count": status_missing,
                "tooltip": (
                    f"<b>{status}</b><br>{len(entry['items'])} labels\n"
                    f"Missing emails: {status_missing}"
                ),
                "text": f"{status}<br>{status_missing} missing",
                "type": "status",
            }
        )
        total_value += status_value

        for item in entry["items"]:
            missing_emails = item["missing_emails"]
            missing_count = item["missing_count"]
            exists = item["exists"]
            preview = missing_emails[:MAX_EMAILS_IN_TOOLTIP]
            tooltip_lines = [
                f"<b>{item['label']}</b>",
                f"Missing emails: {missing_count}",
            ]
            if preview:
                tooltip_lines.append("Emails:")
                tooltip_lines.extend(preview)
                remaining = missing_count - len(preview)
                if remaining > 0:
                    tooltip_lines.append(f"... plus {remaining} more")
            else:
                tooltip_lines.append("No missing emails.")
            if not exists:
                tooltip_lines.append("Label missing from config.")
            tooltip = "<br>".join(tooltip_lines)
            nodes.append(
                {
                    "label": item["label"],
                    "parent": status,
                    "value": item["value"],
                    "missing_count": missing_count,
                    "tooltip": tooltip,
                    "text": (
                        f"{item['label']}<br>{missing_count} missing"
                        if missing_count
                        else f"{item['label']}<br>no missing"
                    ),
                    "type": "label",
                }
            )

    nodes[0]["value"] = total_value or MIN_TREEMAP_VALUE
    nodes[0]["text"] = (
        f"{root_label}<br>{total_missing} missing"
        if total_missing
        else f"{root_label}<br>no missing"
    )

    return nodes


def _build_diff_tree_figure(diff: Dict[str, Any] | None) -> go.Figure:
    """Construct a Plotly treemap figure for grouped diff data."""

    nodes = _prepare_diff_tree_nodes(diff)
    if not nodes:
        fig = go.Figure()
        fig.update_layout(margin=dict(t=40, l=0, r=0, b=0))
        return fig

    labels = [node["label"] for node in nodes]
    parents = [node["parent"] for node in nodes]
    values = [node["value"] for node in nodes]
    texts = [node["text"] for node in nodes]
    customdata = [[node["tooltip"]] for node in nodes]

    color_map = {
        "Existing Labels": "#1976d2",
        "Missing Labels": "#d32f2f",
    }
    colors = []
    for node in nodes:
        if node["type"] == "root":
            colors.append("#78909c")
        elif node["type"] == "status":
            colors.append(color_map.get(node["label"], "#90a4ae"))
        else:
            colors.append(color_map.get(node["parent"], "#90caf9"))

    fig = go.Figure(
        go.Treemap(
            labels=labels,
            parents=parents,
            values=values,
            text=texts,
            textinfo="text",
            customdata=customdata,
            hovertemplate="%{customdata[0]}<extra></extra>",
            branchvalues="total",
            marker=dict(colors=colors),
        )
    )
    fig.update_layout(margin=dict(t=32, l=0, r=0, b=0))
    return fig


def _label_filter_options(rows: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Build dropdown options for the SENDER_TO_LABELS label filter."""

    labels: set[str] = set()
    for row in rows or []:
        raw_label = row.get("label")
        if isinstance(raw_label, str):
            cleaned = raw_label.strip()
        elif raw_label is None:
            cleaned = ""
        else:
            cleaned = str(raw_label).strip()
        if cleaned:
            labels.add(cleaned)
    return [
        {"label": label, "value": label}
        for label in sorted(labels, key=lambda value: (value.casefold(), value))
    ]


def _sanitize_label_filter_value(
    options: List[Dict[str, str]], current_value: str | None
) -> str | None:
    """Return the current value if still valid, otherwise ``None``."""

    valid = {opt["value"] for opt in options}
    return current_value if current_value in valid else None


def _build_label_filter_query(selected_label: str | None) -> str:
    """Return a filter query string for the selected label."""

    if not selected_label:
        return ""
    serialized = json.dumps(str(selected_label))
    return f"{{label}} = {serialized}"


def _prepare_diff_outputs(
    cfg: Dict[str, Any], analysis: Dict[str, Any]
) -> Tuple[html.Div, List[Dict[str, Any]], Dict[str, Any], html.Div]:
    """Build diff table and projection displays.

    Args:
        cfg: Current configuration mapping.
        analysis: Result from :func:`run_full_analysis` for ``cfg``.

    Returns:
        Tuple containing rendered summary div, diff table rows, raw diff dict,
        and projected-change div.
    """

    diff = analysis.get("diff")
    if diff is None:
        return html.Div(), [], {}, html.Div()

    summary = diff["comparison_summary"]
    rows: List[Dict[str, Any]] = []
    for label, info in diff["missing_emails_by_label"].items():
        missing_items = "".join(f"<li>{email}</li>" for email in info["missing_emails"])
        missing_html = (
            "<details><summary>"
            f"{info['missing_emails_count']} missing emails"
            "</summary>"
            f"<ul>{missing_items}</ul></details>"
        )
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
        m = re.search(r"SENDER_TO_LABELS\\.([^\\[\]]+)\\[", c)
        return m.group(1) if m else None

    labels_affected = sorted({lbl for c in changes if (lbl := extract_label(c))})

    before_missing = summary["total_missing_emails"]
    after_missing = proj_diff["comparison_summary"]["total_missing_emails"]
    delta_missing = after_missing - before_missing

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

    summary_div = html.Div(
        [
            html.Div(f"Source labels: {summary['total_labels_in_source']}"),
            html.Div(f"Target labels: {summary['total_labels_in_target']}"),
            html.Div(f"Total missing emails: {summary['total_missing_emails']}"),
        ]
    )

    return summary_div, rows, diff, proj_div


def register_callbacks(app):
    def _render_grouped_tree(
        data: List[Dict[str, Any]] | Dict[str, Dict[Any, List[str]]],
    ):
        def _group_label(gi: int) -> str:
            if gi == 0:
                return "Mark Read"
            if gi == 1:
                return "Mark Unread"
            return f"Group {gi}"

        if isinstance(data, list):
            grouped = rows_to_grouped(data)
        else:
            grouped = {}
            for label, groups in (data or {}).items():
                normalized: Dict[int, List[str]] = {}
                if isinstance(groups, dict):
                    for key, emails in groups.items():
                        normalized[_normalize_group_index(key)] = [
                            str(email) for email in emails or []
                        ]
                grouped[label] = normalized

        items = []
        for label in sorted(grouped):
            group_items = []
            label_groups = grouped.get(label, {}) or {}
            for gi in sorted(label_groups, key=int):
                emails = label_groups.get(gi, [])
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
                            html.Span(_group_label(gi)),
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
        Output("store-grouped", "data", allow_duplicate=True),
        Input("tbl-stl", "data"),
        prevent_initial_call=False,
    )
    def sync_grouped_store(rows):
        return rows_to_grouped(rows or [])

    @app.callback(
        Output("stl-grouped", "children"),
        Input("store-grouped", "data"),
    )
    def refresh_grouped_view(grouped):
        return _render_grouped_tree(grouped or {})

    @app.callback(
        Output("tbl-stl", "data", allow_duplicate=True),
        Output("store-grouped", "data", allow_duplicate=True),
        Output("status", "children", allow_duplicate=True),
        Input({"type": "grp-add", "label": MATCH, "group": MATCH}, "n_clicks"),
        State({"type": "grp-input", "label": MATCH, "group": MATCH}, "value"),
        State("tbl-stl", "data"),
        State("store-defaults", "data"),
        prevent_initial_call=True,
    )
    def on_group_add(n_clicks, value, rows, defaults):
        if not n_clicks:
            raise PreventUpdate
        triggered = ctx.triggered_id or {}
        if not isinstance(triggered, dict):
            raise PreventUpdate
        label = triggered.get("label", "")
        group_index = triggered.get("group")
        email = (value or "").strip()
        if not email:
            return no_update, no_update, "Enter an email before adding."
        try:
            updated_rows = _add_email_to_rows(rows, label, group_index, email, defaults)
        except ValueError as exc:
            logger.warning(
                "Unable to add %s to %s group %s: %s", email, label, group_index, exc
            )
            return no_update, no_update, f"Unable to add email: {exc}"
        grouped = rows_to_grouped(updated_rows)
        return (
            updated_rows,
            grouped,
            f"Added {email} to {label} (group {group_index}).",
        )

    @app.callback(
        Output("tbl-stl", "data", allow_duplicate=True),
        Output("store-grouped", "data", allow_duplicate=True),
        Output("status", "children", allow_duplicate=True),
        Input(
            {"type": "grp-remove", "label": MATCH, "group": MATCH, "email": MATCH},
            "n_clicks",
        ),
        State("tbl-stl", "data"),
        prevent_initial_call=True,
    )
    def on_group_remove(n_clicks, rows):
        if not n_clicks:
            raise PreventUpdate
        triggered = ctx.triggered_id or {}
        if not isinstance(triggered, dict):
            raise PreventUpdate
        label = triggered.get("label", "")
        group_index = triggered.get("group")
        email = triggered.get("email", "")
        try:
            updated_rows = _remove_email_from_rows(rows, label, group_index, email)
        except ValueError as exc:
            logger.warning(
                "Unable to remove %s from %s group %s: %s",
                email,
                label,
                group_index,
                exc,
            )
            return no_update, no_update, f"Unable to remove email: {exc}"
        grouped = rows_to_grouped(updated_rows)
        return (
            updated_rows,
            grouped,
            f"Removed {email} from {label} (group {group_index}).",
        )

    @app.callback(
        Output("tbl-stl", "data", allow_duplicate=True),
        Output("store-config", "data", allow_duplicate=True),
        Output("store-analysis", "data", allow_duplicate=True),
        Output("diff-summary", "children", allow_duplicate=True),
        Output("tbl-diff", "data", allow_duplicate=True),
        Output("store-diff", "data", allow_duplicate=True),
        Output("diff-projected", "children", allow_duplicate=True),
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
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                no_update,
                "No config loaded.",
            )

        # Determine which button fired
        action = ctx.triggered_id if ctx.triggered_id is not None else ""
        tmp = cfg

        if action in ("btn-fix-case", "btn-fix-dups", "btn-fix-all"):
            tmp, _ = normalize_case_and_dups(tmp)
        if action in ("btn-fix-sort", "btn-fix-all"):
            tmp, _ = sort_lists(tmp)

        stl_rows = config_to_table(tmp)
        analysis = run_full_analysis(tmp)
        summary, diff_rows, diff_obj, proj_div = _prepare_diff_outputs(tmp, analysis)
        return (
            stl_rows,
            tmp,
            analysis,
            summary,
            diff_rows,
            diff_obj,
            proj_div,
            f"Applied: {action.replace('btn-', '').replace('-', ' ')}",
        )

    @app.callback(
        Output("store-config", "data", allow_duplicate=True),
        Output("store-analysis", "data", allow_duplicate=True),
        Output("status", "children", allow_duplicate=True),
        Input("btn-apply-edits", "n_clicks"),
        State("tbl-stl", "data"),
        State("store-config", "data"),
        prevent_initial_call=True,
    )
    def on_apply_edits(_n, stl_rows, cfg):
        tmp = table_to_config(stl_rows, cfg)
        analysis = run_full_analysis(tmp)
        return tmp, analysis, "Applied table edits to working config (not yet saved)."

    @app.callback(
        Output("tbl-ignored", "data", allow_duplicate=True),
        Output("store-config", "data", allow_duplicate=True),
        Output("store-analysis", "data", allow_duplicate=True),
        Output("status", "children", allow_duplicate=True),
        Input("btn-apply-ignored", "n_clicks"),
        State("tbl-ignored", "data"),
        State("store-config", "data"),
        prevent_initial_call=True,
    )
    def on_apply_ignored(_n, rows, cfg):
        cfg = cfg or {}
        try:
            rules = rows_to_ignored_rules(rows)
        except ValueError as exc:
            logger.error("Invalid ignored rules: %s", exc)
            return no_update, no_update, no_update, f"Ignored rules invalid: {exc}"
        tmp = dict(cfg)
        tmp["IGNORED_EMAILS"] = rules
        analysis = run_full_analysis(tmp)
        return (
            ignored_rules_to_rows(tmp),
            tmp,
            analysis,
            "Applied IGNORED_EMAILS edits to working config (not yet saved).",
        )

    @app.callback(
        Output("status", "children", allow_duplicate=True),
        Input("btn-save", "n_clicks"),
        State("store-config", "data"),
        State("chk-backup", "value"),
        prevent_initial_call=True,
    )
    def on_save(_n, cfg, backup_flags):
        if not cfg:
            logger.info("Save requested with no configuration in memory.")
            return "Nothing to save."
        backup_requested = "backup" in (backup_flags or [])
        label_count = len((cfg or {}).get("SENDER_TO_LABELS", {}))
        logger.info(
            "Persisting dashboard configuration (backup=%s, labels=%s)",
            backup_requested,
            label_count,
        )
        if backup_requested:
            if CONFIG_JSON.exists():
                bkp = backup_file(CONFIG_JSON)
                write_json(cfg, CONFIG_JSON)
                logger.info(
                    "Configuration saved to %s with backup %s.",
                    CONFIG_JSON,
                    bkp,
                )
                return (
                    f"Backup saved: {bkp.name}\nUpdated: config/gmail_config-final.json"
                )
            write_json(cfg, CONFIG_JSON)
            logger.info(
                "Configuration saved to %s without existing file to backup.",
                CONFIG_JSON,
            )
            return "Updated: config/gmail_config-final.json"
        write_json(cfg, CONFIG_JSON)
        logger.info("Configuration saved without backup to %s.", CONFIG_JSON)
        return "Updated: config/gmail_config-final.json (no backup)"

    @app.callback(
        Output("store-defaults", "data"),
        Input("default-read-status", "value"),
        Input("default-delete-days", "value"),
    )
    def update_defaults(read_value, delete_days):
        return {
            "read_status": "read" in (read_value or []),
            "delete_after_days": delete_days if delete_days not in (None, "") else None,
        }

    @app.callback(
        Output("tbl-stl", "data", allow_duplicate=True),
        Input("btn-add-stl-row", "n_clicks"),
        State("tbl-stl", "data"),
        State("store-defaults", "data"),
        prevent_initial_call=True,
    )
    def add_stl_row(_n, rows, defaults):
        rows = rows or []
        rows.append(make_empty_stl_row(defaults))
        return rows

    @app.callback(
        Output("tbl-ignored", "data", allow_duplicate=True),
        Input("btn-add-ignored-row", "n_clicks"),
        State("tbl-ignored", "data"),
        prevent_initial_call=True,
    )
    def add_ignored_row(_n, rows):
        return _add_ignored_email(rows)

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

    @app.callback(
        Output("diff-table-view", "style"),
        Output("diff-tree-view", "style"),
        Input("diff-view-toggle", "value"),
    )
    def toggle_diff_view(mode):
        if mode == "tree":
            return {"display": "none"}, {"display": "block"}
        return {"display": "block"}, {"display": "none"}

    @app.callback(
        Output("ddl-stl-label-filter", "options"),
        Output("ddl-stl-label-filter", "value"),
        Input("tbl-stl", "data"),
        State("ddl-stl-label-filter", "value"),
    )
    def update_label_filter_dropdown(rows, current_value):
        options = _label_filter_options(rows or [])
        value = _sanitize_label_filter_value(options, current_value)
        return options, value

    @app.callback(
        Output("tbl-stl", "filter_query"),
        Output("tbl-stl", "selected_rows"),
        Input("ddl-stl-label-filter", "value"),
    )
    def on_label_filter_change(selected_label):
        return _build_label_filter_query(selected_label), []

    @app.callback(
        Output("store-theme", "data"),
        Output("app-root", "style"),
        Output("btn-toggle-theme", "children"),
        Input("btn-toggle-theme", "n_clicks"),
        State("store-theme", "data"),
    )
    def on_toggle_theme(n, data):
        theme = (data or {}).get("theme", "light")
        if n:
            theme = "dark" if theme == "light" else "light"
        style = get_theme_style(theme)
        label = "Switch to Light Mode" if theme == "dark" else "Switch to Dark Mode"
        return {"theme": theme}, style, label

    # Grouped-tree Add callback temporarily disabled due to Dash wildcard
    # constraints across multi-output callbacks. Controls are no-ops for now.

    # Grouped-tree Remove callback temporarily disabled due to Dash wildcard
    # constraints across multi-output callbacks. Controls are no-ops for now.

    @app.callback(
        Output("tbl-stl", "data", allow_duplicate=True),
        Output("tbl-ignored", "data", allow_duplicate=True),
        Output("store-config", "data", allow_duplicate=True),
        Output("store-analysis", "data", allow_duplicate=True),
        Output("status", "children", allow_duplicate=True),
        Input("btn-refresh-reports", "n_clicks"),
        prevent_initial_call=True,
    )
    def on_refresh(_n):
        try:
            cfg = load_config()
        except FileNotFoundError as exc:
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                str(exc),
            )
        stl_rows = config_to_table(cfg)
        ignored_rows = ignored_rules_to_rows(cfg)
        analysis = run_full_analysis(cfg)
        try:
            from .reports import write_ECAQ_report, write_diff_json

            write_ECAQ_report()
            write_diff_json()
        except Exception:
            pass
        return (
            stl_rows,
            ignored_rows,
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
                {"email": item["email"], "labels": ", ".join(labels), "action": ""}
            )
            opts = [
                {"label": f"Reassign to {lbl}", "value": "reassign:" + lbl}
                for lbl in labels
            ]
            opts.append({"label": "Split", "value": "split"})
            opts.append({"label": "Remove", "value": "remove"})
            dropdowns.append(
                {"if": {"row_index": i, "column_id": "action"}, "options": opts}
            )
        return collisions, dropdowns

    @app.callback(
        Output("diff-summary", "children", allow_duplicate=True),
        Output("tbl-diff", "data", allow_duplicate=True),
        Output("store-diff", "data", allow_duplicate=True),
        Output("diff-projected", "children", allow_duplicate=True),
        Output("status", "children", allow_duplicate=True),
        Input("store-config", "data"),
        prevent_initial_call="initial_duplicate",
    )
    def on_diff(cfg):
        if not cfg:
            return "", [], None, "", "No config loaded."
        if not LABELS_JSON.exists():
            return "", [], None, "", "Missing config/gmail_labels_data.json"
        analysis = run_full_analysis(cfg)
        summary, rows, diff, proj_div = _prepare_diff_outputs(cfg, analysis)
        return summary, rows, diff, proj_div, "Differences computed."

    @app.callback(
        Output("diff-tree", "figure"),
        Output("diff-tree-empty", "children"),
        Input("store-diff", "data"),
    )
    def on_diff_tree(diff):
        figure = _build_diff_tree_figure(diff)
        has_data = bool(diff and (diff.get("missing_emails_by_label") or {}))
        message = "" if has_data else "No difference data to display."
        return figure, message

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
        logger.info("ECAQ report exported via dashboard UI to %s", REPORT_TXT)
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
        logger.info("Diff JSON exported via dashboard UI to %s", DIFF_JSON)
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
