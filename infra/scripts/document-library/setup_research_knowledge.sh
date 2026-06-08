#!/usr/bin/env bash
# Research Knowledge Base setup — SQL migration, dataset seed, optional crawl + publications.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"

PYTHON="${ROOT}/.venv/bin/python3"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python3"
fi

ENV_FILE="${OMEIA_ENV_FILE:-$ROOT/configs/.env}"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

echo "==> OMEIA Research Knowledge Base setup"
echo "    Repo: $ROOT"

if command -v docker >/dev/null 2>&1; then
  docker compose up -d postgres qdrant 2>/dev/null || true
fi

echo "==> Applying sql/142_research_knowledge.sql (psycopg)"
"$PYTHON" - <<'PY'
from pathlib import Path
import psycopg

from omeia.api.supabase_config import postgres_conn

sql_path = Path("sql/142_research_knowledge.sql")
conn_str = postgres_conn()
print(f"    DSN: {conn_str.split('@')[-1] if '@' in conn_str else 'local'}")
with psycopg.connect(conn_str, connect_timeout=30) as conn:
    with conn.cursor() as cur:
        cur.execute(sql_path.read_text(encoding="utf-8"))
    conn.commit()
print("    Migration applied.")
PY

echo "==> Ensuring Qdrant research_knowledge collection"
"$PYTHON" -c "
from omeia.api.common import qdrant_client
from omeia.api.qdrant_research_indexer import ensure_research_collection
try:
    print(ensure_research_collection(qdrant_client))
except Exception as e:
    print('Qdrant skipped:', e)
" 2>/dev/null || echo "    (Qdrant offline — semantic search uses Postgres keyword fallback)"

echo "==> Seeding datasets"
"$PYTHON" -c "
from omeia.api.common import qdrant_client, llm_client
from omeia.api.research_knowledge_store import seed_datasets
try:
    print(seed_datasets(qdrant=qdrant_client, llm=llm_client))
except Exception as e:
    print('Dataset seed skipped:', e)
"

if [[ "${RESEARCH_KB_RUN_CRAWL:-true}" == "true" ]]; then
  MAX_PAGES="${RESEARCH_KB_SEED_MAX_PAGES:-${RESEARCH_KB_MAX_PUBLIC_PAGES:-100}}"
  echo "==> Crawling farkkilab.org (max ${MAX_PAGES} pages, best effort)"
  "$PYTHON" -c "
from omeia.api.common import qdrant_client, llm_client
from omeia.api.research_knowledge_store import crawl_farkkila_seeds
try:
    print(crawl_farkkila_seeds(max_pages=${MAX_PAGES}, qdrant=qdrant_client, llm=llm_client))
except Exception as e:
    print('Crawl skipped:', e)
" || true
fi

if [[ "${RESEARCH_KB_RUN_PUBLICATIONS:-true}" == "true" ]]; then
  echo "==> Discovering + ingesting publication metadata (best effort)"
  "$PYTHON" -c "
from omeia.api.common import qdrant_client, llm_client
from omeia.api.publication_fetcher import discover_priority_publications
from omeia.api.research_knowledge_store import ingest_publications
try:
    records = discover_priority_publications()
    print(ingest_publications(records, qdrant=qdrant_client, llm=llm_client))
except Exception as e:
    print('Publication ingest skipped:', e)
" || true
fi

echo "==> Status"
"$PYTHON" -c "
from omeia.api.common import qdrant_client
from omeia.api.research_knowledge_store import get_status
import json
print(json.dumps(get_status(qdrant=qdrant_client).model_dump(), indent=2))
" 2>/dev/null || true

echo "==> Done. API: GET /api/research-knowledge/status"
