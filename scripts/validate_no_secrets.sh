#!/bin/bash
# Pre-commit validation script that only blocks real commit risks
# This script checks for sensitive files that would actually be committed

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}🔍 Validating repository for commit risks...${NC}"
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

found_issues=false

# Check 1: Files that are staged (these would actually be committed)
echo -e "${CYAN}📋 Checking staged files...${NC}"
staged_files=$(git diff --cached --name-only 2>/dev/null || true)

if [[ -n "$staged_files" ]]; then
    staged_sensitive=false
    while IFS= read -r file; do
        [[ -z "$file" ]] && continue
        for pattern in "${SENSITIVE_PATTERNS[@]}"; do
            # Convert glob pattern to regex for matching
            regex_pattern=$(echo "$pattern" | sed 's/\*/\.\*/g' | sed 's/\?/\./g')
            if [[ "$file" =~ $regex_pattern ]]; then
                echo -e "${RED}❌ Staged sensitive file: $file${NC}"
                staged_sensitive=true
                found_issues=true
            fi
        done
    done <<< "$staged_files"

    if [[ "$staged_sensitive" == "false" ]]; then
        echo -e "${GREEN}✅ No sensitive files in staging area${NC}"
    fi
else
    echo -e "${GREEN}ℹ️  No files currently staged${NC}"
fi

# Check 2: Untracked files that are NOT gitignored (these could accidentally be added)
echo ""
echo -e "${CYAN}📁 Checking untracked files...${NC}"

# Get files that are untracked AND not ignored
untracked_unignored=$(git ls-files --others --exclude-standard 2>/dev/null || true)
if [[ -n "$untracked_unignored" ]]; then
    untracked_sensitive=false
    while IFS= read -r file; do
        [[ -z "$file" ]] && continue
        for pattern in "${SENSITIVE_PATTERNS[@]}"; do
            regex_pattern=$(echo "$pattern" | sed 's/\*/\.\*/g' | sed 's/\?/\./g')
            if [[ "$file" =~ $regex_pattern ]]; then
                echo -e "${RED}❌ Untracked sensitive file (not gitignored): $file${NC}"
                untracked_sensitive=true
                found_issues=true
            fi
        done
    done <<< "$untracked_unignored"

    if [[ "$untracked_sensitive" == "false" ]]; then
        echo -e "${GREEN}✅ No sensitive files in untracked files${NC}"
    fi
else
    echo -e "${GREEN}✅ No untracked unignored files${NC}"
fi

# Informational: Show gitignored sensitive files (but don't block)
echo ""
echo -e "${CYAN}ℹ️  Checking gitignored files (informational only)...${NC}"
for pattern in "${SENSITIVE_PATTERNS[@]}"; do
    files=$(find . -name "$pattern" -not -path "./.git/*" 2>/dev/null || true)
    if [[ -n "$files" ]]; then
        while IFS= read -r file; do
            [[ -z "$file" ]] && continue
            if git check-ignore "$file" >/dev/null 2>&1; then
                echo -e "${GREEN}✅ $file (properly gitignored)${NC}"
            fi
        done <<< "$files"
    fi
done

# Final result
echo ""
echo "=================================="
if [[ "$found_issues" == "true" ]]; then
    echo -e "${RED}❌ VALIDATION FAILED: Files that could be committed contain sensitive data!${NC}"
    echo ""
    echo -e "${YELLOW}Recommended actions:${NC}"
    echo "1. Remove or unstage sensitive files: git reset HEAD <file>"
    echo "2. Add patterns to .gitignore if needed"
    echo "3. Check files are properly ignored with: git check-ignore <file>"
    echo ""
    exit 1
else
    echo -e "${GREEN}✅ VALIDATION PASSED: Safe to commit!${NC}"
    echo "All sensitive files are either properly gitignored or not in staging area."
    exit 0
fi
