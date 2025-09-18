# Testing and Development Guide

This guide summarizes the recommended checks, scripts, and workflows for
maintaining Gmail Automation.

## Quick Start

1. Ensure the virtual environment is prepared:

   ```bash
   python -m scripts.setup --install-hooks
   ```

   The setup helper upgrades pip, installs runtime + development dependencies,
   and (optionally) configures pre-commit hooks.

2. Run the full automated check suite:

   ```bash
   python -m scripts.dashboard --dev all
   ```

   This executes linting, format checks, type checking, and pytest in one pass.

3. When working iteratively, the most common single commands are:

   ```bash
   python -m pytest
   python -m scripts.dashboard --dev lint
   python -m scripts.dashboard --dev format-check
   python -m scripts.dashboard --dev mypy
   ```

## Test Matrix

Pytest discovers tests in `tests/`. The suite covers configuration parsing,
Dash helpers, Gmail service integrations (mocked), and CLI flows. Selected
entry points:

- `tests/test_cli.py` / `tests/test_cli_entry_point.py` - CLI parsing and module
  execution
- `tests/test_config.py` / `tests/test_sender_last_run.py` - configuration and
  runtime state helpers
- `tests/test_dashboard_*` - dashboard layout, callbacks, transforms, and
  import tooling
- `tests/test_gmail_service.py` / `tests/test_integration.py` - Gmail API logic
  (network calls mocked)
- `tests/test_logging_utils.py` / `tests/test_render_coverage.py` - logging
  helpers and ancillary tools

Run focused subsets with the usual pytest selectors, for example:

```bash
python -m pytest tests/test_dashboard_transforms.py -k diff
python -m pytest -m "not integration"
python -m pytest --cov=src/gmail_automation --cov-report=term-missing
```

Coverage artifacts land in `htmlcov/` and `coverage.xml`.

## Code Quality Tooling

- **Linting** - `python -m scripts.dashboard --dev lint`
- **Formatting** - `python -m scripts.dashboard --dev format`
- **Format check** - `python -m scripts.dashboard --dev format-check`
- **Type checking** - `python -m scripts.dashboard --dev mypy`
- **Cache cleanup** - `python -m scripts.dashboard --dev clean`

`requirements-dev.txt` pins every tool used above.

## Pre-commit Hooks

Pre-commit is optional but recommended. After running the setup helper you can
reinstall or update hooks with:

```bash
python -m scripts.maintenance --install-hooks
python -m scripts.maintenance --autoupdate-hooks
python -m scripts.maintenance --run-hooks
```

## Continuous Integration

GitHub Actions executes `.github/workflows/ci.yml` on pushes and pull requests
against `main` or `develop`. The workflow currently:

1. runs on `windows-latest` with Python 3.12,
2. caches pip downloads,
3. installs `requirements-dev.txt`,
4. lints with flake8,
5. checks formatting with black,
6. runs mypy (non-blocking for now),
7. executes pytest with coverage, and
8. uploads `coverage.xml` to Codecov.

Keep local runs aligned with CI to avoid surprises.

## Troubleshooting

- **Missing dependencies** - Rerun `python -m scripts.setup --install-hooks` or
  `pip install -r requirements-dev.txt` inside the virtual environment.
- **Stale caches** - Use `python -m scripts.dashboard --dev clean` to remove
  `__pycache__`, coverage data, and other build artifacts.
- **CI failures** - Reproduce locally with the matching command from the
  workflow log and re-run the all-in-one helper to ensure consistency.
