#!/usr/bin/env bash

# Script to remove sensitive credentials from Git history
# This script uses git filter-repo to rewrite Git history and remove sensitive files

set -euo pipefail

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

echo -e "${RED}🚨 WARNING: This script will rewrite Git history!${NC}"
echo -e "${YELLOW}Make sure you have a backup of your repository before proceeding.${NC}"
echo ""

# Check if git filter-repo is available
if ! command -v git-filter-repo &> /dev/null; then
    echo -e "${RED}❌ git filter-repo is not installed.${NC}"
    echo -e "${YELLOW}Install it with: pip install git-filter-repo${NC}"
    echo -e "${YELLOW}Or download from: https://github.com/newren/git-filter-repo/${NC}"
    exit 1
fi

# Define sensitive files to remove from history
SENSITIVE_FILES=(
    "client_secret_*.json"
    "gmail-python-email.json"
    "data/gmail-python-email.json"
    "gmail_config-final.json"
    "config/gmail_config-final.json"
    "*.log"
    "logs/*.log"
    "gmail_automation.log"
    "gmail_automation_debug*.log"
    "last_run.txt"
    "data/last_run.txt"
    "processed_email_ids.txt"
    "data/processed_email_ids.txt"
)

echo -e "${CYAN}📋 Files/patterns that will be removed from Git history:${NC}"
for file in "${SENSITIVE_FILES[@]}"; do
    echo "  - $file"
done
echo ""

read -p "Do you want to proceed? This action cannot be undone! (yes/no): " confirmation
if [[ "$confirmation" != "yes" ]]; then
    echo -e "${YELLOW}❌ Operation cancelled.${NC}"
    exit 0
fi

echo -e "${GREEN}🔄 Creating backup branch...${NC}"
git branch backup-before-cleanup 2>/dev/null || true

echo -e "${GREEN}🧹 Removing sensitive files from Git history...${NC}"

# Use git filter-repo to remove the files
for pattern in "${SENSITIVE_FILES[@]}"; do
    echo -e "${YELLOW}Removing pattern: $pattern${NC}"
    if git filter-repo --path-glob "$pattern" --invert-paths --force 2>/dev/null; then
        echo -e "${GREEN}✓ Removed pattern: $pattern${NC}"
    else
        echo -e "${YELLOW}⚠️  Warning: Could not remove pattern $pattern (may not exist in history)${NC}"
    fi
done

echo -e "${GREEN}✅ Git history cleaned successfully!${NC}"
echo ""
echo -e "${CYAN}📊 Repository statistics:${NC}"

# Show repository size
REPO_SIZE=$(du -sh .git 2>/dev/null | cut -f1 || echo "Unknown")
echo -e "${WHITE}Repository .git size: $REPO_SIZE${NC}"

echo ""
echo -e "${GREEN}🔄 Next steps:${NC}"
echo -e "${WHITE}1. Verify the cleanup with: git log --name-only${NC}"
echo -e "${WHITE}2. Force push to remote (if needed): git push --force-with-lease origin main${NC}"
echo -e "${WHITE}3. Inform collaborators to re-clone the repository${NC}"
echo -e "${WHITE}4. Delete the backup branch when satisfied: git branch -D backup-before-cleanup${NC}"
