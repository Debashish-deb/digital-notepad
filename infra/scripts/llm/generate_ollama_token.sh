#!/usr/bin/env bash
# Generate a one-time Ollama proxy bearer token and append to configs/.env
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ROOT}/configs/.env"
TOKEN="$(openssl rand -hex 32)"

echo "Generated OLLAMA_INTERNAL_TOKEN (${#TOKEN} hex chars)"
echo ""
echo "Add to configs/.env:"
echo "  OLLAMA_INTERNAL_TOKEN=${TOKEN}"
echo ""

if [[ -f "$ENV_FILE" ]]; then
  if grep -q '^OLLAMA_INTERNAL_TOKEN=' "$ENV_FILE" 2>/dev/null; then
    echo "configs/.env already has OLLAMA_INTERNAL_TOKEN — update manually if rotating."
  else
    {
      echo ""
      echo "# Ollama proxy bearer token (generated $(date -Iseconds))"
      echo "OLLAMA_INTERNAL_TOKEN=${TOKEN}"
    } >> "$ENV_FILE"
    echo "Appended to configs/.env"
  fi
else
  echo "No configs/.env yet — copy configs/.env.example and add the token above."
fi
