#!/usr/bin/env bash
set -euo pipefail

ISSUE_DIR="issues"
LOG_FILE="logs/create_issues.log"

log(){
    echo "$(date -Iseconds) $1" | tee -a "$LOG_FILE"
}

# Check dependencies
check_dependencies() {
    if ! command -v gh &> /dev/null; then
        log "❌ GitHub CLI (gh) is not installed or not in PATH"
        exit 1
    fi

    if ! command -v jq &> /dev/null; then
        log "❌ jq is not installed or not in PATH"
        exit 1
    fi
}

# check if an open GitHub issue with the given title already exists
issue_exists(){
    local title="$1"
    gh issue list --state open --json title --limit 1000 |
        jq -r '.[].title' | grep -Fxq "$title"
}

# Validate issue file format
validate_issue_file() {
    local file="$1"
    local title=$(head -n1 "$file" | sed 's/^#* *//')
    local body=$(tail -n +2 "$file")

    if [[ -z "$title" ]]; then
        log "❌ File $file: missing or empty title"
        return 1
    fi

    if [[ -z "$body" ]]; then
        log "❌ File $file: missing or empty body"
        return 1
    fi

    return 0
}

# Main execution
main() {
    log "🚀 Starting issue creation process..."

    check_dependencies

    if ! gh auth status >/dev/null 2>&1; then
        log "❌ gh CLI is not authenticated. Run 'gh auth login' first."
        exit 1
    fi

    if [[ ! -d "$ISSUE_DIR" ]]; then
        log "❌ Issues directory '$ISSUE_DIR' does not exist"
        exit 1
    fi

    local processed_count=0
    local skipped_count=0
    local error_count=0


    shopt -s nullglob
    for file in "$ISSUE_DIR"/*.md "$ISSUE_DIR"/*.txt; do
        [ -f "$file" ] || continue

        # skip solved directory
        case "$file" in
            "$ISSUE_DIR"/solved/*)
                log "Skipping solved issue: $file"
                continue
                ;;
        esac

        if ! validate_issue_file "$file"; then
            ((error_count++))
            continue
        fi

        title=$(head -n1 "$file" | sed 's/^#* *//')
        body=$(tail -n +2 "$file")

        if issue_exists "$title"; then
            log "⏭️ Skipping $file: issue with title '$title' already exists"
            ((skipped_count++))
            continue
        fi

        log "📝 Creating issue from $file..."
        issue_number=$(gh issue create --title "$title" --body "$body" --json number --jq '.number' 2>/dev/null || true)

        if [[ -n "$issue_number" && "$issue_number" != "null" ]]; then
            log "✅ Created issue #$issue_number from $file"
            padded=$(printf "%03d" "$issue_number")
            base=$(basename "$file")
            rest=$(echo "$base" | sed 's/^[0-9]\+_//')
            new_file="$ISSUE_DIR/${padded}_${rest}"

            if mv "$file" "$new_file"; then
                log "📁 Renamed $file to $new_file"
                ((processed_count++))
            else
                log "❌ Failed to rename $file"
                ((error_count++))
            fi
        else
            log "❌ Failed to create issue from $file"
            ((error_count++))
        fi

        # avoid hitting API rate limits
        sleep 1
    done

    log "📊 Summary: Processed: $processed_count, Skipped: $skipped_count, Errors: $error_count"
    log "✅ Issue creation process completed"
}

main "$@"
