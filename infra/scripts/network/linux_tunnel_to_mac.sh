#!/usr/bin/env bash
# Run ON LINUX — reverse SSH tunnel so Mac localhost:11434 reaches Linux Ollama.
# Requires: Mac "Remote Login" enabled (System Settings → General → Sharing → Remote Login).
set -euo pipefail

MAC_SSH="${MAC_SSH:-}"
OLLAMA_PORT="${OLLAMA_PORT:-11434}"
QDRANT_PORT="${QDRANT_PORT:-6333}"

if [[ -z "$MAC_SSH" ]]; then
  echo "Usage: MAC_SSH=youruser@your-mac-ip ./scripts/linux_tunnel_to_mac.sh"
  echo ""
  echo "On Mac first:"
  echo "  1. System Settings → General → Sharing → Remote Login ON"
  echo "  2. Note Mac IP: ipconfig getifaddr en0   (Wi‑Fi) or en1"
  echo "  3. Ensure Linux Ollama proxy is up: docker compose up -d ollama-proxy"
  exit 1
fi

echo "=== Linux → Mac reverse tunnel ==="
echo "  Mac 127.0.0.1:${OLLAMA_PORT} → Linux Ollama proxy"
echo "  Mac 127.0.0.1:${QDRANT_PORT} → Linux Qdrant"
echo "  Keep this terminal open on Linux."
echo ""

exec ssh -N \
  -R "127.0.0.1:${OLLAMA_PORT}:127.0.0.1:${OLLAMA_PORT}" \
  -R "127.0.0.1:${QDRANT_PORT}:127.0.0.1:${QDRANT_PORT}" \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  "$MAC_SSH"
