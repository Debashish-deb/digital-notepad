#!/usr/bin/env bash
# Linux workstation — one-shot bootstrap: code, packages, Docker, data paths, migrations, reindex.
#
# Usage (on Linux):
#   cd ~/data4TB/digital-notepad
#   ./scripts/deploy/linux_bootstrap_all.sh
#   ./scripts/deploy/linux_bootstrap_all.sh --skip-docker
#   ./scripts/deploy/linux_bootstrap_all.sh --with-biomodels
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

SKIP_DOCKER=false
WITH_BIOMODELS=false
for arg in "$@"; do
  case "$arg" in
    --skip-docker) SKIP_DOCKER=true ;;
    --with-biomodels) WITH_BIOMODELS=true ;;
    -h|--help)
      echo "Usage: $0 [--skip-docker] [--with-biomodels]"
      exit 0
      ;;
  esac
done

PY=""
for candidate in \
  "$ROOT/.venv-local/bin/python3" \
  "$ROOT/.venv/bin/python3" \
  "$(command -v python3 2>/dev/null || true)"; do
  if [[ -n "$candidate" && -x "$candidate" ]]; then
    PY="$candidate"
    break
  fi
done
if [[ -z "$PY" ]]; then
  echo "--- Creating Python venv ---"
  python3 -m venv "$ROOT/.venv"
  PY="$ROOT/.venv/bin/python3"
fi

ENV_FILE="$ROOT/configs/.env"
LINUX_TEMPLATE="$ROOT/configs/linux-workstation.env.template"

echo "=== OMEIA Linux full bootstrap ==="
echo "  Host: $(hostname)"
echo "  Repo: $ROOT"
echo "  Python: $PY"

echo "--- Git pull ---"
git pull

echo "--- configs/.env (Linux paths) ---"
if [[ ! -f "$ENV_FILE" ]]; then
  cp "$LINUX_TEMPLATE" "$ENV_FILE"
  echo "  Created configs/.env from .env.linux.example"
fi

ensure_kv() {
  local key="$1"
  local value="$2"
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
  else
    echo "${key}=${value}" >>"$ENV_FILE"
  fi
}

DATA_ROOT="${OMEIA_DATA_ROOT:-$HOME/data4TB/OMEIA-database}"
ensure_kv "OMEIA_DEPLOYMENT_PROFILE" "linux_desktop"
ensure_kv "DOCKER_LOCAL" "true"
ensure_kv "DOCKER_AUTO_START" "true"
ensure_kv "DATABASE_ROOT" "$DATA_ROOT"
ensure_kv "PROJECTS_ROOT" "$DATA_ROOT/projects"
ensure_kv "POSTGRES_CONN" "postgresql://farkki:farkki_dev_password@127.0.0.1:5432/farkki_ai"
ensure_kv "QDRANT_URL" "http://127.0.0.1:6333"
ensure_kv "LLM_PROVIDER" "ollama"
ensure_kv "CHAT_LLM_PROVIDER" "ollama"
ensure_kv "OLLAMA_MODEL" "qwen2.5:3b"
ensure_kv "OLLAMA_BASE_URL" "http://127.0.0.1:11434/v1"
ensure_kv "EMBEDDING_PROVIDER" "ollama"
ensure_kv "TEXT_EMBEDDING_MODEL" "nomic-embed-text"
ensure_kv "TEXT_EMBEDDING_DIM" "768"
ensure_kv "RESEARCH_KB_VECTOR_SIZE" "768"
ensure_kv "KNOWLEDGE_INDEXER_ENABLED" "true"
ensure_kv "VECTORIZATION_ENABLED" "true"

if ! grep -q '^OLLAMA_INTERNAL_TOKEN=.\+' "$ENV_FILE" 2>/dev/null; then
  "$ROOT/scripts/llm/generate_ollama_token.sh" || true
fi
ln -sf configs/.env "$ROOT/.env"

# shellcheck disable=SC1091
eval "$("$ROOT/scripts/dev/load_env.sh" "$ENV_FILE")" || true

echo "--- Python packages ---"
"$PY" -m pip install -r "$ROOT/app_skeleton/api/requirements.txt"
"$PY" -m pip install pytest

echo "--- Node.js (Vite 8 needs >=20.19 or >=22.12) ---"
need_node_bump() {
  command -v node >/dev/null 2>&1 || return 0
  node -e 'const v=process.versions.node.split(".").map(Number); const ok=(v[0]>22||(v[0]===22&&v[1]>=12)||(v[0]===20&&v[1]>=19)); process.exit(ok?0:1)' 2>/dev/null
}
if need_node_bump; then
  if [[ -s "$HOME/.nvm/nvm.sh" ]]; then
    # shellcheck disable=SC1091
    . "$HOME/.nvm/nvm.sh"
    nvm install 22
    nvm use 22
  else
    echo "WARN: Node $(node -v 2>/dev/null || echo missing) is too old for Vite 8."
    echo "  Install nvm then re-run bootstrap:"
    echo "    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash"
    echo "    source ~/.nvm/nvm.sh && nvm install 22 && nvm use 22"
  fi
fi

echo "--- Frontend packages ---"
if command -v npm >/dev/null 2>&1; then
  echo "  node: $(node -v)  npm: $(npm -v)"
  (cd "$ROOT/app_skeleton/ui/react_frontend" && npm install)
else
  echo "WARN: npm not found — install Node.js 22 via nvm"
fi

if [[ "$SKIP_DOCKER" != true ]]; then
  echo "--- Docker stack ---"
  "$ROOT/scripts/docker/start_linux_docker_stack.sh"
  echo "--- Post-stack (migrations, embed model, reindex) ---"
  "$ROOT/scripts/docker/linux_post_stack_setup.sh"
  if [[ -f "$ROOT/scripts/ingest/reindex_research_vectors.py" ]]; then
    PYTHONPATH="$ROOT" "$PY" "$ROOT/scripts/ingest/reindex_research_vectors.py" --limit 5000 || true
  fi
fi

if [[ "$WITH_BIOMODELS" == true && -x "$ROOT/scripts/docker/setup_biomodels_docker.sh" ]]; then
  echo "--- Biomedical model containers ---"
  BIOMODEL_PROFILES=biomodels "$ROOT/scripts/docker/setup_biomodels_docker.sh" || echo "WARN: biomodels setup failed"
fi

echo ""
echo "=== Bootstrap complete ==="
echo "  Data root:  $DATA_ROOT"
echo "  Start UI:   ./scripts/start_linux.sh"
echo "  Tailscale:  http://\$(tailscale ip -4):5173"
echo ""
if [[ ! -d "$DATA_ROOT/WET_LAB" && ! -d "$DATA_ROOT/SOCIAL" ]]; then
  echo "WARN: $DATA_ROOT looks empty — run from Mac:"
  echo "  LINUX_SSH=labuser@\$(tailscale ip -4) ./scripts/deploy/mac_push_to_linux.sh --data-only"
fi
