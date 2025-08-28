# ⚠️ Fix Data Type Inconsistencies in Config

These changes are to be implemented in the Dash dashboard.

- Convert `read_status` values like `"true"` (string) into proper booleans.
- Normalize `delete_after_days` to `int` or `null`, not strings.
- Add `_to_bool()` to `transforms.py` and sanitize on import/export.

**Priority**: High
**Labels**: dashboard, ux
