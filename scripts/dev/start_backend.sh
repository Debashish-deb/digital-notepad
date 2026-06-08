#!/usr/bin/env bash
# Start FastAPI backend only (port 8000).
# Frontend: ./scripts/dev/start_frontend.sh
# Full stack: ./start.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

export OMEIA_REPO_ROOT="${OMEIA_REPO_ROOT:-$PROJECT_ROOT}"
export DATABASE_ROOT="${DATABASE_ROOT:-$PROJECT_ROOT/../OMEIA-database}"
export PROJECTS_ROOT="${PROJECTS_ROOT:-$DATABASE_ROOT/projects}"

if [[ -f "${PROJECT_ROOT}/configs/.env" ]]; then
  # shellcheck disable=SC1091
  eval "$("${PROJECT_ROOT}/scripts/dev/load_env.sh" "${PROJECT_ROOT}/configs/.env")"
fi

if [[ -n "${TAILSCALE_LINUX_IP:-}" ]]; then
  export OLLAMA_BASE_URL="http://${TAILSCALE_LINUX_IP}:11434/v1"
  export QDRANT_URL="http://${TAILSCALE_LINUX_IP}:6333"
  export DOCKER_LOCAL=false
  export DOCKER_AUTO_START=false
fi

if [[ "${DOCKER_LOCAL:-true}" != "false" && "${DOCKER_LOCAL:-true}" != "0" ]]; then
  if [[ -x "${PROJECT_ROOT}/scripts/dev/docker_bootstrap.sh" ]]; then
    "${PROJECT_ROOT}/scripts/dev/docker_bootstrap.sh" || echo "WARN: Docker bootstrap incomplete."
  fi
fi

echo "OMEIA backend"
echo "  REPO:     ${OMEIA_REPO_ROOT}"
echo "  DATABASE: ${DATABASE_ROOT}"
echo "  API:      http://127.0.0.1:${OMEIA_BIND_PORT:-8000}/ready"

exec "${PROJECT_ROOT}/deploy/university-desktop/run_api_dev.sh"
