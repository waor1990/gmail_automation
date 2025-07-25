#!/usr/bin/env bash
set -euo pipefail

ISSUE_DIR="issues"
LOG_FILE="create_issues.log"

log(){
    echo "$(date -Iseconds) $1" | tee -a "$LOG_FILE"
}

# check if an open GitHub issue with the given title already exists
issue_exists(){
    local title="$1"
    gh issue list --state open --json title --limit 1000 |
        jq -r '.[].title' | grep -Fxq "$title"
}

if ! gh auth status >/dev/null 2>&1; then
    log "gh CLI is not authenticated. Run 'gh auth login' first."
    exit 1
fi

shopt -s nullglob
for file in "$ISSUE_DIR"/*.md "$ISSUE_DIR"/*.txt; do
    [ -f "$file" ] || continue
    # skip solved directory
    case "$file" in
        "$ISSUE_DIR"/solved/*) continue;;
    esac

    title=$(head -n1 "$file" | sed 's/^#* *//')
    body=$(tail -n +2 "$file")

    if [[ -z "$title" || -z "$body" ]]; then
        log "Skipping $file: missing title or body"
        continue
    fi

    if issue_exists "$title"; then
        log "Skipping $file: issue with title '$title' already exists"
        continue
    fi

    if gh issue create --title "$title" --body "$body"; then
        log "Created issue from $file"
    else
        log "Failed to create issue from $file"
    fi
    # avoid hitting API rate limits
    sleep 1

done
