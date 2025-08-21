#!/usr/bin/env bash
set -euo pipefail

# Simple setup script for gmail_automation
# Creates a Python virtual environment and installs dependencies

VENV_DIR=".venv"

# Detect operating system for cross-platform compatibility
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
    PYTHON_CMD="python"
    ACTIVATE_SCRIPT="$VENV_DIR/Scripts/activate"
else
    PYTHON_CMD="python3"
    ACTIVATE_SCRIPT="$VENV_DIR/bin/activate"
fi

# Check if Python is available
if ! command -v "$PYTHON_CMD" &> /dev/null; then
    echo "❌ Python is not installed or not in PATH"
    exit 1
fi

if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating virtual environment in $VENV_DIR..."
    "$PYTHON_CMD" -m venv "$VENV_DIR"
    echo "✅ Created virtual environment in $VENV_DIR"
fi

# Activate virtual environment (cross-platform)
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
    source "$VENV_DIR/Scripts/activate"
else
    source "$VENV_DIR/bin/activate"
fi

echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Compile the CLI to ensure it's valid
echo "🔍 Validating Gmail automation package..."
if python -m py_compile src/gmail_automation/cli.py; then
    echo "✅ Gmail automation package compiles successfully"
else
    echo "❌ Gmail automation package has compilation errors"
    exit 1
fi

echo "✅ Setup complete!"
echo ""
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
    echo "To activate the environment, run: $VENV_DIR\\Scripts\\activate"
else
    echo "To activate the environment, run: source $VENV_DIR/bin/activate"
fi
