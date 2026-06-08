#!/usr/bin/env bash
# macOS thin client — one command: FastAPI + Vite on Mac, LLM/Qdrant on Linux via Tailscale.
#
# Prerequisite: Linux Docker stack running (scripts/dev/start_linux_desktop.sh on workstation).
#
# Usage:
#   ./scripts/dev/start_mac_thin_client.sh
#   ./scripts/dev/start_mac_thin_client.sh --api-only
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

API_ONLY=false
for arg in "$@"; do
  case "$arg" in
    --api-only) API_ONLY=true ;;
    -h|--help)
      echo "Usage: $0 [--api-only]"
      echo "  --api-only  FastAPI only (no Vite)"
      exit 0
      ;;
  esac
done

# shellcheck source=/dev/null
source "$ROOT/scripts/network/portable_apply_env.sh"

if [[ ! -x "$ROOT/.venv/bin/python3" && ! -x "$ROOT/.venv-local/bin/python3" ]]; then
  echo "ERROR: create venv first: python3 -m venv .venv && pip install -r app_skeleton/api/requirements.txt"
  exit 1
fi

FRONTEND_DIR="$ROOT/app_skeleton/ui/react_frontend"
if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  echo "--- npm install (first run) ---"
  (cd "$FRONTEND_DIR" && npm install)
fi

echo "=== OMEIA Mac thin client ==="
echo "  Profile: ${OMEIA_DEPLOYMENT_PROFILE:-mac_thin_client}"
echo "  Repo:    $ROOT"
echo "  Docker:  remote (DOCKER_LOCAL=false)"

if [[ -z "${TAILSCALE_LINUX_IP:-}" ]]; then
  echo ""
  echo "WARN: TAILSCALE_LINUX_IP is not set in configs/.env"
  echo "      Add: TAILSCALE_LINUX_IP=<linux tailscale ip -4>"
  echo "      Linux must run: ./scripts/dev/start_linux_desktop.sh"
  echo ""
else
  echo "  Linux:   $TAILSCALE_LINUX_IP (Ollama + Qdrant)"
  if command -v curl >/dev/null 2>&1; then
    if ! curl -sf --max-time 3 "http://${TAILSCALE_LINUX_IP}:6333/collections" >/dev/null 2>&1; then
      echo "WARN: Qdrant not reachable at ${TAILSCALE_LINUX_IP}:6333 — start Linux stack first"
    fi
  fi
fi

if [[ "$API_ONLY" == true ]]; then
  echo "--- FastAPI only ---"
  exec "$ROOT/scripts/dev/start_backend.sh"
fi

echo "--- FastAPI + Vite ---"
exec "$ROOT/start.sh"
