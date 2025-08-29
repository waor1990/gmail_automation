# Documentation Directory

- Maintain project documentation in Markdown.
- Use `#`-style headings and wrap lines at ~80 characters.
- Update docs alongside code changes; link to relevant modules or scripts.
- Use relative links for cross-references within the repository.
- Run `pre-commit run --files <doc>` to check formatting.

## Task Documentation Source

- Feature and maintenance tasks are modeled as YAML forms under `.codex/tasks/`.
- These YAMLs follow the GitHub Issue Forms schema and act as the canonical description for scope, acceptance criteria, and verification steps.
- Keep user-facing docs in sync with corresponding task YAMLs when scope or acceptance criteria change.
