#!/usr/bin/env bash
# Bootstrap Docker stack for OMEIA API — health probes + optional auto-start.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

export OMEIA_REPO_ROOT="$ROOT"

# Load .env without executing bare URLs
if [[ -f "$ROOT/configs/.env" ]]; then
  # shellcheck disable=SC1091
  eval "$("$ROOT/scripts/dev/load_env.sh" "$ROOT/configs/.env")"
fi

PYTHON="${ROOT}/.venv-local/bin/python3"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="${ROOT}/.venv/bin/python3"
fi

if [[ "${DOCKER_LOCAL:-true}" == "false" || "${DOCKER_LOCAL:-true}" == "0" ]]; then
  echo "DOCKER_LOCAL=false — skipping local Docker bootstrap (remote services via configs/.env)"
  exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "WARN: docker not installed — skipping Docker bootstrap"
  exit 0
fi

if ! docker info >/dev/null 2>&1; then
  echo "WARN: Docker daemon offline — skipping bootstrap (API will use mock/fallback LLM)"
  exit 0
fi

echo "=== OMEIA Docker bootstrap ==="
"$PYTHON" - <<'PY'
import json
import os
import sys

sys.path.insert(0, os.getcwd())
from app_skeleton.api.docker_service_client import docker_services

summary = docker_services.bootstrap()
print(json.dumps(summary, indent=2))
unhealthy = [n for n, s in summary.get("services", {}).items() if not s.get("healthy")]
if unhealthy:
    print(f"WARN: unhealthy services: {', '.join(unhealthy)}", file=sys.stderr)
PY

echo "=== Docker bootstrap complete ==="
