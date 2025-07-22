#!/usr/bin/env bash
set -euo pipefail

# Simple setup script for gmail_automation
# Creates a Python virtual environment and installs dependencies

VENV_DIR=".venv"

if [[ ! -d "$VENV_DIR" ]]; then
    python3 -m venv "$VENV_DIR"
    echo "Created virtual environment in $VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

pip install --upgrade pip
pip install -r requirements.txt

echo "Setup complete. Activate the environment with 'source $VENV_DIR/bin/activate'"
