"""Render helpers for the grouped tree view in the dashboard."""

from typing import Dict, Iterable, List

from dash import dcc, html
from dash.development.base_component import Component

LabelGroups = Dict[str, Dict[int, List[str]]]


def _group_label(index: int) -> str:
    """Return a friendly label for a group index."""

    if index == 0:
        return "Mark Read"
    if index == 1:
        return "Mark Unread"
    return f"Group {index}"


def _build_email_item(label: str, group_index: int, email: str) -> html.Li:
    """Return a rendered email entry with hidden dash targets."""

    hidden_remove_target = html.Span(
        "",
        id={"type": "grp-dummy", "label": label, "group": group_index, "email": email},
        style={"display": "none"},
    )
    remove_button = html.Button(
        "Remove",
        id={
            "type": "grp-remove",
            "label": label,
            "group": group_index,
            "email": email,
        },
        n_clicks=0,
        style={"marginLeft": "4px", "fontSize": "12px"},
    )
    return html.Li(
        [
            html.Span(email, className="grouped-tree-email-text"),
            hidden_remove_target,
            remove_button,
        ],
        className="grouped-tree-email-item",
        style={"marginBottom": "2px"},
    )


def _build_group_item(label: str, group_index: int, emails: List[str]) -> html.Li:
    """Render a group node containing email items and controls."""

    email_items = [_build_email_item(label, group_index, email) for email in emails]
    hidden_add_target = html.Span(
        "",
        id={"type": "grp-dummy", "label": label, "group": group_index},
        style={"display": "none"},
    )
    email_input = dcc.Input(
        id={"type": "grp-input", "label": label, "group": group_index},
        placeholder="new email",
        style={"marginRight": "4px", "fontSize": "12px"},
    )
    add_button = html.Button(
        "Add",
        id={"type": "grp-add", "label": label, "group": group_index},
        n_clicks=0,
        style={"fontSize": "12px"},
    )

    return html.Li(
        [
            html.Div(
                [
                    html.Span(
                        _group_label(group_index),
                        className="grouped-tree-group-label",
                        style={"fontWeight": "bold"},
                    ),
                    html.Span(
                        f"{len(emails)} email{'s' if len(emails) != 1 else ''}",
                        className="grouped-tree-group-count",
                        style={
                            "marginLeft": "6px",
                            "fontSize": "11px",
                            "color": "#555",
                        },
                    ),
                ],
                className="grouped-tree-group-header",
                style={"marginBottom": "4px"},
            ),
            html.Ul(
                email_items,
                className="grouped-tree-email-list",
                style={"listStyleType": "none", "paddingLeft": "0", "margin": "0"},
            ),
            html.Div(
                [hidden_add_target, email_input, add_button],
                className="grouped-tree-group-controls",
                style={"marginTop": "6px"},
            ),
        ],
        className="grouped-tree-group",
        style={"marginBottom": "12px"},
    )


def render_grouped_tree(
    grouped: LabelGroups, expanded_labels: Iterable[str] | None = None
) -> Component:
    """Render the grouped tree layout for the given grouped data.

    Args:
        grouped: Mapping of label -> group index -> list of emails.
        expanded_labels: Iterable of labels that should be expanded.

    Returns:
        Dash HTML component tree representing the grouped view.
    """

    if not grouped:
        return html.Div(
            "No label assignments found.",
            className="grouped-tree-empty",
            style={"color": "#555", "fontStyle": "italic"},
        )

    expanded_set = {label for label in expanded_labels or [] if label in grouped}
    items: List[html.Li] = []

    for label in sorted(grouped):
        groups = grouped[label]
        total_emails = sum(len(emails) for emails in groups.values())
        caret = "▼" if label in expanded_set else "▶"
        header = html.Div(
            [
                html.Span(
                    caret,
                    className="grouped-tree-caret",
                    style={"width": "14px"},
                ),
                html.Span(
                    label,
                    className="grouped-tree-label-text",
                    style={"flexGrow": 1},
                ),
                html.Span(
                    f"{total_emails} email{'s' if total_emails != 1 else ''}",
                    className="grouped-tree-label-count",
                    style={"fontSize": "12px", "color": "#555"},
                ),
            ],
            id={"type": "grp-label-toggle", "label": label},
            n_clicks=0,
            className="grouped-tree-label-row",
            role="button",
            tabIndex=0,
            style={
                "display": "flex",
                "alignItems": "center",
                "gap": "6px",
                "cursor": "pointer",
                "padding": "6px 8px",
                "backgroundColor": "#f7f7f7",
                "borderRadius": "4px",
            },
        )

        group_items = [
            _build_group_item(label, group_index, groups[group_index])
            for group_index in sorted(groups)
        ]
        content_style = {
            "display": "block" if label in expanded_set else "none",
            "padding": "8px 12px",
            "marginLeft": "18px",
            "borderLeft": "2px solid #ddd",
        }

        items.append(
            html.Li(
                [
                    header,
                    html.Div(
                        html.Ul(
                            group_items,
                            className="grouped-tree-group-list",
                            style={
                                "listStyleType": "none",
                                "paddingLeft": "0",
                                "margin": "8px 0 0 0",
                            },
                        ),
                        className="grouped-tree-content",
                        style=content_style,
                    ),
                ],
                className="grouped-tree-node",
                style={"marginBottom": "12px"},
            )
        )

    return html.Ul(
        items,
        className="grouped-tree",
        style={"listStyleType": "none", "paddingLeft": "0", "margin": "0"},
    )


def toggle_expanded_label(
    target_label: str | None,
    expanded_labels: Iterable[str] | None,
    available_labels: Iterable[str] | None,
) -> List[str]:
    """Return updated expanded-label list after toggling ``target_label``.

    Args:
        target_label: The label that was clicked.
        expanded_labels: Labels currently expanded.
        available_labels: Labels present in the grouped tree.

    Returns:
        Sorted list of expanded labels that remain valid.
    """

    available_set = {label for label in available_labels or []}
    expanded_set = {label for label in expanded_labels or [] if label in available_set}

    if target_label is None or target_label not in available_set:
        return sorted(expanded_set)

    if target_label in expanded_set:
        expanded_set.remove(target_label)
    else:
        expanded_set.add(target_label)

    return sorted(expanded_set)
