#!/usr/bin/env bash
# Stop all OMEIA containers on this machine and optionally quit Docker Desktop (Mac).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker CLI not found — nothing to stop."
  exit 0
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon already stopped."
  exit 0
fi

echo "=== Stopping OMEIA compose stack ==="
docker compose down 2>/dev/null || true

RUNNING="$(docker ps -q --filter name=omeia- 2>/dev/null || true)"
if [[ -n "$RUNNING" ]]; then
  echo "=== Stopping remaining omeia-* containers ==="
  docker stop $RUNNING 2>/dev/null || true
fi

echo ""
docker ps -a --filter name=omeia- --format 'table {{.Names}}\t{{.Status}}' 2>/dev/null || true

if [[ "$(uname -s)" == "Darwin" ]] && [[ "${QUIT_DOCKER_DESKTOP:-true}" != "false" ]]; then
  if pgrep -x "Docker Desktop" >/dev/null 2>&1 || pgrep -f "com.docker.docker" >/dev/null 2>&1; then
    echo ""
    echo "=== Quitting Docker Desktop (frees ~2–4 GB RAM) ==="
    osascript -e 'quit app "Docker"' 2>/dev/null || true
    echo "Done. Disable 'Open Docker Desktop when you log in' in Docker Desktop → Settings → General."
  fi
fi

echo ""
echo "Mac thin client mode: keep DOCKER_LOCAL=false in configs/.env"
echo "LLM/DB run on Linux — use scripts/llm/ollama_ssh_tunnel.sh when needed."
