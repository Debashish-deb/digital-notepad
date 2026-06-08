#!/usr/bin/env bash
# Portable env bootstrap — same repo works on Mac thin client or Linux desktop.
# Sources configs/.env and applies Tailscale remote LLM URLs when configured.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
export OMEIA_REPO_ROOT="$ROOT"

ENV_FILE="${OMEIA_ENV_FILE:-$ROOT/configs/.env}"
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1091
  eval "$("$ROOT/scripts/dev/load_env.sh" "$ENV_FILE")" 2>/dev/null || true
fi

# Portable defaults (override in configs/.env per machine)
export DOCKER_LOCAL="${DOCKER_LOCAL:-false}"
export DOCKER_AUTO_START="${DOCKER_AUTO_START:-false}"
export DATABASE_ROOT="${DATABASE_ROOT:-$ROOT/../OMEIA-database}"
export PROJECTS_ROOT="${PROJECTS_ROOT:-$DATABASE_ROOT/projects}"

# Firebase path relative to repo when not set
if [[ -z "${FIREBASE_SERVICE_ACCOUNT_PATH:-}" && -f "$ROOT/configs/secrets/firebase-adminsdk.json" ]]; then
  export FIREBASE_SERVICE_ACCOUNT_PATH="$ROOT/configs/secrets/firebase-adminsdk.json"
fi

# Tailscale → remote Ollama/Qdrant on Linux workstation
TS_IP="${TAILSCALE_LINUX_IP:-}"
if [[ -n "$TS_IP" ]]; then
  export OLLAMA_BASE_URL="http://${TS_IP}:11434/v1"
  export QDRANT_URL="http://${TS_IP}:6333"
  echo "Portable: remote LLM via Tailscale ${TS_IP}"
elif [[ "${LLM_PROVIDER:-}" == "ollama" ]]; then
  echo "Portable: TAILSCALE_LINUX_IP unset — LLM falls back to gemini,mock if Ollama unreachable"
fi

export OMEIA_DEPLOYMENT_PROFILE="${OMEIA_DEPLOYMENT_PROFILE:-mac_thin_client}"
