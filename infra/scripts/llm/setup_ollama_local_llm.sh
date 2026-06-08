#!/usr/bin/env bash
# Start Ollama in Docker, pull curated OMEIA research models, smoke-test default, print .env hints.
# Models live in the omeia-ollama-data Docker volume (not ~/.ollama on the host).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/configs/.env" ]]; then
  # shellcheck disable=SC1091
  eval "$("$ROOT/scripts/dev/load_env.sh" "$ROOT/configs/.env")" || true
  if [[ -z "${OLLAMA_INTERNAL_TOKEN:-}" ]]; then
    OLLAMA_INTERNAL_TOKEN="$(grep -E '^OLLAMA_INTERNAL_TOKEN=' "$ROOT/configs/.env" | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" || true)"
    export OLLAMA_INTERNAL_TOKEN
  fi
fi

OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5:3b}"
CONTAINER="${OLLAMA_CONTAINER:-omeia-ollama}"
CATALOG="${ROOT}/configs/ollama_research_models.json"
LOG_DIR="${ROOT}/logs"
LOG_FILE="${LOG_DIR}/ollama_setup.log"
PULL_LOG="${LOG_DIR}/ollama_model_pulls.log"

mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

default_models_csv() {
  if [[ -f "$CATALOG" ]]; then
    python3 - <<PY
import json
from pathlib import Path
data = json.loads(Path("${CATALOG}").read_text())
print(",".join(data.get("pull_order", [])))
PY
  else
    echo "qwen2.5:3b,llama3.2:3b,phi3:mini,medgemma:4b,meditron:7b,medllama2:7b,qwen2.5:7b-instruct,llama3.1:8b,mistral-nemo:12b"
  fi
}

is_valid_models_csv() {
  local csv="$1"
  [[ -z "$csv" ]] && return 1
  [[ "$csv" == *"/"* ]] && return 1
  [[ "$csv" == *" "* ]] && return 1
  return 0
}

if is_valid_models_csv "${OLLAMA_MODELS:-}"; then
  MODELS_CSV="$OLLAMA_MODELS"
elif is_valid_models_csv "${OLLAMA_RESEARCH_MODELS:-}"; then
  MODELS_CSV="$OLLAMA_RESEARCH_MODELS"
else
  if [[ -n "${OLLAMA_RESEARCH_MODELS:-}" || -n "${OLLAMA_MODELS:-}" ]]; then
    echo "WARN: OLLAMA_MODELS/OLLAMA_RESEARCH_MODELS looks like a path or invalid list — using catalog pull_order"
  fi
  MODELS_CSV="$(default_models_csv)"
fi

echo "=== OMEIA local LLM setup ($(date -Iseconds)) ==="
echo "Default chat model: ${OLLAMA_MODEL} (container: ${CONTAINER})"
echo "Pull list: ${MODELS_CSV}"
echo "Catalog: ${CATALOG}"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker not found. Install Docker Desktop or colima first."
  exit 1
fi

echo "--- Starting Ollama stack (ollama + auth proxy) ---"
docker compose up -d ollama ollama-proxy

echo "--- Waiting for Ollama API (via proxy) ---"
WAIT_AUTH=()
if [[ -n "${OLLAMA_INTERNAL_TOKEN:-}" ]]; then
  WAIT_AUTH=(-H "Authorization: Bearer ${OLLAMA_INTERNAL_TOKEN}")
fi
for i in $(seq 1 90); do
  if curl -sf "${WAIT_AUTH[@]}" "http://127.0.0.1:11434/" >/dev/null 2>&1; then
    echo "Ollama API ready via proxy (${i}s)"
    break
  fi
  if docker exec "$CONTAINER" ollama list >/dev/null 2>&1; then
    echo "Ollama container healthy (proxy curl pending); continuing (${i}s)"
    break
  fi
  if [[ "$i" -eq 90 ]]; then
    echo "ERROR: Ollama did not become ready on :11434 (check: docker logs omeia-ollama-proxy)"
    exit 1
  fi
  sleep 2
done

IFS=',' read -r -a MODEL_TAGS <<< "$MODELS_CSV"
# trim whitespace per tag
for idx in "${!MODEL_TAGS[@]}"; do
  MODEL_TAGS[$idx]="$(echo "${MODEL_TAGS[$idx]}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
done

echo "--- Pulling models inside container (Docker volume omeia-ollama-data) ---"
echo "=== OMEIA model pulls $(date -Iseconds) ===" >> "$PULL_LOG"
for tag in "${MODEL_TAGS[@]}"; do
  [[ -z "$tag" ]] && continue
  echo "[pull] $(date -Iseconds) ollama pull ${tag}"
  echo "--- pull ${tag} $(date -Iseconds) ---" >> "$PULL_LOG"
  if docker exec "$CONTAINER" ollama pull "$tag" >> "$PULL_LOG" 2>&1; then
    echo "OK ${tag}" >> "$PULL_LOG"
  else
    echo "WARN: pull failed for ${tag} — skipping (check tag on https://ollama.com/library)"
    echo "FAIL ${tag}" >> "$PULL_LOG"
  fi
done
echo "=== pulls finished $(date -Iseconds) ===" >> "$PULL_LOG"

echo "--- Installed models ---"
docker exec "$CONTAINER" ollama list || true

CANCER_MODEL="${OLLAMA_CANCER_MODEL:-medllama2:7b}"
SPATIAL_MODEL="${OLLAMA_SPATIAL_MODEL:-qwen2.5:7b-instruct}"
if docker exec "$CONTAINER" ollama list 2>/dev/null | grep -qF "$CANCER_MODEL"; then
  echo "--- Smoke: cancer/oncology (${CANCER_MODEL}) ---"
  docker exec "$CONTAINER" ollama run "$CANCER_MODEL"     "In 3 sentences: what is HGSC and why does tumor microenvironment matter for immunotherapy?" | head -n 10
fi
if docker exec "$CONTAINER" ollama list 2>/dev/null | grep -qF "$SPATIAL_MODEL"; then
  echo "--- Smoke: spatial biology (${SPATIAL_MODEL}) ---"
  docker exec "$CONTAINER" ollama run "$SPATIAL_MODEL"     "Briefly compare 10x Visium vs GeoMx for TLS and MHC in HGSC." | head -n 10
fi

echo "--- Smoke test: generate (default ${OLLAMA_MODEL}) ---"
docker exec "$CONTAINER" ollama run "$OLLAMA_MODEL" "Reply with one short sentence: you are the OMEIA lab assistant." \
  | head -n 5

echo "--- OpenAI-compatible API test (via localhost proxy) ---"
AUTH_HEADER=()
if [[ -n "${OLLAMA_INTERNAL_TOKEN:-}" ]]; then
  AUTH_HEADER=(-H "Authorization: Bearer ${OLLAMA_INTERNAL_TOKEN}")
fi
curl -sf "http://127.0.0.1:11434/v1/chat/completions" \
  "${AUTH_HEADER[@]}" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"${OLLAMA_MODEL}\",\"messages\":[{\"role\":\"user\",\"content\":\"Say hello in 5 words.\"}],\"stream\":false}" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['choices'][0]['message']['content'][:200])"

echo "--- OMEIA llm_client test ---"
(
  export LLM_PROVIDER=ollama
  export CHAT_LLM_PROVIDER=ollama
  export OLLAMA_MODEL="$OLLAMA_MODEL"
  export LLM_MODEL="$OLLAMA_MODEL"
  export OLLAMA_BASE_URL=http://127.0.0.1:11434/v1
  export LLM_FALLBACK_PROVIDERS=ollama,mock
  cd "$ROOT"
  PY_BIN="${ROOT}/.venv-local/bin/python3"
  if [[ ! -x "$PY_BIN" ]]; then PY_BIN="${ROOT}/.venv/bin/python3"; fi
  "$PY_BIN" - <<'PY'
from omeia.api.llm_client import LLMClient
llm = LLMClient()
print("provider:", llm.provider, "model:", llm.model, "healthy:", llm.healthCheck())
out = llm.generate("What is HGSC in one sentence?", "You are a concise research assistant.")
print("sample:", (out or "")[:300])
meta = llm.public_status()
print("synthesis_mode:", meta.get("last_synthesis", {}).get("synthesis_mode"), "effective:", meta.get("last_synthesis", {}).get("effective_provider"))
PY
)

cat <<EOF

=== Done ===
Model catalog: configs/ollama_research_models.json
  • Daily dev / fast chat: OLLAMA_MODEL=qwen2.5:3b
  • Batch eval (local):    OLLAMA_MODEL=qwen2.5:7b-instruct or meditron:7b
  • Medical phrasing:      medllama2 or medgemma:4b

Add to configs/.env (server-side only):

  LLM_PROVIDER=ollama
  CHAT_LLM_PROVIDER=ollama
  OLLAMA_MODEL=${OLLAMA_MODEL}
  OLLAMA_RESEARCH_MODELS=${MODELS_CSV}
  OLLAMA_BASE_URL=http://127.0.0.1:11434/v1
  OLLAMA_INTERNAL_TOKEN=<run scripts/llm/generate_ollama_token.sh once>
  LLM_FALLBACK_PROVIDERS=ollama,mock

Override pulls: OLLAMA_MODELS=tag1,tag2 scripts/llm/setup_ollama_local_llm.sh

Restart API: ./start.sh
Eval: LLM_PROVIDER=ollama CHAT_LLM_PROVIDER=ollama OLLAMA_MODEL=qwen2.5:7b-instruct .venv/bin/python3 scripts/search/run_ai_lab_assistant_eval.py

Log: ${LOG_FILE}
EOF
