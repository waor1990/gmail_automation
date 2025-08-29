# VS Code Settings Directory

- Contains workspace configuration for VS Code.
- Only include settings beneficial to the entire team.
- Use JSON format; keep indentation at two spaces.
- Document recommended extensions in `extensions.json`.
- Avoid committing user- or machine-specific paths.

## YAML Schema Associations

- `.codex/tasks/*.yaml` are validated against the GitHub Issue Forms schema via `yaml.schemas` in `settings.json`.
- Each file also includes a `yaml-language-server` `$schema` header to aid editor tooling.
- If adding new task YAMLs, ensure they follow the same schema header and reside under `.codex/tasks/`.
- Legacy note: the prior local schema at `.vscode/schemas/codex-task.schema.json` has been removed; do not reintroduce or reference it.
