#!/usr/bin/env bash
# Linux desktop — one command: Docker stack + FastAPI + Vite (single terminal).
#
# Usage:
#   ./scripts/dev/start_linux_desktop.sh           # daily start
#   ./scripts/dev/start_linux_desktop.sh --setup   # first boot: models + post-stack hints
#   ./scripts/dev/start_linux_desktop.sh --api-only
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "ERROR: start_linux_desktop.sh is for Linux. On Mac use: ./scripts/dev/start_mac_thin_client.sh"
  exit 1
fi

API_ONLY=false
FULL_SETUP=false
for arg in "$@"; do
  case "$arg" in
    --api-only) API_ONLY=true ;;
    --setup) FULL_SETUP=true ;;
    -h|--help)
      echo "Usage: $0 [--setup] [--api-only]"
      echo "  --setup    Run full docker stack script (Ollama model pulls, token gen)"
      echo "  --api-only FastAPI only (no Vite)"
      exit 0
      ;;
  esac
done

if [[ ! -x "$ROOT/.venv/bin/python3" && ! -x "$ROOT/.venv-local/bin/python3" ]]; then
  echo "ERROR: create venv first: python3 -m venv .venv && .venv/bin/pip install -r app_skeleton/api/requirements.txt"
  exit 1
fi

if [[ -f "$ROOT/configs/.env" ]]; then
  # shellcheck disable=SC1091
  eval "$("$ROOT/scripts/dev/load_env.sh" "$ROOT/configs/.env")" 2>/dev/null || true
fi

export OMEIA_DEPLOYMENT_PROFILE="${OMEIA_DEPLOYMENT_PROFILE:-linux_desktop}"
export DOCKER_LOCAL=true
export DOCKER_AUTO_START=true
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434/v1}"
export QDRANT_URL="${QDRANT_URL:-http://127.0.0.1:6333}"
export POSTGRES_CONN="${POSTGRES_CONN:-postgresql://farkki:farkki_dev_password@127.0.0.1:5432/farkki_ai}"

echo "=== OMEIA Linux desktop ==="
echo "  Profile: $OMEIA_DEPLOYMENT_PROFILE"
echo "  Repo:    $ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker not found"
  exit 1
fi

if [[ -f "$ROOT/configs/.env" && ! -f "$ROOT/.env" ]]; then
  ln -sf configs/.env "$ROOT/.env"
  echo "  Linked .env -> configs/.env"
fi

if [[ "$FULL_SETUP" == true ]]; then
  echo "--- Full Docker setup (models, Ollama smoke tests) ---"
  "$ROOT/scripts/docker/start_linux_docker_stack.sh"
else
  echo "--- Docker stack (quick) ---"
  docker compose up -d
  docker compose ps
fi

if [[ "$API_ONLY" == true ]]; then
  echo "--- FastAPI only ---"
  exec "$ROOT/scripts/dev/start_backend.sh"
fi

echo "--- FastAPI + Vite ---"
exec "$ROOT/start.sh"
