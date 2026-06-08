#!/usr/bin/env bash
# Portable search index setup — Mac dev or Linux workstation.
# Uses local Docker Postgres + Qdrant when available; falls back to processed JSON stubs.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"

ENV_FILE="${OMEIA_ENV_FILE:-$ROOT/configs/.env}"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

echo "==> OMEIA portable search setup"
echo "    Repo: $ROOT"
echo "    Storage mode: ${OMEIA_STORAGE_MODE:-stub}"

if command -v docker >/dev/null 2>&1; then
  if docker compose ps --status running 2>/dev/null | grep -q postgres || true; then
    echo "==> Docker compose services already running"
  else
    echo "==> Starting Postgres + Qdrant (docker compose up -d)"
    docker compose up -d postgres qdrant 2>/dev/null || docker compose up -d 2>/dev/null || true
  fi
else
  echo "==> Docker not found — continuing with JSON stub indexes only"
fi

if [[ -f "$ROOT/configs/qdrant_collections.yaml" ]]; then
  echo "==> Ensuring Qdrant collections (named vector: text)"
  python3 "$ROOT/scripts/ingest/create_qdrant_collections.py" || echo "    (Qdrant offline — semantic search will use Postgres/JSON fallback)"
fi

if [[ -f "$ROOT/sql/141_search_platform.sql" ]]; then
  echo "==> Applying search platform SQL (141)"
  POSTGRES_CONN="${POSTGRES_CONN:-postgresql://farkki:farkki_dev_password@localhost:5432/farkki_ai}"
  if command -v psql >/dev/null 2>&1; then
    psql "$POSTGRES_CONN" -f "$ROOT/sql/141_search_platform.sql" || echo "    (SQL apply skipped — run manually on Linux workstation)"
  else
    echo "    psql not found — run sql/141_search_platform.sql when Postgres is available"
  fi
fi

echo "==> Building lab processed twins (if DATABASE_ROOT exists)"
export DATABASE_ROOT="${DATABASE_ROOT:-$ROOT/../OMEIA-database}"
if [[ -d "$DATABASE_ROOT" ]]; then
  python3 -m app_skeleton.api.database_processor --all --refresh 2>/dev/null || \
    python3 "$ROOT/omeia/api/database_processor.py" --all --refresh 2>/dev/null || \
    echo "    (processor skipped — use API POST /api/database/process-all when API is up)"
else
  echo "    DATABASE_ROOT not found at $DATABASE_ROOT — using committed processed JSON in repo"
fi

echo "==> Lab knowledge ingest (Qdrant + Postgres, best effort)"
python3 -c "
from app_skeleton.api.lab_knowledge_store import ingest_all_lab_sections
try:
    print(ingest_all_lab_sections(refresh_extract=False))
except Exception as e:
    print('Ingest skipped:', e)
" 2>/dev/null || echo "    (ingest skipped — run POST /api/knowledge/lab/ingest-all when API is up)"

echo "==> Done. Unified search: GET /api/platform/unified-search"
echo "    Index status: GET /api/platform/search-index-status"
