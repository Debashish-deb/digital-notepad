#!/usr/bin/env bash
# Quick check: tunnels + Ollama token + Qdrant reachable from Mac.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/configs/.env" ]]; then
  # shellcheck disable=SC1091
  eval "$("$ROOT/scripts/dev/load_env.sh" "$ROOT/configs/.env")" 2>/dev/null || true
  if [[ -z "${OLLAMA_INTERNAL_TOKEN:-}" ]]; then
    OLLAMA_INTERNAL_TOKEN="$(grep -E '^OLLAMA_INTERNAL_TOKEN=' "$ROOT/configs/.env" | head -1 | cut -d= -f2- | tr -d '"' || true)"
  fi
fi

TOKEN="${OLLAMA_INTERNAL_TOKEN:-}"
OK=0

echo "=== Mac connectivity test ==="

if curl -sf -m 5 ${TOKEN:+-H "Authorization: Bearer $TOKEN"} "http://127.0.0.1:11434/" >/dev/null 2>&1; then
  echo "OK  Ollama tunnel (127.0.0.1:11434)"
  OK=1
else
  echo "FAIL Ollama — run: ./scripts/network/mac_connect_linux.sh (in another terminal)"
fi

if curl -sf -m 5 "http://127.0.0.1:6333/healthz" >/dev/null 2>&1; then
  echo "OK  Qdrant tunnel (127.0.0.1:6333)"
else
  echo "WARN Qdrant — search/research-KB may be limited (tunnel includes 6333 when connect script runs)"
fi

if [[ "$OK" -eq 1 ]]; then
  echo ""
  echo "Ready. Start app: ./start.sh"
  exit 0
fi
exit 1
