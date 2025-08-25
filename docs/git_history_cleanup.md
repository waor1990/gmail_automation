# Git History Cleanup Documentation

This document describes the process for removing sensitive credentials from the Git repository history.

## Overview

The repository previously contained sensitive files in its Git history, including:

- OAuth client secrets (`client_secret_*.json`)
- Access tokens (`gmail-python-email.json`)
- Configuration files with personal data (`gmail_config-final.json`)
- Log files with potentially sensitive information (`*.log`)
- Runtime state files (`last_run.txt`, `processed_email_ids.txt`)

## Cleanup Scripts

Two scripts are provided for cleaning the Git history:

### PowerShell Script (Windows)

```powershell
.\scripts\clean_git_history.ps1
```

### Bash Script (Unix/Linux/macOS/WSL)

```bash
./scripts/clean_git_history.sh
```

## Prerequisites

1. **Install git-filter-repo**:

   ```bash
   pip install git-filter-repo
   ```

   Or download from: <https://github.com/newren/git-filter-repo/>

2. **Backup your repository**: The scripts create an automatic backup branch, but consider making a full backup of your repository directory.

## What the Scripts Do

1. **Verify prerequisites** - Check that `git-filter-repo` is installed
2. **Create backup branch** - Creates `backup-before-cleanup` branch
3. **Remove sensitive files** - Uses `git filter-repo` to rewrite history
4. **Provide next steps** - Shows commands for verification and remote updates

## Files Removed from History

The following patterns are removed from the entire Git history:

- `client_secret_*.json`
- `gmail-python-email.json`
- `data/gmail-python-email.json`
- `gmail_config-final.json`
- `config/gmail_config-final.json`
- `*.log`
- `logs/*.log`
- `gmail_automation.log`
- `gmail_automation_debug*.log`
- `last_run.txt`
- `data/last_run.txt`
- `processed_email_ids.txt`
- `data/processed_email_ids.txt`

## Post-Cleanup Steps

### 1. Verify the Cleanup

```bash
git log --name-only --all | grep -E "(secret|token|credential)" || echo "No sensitive files found"
```

### 2. Update Remote Repository

If you need to update the remote repository (⚠️ **DANGEROUS - READ BELOW**):

```bash
git push --force-with-lease origin main
```

**⚠️ IMPORTANT**: Force pushing rewrites history on the remote. All collaborators must:

1. Delete their local copies
2. Fresh clone the repository
3. Any local branches based on old history will need to be recreated

### 3. Clean Up Backup

Once satisfied with the cleanup:

```bash
git branch -D backup-before-cleanup
```

## Security Considerations

### Immediate Actions Required

1. **Revoke compromised credentials**:
   - Revoke OAuth tokens in Google Cloud Console
   - Generate new client secrets if the old ones were exposed
   - Update any systems using the old credentials

2. **Update `.gitignore`**: Ensure all sensitive file patterns are excluded:

   ```gitignore
   # OAuth tokens and credentials
   config/client_secret_*.json
   data/gmail-python-email.json
   *_token.json

   # Logs
   logs/
   *.log

   # Runtime files
   data/last_run.txt
   data/processed_email_ids.txt
   ```

### For Collaborators

If the repository is shared:

1. **Notify all collaborators** before force-pushing
2. **Provide instructions** for re-cloning the repository
3. **Consider rotating any shared secrets** that may have been exposed

## Recovery

If something goes wrong during cleanup:

1. **Reset to backup**:

   ```bash
   git reset --hard backup-before-cleanup
   ```

2. **Restore from file system backup** if you made one before running the scripts

## Verification Commands

After cleanup, verify no sensitive data remains:

```bash
# Check for sensitive files in current tree
find . -name "client_secret_*.json" -o -name "*token*.json" -o -name "gmail_config-final.json"

# Check Git history for sensitive patterns
git log --name-only --all | grep -i -E "(secret|token|credential|gmail_config-final)"

# Check repository size (should be smaller)
du -sh .git
```

## Best Practices Going Forward

1. **Use sample configurations**: Provide `.sample` versions of config files
2. **Document credential setup**: Clear instructions for obtaining and configuring credentials
3. **Regular audits**: Periodically check what files are being tracked
4. **Pre-commit hooks**: Consider adding hooks to prevent accidental commits of sensitive files

## Troubleshooting

### git-filter-repo Not Found

```bash
# Install via pip
pip install git-filter-repo

# Or install via package manager (Ubuntu/Debian)
sudo apt install git-filter-repo
```

### "Not a fresh clone" Error

If `git filter-repo` complains about not being a fresh clone:

```bash
git remote rm origin  # Remove remote temporarily
# Run the cleanup script
git remote add origin <your-repo-url>  # Re-add remote
```

### Large Repository Size

If the repository is still large after cleanup:

```bash
# Force garbage collection
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```
