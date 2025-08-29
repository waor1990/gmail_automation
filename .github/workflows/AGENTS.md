# GitHub Workflows Directory

- Store GitHub Actions workflow `.yml` files.
- Use descriptive file names with hyphens, e.g. `python-tests.yml`.
- Pin actions to a specific commit or version.
- Test workflow logic locally with `act` when possible.
- Ensure new workflows run `pre-commit` and relevant tests.

## Note on Task YAMLs

- Task YAMLs under `.codex/tasks/` are not workflows. They use the Issue Forms schema for planning and are unrelated to CI/CD.
