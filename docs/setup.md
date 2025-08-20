# Setup Guide

This document explains how to configure and run the Gmail Automation script.

1. Install Python 3.10 or newer.
1. Clone this repository and install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

   You can also run `scripts/setup.sh` to create a virtual environment automatically.
1. Create `config/gmail_config-final.json` from the sample file in `config/config-sample/gmail_config.sample.json` and edit it with
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

1. *(Optional)* Launch the configuration dashboard or export reports:

   ```bash
   python -m scripts.dashboard [--report {ECAQ,diff,all}] [--launch] [--refresh]
   ```

   Examples:

   ```bash
   # Launch the dashboard
   python -m scripts.dashboard

   # Export both reports without starting the dashboard
   python -m scripts.dashboard --report all

   # Refresh data, export ECAQ report, then launch the dashboard
   python -m scripts.dashboard --refresh --report ECAQ --launch
   ```

   Use the optional `--refresh` flag to run `gmail_automation.py` before other
   actions. The dashboard can export `config/ECAQ_Report.txt` and
   `config/email_differences_by_label.json` for further analysis.
