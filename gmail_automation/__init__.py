"""Expose the actual package from ``src`` for direct execution.

This wrapper allows running ``python -m gmail_automation`` without
installing the project by loading the package from ``src/gmail_automation``
at runtime.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

_pkg_init = (
    Path(__file__).resolve().parent.parent / "src" / "gmail_automation" / "__init__.py"
)
_spec = importlib.util.spec_from_file_location(
    __name__,
    _pkg_init,
    submodule_search_locations=[str(_pkg_init.parent)],
)
if _spec is None or _spec.loader is None:  # pragma: no cover - defensive
    raise ModuleNotFoundError("Cannot load package from src/gmail_automation")

_module = importlib.util.module_from_spec(_spec)
sys.modules[__name__] = _module
_spec.loader.exec_module(_module)
