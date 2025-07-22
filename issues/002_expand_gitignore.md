# Issue: Expand .gitignore for logs and credentials

## Problem
The current `.gitignore` does not exclude all log files or credential tokens, allowing them to be accidentally committed.

## Proposed Solution
Add patterns for debug logs, OAuth tokens, and other generated files. Ensure contributors know to keep sensitive data out of version control.
