# Repository Guidelines

- Run `python -m py_compile src/gmail_automation/cli.py` before committing changes to ensure the script compiles.
- Do not commit real credential or log files.
- Sample configuration files are stored in `config/config-sample/` directory.
- All config files except samples and README.md are ignored by git for security.
- Keep dependency information in `requirements.txt`.
- Add new labels or configuration entries to `gmail_config-final.json` only if necessary.
- Keep the repository free of temporary or redundant files.
- Keep `.github/copilot-instructions.md` in sync with `docs/copilot-guidelines.md`.
- Development scripts are located in `scripts/` directory.
- Binary tools are located in `tools/` directory.
