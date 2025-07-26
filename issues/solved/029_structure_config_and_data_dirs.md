# Issue: Organize configuration and runtime data directories

## Problem

Configuration files, OAuth tokens, logs, and runtime data like `last_run.txt` are stored in the repository root. This clutters the project and increases the risk of committing sensitive data.

## Proposed Solution

Create dedicated directories such as `config/`, `data/`, and `logs/` to store configuration files, runtime state, and log files respectively. Update the script to read and write files from these locations and modify `.gitignore` accordingly.
