#!/usr/bin/env bash
echo "Deprecated: use 'python -m scripts.validate_no_secrets'" >&2
python -m scripts.validate_no_secrets "$@"
