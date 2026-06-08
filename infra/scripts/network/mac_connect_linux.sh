#!/usr/bin/env bash
# Mac thin client: SSH tunnels to Linux Docker (Ollama + Qdrant). No Docker on Mac.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/configs/.env" ]]; then
  # shellcheck disable=SC1091
  eval "$("$ROOT/scripts/dev/load_env.sh" "$ROOT/configs/.env")" 2>/dev/null || true
fi

HOST="${OLLAMA_LINUX_SSH:-${OLLAMA_SSH_HOST:-}}"
if [[ -z "$HOST" ]]; then
  echo "ERROR: Set OLLAMA_LINUX_SSH in configs/.env"
  echo "  Example: OLLAMA_LINUX_SSH=debdeba@10.0.0.50"
  echo "  Get IP on Linux: hostname -I | awk '{print \$1}'"
  exit 1
fi

OLLAMA_LOCAL="${OLLAMA_TUNNEL_LOCAL_PORT:-11434}"
OLLAMA_REMOTE="${OLLAMA_TUNNEL_REMOTE_PORT:-11434}"
QDRANT_LOCAL="${QDRANT_TUNNEL_LOCAL_PORT:-6333}"
QDRANT_REMOTE="${QDRANT_TUNNEL_REMOTE_PORT:-6333}"

# Kill existing tunnels on these ports (best-effort)
for port in "$OLLAMA_LOCAL" "$QDRANT_LOCAL"; do
  pids="$(lsof -ti tcp:"$port" 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    echo "Stopping old process on port $port..."
    kill $pids 2>/dev/null || true
    sleep 1
  fi
done

echo "=== Mac → Linux SSH tunnels ==="
echo "  Ollama: 127.0.0.1:${OLLAMA_LOCAL} → ${HOST}:127.0.0.1:${OLLAMA_REMOTE}"
echo "  Qdrant: 127.0.0.1:${QDRANT_LOCAL} → ${HOST}:127.0.0.1:${QDRANT_REMOTE}"
echo "  Keep this terminal open while using the app."
echo ""

exec ssh -N \
  -L "127.0.0.1:${OLLAMA_LOCAL}:127.0.0.1:${OLLAMA_REMOTE}" \
  -L "127.0.0.1:${QDRANT_LOCAL}:127.0.0.1:${QDRANT_REMOTE}" \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  "$HOST"
