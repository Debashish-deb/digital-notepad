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

if command -v tailscale >/dev/null 2>&1; then
  if tailscale ping -c 1 -timeout 3s "$TS_IP" >/dev/null 2>&1; then
    echo "Tailscale ping: OK"
  else
    echo "Tailscale ping: FAIL — run: sudo tailscale up (same account on both machines)"
  fi
else
  echo "Tailscale ping: skipped (tailscale CLI not on PATH)"
fi

if nc -z -G 5 "$TS_IP" 11434 2>/dev/null; then
  echo "TCP 11434: open"
else
  echo "TCP 11434: closed/timeout — on Linux run: scripts/linux_fix_tailscale_inbound.sh"
fi

if curl -sf -m 10 "${AUTH[@]}" "http://${TS_IP}:11434/"; then
  echo ""
  echo "OK — Ollama reachable via Tailscale"
  exit 0
fi
echo "FAIL — Linux local curl works but Mac cannot reach $TS_IP:11434"
exit 1
