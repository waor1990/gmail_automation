# Repository Guidelines

- Use `rg` for searching; avoid `ls -R` and `grep -R`.
- Run `pre-commit run --files <changed files>` before committing.
- Execute `pytest` to ensure tests pass.
- Exclude secrets and generated artifacts from version control.
- Respect nested `AGENTS.md` instructions within subdirectories.

## Task YAMLs (`.codex/tasks`)

- Task files under `.codex/tasks/*.yaml` use the GitHub Issue Forms schema.
- Each YAML begins with `# yaml-language-server: $schema=https://json.schemastore.org/github-issue-forms.json` for editor validation.
- Keep titles, labels, acceptance criteria, and plan sections updated when scope changes.
- To publish these as actual Issue Forms in GitHub, mirror them under `.github/ISSUE_TEMPLATE/` as needed.
