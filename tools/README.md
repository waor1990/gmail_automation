# Tools Directory

This directory contains binary tools and executables used by the project.

## Contents

- `jq.exe` - JSON processor used by shell scripts for parsing GitHub API responses
  - Used by `scripts/create_issues.sh` for processing issue data
  - Windows binary included for convenience

## Usage

The tools in this directory are automatically added to PATH by scripts that need them.
