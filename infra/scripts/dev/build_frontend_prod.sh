#!/usr/bin/env bash
# Build Vite frontend for production (same-origin API when served from FastAPI :8000).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
FRONTEND="$ROOT/web"

if [[ -f "$ROOT/configs/.env" ]]; then
  # shellcheck disable=SC1091
  eval "$("$ROOT/scripts/dev/load_env.sh" "$ROOT/configs/.env")" 2>/dev/null || true
fi

# Same-origin API when UI is co-hosted on :8000
export VITE_API_URL="${VITE_API_URL:-}"

# shellcheck disable=SC1091
source "$ROOT/scripts/dev/ensure_node_for_vite.sh"

cd "$FRONTEND"
if [[ ! -d node_modules ]]; then
  npm ci
fi
npm run build
echo "Frontend build ready: $FRONTEND/dist"
