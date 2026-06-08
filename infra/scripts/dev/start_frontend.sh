#!/usr/bin/env bash
# Start Vite React frontend only (port 5173).
# Backend must be running: ./scripts/dev/start_backend.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
FRONTEND_DIR="${PROJECT_ROOT}/web"
API_URL="${VITE_API_URL:-http://127.0.0.1:8000}"

if [[ ! -d "${FRONTEND_DIR}/node_modules" ]]; then
  echo "Installing frontend dependencies..."
  (cd "${FRONTEND_DIR}" && npm ci)
fi

if [[ ! -f "${FRONTEND_DIR}/.env.local" ]]; then
  if [[ -f "${FRONTEND_DIR}/.env.local.example" ]]; then
    cp "${FRONTEND_DIR}/.env.local.example" "${FRONTEND_DIR}/.env.local"
    echo "Created ${FRONTEND_DIR}/.env.local from example."
  fi
fi

if ! curl -sf "${API_URL}/health" >/dev/null 2>&1; then
  echo "WARN: Backend not reachable at ${API_URL}/health"
  echo "      Start it first: ./scripts/dev/start_backend.sh"
fi

echo "OMEIA frontend → http://localhost:5173"
echo "  API target: ${API_URL} (dev uses Vite proxy when VITE_API_URL is set in .env.local)"

# shellcheck disable=SC1091
source "${PROJECT_ROOT}/scripts/dev/ensure_node_for_vite.sh"

cd "${FRONTEND_DIR}"
exec npm run dev -- --host 0.0.0.0 --port 5173 --strictPort
