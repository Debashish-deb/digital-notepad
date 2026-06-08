#!/usr/bin/env bash
# Build and run the OMEIA imaging-worker Docker image (Mac or Linux workstation).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

COMPOSE_FILE="docker-compose.imaging.yml"

need=(
  "$COMPOSE_FILE"
  docker/imaging-worker/Dockerfile
  docker/imaging-worker/environment-core.yml
  docker/imaging-worker/environment-cycif-amd64.yml
  docker/imaging-worker/healthcheck.py
  omeia/api/imaging_capabilities.py
)

missing=0
for f in "${need[@]}"; do
  if [[ ! -f "$ROOT/$f" ]]; then
    echo "MISSING: $f"
    missing=1
  fi
done

if [[ "$missing" -ne 0 ]]; then
  echo ""
  echo "Copy these from your Mac OMEIA-AI repo, e.g.:"
  echo "  rsync -avz --relative \\"
  echo "    ./docker/imaging-worker \\"
  echo "    ./docker-compose.imaging.yml \\"
  echo "    ./omeia/api/imaging_capabilities.py \\"
  echo "    ./scripts/docker/build_imaging_worker.sh \\"
  echo "    user@linux-host:~/data4TB/digital-notepad/"
  exit 1
fi

echo "=== Building imaging-worker (standalone compose) ==="
docker compose -f "$COMPOSE_FILE" build imaging-worker

echo ""
echo "=== Running capability healthcheck ==="
docker compose -f "$COMPOSE_FILE" run --rm imaging-worker

echo ""
echo "Done. Slim build without napari:"
echo "  IMAGING_INCLUDE_NAPARI=0 $0"
