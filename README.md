# Gmail Automation

[![CI](https://github.com/waor1990/gmail_automation/actions/workflows/python-tests.yml/badge.svg)](https://github.com/waor1990/gmail_automation/actions/workflows/python-tests.yml)

This repository contains a Python script that labels and organizes Gmail messages using the Gmail API. It relies on a JSON configuration that maps specific senders or keywords to labels.

## Requirements

- Python 3.10 or newer
- [Google API credentials](https://developers.google.com/gmail/api/quickstart/python)
- Packages listed in `requirements.txt`
- Development tools listed in `requirements-dev.txt`

Use the setup helper to create the virtual environment, upgrade pip, and install both runtime and development dependencies (add --install-hooks to install pre-commit):

```bat
setup.bat                  # Windows shortcut; forwards to scripts\setup.cmd
scripts\setup.cmd         # preferred entry point; accepts the same flags
scripts\setup.cmd --install-hooks
```

The underlying module works from any shell, or from CI where spawning a new window is undesirable:

```bash
python -m scripts.setup --install-hooks
```

If you need to install manually, fall back to:

```bash
pip install -r requirements-dev.txt
```

Activate the environment yourself when required:

```bash
source .venv/bin/activate         # Linux/macOS
source .venv/Scripts/activate     # Git Bash on Windows
\.venv\Scripts\Activate.ps1      # PowerShell
\.venv\Scripts\activate.bat      # cmd.exe
```

You can also skip activation by invoking the venv's Python directly for one-off commands, for example:

```bat
.\.venv\Scripts\python -m pytest
```

## Testing

Run the test suite with:

```bash
python -m pytest
```

## Maintenance

Use the maintenance helper to validate secrets, manage hooks, run checks, and
handle outdated packages:

```bash
# Validate no secrets are committed
python -m scripts.maintenance --validate-secrets

# Install or autoupdate pre-commit hooks
python -m scripts.maintenance --install-hooks
python -m scripts.maintenance --autoupdate-hooks

# Run pre-commit on all files
python -m scripts.maintenance --run-hooks

# Run the test suite
python -m scripts.maintenance --tests

# Check for dependency conflicts
python -m scripts.maintenance --check-compat

# List outdated packages and choose to upgrade all/some interactively
python -m scripts.maintenance --outdated

# Non-interactive upgrades
python -m scripts.maintenance --outdated --upgrade-all
python -m scripts.maintenance --outdated --upgrade pandas plotly

# List only (no prompts)
python -m scripts.maintenance --outdated --no-input

# Full pass: validate → hooks → run hooks → tests
python -m scripts.maintenance --all
```

## Configuration

1. Obtain a client secret JSON file from Google Cloud and place it in the `config/` directory. The file should be named like `client_secret*.json`.
2. Copy `config/config-sample/gmail_config.sample.json` to `config/gmail_config-final.json` and edit it with your label rules. You can also supply a different configuration file at runtime with `--config path/to/file.json`.
3. On first run, OAuth credentials will be stored in `data/gmail-python-email.json`.
4. The `read_status` value within `SENDER_TO_LABELS` should be a boolean. The script will also accept the strings `"true"` and `"false"` and convert them automatically.

## Token Management

The Gmail API uses OAuth 2.0 tokens for authentication. When you run the script
for the first time, a browser window will prompt you to grant access to your
Google account. After authorization, the resulting credentials are saved in
`data/gmail-python-email.json`.

The script automatically refreshes expired access tokens using the stored
refresh token. If refreshing fails (for example, if you revoke the app's
permissions), delete `data/gmail-python-email.json` and rerun the script to perform
the OAuth flow again. Keep this file private and out of version control.

## Running

```bash
python -m gmail_automation --help
```

The script supports several command line options:

```bash
python -m gmail_automation --config config/gmail_config-final.json --dry-run --verbose
```

- `--config` – path to configuration file (defaults to `config/gmail_config-final.json`)
- `--dry-run` – process emails without making changes
- `--verbose` or `-v` – enable debug logging to the console (equivalent to `--log-level DEBUG`)
- `--log-level` – set the console logging level (choices: DEBUG, INFO, WARNING, ERROR, CRITICAL; default: INFO)
- `--version` – display version information

**Logging Examples:**

```bash
# Standard info logging (default)
python -m gmail_automation

# Verbose debug logging
python -m gmail_automation --verbose
python -m gmail_automation --log-level DEBUG

# Only show warnings and errors
python -m gmail_automation --log-level WARNING

# Only show errors
python -m gmail_automation --log-level ERROR
```

Logs are written to `logs/gmail_automation_info.log` and `logs/gmail_automation_debug.log`.

## Security Note

Credentials and log files should not be committed to version control. Update `.gitignore` accordingly and keep sensitive files private.

## Runtime State

Timestamps of the last processed email for each sender are stored in
`data/sender_last_run.json`. When a new address is introduced in the
`SENDER_TO_LABELS` configuration, the system initializes its entry with
`2000-01-01T00:00:00Z` so that historical messages are considered. After a
successful run (without `--dry-run`), these timestamps are updated to the
current time. A legacy `data/last_run.txt` file is still read if the per-sender
file is absent.

## Dashboard and Reports

An interactive [Dash](https://dash.plotly.com/) dashboard is provided to review
and edit your Gmail configuration. On launch the dashboard automatically runs
all available reports, which now include sections summarizing projected changes
if pending developer fixes were applied. A table of senders with the default
`last_run` timestamp highlights newly added addresses awaiting processing.

Launch the dashboard or export reports via the unified entry point:

```bash
python -m scripts.dashboard [--report {ECAQ,diff,all}] [--launch] [--refresh]
```

Examples:

```bash
# Launch the dashboard
python -m scripts.dashboard

# Export both reports without starting the dashboard
python -m scripts.dashboard --report all

# Refresh data, export the diff report, then launch the dashboard
python -m scripts.dashboard --refresh --report diff --launch

# Launch the dashboard on a different port/host
python -m scripts.dashboard --port 8051                  # change port
python -m scripts.dashboard --host 0.0.0.0 --port 8060   # bind all interfaces

# Alternatively, use environment variables
# Bash
PORT=8052 python -m scripts.dashboard
DASH_PORT=8053 python -m scripts.dashboard

# PowerShell
$env:PORT=8054; python -m scripts.dashboard
$env:DASH_PORT=8055; python -m scripts.dashboard
```

Use the optional `--refresh` flag to run the automation module before other
actions. The dashboard supports exporting:

- `config/ECAQ_Report.txt` – summary of email structure and quality
- `config/email_differences_by_label.json` – missing emails per label

## Documentation

Additional guides are available in the [docs](docs/) directory:

- [Setup Guide](docs/setup.md)
- [Configuration Examples](docs/configuration_examples.md)

## Development

Run tests and code quality checks through the dashboard entry point:

```bash
python -m scripts.dashboard --dev all      # lint, type-check, test
python -m scripts.dashboard --dev format   # auto-format code
```

## Troubleshooting

- **Missing configuration file**: ensure `gmail_config-final.json` exists or pass its path with `--config`.
- **Missing OAuth client secret**: download the OAuth client secrets JSON from Google Cloud and place it in the `config/` directory.
- **Permission errors**: delete `data/gmail-python-email.json` and re-run the script to re-authorize.
