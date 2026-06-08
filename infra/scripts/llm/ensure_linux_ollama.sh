#!/usr/bin/env bash
# Ensure Linux configs/.env uses Ollama for chat (not mock). Safe to re-run after git pull.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/../lib/common.sh"

ROOT="${OMEIA_REPO_ROOT}"
ENV_FILE="${ROOT}/configs/.env"
TEMPLATE="${ROOT}/config/env/linux-workstation.env.template"
if [[ ! -f "$TEMPLATE" ]]; then
  TEMPLATE="${ROOT}/configs/linux-workstation.env.template"
fi

mkdir -p "${ROOT}/configs"

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ -f "$TEMPLATE" ]]; then
    cp "$TEMPLATE" "$ENV_FILE"
    echo "Created configs/.env from $(basename "$TEMPLATE")"
  else
    echo "WARN: configs/.env missing and no template found — creating minimal stub"
    touch "$ENV_FILE"
  fi
fi

_env_value() {
  local key="$1"
  grep -E "^${key}=" "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" | xargs || true
}

_set_or_patch_key() {
  local key="$1"
  local value="$2"
  local force="${3:-false}"
  local current
  current="$(_env_value "$key")"
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    if [[ "$force" == "true" || -z "$current" || "$current" == "mock" ]]; then
      sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
      echo "  patched ${key}=${value} (was: ${current:-<empty>})"
    fi
  else
    echo "${key}=${value}" >>"$ENV_FILE"
    echo "  added ${key}=${value}"
  fi
}

echo "=== ensure_linux_ollama ($(hostname)) ==="
echo "  Repo: ${ROOT}"
echo "  Env:  ${ENV_FILE}"

_set_or_patch_key "LLM_PROVIDER" "ollama" true
_set_or_patch_key "CHAT_LLM_PROVIDER" "ollama" true
_set_or_patch_key "OLLAMA_MODEL" "qwen2.5:3b" false
_set_or_patch_key "OLLAMA_BASE_URL" "http://127.0.0.1:11434/v1" false

omeia_load_env "$ENV_FILE"

echo "--- LLM provider diagnostics ---"
echo "  LLM_PROVIDER=${LLM_PROVIDER:-<unset>}"
echo "  CHAT_LLM_PROVIDER=${CHAT_LLM_PROVIDER:-<unset>}"
echo "  OLLAMA_MODEL=${OLLAMA_MODEL:-<unset>}"
echo "  OLLAMA_BASE_URL=${OLLAMA_BASE_URL:-<unset>}"

CONTAINER="${OLLAMA_CONTAINER:-omeia-ollama}"
if command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$CONTAINER"; then
  echo "--- docker exec ${CONTAINER} ollama list ---"
  docker exec "$CONTAINER" ollama list || echo "WARN: ollama list failed inside ${CONTAINER}"
else
  echo "WARN: container ${CONTAINER} not running — start stack: ./scripts/start_linux.sh"
  echo "      Then pull chat model: docker exec ${CONTAINER} ollama pull qwen2.5:3b"
fi

echo ""
echo "If qwen2.5:3b is missing:"
echo "  docker exec ${CONTAINER} ollama pull qwen2.5:3b"
echo "Restart API after env changes: ./scripts/start_linux.sh"
echo "=== ensure_linux_ollama done ==="
