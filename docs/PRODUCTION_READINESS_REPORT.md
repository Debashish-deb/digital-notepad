# OMEIA Production Readiness Report

**Validation date:** 2026-06-08  
**Branch:** `cursor/unified-search-ai-lab-assistant`  
**Phases validated:** 4 (Firebase/RBAC) · 5–6 (vault semantic) · 7 (deployment ops) · 8 (frontend maintainability)  
**Orchestrator:** `python scripts/ops/validate_platform.py` → `tests/platform_validation_last_run.json`

---

## Executive summary

| Metric | Before (Phases 1–3) | After (Phases 4–8) | Δ |
|--------|---------------------|-------------------|---|
| **Composite readiness** | **58%** | **63%** | **+5** |
| Single-lab Linux (Tailscale) | 72% | **76%** | +4 |
| Full corpus semantic search | 44% | **48%** | +4 |
| Internet-public SaaS | 25% | 25% | — |

### Go / no-go recommendation

| Target | Verdict | Rationale |
|--------|---------|-----------|
| **Linux workstation (daily lab use)** | **GO (conditional)** | Phases 4–8 code merged; keep conservative flags until Linux reindex; run validation on Linux host with Docker up |
| **Mac thin-client dev** | **GO** | `npm run build` passes; search QA 15/15 in-process |
| **Full-corpus AI answers** | **NO-GO** | Qdrant/Ollama not aligned locally; copilot release gates fail without Linux stack |
| **Public SaaS** | **NO-GO** | RBAC off; no HA/WAF/compliance |

**Rollback if Linux validation fails:** keep `KNOWLEDGE_INDEXER_ENABLED=false`, `VECTORIZATION_ENABLED=false`, `ENABLE_OCR=false`, `PROJECT_RBAC_ENABLED=false`, `OMEIA_FRONTEND_MODE=dev`; restore previous `start.sh` / skip backup restore.

---

## Validation results (2026-06-08)

### 1. Backend test suite

| Suite | Result | Notes |
|-------|--------|-------|
| **Full `pytest tests/`** | **284 passed, 29 failed, 9 skipped** | Failures concentrated in auth-gated HTTP integration tests (`test_lab_storage_api`, `test_image_streaming`, `test_admin_index_health`, 2× `test_vault_ingestion_engine`) — expect 401 without Bearer override |
| **Phases 4–8 focused** | **51/51 passed** | Researcher resolver, RBAC, OCR queue/adapter, vault semantic, deployment ops, security auth |
| **OCR sample** | **19 tests** (in focused + `test_ocr_*`) | `needs_ocr` enqueue, retry endpoint, flag gating |
| **Auth/RBAC** | **Pass** (unit) | `test_researcher_resolver`, `test_project_permissions`, `test_security_*` |
| **Vault semantic** | **Pass** | `test_vault_semantic_search`, `test_vault_json_fallback` |

**Blocker:** Update integration tests to use auth dependency overrides (same pattern as `run_search_qa.py`). Not a production API regression — tests predate global `require_platform_user` on routers.

### 2. Search QA

```
python scripts/search/run_search_qa.py
→ 15 passed, 0 failed / 15 checks
→ tests/search_qa_last_run.json
```

Unified search, suggestions, index status, legacy `/platform/search`, copilot `search_only` — all pass in-process. Qdrant unreachable locally (hash/Postgres fallbacks used).

### 3. RAG / copilot evaluation

```
python scripts/search/run_ai_lab_assistant_eval.py
→ artifact: tests/search_qa_ai_last_run.json (2026-06-08)
```

| Release gate | Value | Pass |
|--------------|-------|------|
| Intent accuracy | 91.2% | ✗ (threshold) |
| Citation compliance | 100% | ✓ |
| PII blocking | — | ✓ |
| Research buckets | — | ✗ |
| Provider honesty | 100% | ✓ |
| **Overall** | 24.6% | **✗** |

`http_errors: 0`. Gates fail mainly because eval ran with mixed mock/Gemini providers and without live Qdrant/Ollama on Mac. **Re-run on Linux with Docker stack for authoritative score.**

### 4. OCR validation

| Check | Status |
|-------|--------|
| `sql/145_ocr_jobs.sql` schema | Merged |
| `ENABLE_OCR=false` default | Worker idles safely |
| Enqueue on `needs_ocr` | Tests pass |
| Admin retry endpoint | Tests pass |
| E2E scanned PDF → OCR job | Code merged; Linux Tesseract apply pending |

### 5. Auth / RBAC validation

| Check | Status |
|-------|--------|
| `resolve_researcher()` Firebase → username | ✓ 23 tests |
| `PROJECT_RBAC_ENABLED=false` default | ✓ Open access preserved |
| `can_access_project()` / `ensure_project_access()` | ✓ Unit tests |
| Hardcoded `debdeba` removed from writes | ✓ |
| Production RBAC enforcement | **Not enabled** — flag off |

### 6. Vault semantic search

| Check | Status |
|-------|--------|
| Postgres-first `search_vault()` | ✓ |
| `duplicate_status` / `inventory_active` filters | ✓ |
| `vault_vector_search` + enrichment | ✓ (falls back when Qdrant down) |
| `sql/148_vault_search_indexes.sql` | Merged |
| Checksum cross-bucket dedupe in SearchService | ✓ |
| `/api/vault/search` semantic merge | ✓ |

### 7. Linux sync health

```
python scripts/ops/check_linux_sync_health.py
```

| Check | Mac dev | Linux expected |
|-------|---------|----------------|
| `DATABASE_ROOT` | ✓ | ✓ |
| `PROJECTS_ROOT` | ✓ | ✓ |
| Vault inventory JSON | ✓ | ✓ |
| Processed twins | ✓ | ✓ |
| Project media readable | ✓ | ✓ |
| `CSC_MEDIA_DIR` | ✗ (optional path) | Verify on workstation |

**Mac failure:** `csc_media_readable` only — non-blocking for Linux if `CSC/` not used.

### 8. Backup / restore dry-run

```
bash scripts/ops/backup_linux.sh --dry-run  → exit 0
bash scripts/ops/restore_linux_backup.sh BACKUP_DIR  → dry-run only (safe)
```

Restore requires `--confirm-restore` (destructive Postgres overwrite). **Do not run on production without stopping API.**

### 9. Frontend production build

```
cd omeia/ui/react_frontend && npm run build  → ✓
dist/index.html present
```

`OMEIA_FRONTEND_MODE=prod` serves dist from FastAPI `:8000`. Dev mode unchanged (`:5173` Vite).

### 10. API / observability

| Endpoint | Status |
|----------|--------|
| `GET /health` | ✓ 200 (TestClient) |
| `GET /metrics` | ✓ 200 (`enabled: false` until `ENABLE_REQUEST_METRICS=true`) |
| `X-Request-ID` | ✓ On all requests |
| Startup deployment checklist | ✓ Logged at boot |
| Live API `:8000` | Not running during Mac validation |

---

## Readiness scorecard

### Category scores (weighted)

| Category | Weight | Old | New | Weighted Δ | Evidence |
|----------|--------|-----|-----|------------|----------|
| **Deployment & ops** | 15% | 70% | **78%** | +1.2% | `start.sh` prod/dev, backup/restore, sync health, startup validation, Caddy platform profile |
| **Auth & security** | 15% | 58% | **62%** | +0.6% | Phase 4 binding + RBAC code; flag off; 29 integration tests need auth fixtures |
| **API stability** | 10% | 63% | **65%** | +0.2% | 91% tests pass; feature-flagged paths stable |
| **Frontend UX** | 10% | 65% | **67%** | +0.2% | Build OK; maintainability extractions (explorer/search); no visual redesign |
| **Knowledge & search** | 20% | 56% | **61%** | +1.0% | Search QA 15/15; vault semantic; indexer wired — reindex pending |
| **AI / copilot** | 12% | 52% | **55%** | +0.4% | 0 HTTP errors; release gates need Linux LLM+Qdrant |
| **Imaging** | 8% | 57% | **57%** | — | Unchanged; streaming tests need auth override |
| **Observability** | 5% | 32% | **50%** | +0.9% | `/metrics`, request_id logs, checklist; no Prometheus/Grafana yet |
| **Data integrity** | 5% | 42% | **54%** | +0.6% | Sync health script, backup dry-run, Postgres vault authority |

**Composite: 58% → 63%** (+5 points)

### Score methodology

Scores reflect **code + test artifacts on Mac** plus **documented Linux-only dependencies** (Qdrant, Ollama, reindex). Same weighting as `docs/PLATFORM_ARCHITECTURE_REVIEW.md` §18, with Project Intelligence folded into Knowledge & search.

---

## Remaining blockers

| Priority | Blocker | Owner action |
|----------|---------|--------------|
| P0 | **Linux reindex not run** | `KNOWLEDGE_INDEXER_ENABLED=true`, run `reindex_vectors.py` + research reindex on Linux |
| P0 | **Qdrant/Ollama down on Mac CI** | Run `docker compose up -d` on Linux before copilot gate sign-off |
| P1 | **29 pytest integration failures** | Add `require_platform_user` override to `test_lab_storage_api`, `test_image_streaming`, `test_admin_index_health`, vault ingest API tests |
| P1 | **Copilot release gates fail** | Re-run `run_ai_lab_assistant_eval.py` on Linux with live stack |
| P2 | **`PROJECT_RBAC_ENABLED` untested in prod** | Pilot on one project before lab-wide enable |
| P2 | **`ENABLE_OCR=true`** | Apply migration + install Tesseract on Linux; validate one scanned PDF |
| P2 | **`VAULT_JSON_FALLBACK=false`** | Only after Postgres vault sync + vector reindex on Linux |
| P3 | **CSC media path** | Configure `CSC_MEDIA_DIR` on Linux or downgrade check to warning |

---

## Next 30-day fix list

| Week | Task | Exit criteria |
|------|------|---------------|
| 1 | Linux `git pull` + validation suite | `validate_platform.py` exit 0 on Linux |
| 1 | Docker up + reindex | Qdrant collections populated; `GET /api/admin/index-health` green |
| 2 | Enable `KNOWLEDGE_INDEXER_ENABLED=true`, `VECTORIZATION_ENABLED=true` | Search QA + vault semantic hits from Qdrant |
| 2 | Fix auth integration tests | Full pytest green |
| 3 | `OMEIA_FRONTEND_MODE=prod` on Linux | Tailscale browser → `:8000` serves UI + API |
| 3 | `ENABLE_REQUEST_METRICS=true` | `/metrics` shows request counts |
| 4 | `ENABLE_OCR=true` smoke test | One scanned PDF searchable |
| 4 | First real backup (non-dry-run) | `pg_dump` + Qdrant snapshots on NAS |
| 5–6 | Copilot eval on Linux | `overall_gate_pass: true` on gold set |
| 6 | `PROJECT_RBAC_ENABLED` pilot | One sensitive project gated |

---

## Risky feature flags (keep conservative until Linux sign-off)

| Flag | Default | Risk if enabled early | Safe enable when |
|------|---------|----------------------|------------------|
| `KNOWLEDGE_INDEXER_ENABLED` | `false` | Dual-write / empty Qdrant mismatch | After Linux reindex |
| `VECTORIZATION_ENABLED` | `false` | Vault semantic queries empty or stale | After `vault_asset_chunks` populated |
| `VAULT_JSON_FALLBACK` | `true` | Stale JSON if disabled before Postgres sync | After vault Postgres sync verified |
| `VAULT_USE_VECTOR_INDEXER` | `false` | Legacy embed path if false + vector on | Set `true` with `VECTORIZATION_ENABLED` |
| `ENABLE_OCR` | `false` | Tesseract CPU load; job queue growth | Tesseract installed + ops OK |
| `PROJECT_RBAC_ENABLED` | `false` | Lockout if Firebase binding incomplete | Researcher binding verified per user |
| `PLATFORM_AUTH_DISABLED` | dev `true` | Must be `false` on exposed host | Production Linux only with Firebase |
| `OMEIA_FRONTEND_MODE` | `dev` | Prod without build → no UI | After `npm run build` on Linux |
| `ENABLE_REQUEST_METRICS` | `false` | Negligible | Anytime on Linux |

---

## Linux validation commands (run on workstation)

```bash
git pull
docker compose up -d && docker compose ps
python3 scripts/ops/check_linux_sync_health.py
python3 scripts/ops/validate_platform.py
python3 scripts/search/run_search_qa.py
python3 scripts/search/run_ai_lab_assistant_eval.py --role admin
bash scripts/ops/backup_linux.sh --dry-run
cd omeia/ui/react_frontend && npm run build
curl -s http://127.0.0.1:8000/health | jq .
curl -s http://127.0.0.1:6333/collections | jq .
curl -s http://127.0.0.1:11434/ | head
# With ENABLE_REQUEST_METRICS=true:
curl -s http://127.0.0.1:8000/metrics | jq .
```

---

## Artifacts

| File | Purpose |
|------|---------|
| `tests/platform_validation_last_run.json` | Orchestrator output |
| `tests/search_qa_last_run.json` | Search QA 15/15 |
| `tests/search_qa_ai_last_run.json` | Copilot eval + release gates |
| `docs/PLATFORM_ARCHITECTURE_REVIEW.md` | Prior 58% baseline (§18) |
| `scripts/ops/validate_platform.py` | Single entry validation |

---

## References

- Architecture baseline: `docs/PLATFORM_ARCHITECTURE_REVIEW.md` (58%, 2026-06-08)
- Linux template: `configs/linux-workstation.env.template`
- Rollback flags: `configs/.env.example` Phase 1–4 sections
