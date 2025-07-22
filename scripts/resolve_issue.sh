#!/usr/bin/env bash

# This script closes a GitHub issue using the gh CLI and moves the
# corresponding markdown file into the issues/solved directory.

set -euo pipefail

ISSUES_DIR="issues"
SOLVED_DIR="$ISSUES_DIR/solved"

mkdir -p "$SOLVED_DIR"

INPUT="$1"

if [[ -z "$INPUT" ]]; then
    echo "Usage: $0 <issue-number | issue-file>"
    exit 1
fi

# Determine issue number and associated file
if [[ "$INPUT" =~ ^[0-9]+$ ]]; then
    ISSUE_NUMBER="$INPUT"
    MATCH_FILE=$(find "$ISSUES_DIR" -maxdepth 1 -type f \( -name "${ISSUE_NUMBER}_*.md" -o -name "${ISSUE_NUMBER}_*.txt" \) | head -n 1)
else
    MATCH_FILE="$ISSUES_DIR/$INPUT"
    if [[ ! -f "$MATCH_FILE" ]]; then
        echo "❌ File not found: $MATCH_FILE"
        exit 1
    fi
    BASENAME=$(basename "$MATCH_FILE")
    ISSUE_NUMBER=$(echo "$BASENAME" | grep -oE '^[0-9]+')
fi

if [[ -z "${ISSUE_NUMBER:-}" ]]; then
    echo "❌ Could not determine issue number from input: $INPUT"
    exit 1
fi

# Close the GitHub issue
echo "🔍 Closing Issue #$ISSUE_NUMBER using GitHub CLI..."
if gh issue close "$ISSUE_NUMBER" --comment "Resolved and archived by automation."; then
    echo "✅ Issue closed"
else
    echo "❌ Failed to close issue #$ISSUE_NUMBER" >&2
    exit 1
fi

# Move the issue file if found
if [[ -f "$MATCH_FILE" ]]; then
    mv "$MATCH_FILE" "$SOLVED_DIR/"
    echo "📦 Moved issue file to $SOLVED_DIR/"
else
    echo "⚠️ Issue closed, but no matching file to move."
fi

echo "✅ Issue #$ISSUE_NUMBER resolved and archived."
