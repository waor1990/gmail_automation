# TODO_dashboard.md (August 2025 – User Experience & Visual Design Focus)

## 🎯 Guiding Goals

- Improve **user compatibility** across devices and skill levels (non-technical users included).
- Ensure **visual consistency** and intuitive interactivity throughout the dashboard.
- Enhance **clarity**, **performance**, and **editing safety**.

---

## ✅ High-Priority Improvements

### 1. 📊 Visual Label Sync Coverage (Diff Overview)

- Use charts or progress bars to visualize per-label sync status.
- Surface **% match**, total emails, and missing count with color-coded clarity.
- Add status icons to indicate labels missing entirely from the config.

### 2. ➕ “Add Missing Emails” Inline Action

- Add per-row action buttons in the Differences table to import missing emails directly.
- Preserve source casing and metadata (`read_status`, `delete_after_days`) when possible.
- Prevent duplicates by normalizing against current config.

### 3. ⚠️ Fix Data Type Inconsistencies in Config

- Convert `read_status` values like `"true"` (string) into proper booleans.
- Normalize `delete_after_days` to `int` or `null`, not strings.
- Add `_to_bool()` to `transforms.py` and sanitize on import/export.

### 4. 🚩 Highlight “Unprocessed” Senders Visually ✅

- Pending senders table shows a red indicator for new emails.
- Users can filter, sort, or export the list.
- Added banner: “Not yet processed by Gmail automation.”

### 5. 🧩 Improve Group Index Visibility and Control

- Hide `group_index` by default for simpler editing.
- Add “Advanced Mode” toggle to expose grouping for power users.
- Consider UI widgets for **splitting/merging** groups instead of raw index editing.

### 6. 🔀 Toggle Between “Flat Table” and “Grouped Tree” Views

- Grouped Tree View: Show label → group → email hierarchy.
- Flat Table View: Retain current model (single row per email).
- Preserve editing safety and internal data integrity in both modes.

## 🔶 Medium-Priority Enhancements

### 8. ✅ One-Click “Fix & Re-Analyze” Flow

- Streamline button actions: “Fix All” should trigger normalization, sorting, and re-analysis in one step.
- Reduce user confusion about multi-click workflows.

### 9. 🪟 Hoverable Diff Projections (Lightweight UI)

- Replace bulk “Projected Changes” block with hover cards or expandable previews per label.
- Goal: Let users explore projected outcomes without taking action.

### 10. 🔍 Email Collision Viewer (Cross-Label Duplicates)

- Add panel showing emails that exist in more than one label.
- Include conflict resolution UI (reassign, split, remove).

### 11. 💾 Preserve Log Viewer State

- When viewing logs, retain current selection after reload or refresh.
- Cache selected file and run in local storage or via `dcc.Store`.

### 12. 🧪 Add Import Validator for External Files

- Allow users to upload CSV or JSON files (e.g. from Gmail or Notion) and validate schema before import.
- Provide interactive feedback on format issues.

---

## 🧊 Low-Priority Suggestions (UI Polish & Advanced Features)

### 13. ⚙️ Global Defaults for New Config Entries

- Let users set default values for new entries: `read_status`, `delete_after_days`, etc.
- Offer a settings modal or persistent sidebar for these defaults.

### 14. 🧼 “Ignore Email” Rules

- Add a system for blacklisting emails from future diffs or imports.
- Store in a dedicated `IGNORED_EMAILS` config section.

### 15. 🌙 Add Theme Toggle + Accessibility Support

- Provide dark/light mode toggle with saved user preference.
- Improve tab navigation, color contrast, and focus indicators for screen readers.

### 16. 🛠️ CLI: `--import-missing LABEL` Flag

- Add CLI tool to import missing emails into a specific label from the latest diff file.
- Useful for automated or batch sync workflows.

---

## ✅ Current Health Check

- 🎉 Config passes all structure validations and produces a clean ECAQ report.
- ✅ Differences JSON generation and projection logic are stable.
- 🧩 Opportunities remain around visual experience, data hygiene, and import guidance.
