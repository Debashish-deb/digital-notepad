#!/usr/bin/env bash
# Build and start biomedical model FastAPI services on Linux workstation.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

PROFILES="${BIOMODEL_PROFILES:-biomodels}"
# Examples:
#   BIOMODEL_PROFILES=biomodels ./scripts/docker/setup_biomodels_docker.sh
#   BIOMODEL_PROFILES=biomodels,biomodels-llm ./scripts/docker/setup_biomodels_docker.sh
#   BIOMODEL_PROFILES=biomodels,biomodels-llm,biomodels-singlecell ./scripts/docker/setup_biomodels_docker.sh

IFS=',' read -r -a PROFILE_ARR <<< "$PROFILES"
COMPOSE_PROFILES=()
for p in "${PROFILE_ARR[@]}"; do
  p="$(echo "$p" | xargs)"
  [[ -n "$p" ]] && COMPOSE_PROFILES+=(--profile "$p")
done

echo "=== Ensuring base stack (postgres, qdrant, ollama) ==="
docker compose up -d postgres qdrant ollama ollama-proxy

echo "=== Building biomedical model services: ${PROFILES} ==="
docker compose -f docker-compose.yml -f docker-compose.biomodels.yml "${COMPOSE_PROFILES[@]}" build

echo "=== Starting biomedical model services ==="
docker compose -f docker-compose.yml -f docker-compose.biomodels.yml "${COMPOSE_PROFILES[@]}" up -d

echo ""
echo "Gateway:  http://127.0.0.1:8100/catalog"
echo "Status:   http://127.0.0.1:8100/status"
echo "Embed:    http://127.0.0.1:8101/embed"
echo ""
echo "From Mac thin client set in configs/.env:"
echo "  BIOMEDICAL_MODELS_GATEWAY_URL=http://<TAILSCALE_LINUX_IP>:8100"
echo "  BIOMEDICAL_EMBEDDINGS_URL=http://<TAILSCALE_LINUX_IP>:8101"
docker compose -f docker-compose.yml -f docker-compose.biomodels.yml "${COMPOSE_PROFILES[@]}" ps
