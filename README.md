# Gmail Automation
[![CI](https://github.com/waor1990/gmail_automation/actions/workflows/python-tests.yml/badge.svg)](https://github.com/waor1990/gmail_automation/actions/workflows/python-tests.yml)

This repository contains a Python script that labels and organizes Gmail messages using the Gmail API. It relies on a JSON configuration that maps specific senders or keywords to labels.

## Requirements

- Python 3.10 or newer
- [Google API credentials](https://developers.google.com/gmail/api/quickstart/python)
- Packages listed in `requirements.txt`

Install dependencies with:

```bash
pip install -r requirements.txt
```

You can also run the setup module which creates a Python virtual environment
and installs the dependencies automatically:

```bash
python -m scripts.setup
```

Examples for other shells:

```bash
./scripts/setup.sh        # Git Bash
.\scripts\setup.ps1       # PowerShell
scripts\setup.cmd         # cmd.exe
```

Activate the environment with:

```bash
source .venv/bin/activate       # Linux/macOS
source .venv/Scripts/activate   # Git Bash on Windows
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
