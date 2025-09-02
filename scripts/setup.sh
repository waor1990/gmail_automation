#!/usr/bin/env bash
# Ensure the virtual environment is ready and enter it.

python -m scripts.setup "$@" || exit $?

if [[ -n "$VIRTUAL_ENV" ]]; then
  echo "Already in a virtual environment: $VIRTUAL_ENV"
  exit 0
fi

if [[ ! -f .venv/bin/activate ]]; then
  echo "[error] Activation script not found. Setup may have failed."
  exit 1
fi

# shellcheck disable=SC1091
bash --login -c "source .venv/bin/activate && export PS1='(.venv) \w \$ ' && exec bash"
