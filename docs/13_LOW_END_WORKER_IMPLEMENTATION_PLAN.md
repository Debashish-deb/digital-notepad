# 13 — LOW-END WORKER IMPLEMENTATION PLAN

**Authority:** `docs/12_LUMI_ARCHITECTURE_PACKAGE.md` and approved user brief.  
**Workers must not redesign** ontology, schema shape, page hierarchy, storage strategy, or auth model.

**Stop token:** `NEEDS_ARCHITECT_REVIEW` — use when brief conflicts with code or assignment is ambiguous.

---

## Global rules for every task

- Do not expose `original_path`, WebDAV URLs, or P-drive UNC paths in API JSON consumed by React.
- Do not store OME-TIFF, masks, videos, or large binaries in Supabase.
- Do not vectorize OME-TIFF, masks, videos, binary outputs, model weights.
- Do not delete or move files under `OMEIA-AI/database/`.
- Do not touch `OMEIA-AI/database/projects/**` content (read/process only).
- Match existing code style in `omeia/api/` and `react_frontend/src/`.
- Run smallest test set after each task; report `TASK COMPLETED` block.

---

## Phase 0 — Page domain registry (prerequisite for IA)

### LUMI-W001 — Page domain SQL migration

| Field | Value |
|-------|-------|
| **Phase** | 0 — page domain registry |
| **Objective** | Create `platform.page_domains` and `platform.page_sections` per architect §12 |
| **Inputs** | `docs/12_LUMI_ARCHITECTURE_PACKAGE.md` §2, §12; `navigation.js` |
| **Outputs** | `sql/112_page_domains.sql`; seed rows for 15 top domains + current nav children |
| **Acceptance** | Migration applies cleanly on local Postgres; seed count ≥ 40 sections |
| **Files** | Create `sql/112_page_domains.sql` only |
| **Tests** | `psql` or existing migrate script; no API yet |
| **Dependencies** | None |
| **Do not touch** | Existing 001–111 tables content |
| **Stop if** | Column names conflict with architect — return `NEEDS_ARCHITECT_REVIEW` |

### LUMI-W002 — Asset–page link columns

| Field | Value |
|-------|-------|
| **Phase** | 0 |
| **Objective** | Add nullable `page_domain_id`, `page_section_id` to `platform.raw_asset_vault` |
| **Inputs** | `sql/111_raw_asset_vault.sql`, section hints in inventory |
| **Outputs** | `sql/113_vault_page_links.sql` |
| **Acceptance** | FK to page tables; backfill script optional in W010 |
| **Dependencies** | LUMI-W001 |

---

## Phase 1 — Storage roots

### LUMI-W010 — Storage roots table + API enrichment

| Field | Value |
|-------|-------|
| **Phase** | 1 |
| **Objective** | Persist storage roots; extend `GET /api/storage/roots` with logical roles, no secrets |
| **Inputs** | `paths.py` STORAGE_PROVIDERS; brief DataCloud base URL as env only |
| **Outputs** | `sql/114_storage_roots.sql`; update `paths.py`, `main.py` |
| **Acceptance** | API returns configured flags + `root_logical_path` for DataCloud `/farkkila/LAB-ASSISTANT-PLATFORM` when env set |
| **Tests** | `tests/test_lab_storage_api.py` + one new test for roots schema |
| **Dependencies** | LUMI-W001 optional |
| **Do not touch** | Connector implementation |

---

## Phase 2 — Raw knowledge vault

### LUMI-W020 — Vault audit events

| Field | Value |
|-------|-------|
| **Phase** | 2 |
| **Objective** | `platform.vault_audit_event` on upsert/review status change |
| **Outputs** | `sql/115_vault_audit.sql`; hook in `raw_vault_store.sync_inventory_to_postgres` |
| **Acceptance** | Sync writes audit row per batch |
| **Dependencies** | 111 applied |

### LUMI-W021 — MIME detection at inventory build

| Field | Value |
|-------|-------|
| **Phase** | 2 |
| **Objective** | Add `mime_type` to inventory + vault table |
| **Outputs** | Update `build_raw_asset_inventory.py`, migration, sync mapping |
| **Acceptance** | PDF/DOCX/XLSX common types populated |
| **Tests** | Unit test on `classify_asset_type` sample paths |

---

## Phase 3 — Asset registry

### LUMI-W030 — Public vault DTO hardening

| Field | Value |
|-------|-------|
| **Phase** | 3 |
| **Objective** | Ensure all vault/search/review API paths use `_public_row`; add `page_domain` labels via join |
| **Inputs** | `raw_vault_store.py`, W001 tables |
| **Outputs** | Updated store + `main.py` |
| **Acceptance** | Grep API responses: no `/Users/`, no `debdeba@`, no `remote.php` |
| **Tests** | Extend `test_lab_storage_api.py` |
| **Dependencies** | LUMI-W001, W002 |

### LUMI-W031 — Data & Storage read-only UI

| Field | Value |
|-------|-------|
| **Phase** | 3 |
| **Objective** | React screen: vault summary, search, review queue sample, storage roots |
| **Outputs** | `DataStorageScreen.jsx`, nav entry under new top-level or Projects & Data |
| **Acceptance** | Calls `/api/vault/summary`, `/api/vault/search`, `/api/storage/roots` only |
| **Dependencies** | W030 |
| **Stop if** | Architect has not approved nav placement — `NEEDS_ARCHITECT_REVIEW` |

---

## Phase 4 — Document registry

### LUMI-W040 — Unify document registry view

| Field | Value |
|-------|-------|
| **Phase** | 4 |
| **Objective** | Single `GET /api/documents/registry` merging `rag.document_source` + lab corpus filter |
| **Inputs** | `lab_knowledge_store.py`, `040_rag_audit_security_schema.sql` |
| **Outputs** | New endpoint; no schema breaking changes |
| **Acceptance** | Returns document_code, title, section_id, chunk_count, sensitivity, review_status |
| **Tests** | TestClient with mocked or live DB |

### LUMI-W041 — Link vault assets to documents

| Field | Value |
|-------|-------|
| **Phase** | 4 |
| **Objective** | After lab ingest, store `vault_asset_id` in `rag.document_source.metadata` |
| **Dependencies** | W030, existing ingest |
| **Stop if** | Requires redesign of document_code — `NEEDS_ARCHITECT_REVIEW` |

---

## Phase 5 — User registry

### LUMI-W050 — Allowed users + registration request tables

| Field | Value |
|-------|-------|
| **Phase** | 5 |
| **Objective** | `platform.allowed_email`, `platform.registration_request` per brief |
| **Outputs** | `sql/116_user_registry.sql` |
| **Acceptance** | Matches Firebase email allowlist workflow (pending → approved) |
| **Do not touch** | Firebase SDK yet |

---

## Phase 6 — Permissions

### LUMI-W060 — Firebase auth middleware stub

| Field | Value |
|-------|-------|
| **Phase** | 6 |
| **Objective** | Verify Firebase JWT on protected routes; dev bypass flag `APP_ENV=development` |
| **Outputs** | `auth/firebase_verify.py`, wire to `main.py` dependency |
| **Stop if** | Service account JSON location unknown — `NEEDS_ARCHITECT_REVIEW` |

### LUMI-W061 — Map Firebase UID to `security.user_account`

| Field | Value |
|-------|-------|
| **Phase** | 6 |
| **Objective** | `external_subject` = Firebase UID; email from token |
| **Dependencies** | W050, W060 |

### LUMI-W062 — Project access enforcement

| Field | Value |
|-------|-------|
| **Phase** | 6 |
| **Objective** | Enforce `security.project_access_policy` on `/api/projects/*` and project-files |
| **Dependencies** | W061 |
| **Stop if** | Default policy for dev users unclear — `NEEDS_ARCHITECT_REVIEW` |

---

## Phase 7 — DataCloud WebDAV connector

### LUMI-W070 — WebDAV connector module

| Field | Value |
|-------|-------|
| **Phase** | 7 |
| **Objective** | `storage/datacloud_webdav.py`: PROPFIND list, GET stream, path under `/farkkila/LAB-ASSISTANT-PLATFORM` |
| **Inputs** | Env: `DATACLOUD_WEBDAV_URL`, app password — **NEEDS_USER_CONFIRMATION** |
| **Outputs** | Server-side only; `GET /api/storage/datacloud/list?logical_path=` |
| **Acceptance** | No path in response except logical relative path |
| **Do not touch** | Frontend direct WebDAV |

### LUMI-W071 — Mirror sync job (optional)

| Field | Value |
|-------|-------|
| **Phase** | 7 |
| **Objective** | `POST /api/storage/datacloud/sync-inventory` walks WebDAV, upserts vault |
| **Dependencies** | W070, W020 |

---

## Phase 8 — P-drive connector

### LUMI-W080 — P-drive SMB connector stub

| Field | Value |
|-------|-------|
| **Phase** | 8 |
| **Objective** | `storage/pdrive_smb.py` + env `PDRIVE_SMB_ROOT`; list/read behind same API shape as W070 |
| **Stop if** | UNC path not provided — `NEEDS_ARCHITECT_REVIEW` |

---

## Phase 9 — R2 connector

### LUMI-W090 — R2 preview upload

| Field | Value |
|-------|-------|
| **Phase** | 9 |
| **Objective** | Generate thumbnail for PDF/image; upload to R2; store `preview_r2_key` on vault row |
| **Outputs** | `storage/r2_preview.py`, `GET /api/assets/{id}/preview-url` (signed) |
| **Do not touch** | Storing originals in R2 |

---

## Phase 10 — Metadata extraction

### LUMI-W100 — Extraction job registry

| Field | Value |
|-------|-------|
| **Phase** | 10 |
| **Objective** | `platform.ingestion_jobs` + status on vault `extraction_status` |
| **Reuse** | `document_extraction.py`, `database_processor.py` |

---

## Phase 11 — Ingestion manifest generator

### LUMI-W110 — Manifest export API

| Field | Value |
|-------|-------|
| **Phase** | 11 |
| **Objective** | `GET /api/vault/manifest.json` paginated manifest for workers |
| **Acceptance** | Matches §7 manifest schema in doc 12 |

---

## Phase 12 — Chunking pipeline

### LUMI-W120 — Chunk pipeline idempotency

| Field | Value |
|-------|-------|
| **Phase** | 12 |
| **Objective** | Ingest uses stable `document_code`; re-ingest skips unchanged checksum |
| **Dependencies** | W041 |

---

## Phase 13 — Vector queue

### LUMI-W130 — Vectorization job queue

| Field | Value |
|-------|-------|
| **Phase** | 13 |
| **Objective** | `platform.vectorization_jobs` + worker script consuming eligible vault rows only |
| **Reuse** | `rag.embedding_job`, Qdrant `doc_chunks` |
| **Tests** | Assert OME-TIFF rows never queued |

---

## Phase 14 — Search layer

### LUMI-W140 — Unified search API

| Field | Value |
|-------|-------|
| **Phase** | 14 |
| **Objective** | `GET /api/search?q=&mode=exact|metadata|semantic|hybrid` |
| **Reuse** | `search_vault`, `search_lab_knowledge` |
| **Dependencies** | W130 optional |

### LUMI-W141 — Page-scoped search

| Field | Value |
|-------|-------|
| **Phase** | 14 |
| **Objective** | Filter by `page_domain_id` from nav context |
| **Dependencies** | W001, W140 |

---

## Phase 15 — Admin dashboard

### LUMI-W150 — Administration screen (backend-first)

| Field | Value |
|-------|-------|
| **Phase** | 15 |
| **Objective** | APIs: allowlist CRUD, registration approve/deny, ingestion job list, review queue |
| **UI** | `AdministrationScreen.jsx` — minimal tables |
| **Dependencies** | W050, W060, W100, W130 |

---

## Phase 16–20 — Page APIs & frontend integration

### LUMI-W160 — Navigation alignment

| Field | Value |
|-------|-------|
| **Objective** | Add nav: Data & Storage, Administration; map `databaseSections.js` to `page_section_id` |
| **Stop if** | Research Hub split not approved — `NEEDS_ARCHITECT_REVIEW` |

### LUMI-W161 — Overview subpage stubs

| Field | Value |
|-------|-------|
| **Objective** | Register missing sections (Cleaning → `overview_cleaning` done); add Safety, Contacts as sections when folders exist |

### LUMI-W162 — Projects subnav stubs

| Field | Value |
|-------|-------|
| **Objective** | Project detail tabs: Files (exists), Documents (registry), Data (datasets API), Members (catalog) |

### LUMI-W163 — Remove dead code references

| Field | Value |
|-------|-------|
| **Objective** | Grep `database/tree`, `DatabaseSectionBrowser`; ensure none remain |

---

## Validation checklist (run after each phase)

```bash
cd farkki_ai_platform_blueprint
.venv-local/bin/python -m unittest tests.test_lab_storage_api -v
.venv-local/bin/python scripts/ops/validate_platform.py http://127.0.0.1:8000
```

---

## Current baseline (already done — do not redo)

| Item | Evidence |
|------|----------|
| Lab section path fix | `database_sections.py` |
| Lab knowledge ingest/search | `lab_knowledge_store.py`, 705 docs / 4137 chunks |
| Vault JSON + Postgres 4800 rows | `raw_asset_vault`, `/api/vault/*` |
| Lab file browser deprecated | 410 on tree/read/extract/asset |
| Project folder API | `/api/project-files/*` |
| Hybrid search endpoint | `/api/knowledge/hybrid-search` |

Workers should **extend**, not replace, these unless task says refactor.

---

## Task dependency graph (summary)

```text
W001 → W002 → W030 → W031
W001 → W141
W010 → W070 → W071
W050 → W060 → W061 → W062 → W150
W100 → W110 → W120 → W130 → W140
W090 depends on W070 or local extract path
```

---

## Expected worker output format

```text
TASK COMPLETED

Task: LUMI-W0xx
Files changed:
Tables changed:
APIs changed:
Page/domain affected:
Storage affected:
Tests performed:
Known issues:
Questions:
Next recommended task:
```

---

*Architect package: `12_LUMI_ARCHITECTURE_PACKAGE.md`. Questions 1–7 in §23 require user input before W070, W050, W160.*
