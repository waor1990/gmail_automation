# Enhance IGNORED_EMAILS rules and behaviors

- Enhance the dedicated `IGNORED_EMAILS` section to support richer rule definitions and behaviors within `gmail_automation` (e.g., different actions or processing rules based on ignore criteria).

**Acceptance Criteria**
- Rules can specify behaviors such as: skip analysis, skip import, mark as read, apply labels, archive, and `delete_after_days` (including `0` for immediate delete).
- Updated config schema + validation for `IGNORED_EMAILS` rules with clear, documented fields.
- The IGNORED_EMAILS management UI supports creating, editing, and removing these richer rules.
- Processing pipeline respects the rules deterministically and logs actions taken per email.
- Backward-compatible migration for any existing simple rules.

**Priority**: Medium
**Labels**: enhancement, Medium
