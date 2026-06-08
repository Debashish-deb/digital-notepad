#!/usr/bin/env bash
# One-time Mac portable setup — no Docker Desktop. Ready to move repo to Linux later.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

echo "=== OMEIA Mac portable setup ==="
echo "Repo: $ROOT"

# Python venv
if [[ ! -x "$ROOT/.venv/bin/python3" ]]; then
  echo "ERROR: run from repo with .venv (python3 -m venv .venv && pip install -r requirements.txt)"
  exit 1
fi

# Frontend deps
if [[ ! -d "$ROOT/omeia/ui/react_frontend/node_modules" ]]; then
  echo "=== npm install (frontend) ==="
  (cd "$ROOT/omeia/ui/react_frontend" && npm install)
fi

# Env file
if [[ ! -f "$ROOT/configs/.env" ]]; then
  cp "$ROOT/configs/.env.example" "$ROOT/configs/.env"
  echo "Created configs/.env from example — add secrets before production use."
fi

# Portable profile markers
grep -q '^OMEIA_DEPLOYMENT_PROFILE=' "$ROOT/configs/.env" 2>/dev/null || \
  echo "OMEIA_DEPLOYMENT_PROFILE=mac_thin_client" >> "$ROOT/configs/.env"
grep -q '^DOCKER_LOCAL=' "$ROOT/configs/.env" 2>/dev/null || \
  echo "DOCKER_LOCAL=false" >> "$ROOT/configs/.env"

# Tailscale (optional)
if command -v tailscale >/dev/null 2>&1; then
  echo ""
  echo "=== Tailscale ==="
  if ! tailscale status >/dev/null 2>&1; then
    echo "Tailscale installed but not running. Run once:"
    echo "  sudo brew services start tailscale"
    echo "  sudo tailscale up"
    echo "Then on Linux (same account): sudo tailscale up"
    echo "Set TAILSCALE_LINUX_IP=<linux tailscale ip -4> in configs/.env"
  else
    echo "Tailscale OK:"
    tailscale status 2>/dev/null | head -6
  fi
else
  echo "Install Tailscale: brew install tailscale"
fi

echo ""
echo "=== Done ==="
echo "Start app:  ./scripts/dev/start_portable.sh"
echo "Move later: docs/PORTABLE_MAC_TO_LINUX.md"
