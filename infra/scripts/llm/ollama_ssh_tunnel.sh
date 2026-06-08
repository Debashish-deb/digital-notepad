#!/usr/bin/env bash
# Forward Linux workstation Ollama proxy to Mac localhost:11434 (no Docker on Mac).
# Usage: OLLAMA_SSH_HOST=user@linux-workstation ./scripts/llm/ollama_ssh_tunnel.sh
set -euo pipefail

HOST="${OLLAMA_SSH_HOST:-}"
LOCAL_PORT="${OLLAMA_TUNNEL_LOCAL_PORT:-11434}"
REMOTE_PORT="${OLLAMA_TUNNEL_REMOTE_PORT:-11434}"

if [[ -z "$HOST" ]]; then
  echo "Set OLLAMA_SSH_HOST=user@your-linux-workstation"
  echo "Example: OLLAMA_SSH_HOST=deb@192.168.1.50 ./scripts/llm/ollama_ssh_tunnel.sh"
  exit 1
fi

echo "Tunneling 127.0.0.1:${LOCAL_PORT} -> ${HOST}:127.0.0.1:${REMOTE_PORT}"
echo "Keep this terminal open. In configs/.env use:"
echo "  OLLAMA_BASE_URL=http://127.0.0.1:${LOCAL_PORT}/v1"
echo "  DOCKER_LOCAL=false"
exec ssh -N -L "127.0.0.1:${LOCAL_PORT}:127.0.0.1:${REMOTE_PORT}" "$HOST"
