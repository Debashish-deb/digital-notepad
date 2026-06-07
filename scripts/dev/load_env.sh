#!/usr/bin/env bash
# Export KEY=value pairs from a dotenv file without shell-sourcing raw URLs or curl blocks.
# Usage: eval "$(scripts/dev/load_env.sh /path/to/.env)"

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

path = Path(sys.argv[1])

def parse_env_file(p: Path) -> dict[str, str]:
    try:
        from dotenv import dotenv_values
        raw = dotenv_values(p)
        return {k: v for k, v in raw.items() if v is not None}
    except ImportError:
        out: dict[str, str] = {}
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            out[key.strip()] = value.strip().strip("'").strip('"')
        return out

for key, value in parse_env_file(path).items():
    if value is None:
        continue
    print(f"export {key}={shlex.quote(str(value))}")
PY
