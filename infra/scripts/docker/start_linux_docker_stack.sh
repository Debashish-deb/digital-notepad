#!/usr/bin/env bash
# Run on Linux workstation — starts OMEIA Docker stack (Ollama, Postgres, Qdrant).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker not found. Install Docker Engine on this Linux host."
  exit 1
fi

echo "=== Starting OMEIA Docker stack on $(hostname) ==="
# docker compose reads project-root .env for ${VAR} substitution — link configs/.env
if [[ -f "$ROOT/configs/.env" && ! -f "$ROOT/.env" ]]; then
  ln -sf configs/.env "$ROOT/.env"
  echo "Linked .env -> configs/.env for docker compose"
fi
docker compose up -d

if [[ -x "$ROOT/scripts/llm/generate_ollama_token.sh" ]] && ! grep -q '^OLLAMA_INTERNAL_TOKEN=.\+' "$ROOT/configs/.env" 2>/dev/null; then
  echo "=== Generating Ollama proxy token ==="
  "$ROOT/scripts/llm/generate_ollama_token.sh"
fi

if [[ -x "$ROOT/scripts/llm/setup_ollama_local_llm.sh" ]]; then
  env -u OLLAMA_RESEARCH_MODELS -u OLLAMA_MODELS "$ROOT/scripts/llm/setup_ollama_local_llm.sh"
fi

# Resume any catalog pulls interrupted earlier (medllama2, meditron, etc.)
if [[ -x "$ROOT/scripts/llm/pull_ollama_research_models.sh" ]]; then
  echo "=== Resuming catalog model pulls (background) ==="
  env -u OLLAMA_RESEARCH_MODELS -u OLLAMA_MODELS nohup "$ROOT/scripts/llm/pull_ollama_research_models.sh" &
  echo "  tail -f logs/ollama_model_pulls.log"
fi

echo ""
echo "=== Stack ready ==="
docker compose ps
echo ""
echo "On this Linux host, run post-setup (migrations + reindex + LLM smoke test):"
echo "  ./scripts/docker/linux_post_stack_setup.sh"
echo ""
echo "From your Mac (thin client), set configs/.env:"
echo "  DOCKER_LOCAL=false"
echo "  LLM_PROVIDER=ollama"
echo "  OLLAMA_BASE_URL=http://<this-host-ip>:11434/v1   # or use scripts/llm/ollama_ssh_tunnel.sh"
echo "  POSTGRES_CONN=postgresql://farkki:farkki_dev_password@<this-host-ip>:5432/farkki_ai"
echo "  QDRANT_URL=http://<this-host-ip>:6333"
