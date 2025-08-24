# AGENTS.md

## Overview

This document describes the roles and responsibilities of the automated agents and callbacks defined in the Gmail Automation Dashboard. These agents handle configuration validation, transformation, editing, and reporting tasks in a Dash-based interface.

---

## Agents and Responsibilities

### 1. `app.py`

- **Role**: Bootstraps the dashboard by preparing data, initializing the app, and loading the layout and callbacks.
- **Responsibilities**:
  - Load and parse the Gmail config.
  - Auto-generate reports (`ECAQ`, `Diff`) at startup.
  - Launch Dash app with precomputed analysis and state.
  - Surface senders with no recorded `last_run` timestamp.

### 2. `__main__.py`

- **Role**: Unified CLI entry point.
- **Responsibilities**:
  - Launch dashboard.
  - Generate reports (`ECAQ`, `Diff`) from command line.
  - Trigger data refresh via `python -m gmail_automation`.
  - Support developer tasks: linting, formatting, testing, cleanup.

### 3. `callbacks.py`

- **Role**: Core Dash callback logic.
- **Responsibilities**:
  - Handle button actions: fix-case, remove-duplicates, sort, fix-all.
  - Synchronize table edits into internal config.
  - Persist updates to disk (with optional backup).
  - Recompute live reports and differences.
  - Update UI metrics, issues, and projections.

### 4. `layout.py`

- **Role**: UI definition.
- **Responsibilities**:
  - Render main dashboard layout and tables.
  - Provide editing controls for `SENDER_TO_LABELS`.
  - Host report export buttons and table toggles.
  - Show a table of unprocessed senders for visibility.

### 5. `transforms.py`

- **Role**: Table ↔ Config data transformation.
- **Responsibilities**:
  - Convert config into flat tables for Dash UI.
  - Convert edited tables back into full JSON config format.

### 6. `analysis.py`

- **Role**: Static and semantic analysis on config data.
- **Responsibilities**:
  - Check alphabetization, case, and duplicates.
  - Validate SENDER_TO_LABELS entries for sorting, casing, and duplicates.
  - Compute diffs between current and expected label mappings.
  - Identify senders whose `last_run` remains at the default epoch.

### 7. `reports.py`

- **Role**: Report generation and diff projections.
- **Responsibilities**:
  - Write human-readable ECAQ report.
  - Write machine-readable diff JSON for use in UI and downstream systems.

### 8. `utils_io.py`

- **Role**: I/O utilities.
- **Responsibilities**:
  - Read/write JSON safely.
  - Backup config files.
  - Ensure parent directories exist before writing.

---

## Notes

- All agents are designed to work independently and can be called from the CLI or UI.
- Reports are auto-refreshed on dashboard load and optionally via a refresh button.
- The entire state is round-trippable through JSON, enabling robust state persistence.
