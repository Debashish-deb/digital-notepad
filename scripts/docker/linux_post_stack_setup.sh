#!/usr/bin/env bash
# Run on Linux host AFTER ./scripts/docker/start_linux_docker_stack.sh
# Applies DB migrations, pulls embed model, reindexes Qdrant, smoke-tests LLM + retrieval.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/configs/.env" ]]; then
  # shellcheck disable=SC1091
  eval "$("$ROOT/scripts/dev/load_env.sh" "$ROOT/configs/.env")" || true
fi

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
  echo "ERROR: python3 not found. Create a venv: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

echo "=== Linux post-stack setup (python: $PY) ==="

ensure_env() {
  local key="$1"
  local value="$2"
  local file="$ROOT/configs/.env"
  if grep -q "^${key}=" "$file" 2>/dev/null; then
    return 0
  fi
  echo "${key}=${value}" >>"$file"
  echo "  added ${key} to configs/.env"
}

echo "--- Ensuring Ollama LLM vars in configs/.env ---"
ensure_env "LLM_PROVIDER" "ollama"
ensure_env "CHAT_LLM_PROVIDER" "ollama"
ensure_env "OLLAMA_MODEL" "qwen2.5:3b"
ensure_env "OLLAMA_BASE_URL" "http://127.0.0.1:11434/v1"
ensure_env "EMBEDDING_PROVIDER" "ollama"
ensure_env "TEXT_EMBEDDING_MODEL" "nomic-embed-text"
ensure_env "TEXT_EMBEDDING_DIM" "768"
ensure_env "QDRANT_URL" "http://127.0.0.1:6333"
ensure_env "POSTGRES_CONN" "postgresql://farkki:farkki_dev_password@127.0.0.1:5432/farkki_ai"

# shellcheck disable=SC1091
eval "$("$ROOT/scripts/dev/load_env.sh" "$ROOT/configs/.env")" || true

echo "--- Pulling embedding model (nomic-embed-text) ---"
docker exec omeia-ollama ollama pull nomic-embed-text || echo "WARN: nomic-embed-text pull failed — hash fallback will be used"

echo "--- SQL migrations ---"
PYTHONPATH="$ROOT" "$PY" "$ROOT/scripts/database/apply_sql_migrations.py"

echo "--- Reindex vectors (Ollama embeddings) ---"
PYTHONPATH="$ROOT" \
  EMBEDDING_PROVIDER=ollama \
  TEXT_EMBEDDING_DIM=768 \
  QDRANT_URL="${QDRANT_URL:-http://127.0.0.1:6333}" \
  "$PY" "$ROOT/scripts/ingest/reindex_vectors.py" --limit 5000

echo "--- LLM smoke test ---"
PYTHONPATH="$ROOT" \
  LLM_PROVIDER=ollama \
  CHAT_LLM_PROVIDER=ollama \
  OLLAMA_MODEL=qwen2.5:3b \
  OLLAMA_BASE_URL=http://127.0.0.1:11434/v1 \
  "$PY" - <<'PY'
from app_skeleton.api.llm_client import LLMClient
llm = LLMClient()
print("provider:", llm.provider, "model:", llm.model, "healthy:", llm.healthCheck())
out = llm.generate("What is HGSC in one sentence?", "You are a concise research assistant.")
print("sample:", (out or "")[:280])
meta = llm.public_status()
print("synthesis_mode:", meta.get("last_synthesis", {}).get("synthesis_mode"))
PY

echo "--- Qdrant ping ---"
PYTHONPATH="$ROOT" "$PY" - <<'PY'
from app_skeleton.api.qdrant_vectors import get_qdrant_client, ping_qdrant
c = get_qdrant_client()
print("qdrant_ok:", ping_qdrant(c))
try:
    info = c.get_collection("doc_chunks")
    print("doc_chunks points:", getattr(info, "points_count", "?"))
except Exception as exc:
    print("doc_chunks:", exc)
PY

echo ""
echo "=== Post-stack setup done ==="
echo "Next steps:"
echo "  1. Restart API: ./start.sh"
echo "  2. Ingest a project (API must be running):"
echo "     curl -X POST 'http://127.0.0.1:8000/api/projects/EyeMT/knowledge/ingest' -H 'Authorization: Bearer <token>'"
echo "  3. Quick tests:"
echo "     $PY -m pytest tests/test_production_rag_fixes.py tests/test_copilot_enhancements.py -q"
echo "  4. Full eval (slow):"
echo "     LLM_PROVIDER=ollama OLLAMA_MODEL=qwen2.5:7b-instruct $PY scripts/search/run_ai_lab_assistant_eval.py"
