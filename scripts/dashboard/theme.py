"""Theme utilities for the dashboard."""
from __future__ import annotations

from typing import Dict


def get_theme_style(theme: str) -> Dict[str, str]:
    """Return style dictionary for the given theme.

    Args:
        theme: Either ``"light"`` or ``"dark"``.

    Returns:
        A dictionary of inline CSS styles for the root container.
    """
    base: Dict[str, str] = {
        "fontFamily": "Arial, sans-serif",
        "padding": "20px",
        "maxWidth": "1200px",
        "margin": "0 auto",
    }
    if theme == "dark":
        base.update({"backgroundColor": "#222", "color": "#eee"})
    else:
        base.update({"backgroundColor": "#fff", "color": "#000"})
    return base
