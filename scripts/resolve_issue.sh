#!/usr/bin/env bash

# This script closes a Github issue using the gh CLI and moves the corresponding file from issues/solved/

set -e

# === Configuration ===
ISSUES_DIR="issues"
SOLVED_DIR="$ISSUES_DIR/solved"

mkdir -p "$SOLVED_DIR"

# === Input Handling ===
INPUT="$1"

if [[ -z "$INPUT" ]]; then 
    echo "Usage: $0 <issue-number | issue-file>"
    exit 1
fi

# === Determine Issue Number ===
if [[ "$INPUT" =~ ^[0-9]+$ ]]; then
    ISSUE_NUMBER="$INPUT"
    MATCH_FILE=$(find "$ISSUE_DIR" -maxdepth 1 -type f -name "${ISSUE_NUMBER}_*md" -o -name "${ISSUE_NUMBER}_*.txt" | head -n 1)
else 
    MATCH_FILE="$ISSUES_DIR/$INPUT"
    if [[ ! -f "$MATCH_FILE" ]]; then
        echo "❌ File not found: $MATCH_FILE"
        exit 1
    fi

    # Extract issue number from filename
    BASENAME=$(basename "$MATCH_FILE")
    ISSUE_NUMBER=$(echo "$BASENAME" | grep -oE '^[0-9]+')
fi

if [[ -z "$ISSUE_NUMBER" ]]; then
    echo "❌ Could not determine issue number from input: $INPUT"
    exit 1
fi

# === Close Issue via gh CL ===
echo "🔍 Closing Issue #$ISSUE_NUMBER using GitHub CLI..."
gh issue close "$ISSUE_NUMBER" --comment "Resolved and archived by automation."

# === Move File ===
if [[ -f "$MATCH_FILE" ]]; then
    mv "$MATCH_FILE" "$SOLVED_DIR/"
    echo "📦 Moved issue file to $SOLVED_DIR/"
else
    echo "⚠️ Issue closed, but no matching file to move."
fi 

echo "✅ Issue #$ISSUE_NUMBER resolved and archived."