#!/usr/bin/env bash
# Pull OMEIA research models into omeia-ollama Docker volume. Safe to re-run (skips existing).
# Run on the Linux Docker host (scripts/docker/start_linux_docker_stack.sh), not on Mac thin client.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
CONTAINER="${OLLAMA_CONTAINER:-omeia-ollama}"
LOG="${ROOT}/logs/ollama_model_pulls.log"
mkdir -p "${ROOT}/logs"

load_default_tags() {
  if [[ -f "${ROOT}/configs/ollama_research_models.json" ]]; then
    TAGS=()
    while IFS= read -r line; do TAGS+=("$line"); done < <(
      python3 -c "import json; print('\n'.join(json.load(open('${ROOT}/configs/ollama_research_models.json'))['pull_order']))"
    )
  else
    TAGS=(qwen2.5:3b llama3.2:3b phi3:mini medgemma:4b meditron:7b medllama2:7b qwen2.5:7b-instruct llama3.1:8b mistral-nemo:12b)
  fi
}

valid_models_csv() {
  local csv="$1"
  [[ "$csv" == *"/"* ]] && return 1
  [[ "$csv" =~ ^[a-zA-Z0-9._:-]+(,[a-zA-Z0-9._:-]+)*$ ]] || return 1
}

if [[ -n "${OLLAMA_MODELS:-}" ]] && valid_models_csv "$OLLAMA_MODELS"; then
  IFS=',' read -r -a TAGS <<< "$OLLAMA_MODELS"
elif [[ -n "${OLLAMA_RESEARCH_MODELS:-}" ]] && valid_models_csv "$OLLAMA_RESEARCH_MODELS"; then
  IFS=',' read -r -a TAGS <<< "$OLLAMA_RESEARCH_MODELS"
else
  if [[ -n "${OLLAMA_MODELS:-}" ]] || [[ -n "${OLLAMA_RESEARCH_MODELS:-}" ]]; then
    echo "WARN: ignoring invalid OLLAMA_MODELS/OLLAMA_RESEARCH_MODELS (use comma-separated tags, not paths)" >&2
  fi
  load_default_tags
fi

exec >> "$LOG" 2>&1
echo "=== pull_ollama_research_models $(date -Iseconds) ==="
for tag in "${TAGS[@]}"; do
  tag="$(echo "$tag" | xargs)"
  [[ -z "$tag" ]] && continue
  echo "[pull] $(date -Iseconds) $tag"
  if docker exec "$CONTAINER" ollama pull "$tag"; then
    echo "[ok] $tag"
  else
    echo "[FAILED] $tag"
  fi
done
echo "=== complete $(date -Iseconds) ==="
docker exec "$CONTAINER" ollama list
