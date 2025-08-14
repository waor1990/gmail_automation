#!/bin/bash

echo "Testing validation logic..."

# Test critical files
echo "Checking for critical files..."
CRITICAL_PATTERNS=("client_secret_*.json" "*token*.json" "gmail_config-final.json" "last_run.txt" "processed_email_ids.txt")

for pattern in "${CRITICAL_PATTERNS[@]}"; do
    files=$(find . -name "$pattern" -not -path "./.git/*" 2>/dev/null || true)
    if [[ -n "$files" ]]; then
        echo "Found files matching $pattern:"
        while IFS= read -r file; do
            if [[ -n "$file" ]]; then
                if git check-ignore "$file" >/dev/null 2>&1; then
                    echo "  ✅ $file (properly gitignored)"
                else
                    echo "  ❌ $file (NOT gitignored - would block commit)"
                fi
            fi
        done <<< "$files"
    fi
done

# Test log files
echo "Checking for log files..."
files=$(find . -name "*.log" -not -path "./.git/*" 2>/dev/null || true)
if [[ -n "$files" ]]; then
    echo "Found log files:"
    while IFS= read -r file; do
        if [[ -n "$file" ]]; then
            if git check-ignore "$file" >/dev/null 2>&1; then
                echo "  ✅ $file (properly gitignored)"
            else
                echo "  ❌ $file (NOT gitignored - would block commit)"
            fi
        fi
    done <<< "$files"
fi
