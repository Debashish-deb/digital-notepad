# 32 — Portable unified search setup

End-to-end search works **without permanent Linux storage** by using:

1. **Stub/local mode** (`OMEIA_STORAGE_MODE=stub`) — `DATABASE_ROOT` sibling folder + committed `processed_projects/*.json`
2. **Postgres** (optional Docker) — registry search, query log, RAG fallback
3. **Qdrant** (optional Docker) — semantic lab search; graceful fallback if offline

When the Linux workstation database is connected later, **only env vars change** — no code changes.

---

## Quick start (any workstation)

```bash
# 1. Copy env (git-safe template)
cp configs/.env.example configs/.env

# 2. Optional: start local services
docker compose up -d

# 3. One-shot search setup
chmod +x scripts/setup_search_portable.sh
./scripts/setup_search_portable.sh

# 4. Run API + frontend (existing dev flow)
./deploy/university-desktop/run_api_dev.sh
cd app_skeleton/ui/react_frontend && npm run dev
```

Open app → **⌘K** omnibox or **AI Lab Assistant → Advanced search**.

---

## Environment variables (portable)

| Variable | Default | Purpose |
|----------|---------|---------|
| `OMEIA_STORAGE_MODE` | `stub` | `stub` \| `local` \| `remote` (future mounts) |
| `DATABASE_ROOT` | `../OMEIA-database` | Lab files on disk (outside git) |
| `POSTGRES_CONN` | local Docker URI | Registry + query log |
| `QDRANT_URL` | `http://localhost:6333` | Semantic index |
| `DOCUMENT_QDRANT_VECTOR_NAME` | `text` | Named vector (must match collections YAML) |
| `DOCUMENT_QDRANT_COLLECTION` | `doc_chunks` | Collection for lab + ingest |

**Do not commit** `configs/.env` — only `.env.example`.

---

## Architecture (single search path)

```
⌘K GlobalSearchOverlay
    → GET /api/platform/unified-search
        → SearchService
            → lab: Qdrant → Postgres rag → processed JSON
            → file: section chunks + project twins
            → vault: metadata (domain filter via page_domain_id)
            → registry: notebook/wiki/decision/task (visibility filtered)
            → project: core.project metadata

AI Copilot POST /ask
    → same SearchService (+ RAGAgent project vectors)
    → mode=search_only: all authenticated users (no LLM)

Legacy (still work):
    /platform/search, /api/search, /api/knowledge/hybrid-search
```

---

## Linux workstation migration

When moving from MacBook dev to Linux:

1. Clone repo (same commit)
2. Set `configs/.env` or `/opt/omeia/deploy/university-desktop/.env`:
   - `OMEIA_STORAGE_MODE=local` or `remote`
   - `DATABASE_ROOT=/mnt/...` (real lab mount)
   - `POSTGRES_CONN` or `SUPABASE_DB_PASSWORD` + pooler vars
   - `QDRANT_URL=http://localhost:6333` (local on desktop) or remote URL
3. Run `sql/141_search_platform.sql` on Postgres
4. `./scripts/setup_search_portable.sh`
5. Re-ingest: `POST /api/knowledge/lab/ingest-all` (editor/admin)

Search UI and API contracts are unchanged.

---

## Fallback chain (no fake semantic search)

| Step | When used |
|------|-----------|
| Qdrant cosine | Qdrant up + ingest completed |
| Postgres `rag.document_chunk` token match | Qdrant down or empty |
| Processed JSON chunks | No Postgres RAG rows |
| Vault metadata ILIKE | Always for vault leg |
| ILIKE registry | Notebook/wiki/decision/task |

`/api/platform/search-index-status` reports live status.

---

## SQL migration

Apply on Postgres (once per environment):

```bash
psql "$POSTGRES_CONN" -f sql/141_search_platform.sql
```

Creates `platform.search_query_log` (+ optional `pg_trgm`).

---

## Related docs

- `docs/30_SEARCH_FUNCTIONALITY_AUDIT.md` — audit + bugs
- `docs/31_SEARCH_UNIFIED_AUDIT_AND_SOURCE_BUNDLE.md` — full bundle with source
- `configs/qdrant_collections.yaml` — `doc_chunks` named vector `text`
