#!/usr/bin/env bash
# Reattach core OMEIA Docker services to infra/compose/docker-compose.yml.
# Safe: named volumes (postgres/qdrant/ollama data) are kept.
set -euo pipefail

# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../lib/common.sh"
ROOT="${OMEIA_REPO_ROOT:?run from repo: cd ~/data4TB/digital-notepad}"
cd "$ROOT"

COMPOSE_FILE="$ROOT/infra/compose/docker-compose.yml"
CORE=(omeia-ollama-proxy omeia-ollama omeia-qdrant omeia-postgres)

if [[ -f "$ROOT/configs/.env" && ! -f "$ROOT/.env" ]]; then
  ln -sf configs/.env "$ROOT/.env"
fi

echo "=== Reconcile OMEIA core Docker stack ==="
echo "  Repo: $ROOT"

for name in "${CORE[@]}"; do
  if docker inspect "$name" &>/dev/null; then
    echo "  remove container $name (volume data kept)"
    docker rm -f "$name" >/dev/null
  fi
done

docker compose -f "$COMPOSE_FILE" up -d postgres qdrant ollama ollama-proxy
docker compose -f "$COMPOSE_FILE" ps

echo ""
echo "=== Done ==="
echo "  curl -s http://127.0.0.1:6333/collections"
echo "  curl -s http://127.0.0.1:8000/ready"
