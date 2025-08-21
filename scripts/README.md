# Scripts Directory

This directory contains automation scripts for the Gmail automation project.

## Scripts

### `setup.sh` / `setup.ps1`

Sets up the Python environment and installs dependencies.

- **Bash version**: Cross-platform bash script
- **PowerShell version**: Windows-optimized PowerShell script
- Automatically validates the Gmail automation package

### `extract_gmail_labels.py` / `extract_gmail_labels.ps1`

**NEW**: Extracts Gmail labels and associated email addresses to generate a configuration file.

This script replicates the functionality of the Google Apps Script (`saveLabelsToJSON.gs`) but runs locally using the Gmail API through Python. It serves as a discovery tool to help you identify email addresses in your existing Gmail labels.

- **Python version**: Cross-platform standalone script
- **PowerShell version**: Windows wrapper with virtual environment handling
- Processes Gmail labels in batches to respect API limits
- Generates `config/gmail_labels_data.json` for reference (not used by main automation)
- Helps discover new email addresses to add to your main configuration

#### Usage Examples

```bash
# Basic extraction (saves to config/gmail_labels_data.json, batch size: 5)
python scripts/extract_gmail_labels.py

# Custom output file and batch size
python scripts/extract_gmail_labels.py --output config/my_labels.json --batch-size 10

# Verbose logging
python scripts/extract_gmail_labels.py --verbose
```

```powershell
# Windows PowerShell (handles virtual environment automatically)
.\scripts\extract_gmail_labels.ps1

# With custom parameters
.\scripts\extract_gmail_labels.ps1 -OutputFile "config\my_labels.json" -BatchSize 10 -Verbose
```

#### Output Format

The script generates a JSON file with this structure:

```json
{
  "SENDER_TO_LABELS": {
    "Your_Label_Name": [
      {
        "read_status": false,
        "delete_after_days": 30,
        "emails": ["sender1@example.com", "sender2@example.com"]
      }
    ]
  }
}
```

### `scripts/dashboard/`

Provides a Dash-based web dashboard for inspecting and editing
`gmail_config-final.json`. The dashboard can also export helpful reports:

- `config/ECAQ_Report.txt` – email structure and quality summary
- `config/email_differences_by_label.json` – differences between Gmail labels and your configuration

Use the unified entry point to launch the dashboard, export reports, run the
main automation script, or execute development helpers:

```bash
python -m scripts.dashboard [--report {ECAQ,diff,all}] [--launch] [--refresh] [--dev ACTION]
```

Examples:

```bash
python -m scripts.dashboard                   # start dashboard
python -m scripts.dashboard --report all      # export both reports
python -m scripts.dashboard --refresh --launch # run automation then start dashboard
python -m scripts.dashboard --dev lint        # run flake8 on the codebase
```

### `create_issues.sh`

Creates GitHub issues from markdown files in the `issues/` directory.

- Validates file format before creating issues
- Prevents duplicate issues
- Provides detailed logging

### `resolve_issue.sh`

Closes GitHub issues and archives their corresponding files.

- Cross-platform file handling
- Better error handling and validation
- Moves resolved issues to `issues/solved/`

## Usage

### Windows (PowerShell)

```powershell
# Setup environment
.\scripts\setup.ps1

# Create issues
bash scripts/create_issues.sh

# Resolve an issue
bash scripts/resolve_issue.sh 123
```

### Unix/Linux/macOS (Bash)

```bash
# Setup environment
./scripts/setup.sh

# Create issues
./scripts/create_issues.sh

# Resolve an issue
./scripts/resolve_issue.sh 123
```

## Requirements

- Python 3.x with virtual environment (`.venv`)
- Gmail API credentials (configured via `config/client_secret*.json` files)
- GitHub CLI (`gh`) - for issue management scripts
- `jq` (for JSON parsing in create_issues.sh)
- Git Bash (on Windows, for running bash scripts)

## Notes

- All scripts include comprehensive error handling
- The setup scripts automatically validate the main Python script compilation
- The Gmail extraction scripts respect API rate limits with batch processing
- Generated `gmail_labels_data.json` is automatically ignored by git (see `.gitignore`)
- Log files are created for issue creation operations
- Cross-platform compatibility is maintained where possible

## Gmail Labels Extraction Workflow

1. **Run extraction**: `python scripts/extract_gmail_labels.py`
2. **Review generated file**: Check `config/gmail_labels_data.json` for new email addresses
3. **Update main config**: Manually add relevant emails to `config/gmail_config-final.json`
4. **Run automation**: Use `python -m gmail_automation` with your updated configuration

The extraction script serves as a **discovery tool** and does not replace your main automation configuration.
