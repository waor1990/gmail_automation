# Scripts Directory

This directory contains automation scripts for the Gmail automation project.

## Scripts

### `setup.sh` / `setup.ps1`

Sets up the Python environment and installs dependencies.

- **Bash version**: Cross-platform bash script
- **PowerShell version**: Windows-optimized PowerShell script
- Automatically validates `gmail_automation.py` compilation

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

- Python 3.x
- GitHub CLI (`gh`)
- `jq` (for JSON parsing in create_issues.sh)
- Git Bash (on Windows, for running bash scripts)

## Notes

- All scripts include comprehensive error handling
- The setup scripts automatically validate the main Python script compilation
- Log files are created for issue creation operations
- Cross-platform compatibility is maintained where possible
