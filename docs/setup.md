# Setup Guide

This document explains how to configure and run the Gmail Automation script.

1. Install Python 3.10 or newer.
1. Clone this repository and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
1. Create `config/gmail_config-final.json` from the provided sample and edit it with
   your label rules.
1. Obtain a client secret JSON file from Google Cloud and place it in the
   `config/` directory. When you run the script for the first time it will open a
   browser window asking for permission to access your Gmail account.
1. Run the script with:
   ```bash
   python -m gmail_automation
   ```

OAuth credentials will be stored in `data/gmail-python-email.json` after the first
successful run. Keep this file private.
