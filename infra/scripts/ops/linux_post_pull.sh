#!/usr/bin/env bash
# Post-pull maintenance on the Linux workstation (deps, env reminder, readiness).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "$REPO_ROOT"

echo "=== OMEIA Linux post-pull ==="

REQ="${REPO_ROOT}/omeia/api/requirements.txt"
if [[ -f "$REQ" ]]; then
  echo "Installing Python dependencies..."
  python3 -m pip install -r "$REQ" -q
else
  echo "WARN: requirements not found at $REQ"
fi

ENV_FILE="${REPO_ROOT}/configs/.env"
TEMPLATE="${REPO_ROOT}/configs/linux-workstation.env.template"
if [[ ! -f "$ENV_FILE" && -f "$TEMPLATE" ]]; then
  echo "NOTE: configs/.env missing — copy from template:"
  echo "  cp configs/linux-workstation.env.template configs/.env"
elif [[ -f "$TEMPLATE" ]]; then
  echo "NOTE: merge any new keys from configs/linux-workstation.env.template into configs/.env"
fi

READY_URL="${OMEIA_READY_URL:-http://127.0.0.1:8000/ready}"
echo "Checking readiness: $READY_URL"
if curl -sf "$READY_URL" >/dev/null; then
  echo "Ready check: OK"
else
  echo "Ready check: API not reachable (start with ./scripts/start_linux.sh)"
  exit 1
fi

echo "Post-pull complete."
