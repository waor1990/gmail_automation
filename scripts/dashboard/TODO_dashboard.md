# TODO_dashboard.md

## High-Priority Improvements

### ✅ 1. Consolidate Analysis Logic

- Create a helper `run_full_analysis(cfg)` to reduce duplicated code across `app.py`, `callbacks.py`, and `reports.py`.
- Extract to `analysis_helpers.py` or similar.

### ✅ 2. Handle `read_status` and `delete_after_days` More Robustly

- Normalize `read_status` to actual booleans (`True/False`) instead of string `"true"` or `""`.
- Use a utility like `_to_bool(value)` to sanitize values.
- Normalize `delete_after_days` to `Optional[int]`.

### ✅ 3. Improve `group_index` Handling

- Make `group_index` field hidden or read-only in the UI.
- Prevent user errors by not exposing it directly for editing.

### ✅ 4. Expand Diff Table UX

- The `missing_emails` column currently renders markdown using HTML.
- Replace with expandable rows, modals, or click-to-expand widgets for better user interaction.

### ✅ 5. Projected Diffs Should Actually Project

- `compute_label_differences()` doesn’t reduce diff count in projections.
- Add `case_insensitive=True` option and normalize case during comparison to get realistic projections.

### ✅ 6. Add Lazy-Loading or Server-Side Paging

- Large diffs (500+ emails) will eventually hit Dash/DOM performance limits.
- Switch to server-side pagination or lazy-load emails per label.

### ✅ 7. Improve Config Validation

- Validate that every label group has valid structure before loading.
- Highlight invalid entries or structural issues in the UI.

### ✅ 8. Add Undo/Redo History Support

- Store past configs in `dcc.Store` as a stack.
- Allow users to undo/redo up to N previous states.

### ✅ 9. Add Plugin/Hook Support

- Make it possible to sync with external label data sources (e.g., Gmail API, Google Sheets).
- Use hook mechanism or plugin registration.

## Medium-Priority

### 🔲 Highlight Unlabeled Emails in UI

- Show emails in `EMAIL_LIST` that have no label association.

### 🔲 Lint/Type Checks Pre-Commit

- Add pre-commit hooks for `black`, `flake8`, `mypy`, etc.

### 🔲 Visualize Missing Labels as a Tree Map or Bar Chart

### 🔲 Add Export Option for Filtered Diffs Only

## Low-Priority

### 🔲 Add Theme Toggle (Dark/Light)

### 🔲 Add Command Palette (Jump to actions with keyboard)
