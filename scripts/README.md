# Scripts Directory

Helper commands are exposed as Python modules. Run them with:

``` python
python -m scripts.<name> [options]
```

Available commands:

- `setup` - create or update the virtual environment
- `maintenance` - validate secrets, manage hooks, run checks/tests
- `dashboard` - launch the Dash UI, export reports, refresh data, or run dev
  helpers (`--dev`, `--import-missing`, `--refresh`, etc.)
- `create_issues` - open GitHub issues from files
- `resolve_issue` - close an issue and archive its file
- `clean_git_history` - remove sensitive files from history
- `validate_no_secrets` - check for sensitive files before committing
- `extract_gmail_labels` - export Gmail labels to JSON

Shell and PowerShell shims forward to these modules for convenience.

Windows convenience (preferred):

- Run `setup.bat` from the repo root. It simply forwards to `scripts\setup.cmd`,
  so you can double-click it or type `setup` in Windows Explorer's address bar.
- Call `scripts\setup.cmd` directly when you need to pass flags such as
  `--install-hooks` or `--rebuild`. The script creates or updates the virtual
  environment, installs dependencies, then launches an activated shell
  (PowerShell, cmd.exe, or Git Bash).

Outdated package maintenance:

- List and optionally upgrade interactively:
  - `python -m scripts.maintenance --outdated`
- Upgrade all without prompting:
  - `python -m scripts.maintenance --outdated --upgrade-all`
- Upgrade specific packages:
  - `python -m scripts.maintenance --outdated --upgrade pandas plotly`
- List only (no prompt, no upgrades):
  - `python -m scripts.maintenance --outdated --no-input`

Compatibility checks:

- Verify installed packages have compatible dependencies:
  - `python -m scripts.maintenance --check-compat`

Dash-specific helpers:

- Import missing emails for a label from the latest diff:
  - `python -m scripts.dashboard --import-missing Finance`
- Change host/port or enable Dash debug mode:
  - `python -m scripts.dashboard --host 0.0.0.0 --port 8051 --debug`
- Run targeted developer utilities:
  - `python -m scripts.dashboard --dev lint`
  - `python -m scripts.dashboard --dev test-cov`
