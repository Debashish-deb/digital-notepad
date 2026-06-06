#!/usr/bin/env bash
# Export KEY=value pairs from a dotenv file without shell-sourcing raw URLs or curl blocks.
# Usage: eval "$(scripts/load_env.sh /path/to/.env)"

set -euo pipefail

ENV_FILE="${1:-}"
if [ -z "$ENV_FILE" ] || [ ! -f "$ENV_FILE" ]; then
  exit 0
fi

_PY="python3"
for candidate in "${OMEIA_REPO_ROOT:-}/.venv-local/bin/python" "${OMEIA_REPO_ROOT:-}/.venv/bin/python"; do
  if [ -x "$candidate" ]; then
    _PY="$candidate"
    break
  fi
done

"$_PY" - "$ENV_FILE" <<'PY'
import shlex
import sys
from pathlib import Path

try:
    from dotenv import dotenv_values
except ImportError:
    sys.stderr.write("load_env.sh: python-dotenv is required\n")
    sys.exit(1)

path = Path(sys.argv[1])
for key, value in dotenv_values(path).items():
    if value is None:
        continue
    print(f"export {key}={shlex.quote(str(value))}")
PY
