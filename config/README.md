# Configuration Files

This directory stores configuration files such as the main Gmail rules and OAuth client secrets.

## Directory Structure

- `config-sample/` - Template configuration files that can be copied and customized
  - `client_secret.sample.json` - Example Google API client secret file structure
  - `gmail_config.sample.json` - Example Gmail automation configuration
- `README.md` - This documentation file

## Important Notes

- All other files in this directory are ignored by git for security
- Copy sample files from `config-sample/` to this directory and customize them
- Never commit real credentials or configuration files to version control
- The `gmail_config-final.json` file will be your main configuration
- OAuth client secret files should be named like `client_secret*.json`

## Getting Started

1. Copy `config-sample/gmail_config.sample.json` to `gmail_config-final.json`
2. Copy `config-sample/client_secret.sample.json` to `client_secret_[your-project-id].json`
3. Customize both files with your actual configuration and credentials
4. Run the gmail automation script to begin processing
