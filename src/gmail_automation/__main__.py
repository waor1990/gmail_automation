"""Entry point for running the Gmail automation CLI as a module."""

from __future__ import annotations

import importlib


def main() -> None:
    """Load and execute the CLI main function."""
    module = importlib.import_module("gmail_automation.cli")
    cli_main = module.main
    cli_main()


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
