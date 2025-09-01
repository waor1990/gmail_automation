# Scripts Directory

Helper commands are exposed as Python modules. Run them with:

``` python
python -m scripts.<name> [options]
```

Available commands:

- `setup` – create the virtual environment
- `maintenance` – validate secrets, hooks, run checks/tests
- `create_issues` – open GitHub issues from files
- `resolve_issue` – close an issue and archive its file
- `clean_git_history` – remove sensitive files from history
- `validate_no_secrets` – check for sensitive files before committing
- `extract_gmail_labels` – export Gmail labels to JSON

Shell and PowerShell shims forward to these modules for convenience.

Windows convenience:

- From any shell at the repo root, run `enter_env.bat`. It uses the `setup`
  helper to create the virtual environment and install dependencies if
  missing, then launches an appropriate shell with the environment activated
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
