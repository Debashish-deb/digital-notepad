#!/usr/bin/env bash
# Test Ollama on Linux via Tailscale IP from Mac.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/configs/.env" ]]; then
  # shellcheck disable=SC1091
  eval "$("$ROOT/scripts/load_env.sh" "$ROOT/configs/.env")" 2>/dev/null || true
fi

TS_IP="${TAILSCALE_LINUX_IP:-${OLLAMA_TAILSCALE_IP:-}}"
if [[ -z "$TS_IP" ]]; then
  echo "Set TAILSCALE_LINUX_IP in configs/.env (from: tailscale ip -4 on Linux)"
  echo "Example: TAILSCALE_LINUX_IP=100.64.0.12"
  exit 1
fi

TOKEN="${OLLAMA_INTERNAL_TOKEN:-}"
AUTH=()
[[ -n "$TOKEN" ]] && AUTH=(-H "Authorization: Bearer $TOKEN")

echo "=== Tailscale Ollama test ==="
echo "Linux Tailscale IP: $TS_IP"
if curl -sf -m 10 "${AUTH[@]}" "http://${TS_IP}:11434/"; then
  echo ""
  echo "OK — update configs/.env:"
  echo "  OLLAMA_BASE_URL=http://${TS_IP}:11434/v1"
  echo "  QDRANT_URL=http://${TS_IP}:6333"
  exit 0
fi
echo "FAIL — check tailscale status on both machines and docker compose on Linux"
exit 1
