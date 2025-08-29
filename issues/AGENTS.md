# Issues Directory Guidelines

These changes are to be implemented in the Dash dashboard.


- Store open issues as markdown files named with a numeric prefix, e.g. `001_issue_name.md`.
- Move resolved issues to the `solved/` subfolder.
- Keep this directory free of credential or log files.
- Ensure issue files only exist here (or in `solved/` for completed issues) to avoid duplication elsewhere in the repository.
- Follow repository guidelines from the project root when editing or adding issues.

## Relationship to `.codex/tasks`

- Structured task specs live in `.codex/tasks/` as GitHub Issue Form YAMLs.
- When opening a public-facing issue, copy relevant sections (summary, acceptance criteria, references) from the corresponding task YAML to avoid drift.
