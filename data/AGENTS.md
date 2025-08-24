# Data Directory

- Store small datasets or fixtures used for development and tests.
- Exclude large files (>5MB) and sensitive information via `.gitignore`.
- Document data sources and licenses in a `README.md` when adding new files.
- Prefer CSV or JSON formats for tabular or structured data.
- Ensure deterministic data; avoid committing generated artifacts.
- Runtime state files (e.g., `sender_last_run.json`) must remain ignored via `.gitignore`.
