# Rebase & Squash Helper

The Python helper `python -m scripts.maintenance_helper rebase-squash` rebases
the current branch onto `origin/main`, collapses all local commits into a single
commit, and runs lint plus test checks. It is fully non-interactive, making it
safe to run inside automations or CI without relying on editors, and it refuses
to proceed when the preconditions are not met.

> **Note**
> The previous shell script has been replaced with this Python helper to stay
> consistent with the rest of the maintenance tooling.

## Safety Guarantees

- Verifies Git 2.30+ and a clean working tree with no staged or untracked
  changes.
- Fast-forwards the local `main` branch to `origin/main` before rebasing.
- Creates a timestamped backup branch (`backup/rebase-<branch>-<timestamp>`)
  prior to any rewrite so you can recover instantly.
- Aborts automatically on conflicts or verification failures and restores the
  current branch from the backup.
- Declines to run on merge commits unless `--allow-merges` is provided.

## Flags

- `--dry-run` prints the planned actions and inferred commit message without
  touching the repository.
- `--no-verify` skips lint and test execution. Use only when external workflows
  cover the checks.
- `--allow-merges` permits merge commits and replays them with
  `git rebase --rebase-merges` before squashing the final tree.
- `--author "Name <email>"` overrides the author of the squashed commit.
- `--message "custom message"` overrides the generated commit message.
- `--verbose` emits detailed logging for debugging.
- `--self-check` spins up a temporary worktree and validates commit-style
  detection without network access.

## Typical Workflow

```bash
# Preview the plan
python -m scripts.maintenance_helper rebase-squash --dry-run

# Execute and run verification checks
python -m scripts.maintenance_helper rebase-squash
```

On success the script prints the new single-commit SHA and the exact
`git push --force-with-lease` command to publish the rewrite safely.

## Commit Message Detection

The helper inspects `README.md` and nearby `AGENTS.md` files to decide how to
format the squashed commit message:

- **Conventional Commits**: Derives a type from the branch prefix
  (`feature/` -> `feat`, `fix/` -> `fix`, etc.) and falls back to
  `chore(rebase): squash <branch> onto main` when ambiguous.
- **Gitmoji**: Prepends the appropriate emoji (for example ✨ for a feature or 🐛
  for a fix) when the documentation references Gitmoji usage.

Override the inference with `--message "type(scope): subject"` or customize the
author with `--author`.

## Verification and Recovery

Linting and tests run automatically after the squash using tools detected from
the repository:

1. JavaScript/TypeScript (`package.json`): `npm run lint --if-present`, then
   `npm test --if-present` (preferring pnpm or yarn when lockfiles indicate).
2. Python (`pyproject.toml`/`requirements.txt`): `ruff` or `flake8` when
   available, followed by `pytest -q` (or `python -m pytest -q`).
3. Go, Rust, or Makefile projects fall back to their canonical lint/test combos.

If any command fails, the helper restores the original branch from the backup
and exits with code `3` so you can fix issues and rerun safely.

## Force Push Guidance

Always publish the rewritten branch with `git push --force-with-lease` to avoid
overwriting teammates' work. If you need to undo the squash later, switch back
to the saved backup branch:

```bash
git switch backup/rebase-my-branch-20240101123456
# or reset the feature branch to it
git switch -C feature/my-branch backup/rebase-my-branch-20240101123456
```

Remove stale backup branches when you are confident the rewrite is final.
