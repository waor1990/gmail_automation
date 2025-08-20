# GitHub Configuration Directory

- Houses repository-wide configuration such as issue templates and workflows.
- Keep YAML files well formatted and validate them with `pre-commit run --files <file>`.
- Reference external actions with tagged versions rather than `@main`.
- Avoid storing secrets; use encrypted repository or organization secrets.
- When adding new workflows or templates, update documentation or README references.
