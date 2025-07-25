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

1. Obtain a client secret JSON file from Google Cloud and place it in the project directory.
2. Copy `gmail_config.sample.json` to `gmail_config-final.json` and edit it with your label rules.
3. On first run, OAuth credentials will be stored in `gmail-python-email.json`.
4. The `read_status` value within `SENDER_TO_LABELS` should be a boolean. The
   script will also accept the strings `"true"` and `"false"` and convert them
   automatically.

## Token Management

The Gmail API uses OAuth 2.0 tokens for authentication. When you run the script
for the first time, a browser window will prompt you to grant access to your
Google account. After authorization, the resulting credentials are saved in
`gmail-python-email.json`.

The script automatically refreshes expired access tokens using the stored
refresh token. If refreshing fails (for example, if you revoke the app's
permissions), delete `gmail-python-email.json` and rerun the script to perform
the OAuth flow again. Keep this file private and out of version control.

## Running

```bash
python -m gmail_automation
```

The script logs activity to `gmail_automation_info.log` and `gmail_automation_debug.log`.

## Security Note

Credentials and log files should not be committed to version control. Update `.gitignore` accordingly and keep sensitive files private.
