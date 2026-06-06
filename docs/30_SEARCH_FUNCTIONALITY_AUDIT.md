# 30 — Search Functionality Audit (OMEIA / Färkkilä Lab Assistant)

**Date:** 2026-06-06 (merged backend + frontend deep audits)  
**Scope:** End-to-end search across React frontend, FastAPI backend, RAG/copilot, lab corpus, vault, and notebook surfaces.  
**Goal:** Assess current status, integration with the AI Lab Assistant, bugs/gaps, and a phased plan toward “immaculate” unified search.  
**Sources:** Codebase review + [backend API audit](e8991d98-53a0-4965-9fab-259ed7580889) + [frontend UI audit](3ad746a2-ba9b-46de-a821-a60519ffdd9b).  
**Full bundle (audits + embedded source):** [`31_SEARCH_UNIFIED_AUDIT_AND_SOURCE_BUNDLE.md`](31_SEARCH_UNIFIED_AUDIT_AND_SOURCE_BUNDLE.md)  
**Portable setup (implemented):** [`32_SEARCH_PORTABLE_SETUP.md`](32_SEARCH_PORTABLE_SETUP.md)

---

## Executive summary

The platform has **six partially overlapping search systems**, not one. Each uses different data sources, ranking logic, and UI entry points. The **AI Lab Assistant** (`POST /ask`) performs its own retrieval (Qdrant RAG + `search_lab_knowledge`) but **does not control or synchronize** with the sidebar global search or per-module file filters.

| Maturity | Area |
|----------|------|
| **Strong (backend)** | Lab knowledge semantic search (`search_lab_knowledge`), vault metadata search, copilot RAG pipeline |
| **Partial** | Unified API (`/api/search`, hybrid modes), section document index search |
| **Weak / broken (UI)** | Global search overlay field mismatch, non-navigable knowledge search screen, client-only document filters |
| **Missing** | Single search UX, AI→UI result handoff, cross-corpus ranking, keyboard-first omnibox |

**Bottom line:** Search *infrastructure* exists; search *product experience* is fragmented. Fixing the global overlay bug and unifying APIs under one omnibox should be Phase 1.

---

## 1. Architecture map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         USER ENTRY POINTS (UI)                              │
├─────────────────┬─────────────────┬──────────────────┬──────────────────────┤
│ Sidebar ⌘K      │ Knowledge       │ Document file    │ Lab Knowledge        │
│ GlobalSearch    │ SearchScreen    │ search (local)   │ catalog search       │
│ Overlay         │ (orphan route)  │ filterDocsByQuery│ (static JSON)        │
└────────┬────────┴────────┬────────┴────────┬─────────┴──────────┬───────────┘
         │                 │                 │                    │
         ▼                 ▼                 ▼                    ▼
   GET /platform/    GET /api/search   (no API — in-browser)   /database/catalog.json
   search            GET /api/knowledge/hybrid-search
         │                 │
         │                 ├─ lab_results ← search_lab_knowledge()
         │                 └─ vault_results ← search_vault()
         │
         ▼
   Postgres ILIKE on platform.notebook_entry, research_wiki, decision_registry
   (NOT lab corpus files, NOT Qdrant)

┌─────────────────────────────────────────────────────────────────────────────┐
│                    AI LAB ASSISTANT (parallel path)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ ChatWidget → POST /ask                                                      │
│   ├─ RAGAgent.retrieve() → Qdrant doc_chunks (project-scoped vectors)       │
│   ├─ search_lab_knowledge() → Qdrant corpus=lab_operations + PG fallback    │
│   ├─ query_postgres_metadata() → patient/sample counts                      │
│   └─ LLM answer + SourceInfo[] (shown in chat, not in search UI)            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Search surfaces (frontend)

### 2.1 Global search overlay (primary discovery)

| Property | Value |
|----------|-------|
| **Component** | `app_skeleton/ui/react_frontend/src/components/GlobalSearchOverlay.jsx` |
| **Trigger** | Sidebar search button → `App.jsx` `isSearchOpen` |
| **API** | `GET /platform/search?q={query}` |
| **Debounce** | 300 ms |
| **Corpora** | Notebook, wiki, decisions, tasks (UI expects 4 buckets) |

**Behavior:** Modal overlay; expandable result cards; no navigation to source screen or deep link.

### 2.2 Knowledge search screen (advanced / dev)

| Property | Value |
|----------|-------|
| **Component** | `KnowledgeSearchScreen.jsx` |
| **Route** | `App.jsx` `case 'knowledge_search'` |
| **Navigation** | **Not listed in `navigation.js`** — effectively unreachable from sidebar unless URL/hash is manually set |
| **APIs** | `GET /api/search` (modes: hybrid, semantic, metadata, exact) or `GET /api/knowledge/hybrid-search` |
| **UX** | Plain bullet lists; no open-preview, no nav jump, no highlighting |

### 2.3 Per-module document file search (local filter)

| Property | Value |
|----------|-------|
| **Component** | `DocumentFileSearch.jsx` + `filterDocsByQuery()` in `documentBrowserUtils.js` |
| **Used in** | `LabDocumentsBrowser`, project workspace, orders/storage/overview document browsers |
| **API** | None — filters already-loaded twin JSON by path + display title |
| **Limit** | Only files in current section/tab; no cross-module search |

### 2.4 Lab Knowledge static catalog search

| Property | Value |
|----------|-------|
| **Component** | `LabKnowledgeScreen.jsx` |
| **Data** | `fetch('/database/catalog.json')` — static prebuilt catalog |
| **API** | No server search; client filter on paths |
| **Note** | Separate from processed twins (`/processed/lab__*.json`) used elsewhere |

### 2.5 Notebook / Wiki screen search

| Property | Value |
|----------|-------|
| **Component** | `NotebookWikiScreen.jsx` |
| **Data** | **Static** `technicalNotebook.js` / `technicalWiki.js` |
| **Conflict** | Global search queries **Postgres** `platform.notebook_entry` / `research_wiki` — different data source |

### 2.6 AI Lab Assistant chat

| Property | Value |
|----------|-------|
| **Component** | `ChatWidget.jsx` inside `AiLabAssistantScreen.jsx` |
| **API** | `POST /ask` with `project_codes`, `mode: 'documentation_only'` |
| **Retrieval** | RAG + lab knowledge (see §3.4) |
| **UI** | Sources in collapsible `<details>`; scores shown; **no link to open document in app** |

### 2.7 Other search-adjacent UIs

| Surface | Mechanism |
|---------|-----------|
| `LabCorpusBrowser` | Section browser only — **no query box** |
| `FeatureClinicalScreen` | Feature warehouse similarity (separate domain) |
| `ProjectLogPanel` | Client filter in log stream |
| `AdministrationScreen` | Ingestion jobs list — no global search |

---

## 3. Search backends (API)

All routers mount with `Depends(require_platform_user)` unless noted (`app_skeleton/api/main.py`).

### 3.1 Platform registry search (global overlay)

| Endpoint | `GET /platform/search` |
|----------|------------------------|
| **File** | `app_skeleton/api/routers/research.py` (`platform_search`) |
| **Engine** | Postgres `ILIKE %q%` on title/content/rationale |
| **Tables** | `platform.notebook_entry`, `platform.research_wiki`, `platform.decision_registry` |
| **Params** | `q`, `project_code?`, `include` (default `notebook,wiki,decisions`), `limit` |
| **Ranking** | `ORDER BY created_at/updated_at DESC` — recency, not relevance |
| **Tasks** | **Not implemented** in API despite UI expecting `tasks[]` |

**Response shape (actual):**
```json
{
  "notebook": [{ "id", "project_code", "title", "excerpt", "kind", "created_at" }],
  "wiki": [{ "id", "project_code", "title", "excerpt", "kind", "updated_at" }],
  "decisions": [{ "id", "project_code", "title", "excerpt", "decision_date" }]
}
```

### 3.2 Unified knowledge search

| Endpoint | `GET /api/search` |
|----------|-------------------|
| **File** | `app_skeleton/api/routers/knowledge.py` |
| **Modes** | `exact`, `metadata`, `semantic`, `hybrid` |
| **Lab leg** | `search_lab_knowledge()` when semantic/hybrid |
| **Vault leg** | `search_vault()` when metadata/exact/hybrid |
| **Unused param** | `page_domain_id` accepted but **not applied** to filtering |

### 3.3 Hybrid search (explicit)

| Endpoint | `GET /api/knowledge/hybrid-search` |
|----------|--------------------------------------|
| **Returns** | `{ lab_results, vault_results, count }` |
| **Same engines** | As `/api/search` hybrid mode |

### 3.4 Lab knowledge semantic search (canonical lab corpus)

| Function | `search_lab_knowledge()` in `lab_knowledge_store.py` |
|----------|------------------------------------------------------|
| **Primary** | Qdrant collection `doc_chunks`, filter `corpus=lab_operations` |
| **Vector** | `llm.embed(query, dim=384)` |
| **Fallback** | Postgres `rag.document_chunk` token LIKE scoring |
| **Offline fallback** | `search_section_chunks()` on processed JSON (`database_processor.py`) via `/api/database/search` |
| **Ingest** | `POST /api/knowledge/lab/ingest-all`, per-section ingest |
| **Requires** | Qdrant up + ingest run; otherwise PG/JSON fallback quality drops |

### 3.5 Vault metadata search

| Endpoint | `GET /api/vault/search` |
|----------|-------------------------|
| **File** | `app_skeleton/api/routers/vault.py` |
| **Engine** | Postgres first, JSON manifest fallback (`raw_vault_store.py`) |
| **Auth** | `_FIREBASE_PROTECTED` on vault routes (stricter than platform search) |
| **Filters** | domain, project_hint, review_status, vector_status, extraction_status, uncategorized_only |

### 3.6 Section document index (local twins)

| Endpoint | `GET /api/lab/section/{section_id}/documents?q=` |
|----------|---------------------------------------------------|
| **Engine** | Token substring match on `document_index` in `lab__{section}.json` |
| **No vectors** | Fast, works offline |
| **Used by** | Not wired to global search today |

### 3.7 Legacy per-entity search

| Endpoint | Purpose |
|----------|---------|
| `GET /notebook/search` | Notebook only |
| `GET /wiki/search` | Wiki only |
| `GET /decisions/search` | Decisions only |

Superseded by `/platform/search` but still exist.

### 3.8 Copilot / AI retrieval (not exposed as search API)

| Endpoint | `POST /ask` |
|----------|-------------|
| **File** | `app_skeleton/api/routers/copilot.py` |
| **Pipeline** | Privacy audit → PG metadata → `RAGAgent.retrieve()` → `search_lab_knowledge()` → merge/dedupe → LLM |
| **Limit** | 12 sources max in response |
| **Logging** | `platform.conversation` + `platform.message.retrieved_chunks` |

`RAGAgent` (`agents.py`) queries Qdrant with project-code filtering on payload `allowed_project_codes`.

### 3.9 Digitalization search

| Endpoint | `GET /api/digitalize/search` |
|----------|------------------------------|
| **Scope** | Ingested digitalization assets — separate from lab documents UI |

---

## 4. Data sources & index coverage

| Corpus | Indexed for search? | Used by |
|--------|---------------------|---------|
| Lab Drive folders → processed twins | Partial (JSON chunks; Qdrant if ingested) | Document browsers, `search_lab_knowledge`, `/api/database/search` |
| Vault assets (ingestion pipeline) | Yes (metadata; vectors if embedded) | `/api/search`, `/api/vault/search` |
| Project RAG chunks (per-project ingest) | Yes (Qdrant `doc_chunks`) | `/ask`, ingest tab |
| Postgres notebook/wiki/decisions | Yes (ILIKE) | `/platform/search` |
| Static `technicalNotebook.js` / wiki JS | **No** — UI only | NotebookWiki screen |
| Static `database/catalog.json` | **No** server index | LabKnowledgeScreen |
| Orders / meetings / social processed JSON | Client filter only | Module document browsers |
| Feature warehouse | Vector similarity | Features screen only |

**Coverage gap:** A file visible in Overview → Documents may appear in local file search but **not** in global overlay or notebook search unless ingested/indexed in the right store.

---

## 5. AI assistant ↔ search integration (current vs desired)

### Current state

| Capability | Status |
|------------|--------|
| AI retrieves same lab index as `/api/search` | **Yes** — `search_lab_knowledge()` in `/ask` |
| AI retrieves project-specific chunks | **Yes** — `RAGAgent` with `project_codes` |
| AI shows source citations | **Yes** — `SourceList` in chat |
| AI can open/navigate user to hit | **No** |
| Search UI can show AI-suggested query refinements | **No** |
| Shared session context (chat query → search results panel) | **No** |
| AI can “dictate” search filters (section, project, mode) | **No** — no tool/function calling |
| Ingest from AI tab updates search index | **Partial** — `/ingest-document` indexes project vectors; lab ingest is separate admin flow |

### Desired “wired together” model

1. **Single Search Service** backend: one endpoint returns ranked buckets (lab, vault, registry, tasks, projects).
2. **Copilot tools**: `search_platform({ q, scopes, project_codes })` callable by LLM; returns structured hits.
3. **UI contract**: Every hit has `open_action` (nav hash + file path + section_id).
4. **Bi-directional UI**: “Search this in lab documents” button on assistant sources; “Ask AI about these results” on search overlay.

---

## 6. Confirmed bugs

### BUG-1 — Global search response/schema mismatch (Critical)

**Symptom:** Overlay shows empty or broken cards even when API returns data.

| UI expects (`GlobalSearchOverlay.jsx`) | API returns (`platform_search`) |
|----------------------------------------|----------------------------------|
| `entry_id` | `id` |
| `wiki_id` | `id` |
| `decision_id` | `id` |
| `content` | `excerpt` |
| `decision_details` | `excerpt` |
| `task_id`, `tasks[]` | **Not returned** |

**Fix:** Align API response to UI contract OR map fields in `GlobalSearchOverlay` after fetch.

---

### BUG-2 — Tasks bucket always empty (High)

UI renders `results.tasks` but `/platform/search` never queries `platform` tasks table and `include` default omits tasks.

**Fix:** Add task query to `platform_search` + pass `include=notebook,wiki,decisions,tasks` from UI.

---

### BUG-3 — Knowledge Search screen unreachable (High)

`KnowledgeSearchScreen` is wired in `App.jsx` but **absent from `navigation.js`**. Users cannot discover hybrid/semantic search.

**Fix:** Add under Administration, Data & Storage, or AI Assistant submenu.

---

### BUG-4 — Notebook/Wiki dual reality (High)

- **UI screens** use static JS datasets (read-only alerts).
- **Global search** queries Postgres tables that may be empty or divergent.

**Fix:** Single source of truth — either migrate UI to API or stop advertising notebook search until synced.

---

### BUG-5 — `page_domain_id` no-op (Medium)

`GET /api/search?page_domain_id=...` records the param in JSON but does not filter results.

**Fix:** Wire to vault domain filter per `docs/21_PAGE_DOMAIN_MAPPING.md`.

---

### BUG-6 — Global search error handling silent (Medium)

`GlobalSearchOverlay` catches errors with `console.error` only — user sees “No matching records” or stale results.

**Fix:** Show error state + retry.

---

### BUG-7 — Knowledge search results not actionable (Medium)

Hits list title/snippet only — no click → preview, no `section_id` routing.

**Fix:** Use `where_to_find`, `relative_path`, `document_code` from `search_lab_knowledge` hit shape.

---

### BUG-8 — Auth inconsistency on vault search (Low–Medium)

`/api/vault/search` uses `_FIREBASE_PROTECTED`; `/api/search` vault leg uses same `search_vault()` but different route auth stack. Behavior may differ when Firebase vs platform auth enabled.

---

### BUG-9 — Qdrant vector schema conflict (Critical, backend)

Lab ingest uses **named** vector `"text"` (`lab_knowledge_store.py`); `/ingest-document` (`vault.py`) may create `doc_chunks` with **flat** `VectorParams` and flat upserts. Mixed schemas in one collection can break retrieval depending on creation order.

**Fix:** Standardize on named vector `{"text": vec}` everywhere; re-index.

---

### BUG-10 — `hybrid-search` omits shared clients (Medium, backend)

`GET /api/knowledge/hybrid-search` calls `search_lab_knowledge(q, …)` without injected `qdrant`/`llm` clients, unlike `/api/knowledge/lab/search`. Inconsistent behavior under connection pooling or test doubles.

---

### BUG-11 — Platform search ignores `visibility_level` (High, backend)

Notebook/wiki/decision endpoints return `visibility_level` but **do not filter** on it — restricted entries may surface to all authenticated users.

---

### BUG-12 — Project workspace ingest not in semantic index (High, backend)

`extract_and_ingest_project()` writes Postgres `rag.*` with `corpus=project_workspace` but **no Qdrant upsert**. Copilot RAG and `search_lab_knowledge` (filters `lab_operations`) may miss project-folder content unless ingested via another path.

**Related gap:** No `GET /api/project-files/search` — only full list + client filename filter.

---

### BUG-13 — Stale global search responses (Medium, frontend)

`GlobalSearchOverlay` debounces but does not abort in-flight fetches; fast typing can show out-of-order results.

---

### BUG-14 — `KnowledgeSearchScreen` dead branch (Low, frontend)

`KnowledgeSearchScreen.jsx`: unreachable ternary in non-`hybrid-lab` branch (`mode === 'hybrid-lab'` inside else) — mode routing is confusing and partially dead code.

---

### BUG-15 — Triple document-search UX (Medium, frontend)

Same mental model (“search lab files”) implemented three ways: `LabDocumentsBrowser` (processed twins), `LabKnowledgeScreen` (static `catalog.json`), `LabSectionTwinPanel` (static catalog). Data sources diverge.

---

### BUG-16 — Auth asymmetry global vs AI (Medium, product)

`/platform/search` and `/api/search` work without role gate; `/ask` requires editor/admin. Global search works logged-out; AI search does not.

---

## 7. Gaps (not quite bugs)

| ID | Gap | Impact |
|----|-----|--------|
| G-1 | **No unified ranking** across lab + vault + registry | User must know which screen to use |
| G-2 | **No fuzzy/typo tolerance** on ILIKE platform search | Misspelled queries fail |
| G-3 | **No query logging/analytics** | Cannot tune relevance |
| G-4 | **No search suggestions / recent queries** | Poor discoverability |
| G-5 | **No keyboard navigation** in overlay (arrows, enter to open) | Accessibility |
| G-6 | **Lab ingest not automatic** on processor refresh | Stale semantic index |
| G-7 | **Copilot project scope** does not match global search scope | AI answers may omit lab-wide docs |
| G-8 | **i18n**: search placeholders English-only in several components | |
| G-9 | **Feature warehouse search** isolated from main search | |
| G-10 | **Digitalization search** not linked from UI search surfaces | |
| G-11 | **Hashed local embeddings** (`LLMClient.embed`) — not true semantic vectors | Limits RAG quality |
| G-12 | **Two digitalization schemas** — `knowledge_assets` (searchable) vs `canonical_document` (list only, no `q`) | Split product surface |
| G-13 | **Vault `vector_status` filter only** — vault search is metadata ILIKE, not vector retrieval | Misleading filter name |
| G-14 | **No Postgres full-text** (`tsvector`) anywhere | Recency-only ranking on registry |
| G-15 | **File filter ignores body text** — `filterDocsByQuery` path/title only | Cannot find by protocol content in-module |
| G-16 | **No search persistence** — no URL params, localStorage history, or shareable results | |
| G-17 | **Copilot role gate** — researchers cannot use `/ask` retrieval path | AI search limited to editors |
| G-18 | **Dead code** — `OrdersHubScreen.jsx` blueprint search (~400 lines) superseded by `OrdersBillingBrowser` | Maintenance noise |
| G-19 | **Duplicate unmounted routers** — `knowledge copy.py`, `vault copy.py`, `research copy.py` | Audit confusion |

---

## 8. Quality bar: “immaculate search” checklist

Use this as the target acceptance criteria.

### Retrieval quality
- [ ] One query searches lab corpus, vault, notebook/registry, tasks, projects
- [ ] Semantic + keyword hybrid with explicit scores
- [ ] Section/project/mode filters respected
- [ ] Ingest pipeline keeps Qdrant within 24h of processor refresh
- [ ] Fallback chain documented and tested (Qdrant → PG → JSON)

### UX
- [ ] Single omnibox (⌘K) with categorized results
- [ ] Every result opens correct module + file preview
- [ ] Highlight query terms in snippets
- [ ] Empty/error/loading states
- [ ] &lt;300ms perceived latency for keyword; &lt;1.5s for semantic

### AI integration
- [ ] `/ask` uses same `SearchService` as UI
- [ ] Assistant can invoke search tool and render hits in chat
- [ ] “Open in browser” on every source citation
- [ ] Optional: assistant suggests narrower queries when too many hits

### Engineering
- [ ] One response schema (`SearchHit` type) shared frontend/backend
- [ ] Contract tests for `/platform/search` field names
- [ ] Retrieval regression suite (`tests/retrieval_test_questions.md` automated)

---

## 9. Recommended phased plan

### Phase 1 — Fix what’s broken (1–2 weeks)

1. **Fix BUG-1 + BUG-2** — align `GlobalSearchOverlay` ↔ `platform_search` (+ tasks query).
2. **Fix BUG-9** — unify Qdrant vector schema; schedule re-ingest.
3. **Expose Knowledge Search** in navigation OR merge into global overlay “Advanced” tab.
4. **Unify notebook data path** — pick Postgres or static; deprecate the other.
5. **Add error/empty states + abort stale fetches** (BUG-6, BUG-13) to global overlay.
6. **Make knowledge hits clickable** — navigate to `data_storage:documents` or overview doc browser with `path` query param.
7. **Filter `visibility_level`** on platform search (BUG-11).

### Phase 2 — Unified Search Service (2–4 weeks)

1. New `GET /api/platform/unified-search?q=&scopes=&project_code=&section_id=&mode=`
   - Merges: `platform_search`, `search_lab_knowledge`, `search_vault`, `section_documents` summaries
   - Normalized hit schema:
     ```typescript
     type SearchHit = {
       id: string;
       bucket: 'lab' | 'vault' | 'notebook' | 'wiki' | 'decision' | 'task' | 'project';
       title: string;
       snippet: string;
       score: number;
       nav?: { main: string; sub: string; path?: string; section_id?: string };
     };
     ```
2. Replace `GlobalSearchOverlay` fetch with unified endpoint.
3. Refactor `KnowledgeSearchScreen` to use same component library.

### Phase 3 — AI copilot coupling (2–3 weeks)

1. Add `search_platform` tool to copilot request handler (server-side function calling or explicit pre-step).
2. Return `search_hits[]` alongside `answer` in `QuestionResponse` when retrieval runs.
3. Chat UI: render hits as chips above answer; click → same `open_action` as overlay.
4. Overlay: “Ask AI about this query” sends query to copilot pane.

### Phase 4 — Relevance & polish (ongoing)

1. Implement BM25 or Postgres `tsvector` for registry search.
2. Apply `page_domain_id` filters per domain mapping doc.
3. Query log table + admin dashboard.
4. Automate lab re-ingest on `database_processor --all --refresh`.
5. Automated retrieval QA from `tests/retrieval_test_questions.md`.

---

## 10. File reference index

### Frontend
| File | Role |
|------|------|
| `components/GlobalSearchOverlay.jsx` | Sidebar global search |
| `screens/KnowledgeSearchScreen.jsx` | Hybrid/semantic search page |
| `components/DocumentFileSearch.jsx` | Module header file filter |
| `utils/documentBrowserUtils.js` | `filterDocsByQuery`, grouping |
| `components/ChatWidget.jsx` | AI chat + sources |
| `screens/AiLabAssistantScreen.jsx` | Ingest + copilot shell |
| `screens/NotebookWikiScreen.jsx` | Static notebook/wiki |
| `screens/LabKnowledgeScreen.jsx` | Static catalog browser |
| `components/LabCorpusBrowser.jsx` | Section browser (no search) |
| `App.jsx` | Routes + overlay mount |

### Backend
| File | Role |
|------|------|
| `api/routers/research.py` | `/platform/search`, entity searches |
| `api/routers/knowledge.py` | `/api/search`, hybrid, lab section docs |
| `api/routers/copilot.py` | `/ask` RAG orchestration |
| `api/lab_knowledge_store.py` | `search_lab_knowledge`, ingest |
| `api/raw_vault_store.py` | `search_vault` |
| `api/database_processor.py` | `section_documents_for_api`, `search_section_chunks` |
| `api/agents.py` | `RAGAgent.retrieve` |
| `api/routers/vault.py` | `/api/vault/search` |

### Related docs
| Doc | Topic |
|-----|-------|
| `docs/03_VECTOR_RAG_DEEP_DIVE.md` | Vector/RAG contracts |
| `docs/21_PAGE_DOMAIN_MAPPING.md` | Domain filters (unused in search today) |
| `tests/retrieval_test_questions.md` | Manual retrieval QA questions |

---

## 11. Immediate action list (priority order)

| # | Action | Owner hint | Effort |
|---|--------|------------|--------|
| 1 | Fix global overlay field mapping + tasks API | Frontend + `research.py` | S |
| 2 | Unify Qdrant vector naming + re-index | Backend | M |
| 3 | Add nav entry for Knowledge Search or fold into overlay | Frontend | S |
| 4 | `visibility_level` filters on registry search | Backend | S |
| 5 | Add `GET /api/project-files/search` (processed index or `rag.*`) | Backend | M |
| 6 | Document ingest status in Admin UI (“search index freshness”) | Full-stack | M |
| 7 | Clickable search results → document preview routes | Frontend | M |
| 8 | Design `SearchHit` schema + unified endpoint | Backend | M |
| 9 | Copilot returns shared `search_hits` | Backend + chat UI | L |
| 10 | Postgres full-text or trigram for platform search | Backend | M |
| 11 | Automate lab ingest after processor | Ops/script | M |
| 12 | Retire `LabKnowledgeScreen` catalog search where twins exist | Frontend | M |

---

## 12. Conclusion

Search in this platform is **technically capable** (semantic lab index, vault metadata, RAG copilot, registry SQL) but **product-fragmented**. The AI assistant already shares the lab knowledge retrieval function with the knowledge API, yet the user-facing search overlay is **out of sync with its backend**, and several screens search **different copies of the same conceptual data**.

Phases 1–2 deliver the biggest user-visible improvement: one reliable omnibox with correct results. Phase 3 realizes the vision of a lab assistant that **searches with the user** rather than beside them.

---

## 14. Implementation status (2026-06-06)

| Phase | Status |
|-------|--------|
| Phase 1 — Fix broken overlay, tasks, hybrid clients | **Done** |
| Phase 2 — `SearchService` + `/api/platform/unified-search` + `SearchHit` | **Done** |
| Phase 3 — Copilot shared retrieval, `search_only` mode, clickable sources | **Done** |
| Phase 4 — Query log SQL, recent queries, excerpt file filter, index status API | **Done** |
| Portable stub storage + Qdrant named-vector unification | **Done** — see `32_SEARCH_PORTABLE_SETUP.md` |

Remaining optional polish: Postgres `tsvector` ranking, automated ingest cron, notebook static→API full migration.

---

## 13. Cross-audit synthesis

| Layer | Verdict |
|-------|---------|
| **Backend** | 12+ endpoints across six data planes; lab semantic + vault metadata are the strongest legs; registry search is ILIKE + recency; project files lack a search API; embeddings are hashed offline vectors. |
| **Frontend** | Per-module filename filter works; global overlay is **broken by schema drift**; knowledge/hybrid screen is **orphaned**; AI RAG is live but **not bridged** to search UI. |
| **Integration** | Copilot and `/api/search` share `search_lab_knowledge()`; everything else is parallel silos with no shared `SearchHit` contract or navigation actions. |

**Highest-impact fixes:** BUG-1 (overlay), BUG-9 (Qdrant schema), expose/merge knowledge search, unified endpoint + deep links, then copilot tool wiring.

---

*Generated from codebase audit of `app_skeleton/` on branch working tree 2026-06-06. Merged with parallel backend and frontend subagent audits.*
