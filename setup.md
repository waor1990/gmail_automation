# Setup Guide

This guide explains how to configure the Gmail automation script.

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

## 2. Prepare Configuration

1. Copy `config/gmail_config.sample.json` to `config/gmail_config-final.json`.
2. Edit the file to match your own label rules.
3. You can override the configuration location when running the script with `--config PATH`.

## 3. Obtain OAuth Credentials

1. Create a project in the [Google Cloud Console](https://console.cloud.google.com/).
2. Enable the Gmail API and generate OAuth client credentials for a desktop application.
3. Download the client secret JSON file and place it in the `config/` directory. The file name should start with `client_secret`.

## 4. First Run

Run the script to complete the OAuth flow:

```bash
python gmail_automation.py --config config/gmail_config-final.json
```

A browser window will open asking for permission to access your Gmail account. After authorization, credentials are stored in `data/gmail-python-email.json`.

## 5. Optional Flags

- `--dry-run` – show what would happen without modifying any messages.
- `--verbose` – display debug output in the console.
- `--version` – show the installed version.

## 6. Troubleshooting

- Ensure the configuration file path is correct.
- Verify the OAuth client secret JSON exists in the `config/` directory.
- Delete `data/gmail-python-email.json` if you need to re-run the OAuth flow.
