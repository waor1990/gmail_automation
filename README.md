# Gmail Automation

This repository contains a Python script that labels and organizes Gmail messages using the Gmail API. It relies on a JSON configuration that maps specific senders or keywords to labels.

## Requirements

- Python 3.10 or newer
- [Google API credentials](https://developers.google.com/gmail/api/quickstart/python)
- Packages listed in `requirements.txt`

Install dependencies with:

```bash
pip install -r requirements.txt
```

You can also run the setup script which creates a Python virtual environment
and installs the dependencies automatically:

```bash
./scripts/setup.sh
```

## Configuration

1. Obtain a client secret JSON file from Google Cloud and place it in the `config/` directory. The file should be named like `client_secret*.json`.
2. Copy `config/gmail_config.sample.json` to `config/gmail_config-final.json` and edit it with your label rules. You can also supply a different configuration file at runtime with `--config path/to/file.json`.
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
python gmail_automation.py --help
```

The script supports several command line options:

```bash
python gmail_automation.py --config config/gmail_config-final.json --dry-run --verbose
```

- `--config` – path to configuration file (defaults to `config/gmail_config-final.json`)
- `--dry-run` – process emails without making changes
- `--verbose` – enable debug logging to the console
- `--version` – display version information

Logs are written to `logs/gmail_automation_info.log` and `logs/gmail_automation_debug.log`.

## Security Note

Credentials and log files should not be committed to version control. Update `.gitignore` accordingly and keep sensitive files private.

## Documentation

Additional guides are available in the [docs](docs/) directory:

- [Setup Guide](docs/setup.md)
- [Configuration Examples](docs/configuration_examples.md)

## Troubleshooting

- **Missing configuration file**: ensure `gmail_config-final.json` exists or pass its path with `--config`.
- **Missing OAuth client secret**: download the OAuth client secrets JSON from Google Cloud and place it in the `config/` directory.
- **Permission errors**: delete `data/gmail-python-email.json` and re-run the script to re-authorize.
