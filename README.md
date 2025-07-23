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

## Running

```bash
python gmail_automation.py
```

The script logs activity to `gmail_automation_info.log` and `gmail_automation_debug.log`.

## Security Note

Credentials and log files should not be committed to version control. Update `.gitignore` accordingly and keep sensitive files private.
