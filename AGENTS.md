# Repository Guidelines

- Use `rg` for searching; avoid `ls -R` and `grep -R`.
- Run `pre-commit run --files <changed files>` before committing.
- Execute `pytest` to ensure tests pass.
- Exclude secrets and generated artifacts from version control.
- Respect nested `AGENTS.md` instructions within subdirectories.
