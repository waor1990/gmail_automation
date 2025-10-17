#!/usr/bin/env python3
"""Maintenance helper CLI with rebase-and-squash support."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

from scripts import maintenance

LOG = logging.getLogger("maintenance_helper")


EXIT_OK = 0
EXIT_PRECONDITION = 2
EXIT_VERIFY_FAILED = 3
EXIT_GIT_FAILED = 4


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


class MaintenanceError(RuntimeError):
    def __init__(self, message: str, code: int) -> None:
        super().__init__(message)
        self.code = code


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="[%(levelname)s] %(message)s")


def run_command(
    args: Sequence[str],
    *,
    cwd: Path,
    check: bool = True,
    capture_output: bool = False,
    env: dict[str, str] | None = None,
) -> CommandResult:
    LOG.debug("Running command: %s", " ".join(args))
    completed = subprocess.run(
        list(args),
        cwd=str(cwd),
        check=False,
        text=True,
        capture_output=capture_output,
        env=env,
    )
    if check and completed.returncode != 0:
        stdout = completed.stdout.strip() if completed.stdout else ""
        stderr = completed.stderr.strip() if completed.stderr else ""
        message = stderr or stdout or "command failed"
        raise MaintenanceError(message, EXIT_GIT_FAILED)
    return CommandResult(
        completed.returncode,
        completed.stdout or "",
        completed.stderr or "",
    )


def get_repo_root() -> Path:
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(completed.stdout.strip())


def compare_versions(version: str, minimum: str) -> bool:
    def parse(v: str) -> tuple[int, int, int]:
        parts = v.split(".")
        return (
            int(parts[0]) if len(parts) > 0 else 0,
            int(parts[1]) if len(parts) > 1 else 0,
            int(parts[2]) if len(parts) > 2 else 0,
        )

    v_major, v_minor, v_patch = parse(version)
    m_major, m_minor, m_patch = parse(minimum)
    if v_major != m_major:
        return v_major > m_major
    if v_minor != m_minor:
        return v_minor > m_minor
    return v_patch >= m_patch


def ensure_git_version(repo_root: Path) -> None:
    completed = run_command(
        ["git", "version"],
        cwd=repo_root,
        capture_output=True,
    )
    match = re.search(r"(\d+\.\d+\.\d+)", completed.stdout)
    if not match:
        raise MaintenanceError("Unable to parse git version", EXIT_PRECONDITION)
    version = match.group(1)
    if not compare_versions(version, "2.30.0"):
        raise MaintenanceError(
            f"git >= 2.30.0 required (found {version})", EXIT_PRECONDITION
        )


def ensure_clean_worktree(repo_root: Path) -> None:
    result = run_command(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        capture_output=True,
    )
    if result.stdout.strip():
        raise MaintenanceError(
            "Working tree must be clean (no staged or untracked changes)",
            EXIT_PRECONDITION,
        )


def detect_commit_style(repo_root: Path) -> str:
    content = ""
    for candidate in (
        repo_root / "README.md",
        repo_root / "AGENTS.md",
        repo_root / "docs" / "AGENTS.md",
    ):
        if candidate.exists():
            content += candidate.read_text(encoding="utf-8", errors="ignore").lower()
    if "gitmoji" in content:
        return "gitmoji"
    if "conventional commits" in content or "semantic-release" in content:
        return "conventional"
    return "conventional"


def trim_scope(scope: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", scope.lower())


def infer_type_scope(branch: str) -> tuple[str | None, str | None]:
    lower = branch.lower()
    branch_type: str | None = None
    scope: str | None = None
    mapping = {
        ("feat/", "feature/"): "feat",
        ("fix/", "bugfix/", "hotfix/"): "fix",
        ("docs/",): "docs",
        ("chore/", "maintenance/", "maint/"): "chore",
        ("refactor/",): "refactor",
        ("test/", "tests/"): "test",
        ("ci/",): "ci",
        ("build/",): "build",
        ("perf/",): "perf",
    }
    for prefixes, type_name in mapping.items():
        if any(lower.startswith(prefix) for prefix in prefixes):
            branch_type = type_name
            break

    remainder = branch
    if "/" in branch:
        remainder = branch.split("/", 1)[1]
    if branch_type and remainder.startswith(f"{branch_type}/"):
        remainder = remainder[len(branch_type) + 1 :]
    elif branch_type and remainder.startswith(f"{branch_type}-"):
        remainder = remainder[len(branch_type) + 1 :]

    remainder = remainder.replace("/", "-")
    scope_candidate = remainder.split("-", 1)[0].lower()
    if scope_candidate and scope_candidate != lower:
        scope = trim_scope(scope_candidate) or None
    return branch_type, scope


def infer_commit_message(repo_root: Path, branch: str) -> str:
    style = detect_commit_style(repo_root)
    branch_type, scope = infer_type_scope(branch)
    subject = f"squash {branch} onto main"
    if style == "gitmoji":
        emoji_map = {
            "feat": "✨",
            "fix": "🐛",
            "docs": "📝",
            "test": "✅",
            "refactor": "♻️",
            "perf": "⚡️",
            "build": "🏗️",
            "ci": "👷",
        }
        emoji = emoji_map.get(branch_type or "", "🧹")
        return f"{emoji} {subject}"

    final_type = branch_type or "chore"
    final_scope = scope or "rebase"
    return f"{final_type}({final_scope}): {subject}"


def update_local_main(repo_root: Path) -> None:
    LOG.info("Fetching origin/main")
    run_command(["git", "fetch", "origin", "main"], cwd=repo_root)
    result = run_command(
        ["git", "show-ref", "--verify", "--quiet", "refs/heads/main"],
        cwd=repo_root,
        check=False,
    )
    if result.returncode != 0:
        return
    ancestor = run_command(
        [
            "git",
            "merge-base",
            "--is-ancestor",
            "refs/heads/main",
            "refs/remotes/origin/main",
        ],
        cwd=repo_root,
        check=False,
    )
    if ancestor.returncode == 0:
        LOG.info("Fast-forwarding local main to match origin/main")
        run_command(
            ["git", "update-ref", "refs/heads/main", "refs/remotes/origin/main"],
            cwd=repo_root,
        )
    else:
        LOG.warning("Local main has diverged; not fast-forwarding automatically")


def create_backup_branch(repo_root: Path, name: str) -> None:
    run_command(["git", "branch", name, "HEAD"], cwd=repo_root)


def restore_from_backup(
    repo_root: Path, current_branch: str, backup_branch: str
) -> None:
    LOG.warning("Restoring branch %s from backup %s", current_branch, backup_branch)
    run_command(
        ["git", "switch", "-C", current_branch, backup_branch],
        cwd=repo_root,
    )


def parse_author(author: str) -> tuple[str, str]:
    match = re.match(r"^(.*?)<(.+?)>$", author.strip())
    if not match:
        raise MaintenanceError(
            'Author must be in the form "Name <email>"', EXIT_PRECONDITION
        )
    name = match.group(1).strip()
    email = match.group(2).strip()
    if not name or not email:
        raise MaintenanceError(
            "Author name and email must be non-empty", EXIT_PRECONDITION
        )
    return name, email


def has_package_script(package_json: Path, script_name: str) -> bool:
    try:
        with package_json.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return False
    scripts = data.get("scripts")
    return isinstance(scripts, dict) and script_name in scripts


def has_pyproject_tool(pyproject: Path, key: str) -> bool:
    if not pyproject.exists():
        return False
    try:
        import tomllib  # Python 3.11+
    except ModuleNotFoundError:  # pragma: no cover - safety fallback
        return False
    try:
        with pyproject.open("rb") as fh:
            data = tomllib.load(fh)
    except OSError:
        return False
    except Exception:
        return False
    tool = data.get("tool")
    if not isinstance(tool, dict):
        return False
    return key in tool


def run_verification(repo_root: Path, skip: bool) -> bool:
    if skip:
        LOG.info("Skipping verification (requested)")
        return True

    commands: list[list[str]] = []
    package_json = repo_root / "package.json"
    pyproject = repo_root / "pyproject.toml"
    requirements = repo_root / "requirements.txt"

    if package_json.exists():
        if (repo_root / "pnpm-lock.yaml").exists() and shutil.which("pnpm"):
            if has_package_script(package_json, "lint"):
                commands.append(["pnpm", "run", "lint", "--if-present"])
            if has_package_script(package_json, "test"):
                commands.append(["pnpm", "run", "test", "--if-present"])
        elif (repo_root / "yarn.lock").exists() and shutil.which("yarn"):
            if has_package_script(package_json, "lint"):
                commands.append(["yarn", "run", "lint"])
            if has_package_script(package_json, "test"):
                commands.append(["yarn", "test"])
        elif shutil.which("npm"):
            if has_package_script(package_json, "lint"):
                commands.append(["npm", "run", "lint", "--if-present"])
            if has_package_script(package_json, "test"):
                commands.append(["npm", "test", "--if-present"])
    elif pyproject.exists() or requirements.exists():
        if shutil.which("ruff"):
            commands.append(["ruff", "check", "."])
        elif has_pyproject_tool(pyproject, "ruff"):
            commands.append([sys.executable, "-m", "ruff", "check", "."])
        elif shutil.which("flake8"):
            commands.append(["flake8"])
        elif has_pyproject_tool(pyproject, "flake8"):
            commands.append([sys.executable, "-m", "flake8"])

        if shutil.which("pytest"):
            commands.append(["pytest", "-q"])
        else:
            commands.append([sys.executable, "-m", "pytest", "-q"])
    elif (repo_root / "go.mod").exists():
        if shutil.which("go"):
            commands.append(["go", "vet", "./..."])
            commands.append(["go", "test", "./..."])
    elif (repo_root / "Cargo.toml").exists():
        if shutil.which("cargo"):
            fmt_cmd = ["cargo", "fmt", "--", "--check"]
            if (
                shutil.which("cargo-fmt")
                or run_command(
                    ["cargo", "fmt", "--version"], cwd=repo_root, check=False
                ).returncode
                == 0
            ):
                commands.append(fmt_cmd)
            clippy_cmd = ["cargo", "clippy", "-D", "warnings"]
            if (
                shutil.which("cargo-clippy")
                or run_command(
                    ["cargo", "clippy", "--version"], cwd=repo_root, check=False
                ).returncode
                == 0
            ):
                commands.append(clippy_cmd)
            commands.append(["cargo", "test"])
    elif (repo_root / "Makefile").exists() and shutil.which("make"):
        if (
            run_command(["make", "-n", "lint"], cwd=repo_root, check=False).returncode
            == 0
        ):
            commands.append(["make", "lint"])
        if (
            run_command(["make", "-n", "test"], cwd=repo_root, check=False).returncode
            == 0
        ):
            commands.append(["make", "test"])

    if not commands:
        LOG.info("No verification commands detected")
        return True

    for command in commands:
        LOG.info("Running verification: %s", " ".join(command))
        result = subprocess.run(command, cwd=str(repo_root))
        if result.returncode != 0:
            LOG.error("Verification command failed: %s", " ".join(command))
            return False
    return True


def perform_self_check(repo_root: Path) -> int:
    tmpdir = Path(tempfile.mkdtemp(prefix="maintenance-helper-selfcheck-"))
    try:
        LOG.info("Creating temporary worktree at %s", tmpdir)
        run_command(
            ["git", "worktree", "add", "--detach", str(tmpdir), "HEAD"], cwd=repo_root
        )
        completed = run_command(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=tmpdir,
            capture_output=True,
        )
        branch = completed.stdout.strip()
        if branch == "HEAD":
            branch = "self-check/branch"
        message = infer_commit_message(repo_root, branch)
        LOG.info("Generated commit message: %s", message)
    finally:
        run_command(
            ["git", "worktree", "remove", "--force", str(tmpdir)],
            cwd=repo_root,
            check=False,
        )
        shutil.rmtree(tmpdir, ignore_errors=True)
    LOG.info("Self-check complete")
    return EXIT_OK


def execute_rebase_squash(args: argparse.Namespace) -> int:
    configure_logging(args.verbose)
    repo_root = get_repo_root()

    if args.self_check:
        return perform_self_check(repo_root)

    ensure_git_version(repo_root)
    ensure_clean_worktree(repo_root)

    completed = run_command(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_root,
        capture_output=True,
    )
    branch = completed.stdout.strip()
    if branch == "HEAD":
        raise MaintenanceError("Detached HEAD is not supported", EXIT_PRECONDITION)
    if branch == "main":
        raise MaintenanceError("Already on main; nothing to rebase", EXIT_PRECONDITION)

    message = args.message or infer_commit_message(repo_root, branch)
    LOG.info("Computed commit message: %s", message)

    if args.dry_run:
        LOG.info("--dry-run: no changes will be made")
        LOG.info("Planned actions:")
        plan = [
            "Verify clean working tree",
            "Fetch and fast-forward origin/main",
            "Create backup branch",
            f"Rebase {branch} onto origin/main",
            "Collapse commits into a single commit",
        ]
        if args.no_verify:
            plan.append("Verification skipped (--no-verify)")
        else:
            plan.append("Run verification commands")
        for item in plan:
            LOG.info("  - %s", item)
        LOG.info("Proposed commit message: %s", message)
        return EXIT_OK

    update_local_main(repo_root)

    fork_point = run_command(
        ["git", "merge-base", "HEAD", "origin/main"],
        cwd=repo_root,
        capture_output=True,
    ).stdout.strip()
    if not fork_point:
        raise MaintenanceError(
            "Unable to determine merge base with origin/main", EXIT_GIT_FAILED
        )

    commit_count = int(
        run_command(
            ["git", "rev-list", "--count", f"{fork_point}..HEAD"],
            cwd=repo_root,
            capture_output=True,
        ).stdout.strip()
    )
    if commit_count == 0:
        raise MaintenanceError(
            "No commits to rebase; branch already matches origin/main",
            EXIT_PRECONDITION,
        )
    LOG.info("Found %d commits to rewrite", commit_count)

    merge_commits = run_command(
        ["git", "rev-list", "--merges", f"{fork_point}..HEAD"],
        cwd=repo_root,
        capture_output=True,
    ).stdout.strip()
    if merge_commits and not args.allow_merges:
        raise MaintenanceError(
            "Merge commits detected; rerun with --allow-merges to proceed",
            EXIT_PRECONDITION,
        )

    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    backup_branch = f"backup/rebase-{branch.replace('/', '-')}-{timestamp}"
    LOG.info("Creating backup branch %s", backup_branch)
    create_backup_branch(repo_root, backup_branch)

    latest_author_name = run_command(
        ["git", "log", "-1", "--pretty=format:%an", backup_branch],
        cwd=repo_root,
        capture_output=True,
        check=False,
    ).stdout.strip()
    latest_author_email = run_command(
        ["git", "log", "-1", "--pretty=format:%ae", backup_branch],
        cwd=repo_root,
        capture_output=True,
        check=False,
    ).stdout.strip()

    rebase_started = False
    try:
        rebase_started = True
        LOG.info("Rebasing %s onto origin/main", branch)
        if args.allow_merges:
            run_command(
                ["git", "rebase", "--rebase-merges", "origin/main"], cwd=repo_root
            )
        else:
            run_command(["git", "rebase", "origin/main"], cwd=repo_root)
        rebase_started = False
    except MaintenanceError as exc:
        if rebase_started:
            run_command(["git", "rebase", "--abort"], cwd=repo_root, check=False)
            restore_from_backup(repo_root, branch, backup_branch)
        raise MaintenanceError(f"Rebase failed: {exc}", EXIT_GIT_FAILED) from exc

    LOG.info("Squashing rebased commits into a single commit")
    run_command(["git", "reset", "--soft", "origin/main"], cwd=repo_root)
    diff_status = run_command(
        ["git", "diff", "--cached", "--quiet"],
        cwd=repo_root,
        check=False,
    )
    if diff_status.returncode == 0:
        restore_from_backup(repo_root, branch, backup_branch)
        raise MaintenanceError(
            "No staged changes after squash; branch restored", EXIT_PRECONDITION
        )

    env = os.environ.copy()
    if args.author:
        name, email = parse_author(args.author)
        env["GIT_AUTHOR_NAME"] = name
        env["GIT_AUTHOR_EMAIL"] = email
    elif latest_author_name and latest_author_email:
        env["GIT_AUTHOR_NAME"] = latest_author_name
        env["GIT_AUTHOR_EMAIL"] = latest_author_email

    run_command(["git", "commit", "-m", message], cwd=repo_root, env=env)

    if not run_verification(repo_root, args.no_verify):
        restore_from_backup(repo_root, branch, backup_branch)
        raise MaintenanceError(
            "Verification failed; branch restored to pre-rebase state",
            EXIT_VERIFY_FAILED,
        )

    new_sha = run_command(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        capture_output=True,
    ).stdout.strip()
    LOG.info("Rebase and squash completed. New commit: %s", new_sha)
    LOG.info("Force-push with: git push --force-with-lease origin %s", branch)
    return EXIT_OK


def maintenance_args(
    venv: str,
    dry_run: bool,
    log_level: str,
    extras: Iterable[str],
) -> list[str]:
    args: list[str] = ["--venv", venv]
    if dry_run:
        args.append("--dry-run")
    if log_level:
        args.extend(["--log-level", log_level])
    args.extend(extras)
    return args


def run_cleanup(args: argparse.Namespace) -> int:
    return maintenance.main(
        maintenance_args(args.venv, args.dry_run, args.log_level, ["--all"])
    )


def run_release(args: argparse.Namespace) -> int:
    extras = [
        "--validate-secrets",
        "--install-hooks",
        "--autoupdate-hooks",
        "--run-hooks",
        "--tests",
        "--check-compat",
    ]
    return maintenance.main(
        maintenance_args(args.venv, args.dry_run, args.log_level, extras)
    )


def run_verify(args: argparse.Namespace) -> int:
    extras = ["--run-hooks", "--tests", "--check-compat"]
    return maintenance.main(
        maintenance_args(args.venv, args.dry_run, args.log_level, extras)
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Maintenance helper utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument(
            "--venv", default=".venv", help="virtual environment path"
        )
        subparser.add_argument(
            "--dry-run", action="store_true", help="show actions without executing"
        )
        subparser.add_argument(
            "--log-level", default="INFO", help="log level for maintenance module"
        )

    cleanup_parser = subparsers.add_parser(
        "cleanup", help="Run standard cleanup workflow (validate, hooks, tests)"
    )
    add_common(cleanup_parser)

    release_parser = subparsers.add_parser(
        "release",
        help=(
            "Prepare release by running validation, hooks, tests, and "
            "compatibility checks"
        ),
    )
    add_common(release_parser)

    verify_parser = subparsers.add_parser(
        "verify", help="Run lint/test verification quick pass"
    )
    add_common(verify_parser)

    rebase_parser = subparsers.add_parser(
        "rebase-squash",
        help="Rebase current branch onto origin/main and squash commits",
    )
    rebase_parser.add_argument(
        "--dry-run", action="store_true", help="show actions without executing"
    )
    rebase_parser.add_argument(
        "--no-verify", action="store_true", help="skip lint/tests"
    )
    rebase_parser.add_argument(
        "--allow-merges",
        action="store_true",
        help="allow branches containing merge commits",
    )
    rebase_parser.add_argument(
        "--author", help='override author, format "Name <email>"'
    )
    rebase_parser.add_argument("--message", help="override generated commit message")
    rebase_parser.add_argument(
        "--verbose", action="store_true", help="enable verbose logging"
    )
    rebase_parser.add_argument(
        "--self-check",
        action="store_true",
        help="simulate commit message detection using a temporary worktree",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "cleanup":
            return run_cleanup(args)
        if args.command == "release":
            return run_release(args)
        if args.command == "verify":
            return run_verify(args)
        if args.command == "rebase-squash":
            return execute_rebase_squash(args)
        raise MaintenanceError(f"Unknown command: {args.command}", EXIT_PRECONDITION)
    except MaintenanceError as exc:
        configure_logging(getattr(args, "verbose", False))
        LOG.error("%s", exc)
        return exc.code


if __name__ == "__main__":
    raise SystemExit(main())
