# Git Aliases: Release Squash on `main` (with Dry Run)

These aliases help you squash commits on `main` into a single **release** commit.
Intended for **solo repos** (rewriting history is OK). For team/shared repos, do
**not** use on published branches.

## Install

These were added to your global config: `%USERPROFILE%\\.gitconfig` under
`[alias]`. If re-adding manually, avoid duplicate keys.

## Base Selection

- If you provide a `BASE`, we squash commits **since `BASE`**.
- If you **omit** `BASE`, we try the **last annotated tag**
  (`git describe --tags --abbrev=0`).
- If no tags exist, we use the **root commit** of the repo.

## Dry Run First (recommended)

```bash
git release-squash-dry [BASE]   # e.g., v1.2.3 or a commit hash
```

Shows the commits that would be squashed and a diffstat.

## Apply (do the squash)

```bash
git checkout main
git main-ffonly                 # optional: safe update if tracking a remote
git release-squash-apply [BASE]
git push-lease origin main      # if you want to update your remote
```

### What happens

1. Verifies you are on `main` and the working tree is clean.
2. Determines `BASE` (arg → last tag → root commit).
3. Creates a backup branch: `backup/main-YYYYmmdd-HHMMSS`.
4. Soft-resets to `BASE` and creates a single commit:

   ```bash
   release: squash commits since <BASE>
   ```

### Recovering

If you need to undo, simply:

```bash
git checkout main
git reset --hard backup/main-<timestamp>
git push-lease origin main   # if you had force-pushed
```

## Warnings

- Rewriting `main` rewrites history. Only do this on **solo repos** (this one
  qualifies).
- If `main` is published and others have pulled it, coordinate or avoid
  rewriting.

## Example (this repo)

From Git Bash in:

```bash
C:\\Users\\Wesley Allegre\\source\\repos\\GitHub\\gmail_automation
```

Dry run:

```bash
git release-squash-dry
```

Apply:

```bash
git checkout main
git release-squash-apply v0.9.0
git push-lease origin main
```

## Verify Aliases

```bash
git config --global --get-regexp '^alias\.'
```

Happy releasing!
