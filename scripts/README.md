# Scripts Directory

Helper commands are exposed as Python modules. Run them with:

``` python
python -m scripts.<name> [options]
```

Available commands:

- `setup` – create the virtual environment
- `maintenance` – validate secrets, hooks, run checks/tests
- `enter_venv` – open a new Command Prompt with the venv activated (Windows)
- `create_issues` – open GitHub issues from files
- `resolve_issue` – close an issue and archive its file
- `clean_git_history` – remove sensitive files from history
- `validate_no_secrets` – check for sensitive files before committing
- `extract_gmail_labels` – export Gmail labels to JSON

Legacy `.sh` and `.ps1` shims forward to these modules and print a
deprecation notice.

Windows convenience:

- From any shell, run `scripts\enter_venv.cmd` to create the venv if missing
  and open a new Command Prompt already activated at the repo root.

Outdated package maintenance:

- List and optionally upgrade interactively:
  - `python -m scripts.maintenance --outdated`
- Upgrade all without prompting:
  - `python -m scripts.maintenance --outdated --upgrade-all`
- Upgrade specific packages:
  - `python -m scripts.maintenance --outdated --upgrade pandas plotly`
- List only (no prompt, no upgrades):
  - `python -m scripts.maintenance --outdated --no-input`
