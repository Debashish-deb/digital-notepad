#!/usr/bin/env bash
# Linux desktop — ONE script: Docker + FastAPI + Vite (single terminal, Ctrl+C stops all).
#
# Prefer: ./start_linux.sh   or   ./scripts/start_linux.sh
#
# Usage:
#   ./start_linux.sh                    # daily start
#   ./start_linux.sh --setup            # first boot: models + post-stack hints
#   ./start_linux.sh --prod             # production UI on :8000 (no Vite dev server)
#   ./start_linux.sh --api-only         # Docker + API only
set -euo pipefail

# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../lib/common.sh"
ROOT="${OMEIA_REPO_ROOT:?OMEIA_REPO_ROOT unset — cd to repo root first}"
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
    --prod) export OMEIA_FRONTEND_MODE=prod ;;
    --dev) export OMEIA_FRONTEND_MODE=dev ;;
    -h|--help)
      echo "OMEIA Linux — single launcher (Docker + API + frontend)"
      echo ""
      echo "Usage: ./start_linux.sh [options]"
      echo ""
      echo "  (no flags)  Docker compose up + FastAPI :8000 + Vite :5173"
      echo "  --setup     First boot: full stack + Ollama model pulls"
      echo "  --api-only  Docker + FastAPI only"
      echo "  --prod      Build frontend; serve UI from API on :8000"
      echo "  --dev       Vite dev server on :5173 (default)"
      echo ""
      echo "Tailscale: http://\$(tailscale ip -4):5173"
      exit 0
      ;;
  esac
done

export OMEIA_FRONTEND_MODE="${OMEIA_FRONTEND_MODE:-dev}"

if [[ ! -x "$ROOT/.venv/bin/python3" && ! -x "$ROOT/.venv-local/bin/python3" ]]; then
  echo "ERROR: create venv first: python3 -m venv .venv && .venv/bin/pip install -r omeia/api/requirements.txt"
  exit 1
fi

if [[ -f "$ROOT/configs/.env" ]]; then
  # shellcheck disable=SC1091
  eval "$("$ROOT/scripts/dev/load_env.sh" "$ROOT/configs/.env")" 2>/dev/null || true
fi

export OMEIA_DEPLOYMENT_PROFILE="${OMEIA_DEPLOYMENT_PROFILE:-linux_desktop}"
export VITE_MIN_NODE="${VITE_MIN_NODE:-22.14.0}"
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
if [[ -s "$NVM_DIR/nvm.sh" ]]; then
  # shellcheck disable=SC1091
  . "$NVM_DIR/nvm.sh"
  if ! nvm use "$VITE_MIN_NODE" 2>/dev/null; then
    echo "Installing Node ${VITE_MIN_NODE} for Vite 8..."
    nvm install "$VITE_MIN_NODE"
    nvm use "$VITE_MIN_NODE"
  fi
  nvm alias default "$VITE_MIN_NODE" 2>/dev/null || true
  hash -r
  export PATH="${NVM_DIR}/versions/node/v${VITE_MIN_NODE}/bin:${PATH}"
fi
export DOCKER_LOCAL=true
export DOCKER_AUTO_START=true
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434/v1}"
export QDRANT_URL="${QDRANT_URL:-http://127.0.0.1:6333}"
export POSTGRES_CONN="${POSTGRES_CONN:-postgresql://farkki:farkki_dev_password@127.0.0.1:5432/farkki_ai}"

echo "=== OMEIA Linux desktop ==="
echo "  Profile:       $OMEIA_DEPLOYMENT_PROFILE"
echo "  Frontend mode: $OMEIA_FRONTEND_MODE"
echo "  Repo:          $ROOT"

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
  export DOCKER_COMPOSE_STARTED=true
else
  echo "--- Docker stack (quick) ---"
  COMPOSE_FILE="$ROOT/infra/compose/docker-compose.yml"
  docker compose -f "$COMPOSE_FILE" up -d
  docker compose -f "$COMPOSE_FILE" ps
  export DOCKER_COMPOSE_STARTED=true
fi

if [[ "$API_ONLY" == true ]]; then
  echo "--- FastAPI only ---"
  exec "$ROOT/scripts/dev/start_backend.sh"
fi

echo "--- Sync health (non-blocking) ---"
python3 "$ROOT/scripts/ops/check_linux_sync_health.py" || echo "WARN: sync health reported issues — see JSON above."

if [[ "$OMEIA_FRONTEND_MODE" == "prod" ]]; then
  echo "--- FastAPI + production frontend ---"
  UI_URL="http://$(hostname -I 2>/dev/null | awk '{print $1}'):8000"
else
  echo "--- FastAPI + Vite dev ---"
  UI_URL="http://$(hostname -I 2>/dev/null | awk '{print $1}'):5173"
fi

echo ""
echo "=== Full stack starting (one terminal — Ctrl+C stops API + UI) ==="
echo "  Docker:   postgres :5432, qdrant :6333, ollama :11434"
echo "  API:      http://127.0.0.1:8000/ready (readiness)  /live (liveness)"
if [[ "$OMEIA_FRONTEND_MODE" == "prod" ]]; then
  echo "  Frontend: ${UI_URL} (production build on :8000)"
else
  echo "  Frontend: ${UI_URL} (Vite dev :5173)"
  echo "  Node:     $(node -v 2>/dev/null || echo 'missing — install nvm + Node 22.14.0')"
fi
echo ""

exec "$ROOT/start.sh"
