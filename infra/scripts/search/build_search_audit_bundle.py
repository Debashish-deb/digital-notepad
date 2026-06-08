#!/usr/bin/env python3
"""Build unified search audit markdown with embedded source snapshots."""
from __future__ import annotations

from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs" / "31_SEARCH_UNIFIED_AUDIT_AND_SOURCE_BUNDLE.md"

MASTER_AUDIT = ROOT / "docs" / "30_SEARCH_FUNCTIONALITY_AUDIT.md"

BACKEND_AUDIT = """# Backend Search Audit — OMEIA-AI

## Architecture overview

Search is fragmented across **six data planes**, not one unified index:

| Plane | Index store | Search style |
|-------|-------------|--------------|
| Lab knowledge | Qdrant `doc_chunks` + Postgres `rag.*` + local processed JSON | Semantic (hashed embed) + keyword fallback |
| Vault assets | Postgres `platform.raw_asset_vault` + JSON inventory | Metadata/path keyword |
| Digitalization (legacy) | Postgres `platform.knowledge_assets` + `extracted_texts` | ILIKE on filename/path/text |
| Digitalization (canonical) | Postgres `platform.canonical_document` | **List/filter only — no text search** |
| Platform research | Postgres notebook/wiki/decisions | ILIKE |
| Project workspace | Processed JSON twins + optional Postgres `rag.*` | Client-side / ingest only; **no search API** |

Router registration: `omeia/api/main.py` — all API routers except `health` get `Depends(require_platform_user)`.

---

## Core implementation files

| Path | Role |
|------|------|
| `omeia/api/routers/knowledge.py` | Lab, hybrid, unified, database search endpoints |
| `omeia/api/lab_knowledge_store.py` | Lab ingest + `search_lab_knowledge()` |
| `omeia/api/database_processor.py` | Processed JSON build, `search_section_chunks()`, section document filter |
| `omeia/api/raw_vault_store.py` | `search_vault()` Postgres + JSON fallback |
| `omeia/api/routers/vault.py` | Vault + digitalize search routes |
| `omeia/api/project_digitalization_engine.py` | `search_knowledge()` for legacy digitalization |
| `omeia/api/routers/digitalization.py` | Canonical documents (no `q` search) |
| `omeia/api/routers/research.py` | Notebook/wiki/decisions/platform unified search |
| `omeia/api/agents.py` | `RAGAgent.retrieve()` — copilot Qdrant retrieval |
| `omeia/api/routers/copilot.py` | `/ask` RAG + `/features/similarity` |
| `omeia/api/project_knowledge_extractor.py` | Project file ingest → Postgres only |
| `omeia/api/routers/datapad.py` | Project file list/preview (no search) |
| `omeia/api/feature_warehouse.py` | Sample similarity (Qdrant `feature` vectors) |
| `omeia/api/llm_client.py` | `embed()` — deterministic hashed 384-d vectors |
| `omeia/security/auth.py` | `require_platform_user` |
| `omeia/api/auth_firebase.py` | `require_firebase_user` |

Duplicate unmounted copies exist (`knowledge copy.py`, `vault copy.py`, `research copy.py`) — not wired in `main.py`.

---

## Endpoint catalog

### 1. Knowledge / lab search (`knowledge.py`)

| Endpoint | Auth | Params | Behavior |
|----------|------|--------|----------|
| `GET /api/knowledge/lab/search` | `require_platform_user` (router) | `q` (min 2), `section_id?`, `limit` 1–50 | Canonical lab search via `search_lab_knowledge()` |
| `GET /api/knowledge/hybrid-search` | same | `q`, `section_id?`, `limit` 1–40 | Lab semantic + vault metadata; vault limit = `max(5, limit//2)` |
| `GET /api/search` | same | `q`, `mode`=`hybrid\\|semantic\\|metadata\\|exact`, `section_id?`, `page_domain_id?`, `limit` | Mode-gated merge of lab + vault |
| `GET /api/database/search` | same | `q`, `section_id?`, `limit` | **Deprecated**; lab search, falls back to `search_section_chunks()` on processed JSON |
| `GET /api/lab/section/{id}/documents` | same | `q?`, `offset`, `limit` | Keyword filter on local `document_index` in processed twin |

**`search_lab_knowledge()` flow** (`lab_knowledge_store.py`):

1. Embed query with `LLMClient.embed()` (hashed, 384-d, no external API).
2. Qdrant `doc_chunks`, vector name `"text"`, filter `corpus=lab_operations`, optional `section_id`.
3. On Qdrant failure: Postgres `rag.document_chunk` keyword scoring (`LIKE` per token ≥3 chars).
4. Returns: `rank`, `score`, `citation`, `excerpt`, `where_to_find`, `section_id`, `relative_path`.

### 2. Vault search (`vault.py`)

| Endpoint | Auth | Params | Behavior |
|----------|------|--------|----------|
| `GET /api/vault/search` | `require_platform_user` **+** `_FIREBASE_PROTECTED` | `q` (min 0!), `domain?`, `project_hint?`, `review_status?`, `extraction_status?`, `vector_status?`, `uncategorized_only`, `limit` 1–100 | Metadata search on `platform.raw_asset_vault`; JSON inventory fallback |

**Ranking:** Postgres — `ORDER BY assignment_confidence DESC, logical_path`. Tokens matched via `ILIKE` on `logical_path || filename`. JSON fallback — token hit score (2.0 per token), no vector search despite `vector_status` filter.

### 3. Digitalization search

| Endpoint | Auth | Params | Behavior |
|----------|------|--------|----------|
| `GET /api/digitalize/search` | platform + Firebase | `q` (min 1), `uncategorized_only`, `limit` 1–200 | ILIKE on `knowledge_assets` + latest `extracted_texts` |
| `GET /api/digitalization/documents` | platform only | `offset`, `limit`, `domain?`, `document_type?`, `needs_review?` | **No text query** — paginated list from `canonical_document` |

### 4. Platform research search (`research.py`)

| Endpoint | Auth | Params | Behavior |
|----------|------|--------|----------|
| `GET /notebook/search` | platform | `q` (min 2), `project_code?`, `entry_type?`, `limit` | ILIKE title/content/conclusions/issues/next_steps + exact tag match |
| `GET /wiki/search` | platform | `q`, `wiki_type?`, `project_code?`, `limit` | ILIKE title/content |
| `GET /decisions/search` | platform | `q`, `project_code?`, `limit` | ILIKE title/details/rationale/alternatives |
| `GET /platform/search` | platform | `q`, `project_code?`, `include`=`notebook,wiki,decisions`, `limit` | UI global search; separate buckets, **no cross-type ranking** |

All order by recency (`created_at` / `updated_at` / `decision_date`), not text relevance.

### 5. Copilot / RAG (not REST search, but retrieval)

| Endpoint | Auth | Behavior |
|----------|------|----------|
| `POST /ask` | platform + **editor/admin** | `RAGAgent.retrieve()` on Qdrant `doc_chunks` + `search_lab_knowledge()` merge |
| `POST /features/similarity` | platform | `find_similar_samples()` — Qdrant `FEATURE_COLLECTION` or CSV cosine fallback |

`RAGAgent` filters by `project_codes`; lab corpus (`scope=lab`) always passes filter.

### 6. Project file “search” — gap

| Endpoint | Search? |
|----------|---------|
| `GET /api/project-files/list/{project_code}` | Returns full file list from disk walk — **no `q` param** |
| `POST /api/projects/{project_code}/knowledge/ingest` | Ingests to Postgres `rag.*` only — **no Qdrant vectors** |

---

## How indexes are built

### Lab pipeline

```
Disk (DATABASE_ROOT)
 → database_processor.py (extract/chunk)
 → omeia/data/processed_projects/lab__*.json + *.chunks.jsonl
 → lab_knowledge_store.ingest_section_to_database()
 → Postgres rag.document_source + rag.document_chunk
 → Qdrant doc_chunks (named vector "text", corpus=lab_operations)
```

Trigger endpoints: `POST /api/database/process-all`, `POST /api/knowledge/lab/ingest-all`, per-section variants (editor/admin).

### Vault pipeline

```
Disk scan (vault_ingestion_engine)
 → raw_asset_inventory.json (omeia/data/)
 → platform.raw_asset_vault (Postgres)
```

Search is **metadata-only**; `vector_status` tracks indexing state but vault search does not query vectors.

### Document ingest (vault router)

`POST /ingest-document` chunks uploaded text → Qdrant `doc_chunks` with **flat** `vector=vec` (not `{"text": vec}`), plus `platform.document_ingestion` row.

### Project knowledge

`extract_and_ingest_project()` walks project folder → Postgres `rag.*` with `corpus=project_workspace`. **No Qdrant upsert** in that module.

### Embeddings

All local indexing uses `LLMClient.embed()` — Blake2b hashed bag-of-tokens, L2-normalized. Deterministic and offline-safe, but **not true semantic embeddings**.

---

## Auth & permissions summary

| Layer | Mechanism | Notes |
|-------|-----------|-------|
| Router default | `require_platform_user` | Firebase bearer; dev bypass via `PLATFORM_AUTH_DISABLED` |
| Vault/storage/digitalize search | `+ _FIREBASE_PROTECTED` | Effectively double auth (same Firebase check, two dependency paths) |
| Ingest/rebuild | `require_role(["editor","admin"])` | Lab process, vault rebuild, project write |
| Copilot `/ask` | editor/admin only | Researchers cannot query RAG via API |
| Health routes | **No auth** | No search endpoints there |

**Gaps:** Notebook/wiki/decision search returns `visibility_level` but **does not filter** on it — potential over-exposure if restricted entries exist.

---

## Query parameters, ranking, filters

| System | Ranking | Filters |
|--------|---------|---------|
| Lab Qdrant | Cosine similarity score | `section_id`, `corpus=lab_operations` |
| Lab Postgres fallback | Token hit count | `section_id`, tokens ≥3 chars |
| Vault | `assignment_confidence`, path alpha | domain, project_hint, review/vector/extraction status, uncategorized |
| Digitalize legacy | `updated_at DESC` | uncategorized_only |
| Platform research | Recency only | project_code, entry_type/wiki_type |
| Unified `/api/search` | Per-subsystem | `mode` gates which backends run |
| Section documents | Substring token match | section scoped |

**Dead parameter:** `page_domain_id` on `GET /api/search` is echoed in the response but **never applied** to vault or lab queries.

**Mode naming:** `mode=exact` still runs `search_vault()` under `metadata`/`exact`/`hybrid` — it is not “exact string match”; lab side is explicitly emptied for `exact`.

---

## Known limitations

1. **No unified index** — UI uses `/platform/search` (Postgres ILIKE) and `/api/knowledge/hybrid-search` (vectors + vault) separately.
2. **No project-file search API** — only full list + client filter or processed twin browse.
3. **Weak embeddings** — hashed local vectors limit semantic quality.
4. **Two digitalization schemas** — `platform.knowledge_assets` (searchable) vs `platform.canonical_document` (list only).
5. **Vault search is not vector search** — `vector_status` is a filter, not retrieval.
6. **Project ingest incomplete for RAG** — Postgres chunks without Qdrant means copilot may miss project docs.
7. **Processed JSON dependency** — `search_section_chunks()` and section document search require prior `database_processor` run.
8. **Empty vault query allowed** — `q=""` returns filter-matched inventory (browse mode).
9. **No Postgres full-text** — no `tsvector`, no ranked ILIKE beyond simple patterns.
10. **Copilot role gate** — search-via-ask limited to editors/admins.

---

## Visible bugs / inconsistencies

1. **Qdrant vector schema conflict** — Lab ingest uses named vector `"text"` (`lab_knowledge_store.py`); `/ingest-document` creates collection with flat `VectorParams` and upserts flat vectors (`vault.py`). Mixed schemas in one `doc_chunks` collection can break retrieval depending on creation order.

2. **`page_domain_id` unused** in unified search (`knowledge.py`).

3. **`hybrid-search` omits shared clients** — calls `search_lab_knowledge(q, ...)` without `qdrant=qdrant_client, llm=llm_client`, unlike `/api/knowledge/lab/search`.

4. **Notebook search ignores `visibility_level`** — returns all matching rows regardless of access level.

5. **`extract_and_ingest_project` name vs behavior** — ingests to SQL only; semantic search path (`search_lab_knowledge` filters `lab_operations` corpus) won't find `project_workspace` chunks.

6. **Tag search bug risk** in notebook search: `%s = ANY(ne.tags)` uses raw `q`, not `pattern` — only exact tag match, not substring.

7. **Hardcoded researcher** in vault `ingest-document` and several research mutations (`username = 'debdeba'`) — unrelated to search but affects ingest audit trail.

8. **Duplicate router copies** in repo may confuse audits (not mounted).

---

## Data sources indexed (quick reference)

| Source | Location |
|--------|----------|
| Lab section files | `DATABASE_ROOT` → processed JSON → `rag.*` + Qdrant |
| Vault filesystem | `DATABASE_ROOT` / projects → `raw_asset_vault` + JSON inventory |
| Uploaded docs | `platform.document_ingestion` + Qdrant `doc_chunks` |
| Legacy digitalization | `platform.knowledge_assets`, `extracted_texts` |
| Canonical digitalization | `platform.canonical_document`, `document_chunk` (no search endpoint) |
| Research notes | `platform.notebook_entry`, `research_wiki`, `decision_registry` |
| Project folders | Processed twins under `processed_projects/`; optional `rag.*` without vectors |
| Clinical features | CSV matrices + Qdrant feature collection (similarity only) |

---

## Frontend wiring (for context)

- Global overlay: `GET /platform/search` — `GlobalSearchOverlay.jsx`
- Knowledge screen: `/api/knowledge/hybrid-search`, `/api/search` — `KnowledgeSearchScreen.jsx`
- Project browser vault tab: `/api/vault/search` — `ProjectFolderBrowser.jsx`

---

## Recommended follow-ups

1. Add `GET /api/project-files/search` over processed `document_index` or Postgres `rag.*` with `corpus=project_workspace`.
2. Unify Qdrant vector naming (always `{"text": vec}`) and re-index.
3. Wire `page_domain_id` into vault search or remove the parameter.
4. Add `visibility_level` filters to platform search endpoints.
5. Expose `q` on `/api/digitalization/documents` or route to canonical chunk search.
6. Pass shared `qdrant_client`/`llm_client` in hybrid-search for consistency.
"""

FRONTEND_AUDIT = """# OMEIA-AI React Frontend — Search Audit

Search in this frontend is **not one system** — it is four loosely related tiers with different data sources, UX patterns, and almost no shared state.

---

## 1. Component map

| Component | Path | Search type | Scope |
|-----------|------|-------------|-------|
| **GlobalSearchOverlay** | `src/components/GlobalSearchOverlay.jsx` | Server debounced (300ms) | Notebook, wiki, decisions, tasks (Postgres) |
| **KnowledgeSearchScreen** | `src/screens/KnowledgeSearchScreen.jsx` | Server on Enter/button | Lab corpus + vault (semantic/hybrid) |
| **Sidebar search button** | `src/components/Sidebar.jsx` | Opens overlay only | Global registry |
| **DocumentFileSearch** | `src/components/DocumentFileSearch.jsx` | Controlled input UI | Reused by module browsers |
| **LabDocumentsBrowser** | `src/components/LabDocumentsBrowser.jsx` | Instant client filter | Path + display title per section |
| **ProjectDocumentsBrowser** | `src/components/ProjectDocumentsBrowser.jsx` | Same | Per-project workspace files |
| **LabSectionTwinPanel** | `src/components/LabSectionTwinPanel.jsx` | Client filter on static catalog | Section-scoped static JSON |
| **LabKnowledgeScreen** | `src/screens/LabKnowledgeScreen.jsx` | Client filter (legacy path) | Static `/database/catalog.json` |
| **ProjectFolderBrowser** | `src/components/ProjectFolderBrowser.jsx` | Client filter + vault excerpt lookup | Project twin folders |
| **ChatWidget** | `src/components/ChatWidget.jsx` | Implicit RAG via `/ask` | Project-scoped vectors + lab knowledge |
| **FeatureClinicalScreen** | `src/screens/FeatureClinicalScreen.jsx` | Sample similarity (unrelated) | Clinical feature vectors |
| **LabCorpusBrowser** | `src/components/LabCorpusBrowser.jsx` | **No search** | Section browser only |

**Consumers of `LabDocumentsBrowser`:** `OrdersBillingBrowser.jsx`, `OrdersArchiveBrowser.jsx`, `WetLabProtocolsBrowser.jsx`, `StorageTabDocuments.jsx`, `SectionDocumentsScreen.jsx`, `OverviewDocumentsScreen.jsx`, `LabDocumentsHub.jsx`

---

## 2. User flows

### A. Global registry search (primary “Search Registry”)

1. User clicks Sidebar “Search Registry” or presses **⌘K / Ctrl+K** (`App.jsx`).
2. `GlobalSearchOverlay` opens, input auto-focused, query/results cleared.
3. After **300ms debounce**, `GET /platform/search?q=…` via `apiGet`.
4. Results grouped: Notebook → Wiki → Decisions → Tasks.
5. Click row → expand/collapse inline (no navigation, no deep link).
6. Close via backdrop click or X. **No Escape handler.**

### B. Per-module document file search (most common UX)

1. User opens any lab/project document module.
2. `DocumentFileSearch` appears in module header or inline.
3. Keystrokes update query **immediately** (no debounce).
4. `filterDocsByQuery()` matches **path + display title only** — not excerpt/body.
5. Selecting a file opens preview pane; search state is **not persisted** across tab changes.

### C. Legacy static catalog search (`LabKnowledgeScreen`)

Filters `/database/catalog.json` by title/path, section-scoped by tab. Parallel older UX to `LabDocumentsBrowser` processed twins.

### D. Knowledge / hybrid API search (`KnowledgeSearchScreen`)

1. Manual query (min 2 chars) + mode select + Search button or Enter.
2. Calls either `/api/knowledge/hybrid-search` or `/api/search`.
3. Renders flat lists — **not clickable**, no navigation to documents.

**Not reachable from sidebar** — screen case exists in `App.jsx` but **no nav entry** in `navigation.js`.

### E. AI copilot “search”

1. User opens **AI Assistant → Chat Copilot**.
2. Optional project scope chips (RAG scope).
3. Submit question → `POST /ask` with `{ question, project_codes, mode: 'documentation_only' }`.
4. Backend runs vector RAG + `search_lab_knowledge` + Postgres metadata.
5. Answer + collapsible sources with scores shown in chat.

No bridge from global/file search results → “Ask AI about this.”

### F. Vault excerpt lookup (preview aid, not user search)

`ProjectFolderBrowser.fetchVaultExcerpt()` calls `GET /api/vault/search?q=…` using filename stem to enrich file preview text.

---

## 3. API calls

| Endpoint | Called from | Method | Purpose |
|----------|-------------|--------|---------|
| `/platform/search` | `GlobalSearchOverlay.jsx` | GET `q` | Postgres ILIKE notebook/wiki/decisions |
| `/api/search` | `KnowledgeSearchScreen.jsx` | GET `q, mode, limit` | Unified semantic/metadata/hybrid |
| `/api/knowledge/hybrid-search` | `KnowledgeSearchScreen.jsx` | GET `q, limit` | Lab + vault hybrid |
| `/api/vault/search` | `ProjectFolderBrowser.jsx` | GET `q, limit` | Preview excerpt lookup |
| `/ask` | `ChatWidget.jsx` | POST | RAG Q&A |
| `/ingest-document` | `AiLabAssistantScreen.jsx` | POST | Index text for RAG |
| `/features/similarity` | `FeatureClinicalScreen.jsx` | POST | Clinical sample similarity |

**`ApiContext.jsx`** — no search helpers. **`client.js`** — generic `apiGet`/`apiFetch`; no search-specific utilities, caching, or abort-on-new-query.

---

## 4. localStorage, routing, debouncing, rendering

### localStorage
- `farkki_nav_v2` — nav only; **not search state**
- `farkki_id_token` — auth for API calls
- **No search query/history persistence**

### Routing
- Global search: overlay modal — **no URL/hash/query param**
- `KnowledgeSearchScreen`, `lab_corpus`, `ingestion_dashboard`, `digitalization` — switch cases exist, no sidebar routes

### Debouncing
| Location | Debounce |
|----------|----------|
| `GlobalSearchOverlay.jsx` | **300ms** (only server search) |
| All `DocumentFileSearch` consumers | **None** |
| `KnowledgeSearchScreen` | **None** — explicit submit |

---

## 5. AI integration points

| Integration | Status |
|-------------|--------|
| Chat copilot RAG | **Live** — `ChatWidget` → `/ask` |
| Document ingest for RAG | **Live** — `AiLabAssistantScreen` ingest tab |
| Global search → AI | **Missing** |
| KnowledgeSearchScreen → AI | **Missing** |
| File search → AI | **Missing** |
| Shared project scope | Partial — ChatWidget has project chips; global/file search ignore project context |

---

## 6. Global vs per-module search — gap analysis

| Dimension | Global | Per-module | Knowledge API | AI |
|-----------|--------|------------|---------------|-----|
| Data source | Postgres structured records | Processed twin JSON / static catalog | Vector index + vault metadata | Qdrant + lab knowledge + DB counts |
| Content searched | Notebook/wiki/decisions (intended: tasks) | Filename + path (+ title) | Full corpus semantic/metadata | Natural language question |
| Trigger | ⌘K, auto debounced | Instant keystroke | Manual submit | Chat send |
| Navigation | Expand only | Opens file preview | None | Chat thread |
| Visible in nav | Yes | Yes | **No** | Yes |

**Architectural split:** Global search targets **live DB registry**; module search targets **static/processed files**; knowledge/AI search targets **indexed chunks** — three different corpora with no unified index or UI.

---

## 7. Bugs and gaps (with file paths)

### Critical — Global search schema mismatch

Backend `/platform/search` returns: `id`, `excerpt`, `kind`, `updated_at`

Frontend `GlobalSearchOverlay.jsx` expects: `entry_id`, `content`, `wiki_id`, `decision_id`, `decision_details`, `tasks[]`

**Effect:** Titles may render; body text, metadata, and React keys are broken/empty.

### Critical — Tasks never returned

UI advertises tasks; backend default `include=notebook,wiki,decisions` — **no tasks query**.

### High — Orphaned screens

`KnowledgeSearchScreen` — `App.jsx`, **not in** `navigation.js`.

### High — Duplicate / divergent document search UX

Modern: `LabDocumentsBrowser` + processed twins. Legacy: `LabKnowledgeScreen.jsx` static catalog. Archive: `LabSectionTwinPanel.jsx` static catalog.

### Medium — `KnowledgeSearchScreen` logic bug

Dead ternary in non-`hybrid-lab` branch.

### Medium — No stale-request cancellation

`GlobalSearchOverlay` debounce does not abort prior fetches.

### Medium — Search only matches filenames, not content

`filterDocsByQuery` ignores excerpts/chunks.

### Medium — Dead Orders blueprint search code

`OrdersHubScreen.jsx` contains unused search infrastructure superseded by `OrdersBillingBrowser`.

### Low — UX polish gaps

No Escape to close; no error message in UI; unused `API_URL` props; no search state in URL; `LabCorpusBrowser` — browse-only.

### Low — Auth asymmetry

`/ask` requires auth + role; `/platform/search`, `/api/search` are open.

---

## 8. Recommended unification direction

1. **Fix global search contract** — map backend `id`/`excerpt` → UI fields; add `include=tasks` if desired.
2. **Expose KnowledgeSearchScreen** in nav or merge into global overlay as a mode tab.
3. **Single file-search primitive** — extend `filterDocsByQuery` to optionally search excerpts; retire `LabKnowledgeScreen` catalog search where covered.
4. **Command palette** — one overlay: Registry | Files (current section) | Ask AI.
5. **Wire AI** — “Ask about this” on search hits and file previews.

**Bottom line:** Per-module filename filter works; AI RAG path works; **global registry search is effectively broken**; **knowledge/hybrid search is unreachable**; three tiers do not share query state or navigation.
"""

BACKEND_FILES = [
    "omeia/api/routers/knowledge.py",
    "omeia/api/routers/research.py",
    "omeia/api/routers/copilot.py",
    "omeia/api/routers/vault.py",
    "omeia/api/lab_knowledge_store.py",
    "omeia/api/raw_vault_store.py",
    "omeia/api/database_processor.py",
    "omeia/api/agents.py",
    "omeia/api/llm_client.py",
    "omeia/api/project_digitalization_engine.py",
]

FRONTEND_FILES = [
    "web/src/components/GlobalSearchOverlay.jsx",
    "web/src/screens/KnowledgeSearchScreen.jsx",
    "web/src/components/DocumentFileSearch.jsx",
    "web/src/utils/documentBrowserUtils.js",
    "web/src/components/ChatWidget.jsx",
    "web/src/api/client.js",
    "web/src/App.jsx",
    "web/src/components/Sidebar.jsx",
    "web/src/components/ProjectFolderBrowser.jsx",
    "web/src/components/LabDocumentsBrowser.jsx",
    "web/src/screens/AiLabAssistantScreen.jsx",
    "web/src/screens/LabKnowledgeScreen.jsx",
    "web/src/components/ProjectDocumentsBrowser.jsx",
]


def lang_for(path: str) -> str:
    if path.endswith(".py"):
        return "python"
    if path.endswith((".jsx", ".js")):
        return "javascript"
    return ""


def embed_file(path: str) -> str:
    full = ROOT / path
    text = full.read_text(encoding="utf-8", errors="replace")
    lang = lang_for(path)
    return f"### `{path}`\n\n```{lang}\n{text}\n```\n\n"


def main() -> None:
    parts: list[str] = []
    parts.append(f"# 31 — Unified Search Audit & Source Bundle (OMEIA / Färkkilä Lab Assistant)\n\n")
    parts.append(f"**Generated:** {date.today().isoformat()}  \n")
    parts.append("**Contents:** Master audit + backend API audit + frontend UI audit + full source snapshots of all search-related scripts.\n\n")
    parts.append("---\n\n")
    parts.append("## Table of contents\n\n")
    parts.append("1. [Part I — Master search audit (synthesis)](#part-i--master-search-audit-synthesis)\n")
    parts.append("2. [Part II — Backend API audit](#part-ii--backend-api-audit)\n")
    parts.append("3. [Part III — Frontend UI audit](#part-iii--frontend-ui-audit)\n")
    parts.append("4. [Part IV — Backend source appendix](#part-iv--backend-source-appendix)\n")
    parts.append("5. [Part V — Frontend source appendix](#part-v--frontend-source-appendix)\n\n")
    parts.append("---\n\n")

    parts.append('<a id="part-i--master-search-audit-synthesis"></a>\n\n')
    parts.append("# Part I — Master search audit (synthesis)\n\n")
    parts.append(MASTER_AUDIT.read_text(encoding="utf-8"))
    parts.append("\n\n---\n\n")

    parts.append('<a id="part-ii--backend-api-audit"></a>\n\n')
    parts.append("# Part II — Backend API audit\n\n")
    parts.append(BACKEND_AUDIT)
    parts.append("\n\n---\n\n")

    parts.append('<a id="part-iii--frontend-ui-audit"></a>\n\n')
    parts.append("# Part III — Frontend UI audit\n\n")
    parts.append(FRONTEND_AUDIT)
    parts.append("\n\n---\n\n")

    parts.append('<a id="part-iv--backend-source-appendix"></a>\n\n')
    parts.append("# Part IV — Backend source appendix\n\n")
    parts.append("Full file copies as of audit date. Paths relative to repository root.\n\n")
    for rel in BACKEND_FILES:
        parts.append(embed_file(rel))

    parts.append("---\n\n")
    parts.append('<a id="part-v--frontend-source-appendix"></a>\n\n')
    parts.append("# Part V — Frontend source appendix\n\n")
    parts.append("Full file copies as of audit date. Paths relative to repository root.\n\n")
    for rel in FRONTEND_FILES:
        parts.append(embed_file(rel))

    parts.append("---\n\n")
    parts.append("*End of unified search audit bundle.*\n")

    OUT.write_text("".join(parts), encoding="utf-8")
    line_count = OUT.read_text(encoding="utf-8").count("\n") + 1
    print(f"Wrote {OUT} ({line_count:,} lines)")


if __name__ == "__main__":
    main()
