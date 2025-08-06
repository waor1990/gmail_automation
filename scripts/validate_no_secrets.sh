#!/usr/bin/env bash

# Script to validate that no sensitive files are present in the repository
# This can be run before commits to ensure sensitive data isn't accidentally included

set -euo pipefail

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}🔍 Validating repository for sensitive files...${NC}"
echo ""

# Define sensitive file patterns
SENSITIVE_PATTERNS=(
    "client_secret_*.json"
    "*token*.json" 
    "gmail_config-final.json"
    "*.log"
    "last_run.txt"
    "processed_email_ids.txt"
)

# Check working directory for sensitive files
echo -e "${CYAN}📁 Checking working directory...${NC}"
found_sensitive=false

for pattern in "${SENSITIVE_PATTERNS[@]}"; do
    files=$(find . -name "$pattern" -not -path "./.git/*" 2>/dev/null || true)
    if [[ -n "$files" ]]; then
        echo -e "${RED}❌ Found sensitive files matching pattern '$pattern':${NC}"
        echo "$files" | sed 's/^/  /'
        found_sensitive=true
    fi
done

if [[ "$found_sensitive" == "false" ]]; then
    echo -e "${GREEN}✅ No sensitive files found in working directory${NC}"
fi

# Check staged files
echo ""
echo -e "${CYAN}📋 Checking staged files...${NC}"
staged_files=$(git diff --cached --name-only 2>/dev/null || true)

if [[ -n "$staged_files" ]]; then
    staged_sensitive=false
    while IFS= read -r file; do
        for pattern in "${SENSITIVE_PATTERNS[@]}"; do
            # Convert shell glob to regex for matching
            regex_pattern=$(echo "$pattern" | sed 's/\*/\.*/g')
            if [[ "$file" =~ $regex_pattern ]]; then
                echo -e "${RED}❌ Staged file matches sensitive pattern '$pattern': $file${NC}"
                staged_sensitive=true
                found_sensitive=true
            fi
        done
    done <<< "$staged_files"
    
    if [[ "$staged_sensitive" == "false" ]]; then
        echo -e "${GREEN}✅ No sensitive files in staging area${NC}"
    fi
else
    echo -e "${YELLOW}ℹ️  No files currently staged${NC}"
fi

# Check Git history for sensitive files (basic check)
echo ""
echo -e "${CYAN}🕒 Checking recent Git history...${NC}"
history_files=$(git log --name-only --pretty=format: -10 | sort -u | grep -v "^$" || true)

if [[ -n "$history_files" ]]; then
    history_sensitive=false
    while IFS= read -r file; do
        for pattern in "${SENSITIVE_PATTERNS[@]}"; do
            regex_pattern=$(echo "$pattern" | sed 's/\*/\.*/g')
            if [[ "$file" =~ $regex_pattern ]]; then
                echo -e "${RED}❌ Recent history contains sensitive file: $file${NC}"
                history_sensitive=true
                found_sensitive=true
            fi
        done
    done <<< "$history_files"
    
    if [[ "$history_sensitive" == "false" ]]; then
        echo -e "${GREEN}✅ No sensitive files found in recent history${NC}"
    fi
fi

# Final result
echo ""
echo "=================================="
if [[ "$found_sensitive" == "true" ]]; then
    echo -e "${RED}❌ VALIDATION FAILED: Sensitive files detected!${NC}"
    echo ""
    echo -e "${YELLOW}Recommended actions:${NC}"
    echo "1. Remove sensitive files from working directory"
    echo "2. Unstage any sensitive files: git reset HEAD <file>"
    echo "3. Add patterns to .gitignore if needed"
    echo "4. If files are in history, run the cleanup script"
    echo ""
    exit 1
else
    echo -e "${GREEN}✅ VALIDATION PASSED: No sensitive files detected${NC}"
    echo ""
    echo -e "${CYAN}Repository appears clean of sensitive data.${NC}"
    exit 0
fi
