# GitHub Configuration Directory

- Houses repository-wide configuration such as issue templates and workflows.
- Keep YAML files well formatted and validate them with `pre-commit run --files <file>`.
- Reference external actions with tagged versions rather than `@main`.
- Avoid storing secrets; use encrypted repository or organization secrets.
- When adding new workflows or templates, update documentation or README references.

## Issue Forms vs Local Task YAMLs

- This repository maintains structured task definitions under `.codex/tasks/` using the GitHub Issue Forms schema.
- These files are local authoring artifacts and are not automatically published as GitHub Issue Templates.
- To expose a task as an Issue Form in GitHub, place an equivalent YAML under `.github/ISSUE_TEMPLATE/`.
