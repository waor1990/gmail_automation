import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = [
    ("setup", []),
    ("clean_git_history", []),
    ("create_issues", []),
    ("resolve_issue", ["0"]),
    ("validate_no_secrets", []),
]


@pytest.mark.parametrize("name,args", SCRIPTS)
def test_cli_dry_run(name, args):
    repo_root = Path(__file__).resolve().parents[1]
    cmd = [sys.executable, "-m", f"scripts.{name}", "--dry-run", *args]
    subprocess.run(cmd, cwd=repo_root, check=True)
