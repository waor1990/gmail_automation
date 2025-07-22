# Issue: Remove sensitive credentials from Git history

## Problem
Sensitive credential files are present in the repository history, which poses a security risk.

## Proposed Solution
Rewrite the Git history to remove these files and force push the cleaned repository. Document the cleanup process for contributors.
