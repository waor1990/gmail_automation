#!/usr/bin/env bash

# This script closes a GitHub issue using the gh CLI and moves the
# corresponding markdown file into the issues/solved directory.

set -euo pipefail

ISSUES_DIR="issues"
SOLVED_DIR="$ISSUES_DIR/solved"

# Create solved directory with cross-platform compatibility
mkdir -p "$SOLVED_DIR"

INPUT="$1"

if [[ -z "$INPUT" ]]; then
    echo "Usage: $0 <issue-number | issue-file>"
    echo "Examples:"
    echo "  $0 123"
    echo "  $0 001_some_issue.md"
    exit 1
fi

# Determine issue number and associated file
if [[ "$INPUT" =~ ^[0-9]+$ ]]; then
    ISSUE_NUMBER="$INPUT"
    PADDED_NUM=$(printf "%03d" "$ISSUE_NUMBER")
    # Improved file matching with better error handling
    MATCH_FILE=$(find "$ISSUES_DIR" -maxdepth 1 -type f \( -name "${PADDED_NUM}_*.md" -o -name "${PADDED_NUM}_*.txt" -o -name "${ISSUE_NUMBER}_*.md" -o -name "${ISSUE_NUMBER}_*.txt" \) 2>/dev/null | head -n 1)
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

# Verify gh CLI is available and authenticated
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) is not installed or not in PATH"
    exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
    echo "❌ GitHub CLI is not authenticated. Run 'gh auth login' first."
    exit 1
fi

# Close the GitHub issue
echo "🔍 Closing Issue #$ISSUE_NUMBER using GitHub CLI..."
if gh issue close "$ISSUE_NUMBER" --comment "Resolved and archived by automation."; then
    echo "✅ Issue #$ISSUE_NUMBER closed successfully"
else
    echo "❌ Failed to close issue #$ISSUE_NUMBER" >&2
    exit 1
fi

# Move the issue file if found
if [[ -f "$MATCH_FILE" ]]; then
    if mv "$MATCH_FILE" "$SOLVED_DIR/"; then
        echo "📦 Moved issue file to $SOLVED_DIR/"
    else
        echo "❌ Failed to move file $MATCH_FILE" >&2
        exit 1
    fi
else
    echo "⚠️ Issue closed, but no matching file to move."
fi

echo "✅ Issue #$ISSUE_NUMBER resolved and archived."
