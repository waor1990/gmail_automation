# Instant delete for selected emails

- Implement a feature that lets `gmail_automation` delete selected emails instantly, with an option to delete them only after they’ve been read.

**Acceptance Criteria**
- A user can select one or more emails and trigger deletion immediately.
- An option exists to defer deletion until the selected emails are read.
- Includes a confirmation step and logs each deletion (id, timestamp, actor, mode).
- Supports dry-run mode and clear error handling.
- Respects existing label- and rule-based protections (e.g., do not delete protected labels).

**Priority**: High
**Labels**: enhancement, High
