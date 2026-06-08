#!/usr/bin/env bash
set -euo pipefail
echo "Farkki-AI development bootstrap"
echo "Documentation/synthetic mode only. Do not use with real patient data."
python - <<'PY'
print("Python OK")
PY
echo "Next:"
echo "  docker compose -f configs/docker-compose.dev.yml up -d"
echo "  python scripts/ingest/create_qdrant_collections.py"
echo "  python scripts/ops/validate_manifests.py"
