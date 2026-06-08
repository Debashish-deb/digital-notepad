# 31 — Unified Search Audit & Source Bundle (OMEIA / Färkkilä Lab Assistant)

**Generated:** 2026-06-06  
**Contents:** Master audit + backend API audit + frontend UI audit + full source snapshots of all search-related scripts.

---

## Table of contents

1. [Part I — Master search audit (synthesis)](#part-i--master-search-audit-synthesis)
2. [Part II — Backend API audit](#part-ii--backend-api-audit)
3. [Part III — Frontend UI audit](#part-iii--frontend-ui-audit)
4. [Part IV — Backend source appendix](#part-iv--backend-source-appendix)
5. [Part V — Frontend source appendix](#part-v--frontend-source-appendix)

---

<a id="part-i--master-search-audit-synthesis"></a>

# Part I — Master search audit (synthesis)

# 30 — Search Functionality Audit (OMEIA / Färkkilä Lab Assistant)

**Date:** 2026-06-06 (merged backend + frontend deep audits)  
**Scope:** End-to-end search across React frontend, FastAPI backend, RAG/copilot, lab corpus, vault, and notebook surfaces.  
**Goal:** Assess current status, integration with the AI Lab Assistant, bugs/gaps, and a phased plan toward “immaculate” unified search.  
**Sources:** Codebase review + [backend API audit](e8991d98-53a0-4965-9fab-259ed7580889) + [frontend UI audit](3ad746a2-ba9b-46de-a821-a60519ffdd9b).

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
| **Component** | `apps/web/src/components/GlobalSearchOverlay.jsx` |
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

All routers mount with `Depends(require_platform_user)` unless noted (`omeia/api/main.py`).

### 3.1 Platform registry search (global overlay)

| Endpoint | `GET /platform/search` |
|----------|------------------------|
| **File** | `omeia/api/routers/research.py` (`platform_search`) |
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
| **File** | `omeia/api/routers/knowledge.py` |
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
| **File** | `omeia/api/routers/vault.py` |
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
| **File** | `omeia/api/routers/copilot.py` |
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

## 13. Cross-audit synthesis

| Layer | Verdict |
|-------|---------|
| **Backend** | 12+ endpoints across six data planes; lab semantic + vault metadata are the strongest legs; registry search is ILIKE + recency; project files lack a search API; embeddings are hashed offline vectors. |
| **Frontend** | Per-module filename filter works; global overlay is **broken by schema drift**; knowledge/hybrid screen is **orphaned**; AI RAG is live but **not bridged** to search UI. |
| **Integration** | Copilot and `/api/search` share `search_lab_knowledge()`; everything else is parallel silos with no shared `SearchHit` contract or navigation actions. |

**Highest-impact fixes:** BUG-1 (overlay), BUG-9 (Qdrant schema), expose/merge knowledge search, unified endpoint + deep links, then copilot tool wiring.

---

*Generated from codebase audit of `omeia/` on branch working tree 2026-06-06. Merged with parallel backend and frontend subagent audits.*


---

<a id="part-ii--backend-api-audit"></a>

# Part II — Backend API audit

# Backend Search Audit — OMEIA-AI

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
| `GET /api/search` | same | `q`, `mode`=`hybrid\|semantic\|metadata\|exact`, `section_id?`, `page_domain_id?`, `limit` | Mode-gated merge of lab + vault |
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


---

<a id="part-iii--frontend-ui-audit"></a>

# Part III — Frontend UI audit

# OMEIA-AI React Frontend — Search Audit

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


---

<a id="part-iv--backend-source-appendix"></a>

# Part IV — Backend source appendix

Full file copies as of audit date. Paths relative to repository root.

### `omeia/api/routers/knowledge.py`

```python
from omeia.security.permissions import require_role
from omeia.security.auth import require_platform_user
from fastapi import APIRouter, Depends, Query, Path, HTTPException, Request, Response, BackgroundTasks, UploadFile, File
from omeia.api.common import *
from typing import *
from pydantic import BaseModel, Field
import psycopg

router = APIRouter()

@router.get("/api/knowledge/lab/stats")
def knowledge_lab_stats() -> dict:
    return get_lab_index_stats()

@router.get("/api/knowledge/lab/search")
def knowledge_lab_search(
    q: str = Query(..., min_length=2),
    section_id: Optional[str] = Query(None),
    limit: int = Query(15, ge=1, le=50),
) -> dict:
    if section_id and section_id not in DATABASE_SECTIONS:
        raise HTTPException(status_code=404, detail="Unknown section.")
    results = search_lab_knowledge(
        q,
        section_id=section_id,
        limit=limit,
        qdrant=qdrant_client,
        llm=llm_client,
    )
    return {"corpus": LAB_CORPUS, "query": q, "count": len(results), "results": results}

@router.post("/api/knowledge/lab/ingest-all")
def knowledge_lab_ingest_all(req: LabIngestRequest = LabIngestRequest()) -> dict:
    try:
        return ingest_all_lab_sections(
            refresh_extract=req.refresh_extract,
            qdrant=qdrant_client,
            llm=llm_client,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.post("/api/knowledge/lab/ingest/{section_id}")
def knowledge_lab_ingest_section(section_id: str, req: LabIngestRequest = LabIngestRequest()) -> dict:
    if section_id not in DATABASE_SECTIONS:
        raise HTTPException(status_code=404, detail="Unknown section.")
    try:
        return ingest_section_to_database(
            section_id,
            refresh_extract=req.refresh_extract,
            qdrant=qdrant_client,
            llm=llm_client,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get("/api/knowledge/hybrid-search")
def knowledge_hybrid_search(
    q: str = Query(..., min_length=2),
    section_id: Optional[str] = Query(None),
    limit: int = Query(12, ge=1, le=40),
) -> dict:
    """Semantic lab index + metadata vault search (no disk paths)."""
    lab_hits = search_lab_knowledge(q, section_id=section_id, limit=limit)
    vault_hits = search_vault(q, limit=max(5, limit // 2))
    return {
        "query": q,
        "lab_results": lab_hits,
        "vault_results": vault_hits,
        "count": len(lab_hits) + len(vault_hits),
    }

@router.get("/api/search")
def unified_search(
    q: str = Query(..., min_length=2),
    mode: str = Query("hybrid"),
    section_id: Optional[str] = Query(None),
    page_domain_id: Optional[str] = Query(None),
    limit: int = Query(15, ge=1, le=50),
) -> dict:
    """Unified search: exact|metadata|semantic|hybrid (LUMI-W140)."""
    mode = (mode or "hybrid").lower()
    out: dict = {"query": q, "mode": mode}
    if mode in ("semantic", "hybrid"):
        out["lab_results"] = search_lab_knowledge(q, section_id=section_id, limit=limit)
    if mode in ("metadata", "exact", "hybrid"):
        out["vault_results"] = search_vault(q, limit=limit)
    if mode == "exact" and not out.get("lab_results"):
        out["lab_results"] = []
    out["count"] = len(out.get("lab_results") or []) + len(out.get("vault_results") or [])
    out["page_domain_id"] = page_domain_id
    return out

@router.get("/api/documents/registry")
def documents_registry(
    section_id: Optional[str] = Query(None),
    corpus: Optional[str] = Query("lab_operations"),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    docs = list_registry_documents(section_id=section_id, corpus=corpus, limit=limit)
    return {"count": len(docs), "documents": docs}

@router.get("/api/lab/sections")
def lab_sections_list(user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    """Lab database sections with processed-twin and vault asset counts.

    Processed twins are read from local ``omeia/data/processed_projects/lab__*.json``
    (not Supabase/remote Postgres). Run ``database_processor --all --refresh`` to rebuild.
    """
    return {
        "sections": list_lab_sections_detail(),
        "missing_section_roots": assert_all_section_roots_exist(),
        "section_count": len(DATABASE_SECTIONS),
        "processed_source": "local_processed_json",
    }

@router.get("/api/lab/section/{section_id}")
def lab_section_detail(section_id: str) -> dict:
    """Processed digital twin for a lab section (local JSON, document preview up to 50)."""
    try:
        return section_detail_for_api(section_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.get("/api/lab/section/{section_id}/summary")
def lab_section_summary(section_id: str) -> dict:
    """Alias for ``GET /api/lab/section/{section_id}`` (backward compatible)."""
    try:
        return section_summary_for_api(section_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.get("/api/lab/section/{section_id}/documents")
def lab_section_documents(
    section_id: str,
    q: Optional[str] = Query(None, min_length=1),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """Paginated search within a section's processed document_index (local twin)."""
    try:
        return section_documents_for_api(section_id, q=q, offset=offset, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.get("/api/database/sections")
def database_sections_list() -> dict:
    return {
        "sections": list_sections(),
        "processed_summary": list_processed_summary(),
        "missing_section_roots": assert_all_section_roots_exist(),
    }

@router.get("/api/database/processed-summary")
def database_processed_summary() -> dict:
    return {"sections": list_processed_summary(), "output_dir": str(PROCESSED_DIR)}

@router.get("/api/database/processed/{section_id}")
def database_processed_twin(section_id: str, refresh: bool = False) -> dict:
    if section_id not in DATABASE_SECTIONS:
        raise HTTPException(status_code=404, detail="Unknown section.")
    try:
        return get_section_record(section_id, refresh=refresh)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get("/api/database/processed/{section_id}/summary")
def database_processed_summary(section_id: str) -> dict:
    """Lightweight processed record for UI (document index + metrics, no full chunk text)."""
    if section_id not in DATABASE_SECTIONS:
        raise HTTPException(status_code=404, detail="Unknown section.")
    twin = load_processed_section(section_id)
    if not twin:
        raise HTTPException(
            status_code=404,
            detail="Section not processed yet. Run Process all lab database or reprocess_lab_database.py.",
        )
    return {
        "section_id": section_id,
        "section_label": twin.get("section_label"),
        "description": twin.get("description"),
        "metrics": twin.get("metrics"),
        "processed_at": twin.get("processed_at"),
        "extraction": twin.get("extraction"),
        "document_index": twin.get("document_index") or [],
        "folder_tree": (twin.get("folder_tree") or [])[:200],
        "content_library_totals": (twin.get("content_library") or {}).get("totals"),
    }

@router.get("/api/database/processed/{section_id}/document-text")
def database_document_text(
    section_id: str,
    relative_path: str = Query(...),
) -> dict:
    if section_id not in DATABASE_SECTIONS:
        raise HTTPException(status_code=404, detail="Unknown section.")
    twin = load_processed_section(section_id)
    if not twin:
        raise HTTPException(status_code=404, detail="Section not processed.")
    norm = relative_path.strip().lstrip("/").replace("\\", "/")
    parts = []
    for chunk in _iter_chunks_from_disk(section_id):
        if (chunk.get("source_file") or "").replace("\\", "/") == norm:
            parts.append((chunk.get("chunk_index") or 0, chunk.get("text") or ""))
    if parts:
        parts.sort(key=lambda x: x[0])
        return {
            "path": norm,
            "content": "\n\n".join(t for _, t in parts if t),
            "source": "processed_chunks",
        }
    for doc in twin.get("document_index") or []:
        if (doc.get("path") or "").replace("\\", "/") == norm and doc.get("excerpt"):
            return {"path": norm, "content": doc["excerpt"], "source": "excerpt"}
    raise HTTPException(status_code=404, detail="No extracted text for this file.")

@router.post("/api/database/process-all")
def database_process_all(user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    """Extract lab files to processed twins, then assimilate into canonical rag.* + Qdrant."""
    job = platform_admin.create_ingestion_job("lab_process_all")
    try:
        extract_result = process_all_sections(refresh=True)
        ingest_result = ingest_all_lab_sections(
            refresh_extract=False,
            qdrant=qdrant_client,
            llm=llm_client,
        )
        totals = ingest_result.get("totals") or {}
        platform_admin.finish_ingestion_job(
            job["job_id"],
            items_processed=totals.get("documents") or totals.get("chunks"),
        )
        return {
            "extract": extract_result,
            "ingest": ingest_result,
            "index_stats": get_lab_index_stats(),
            "job_id": job["job_id"],
        }
    except Exception as exc:
        platform_admin.finish_ingestion_job(job["job_id"], status="failed", error_summary=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.post("/api/database/process/{section_id}")
def database_process_section(section_id: str, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    if section_id not in DATABASE_SECTIONS:
        raise HTTPException(status_code=404, detail="Unknown section.")
    try:
        twin = get_section_record(section_id, refresh=True)
        path = save_processed_section(section_id, twin)
        ingest_stats = ingest_section_to_database(
            section_id,
            refresh_extract=False,
            qdrant=qdrant_client,
            llm=llm_client,
        )
        return {
            "section_id": section_id,
            "metrics": twin.get("metrics"),
            "extraction": twin.get("extraction"),
            "output": str(path),
            "ingest": ingest_stats,
            "index_stats": get_lab_index_stats(),
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get("/api/database/search")
def database_search(
    q: str = Query(..., min_length=2),
    section_id: Optional[str] = Query(None),
    limit: int = Query(15, ge=1, le=50),
) -> dict:
    """Deprecated alias — routes to canonical lab knowledge search."""
    hits = search_lab_knowledge(q, section_id=section_id, limit=limit)
    source = "lab_knowledge"
    if not hits:
        hits = search_section_chunks(q, section_id=section_id, limit=limit)
        source = "processed_chunks"
    return {"query": q, "count": len(hits), "results": hits, "source": source}

@router.get("/api/database/tree")
def database_tree(
    section_id: str = Query(...),
    relative_path: str = Query(""),
) -> dict:
    del section_id, relative_path
    raise HTTPException(status_code=410, detail=_LAB_FILE_BROWSER_DEPRECATED)

@router.get("/api/database/read", dependencies=_FIREBASE_PROTECTED)
def database_read_file(
    section_id: str = Query(...),
    relative_path: str = Query(...),
) -> dict:
    del section_id, relative_path
    raise HTTPException(status_code=410, detail=_LAB_FILE_BROWSER_DEPRECATED)

@router.get("/api/database/extract")
def database_extract_text(
    section_id: str = Query(...),
    relative_path: str = Query(...),
) -> dict:
    del section_id, relative_path
    raise HTTPException(status_code=410, detail=_LAB_FILE_BROWSER_DEPRECATED)

@router.get("/api/database/asset")
def database_asset(
    section_id: str = Query(...),
    relative_path: str = Query(...),
):
    del section_id, relative_path
    raise HTTPException(status_code=410, detail=_LAB_FILE_BROWSER_DEPRECATED)

@router.get("/api/database/asset-url", dependencies=_FIREBASE_PROTECTED)
def database_asset_url(section_id: str = Query(...), relative_path: str = Query(...)) -> dict:
    if section_id not in DATABASE_SECTIONS:
        raise HTTPException(status_code=404, detail="Unknown section.")
    root = section_root(section_id)
    abs_path = safe_relative_path(root, relative_path)
    if not abs_path.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    if not _is_database_asset_file(abs_path):
        raise HTTPException(status_code=415, detail="File type cannot be opened.")
    return {
        "url": _database_static_url(section_id, relative_path),
        "path": relative_path,
        "section_id": section_id,
        "name": abs_path.name,
        "extension": abs_path.suffix.lower(),
    }
```

### `omeia/api/routers/research.py`

```python
from omeia.security.permissions import require_role
from omeia.security.auth import require_platform_user
from fastapi import APIRouter, Depends, Query, Path, HTTPException, Request, Response, BackgroundTasks, UploadFile, File
from omeia.api.common import *
from typing import *
from pydantic import BaseModel, Field
import psycopg

router = APIRouter()

@router.get("/projects")
def get_projects() -> List[Dict[str, Any]]:
    return fetch_projects_unified()

@router.put("/projects/{project_code}")
def update_project(project_code: str, req: ProjectExtensionUpdate, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT project_id FROM core.project WHERE project_code = %s;", (project_code,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Project not found")
                pid = row[0]

                # Make sure row exists in project_extension
                cur.execute("INSERT INTO platform.project_extension (project_id) VALUES (%s) ON CONFLICT DO NOTHING;", (pid,))

                # Build update query
                fields = []
                params = []
                for k, v in req.model_dump(exclude_unset=True).items():
                    fields.append(f"{k} = %s")
                    params.append(v)
                params.append(pid)

                if fields:
                    query = f"UPDATE platform.project_extension SET {', '.join(fields)}, updated_at = now() WHERE project_id = %s;"
                    cur.execute(query, tuple(params))

                # Automatically append to the notebook system of record!
                cur.execute("SELECT researcher_id FROM platform.researcher WHERE username = 'debdeba';")
                debdeba_id = cur.fetchone()[0]
                auto_log_notebook_entry(
                    conn, pid, debdeba_id, 
                    title=f"Project {project_code} parameters updated",
                    content=f"Researcher updated project extensions: {', '.join(fields)}",
                    entry_type="protocol_deviation_note"
                )
                conn.commit()
                return {"status": "success"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/notebook")
def get_notebook(project_code: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT ne.entry_id, p.project_code, s.sample_code, ne.title, ne.pipeline_stage, ne.content, ne.conclusions, ne.issues_found, ne.next_steps, ne.tags, ne.entry_type, ne.visibility_level, ne.created_at, r.full_name,
                           (SELECT COUNT(*) FROM platform.notebook_revision nr WHERE nr.entry_id = ne.entry_id) as revision_count
                    FROM platform.notebook_entry ne
                    JOIN core.project p ON ne.project_id = p.project_id
                    LEFT JOIN core.sample s ON ne.sample_id = s.sample_id
                    JOIN platform.researcher r ON ne.author_id = r.researcher_id
                """
                params = []
                if project_code:
                    query += " WHERE p.project_code = %s"
                    params.append(project_code)
                query += " ORDER BY ne.created_at DESC;"
                
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                result = []
                for r in rows:
                    result.append({
                        "entry_id": str(r[0]),
                        "project_code": r[1],
                        "sample_code": r[2],
                        "title": r[3],
                        "pipeline_stage": r[4],
                        "content": r[5],
                        "conclusions": r[6],
                        "issues_found": r[7],
                        "next_steps": r[8],
                        "tags": r[9],
                        "entry_type": r[10],
                        "visibility_level": r[11],
                        "created_at": r[12].isoformat(),
                        "author_name": r[13],
                        "version": r[14]
                    })
                return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/notebook/{entry_id}/revisions")
def get_notebook_revisions(entry_id: str) -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT revision_id, revision_number, title, content, created_at
                    FROM platform.notebook_revision
                    WHERE entry_id = %s
                    ORDER BY revision_number DESC;
                """, (entry_id,))
                rows = cur.fetchall()
                return [{
                    "revision_id": str(r[0]),
                    "revision_number": r[1],
                    "title": r[2],
                    "content": r[3],
                    "created_at": r[4].isoformat()
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/notebook")
def create_notebook(req: NotebookEntryCreate, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT project_id FROM core.project WHERE project_code = %s;", (req.project_code,))
                p_row = cur.fetchone()
                if not p_row:
                    raise HTTPException(status_code=404, detail="Project not found")
                pid = p_row[0]

                sid = None
                if req.sample_code:
                    cur.execute("SELECT sample_id FROM core.sample WHERE sample_code = %s;", (req.sample_code,))
                    s_row = cur.fetchone()
                    if s_row:
                        sid = s_row[0]

                cur.execute("SELECT researcher_id FROM platform.researcher WHERE username = 'debdeba';")
                debdeba_id = cur.fetchone()[0]

                entry_id = auto_log_notebook_entry(
                    conn, pid, debdeba_id, req.title, req.content,
                    req.entry_type, sid, req.pipeline_stage
                )

                # Set extra fields if passed
                if req.conclusions or req.issues_found or req.next_steps:
                    cur.execute("""
                        UPDATE platform.notebook_entry
                        SET conclusions = %s, issues_found = %s, next_steps = %s, tags = %s::text[]
                        WHERE entry_id = %s;
                    """, (req.conclusions, req.issues_found, req.next_steps, req.tags, entry_id))

                conn.commit()
                return {"status": "success", "entry_id": str(entry_id)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.put("/notebook/{entry_id}")
def update_notebook(entry_id: str, req: NotebookEntryUpdate, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                # Get next version number
                cur.execute("SELECT COUNT(*) FROM platform.notebook_revision WHERE entry_id = %s;", (entry_id,))
                rev_count = cur.fetchone()[0]
                new_rev = rev_count + 1

                cur.execute("SELECT researcher_id FROM platform.researcher WHERE username = 'debdeba';")
                debdeba_id = cur.fetchone()[0]

                # Update main table
                cur.execute("""
                    UPDATE platform.notebook_entry
                    SET title = %s, content = %s, conclusions = %s, issues_found = %s, next_steps = %s, tags = %s::text[], entry_type = %s, updated_at = now()
                    WHERE entry_id = %s;
                """, (req.title, req.content, req.conclusions, req.issues_found, req.next_steps, req.tags, req.entry_type, entry_id))

                # Insert revision record
                cur.execute("""
                    INSERT INTO platform.notebook_revision (entry_id, revision_number, title, content, conclusions, issues_found, next_steps, tags, author_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::text[], %s);
                """, (entry_id, new_rev, req.title, req.content, req.conclusions, req.issues_found, req.next_steps, req.tags, debdeba_id))

                conn.commit()
                return {"status": "success", "revision_number": new_rev}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/notebook/{entry_id}/rollback")
def rollback_notebook(entry_id: str, revision_number: int = Query(...)) -> dict:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT title, content, conclusions, issues_found, next_steps, tags
                    FROM platform.notebook_revision
                    WHERE entry_id = %s AND revision_number = %s;
                """, (entry_id, revision_number))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Revision not found")

                cur.execute("""
                    UPDATE platform.notebook_entry
                    SET title = %s, content = %s, conclusions = %s, issues_found = %s, next_steps = %s, tags = %s::text[], updated_at = now()
                    WHERE entry_id = %s;
                """, (row[0], row[1], row[2], row[3], row[4], row[5], entry_id))

                conn.commit()
                return {"status": "success"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/decisions")
def get_decisions(project_code: Optional[str] = None, user: dict = Depends(require_platform_user)) -> List[Dict[str, Any]]:
    require_role(user, ["editor", "admin"])
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT d.decision_id, p.project_code, d.title, d.decision_details, d.rationale, d.alternatives_considered, r.full_name, d.decision_date
                    FROM platform.decision_registry d
                    JOIN core.project p ON d.project_id = p.project_id
                    LEFT JOIN platform.researcher r ON d.decided_by_id = r.researcher_id
                """
                params = []
                if project_code:
                    query += " WHERE p.project_code = %s"
                    params.append(project_code)
                query += " ORDER BY d.decision_date DESC;"
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                return [{
                    "decision_id": str(r[0]),
                    "project_code": r[1],
                    "title": r[2],
                    "decision_details": r[3],
                    "rationale": r[4],
                    "alternatives_considered": r[5],
                    "decider_name": r[6],
                    "decision_date": str(r[7])
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/decisions")
def create_decision(req: DecisionCreate, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT project_id FROM core.project WHERE project_code = %s;", (req.project_code,))
                pid = cur.fetchone()[0]
                
                cur.execute("SELECT researcher_id FROM platform.researcher WHERE username = %s;", (req.decided_by_username,))
                rid = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO platform.decision_registry (project_id, title, decision_details, rationale, alternatives_considered, decided_by_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING decision_id;
                """, (pid, req.title, req.decision_details, req.rationale, req.alternatives_considered, rid))
                decision_id = cur.fetchone()[0]

                # Automatically log in the notebook
                auto_log_notebook_entry(
                    conn, pid, rid,
                    title=f"Decision Logged: {req.title}",
                    content=f"A formal research decision was committed.\nDetails: {req.decision_details}\nRationale: {req.rationale}",
                    entry_type="decision_note"
                )
                conn.commit()
                return {"status": "success", "decision_id": str(decision_id)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/wiki")
def get_wiki() -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT w.wiki_id, w.title, w.slug, w.content, w.wiki_type, p.project_code, r.full_name, w.updated_at,
                           (SELECT COUNT(*) FROM platform.wiki_revision WHERE wiki_id = w.wiki_id) as rev_count
                    FROM platform.research_wiki w
                    LEFT JOIN core.project p ON w.project_id = p.project_id
                    LEFT JOIN platform.researcher r ON w.created_by_id = r.researcher_id
                    ORDER BY w.updated_at DESC;
                """)
                rows = cur.fetchall()
                return [{
                    "wiki_id": str(r[0]),
                    "title": r[1],
                    "slug": r[2],
                    "content": r[3],
                    "wiki_type": r[4],
                    "project_code": r[5],
                    "author_name": r[6],
                    "updated_at": r[7].isoformat(),
                    "revision": r[8] if r[8] > 0 else 1
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/wiki")
def create_wiki_page(req: WikiPageCreate, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                pid = None
                if req.project_code:
                    cur.execute("SELECT project_id FROM core.project WHERE project_code = %s;", (req.project_code,))
                    pid = cur.fetchone()[0]

                cur.execute("SELECT researcher_id FROM platform.researcher WHERE username = 'debdeba';")
                rid = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO platform.research_wiki (title, slug, content, wiki_type, project_id, created_by_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING wiki_id;
                """, (req.title, req.slug, req.content, req.wiki_type, pid, rid))
                wiki_id = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO platform.wiki_revision (wiki_id, revision_number, title, content, author_id)
                    VALUES (%s, 1, %s, %s, %s);
                """, (wiki_id, req.title, req.content, rid))

                conn.commit()
                return {"status": "success", "wiki_id": str(wiki_id)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.put("/wiki/{wiki_id}")
def update_wiki_page(wiki_id: str, req: WikiPageUpdate, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                # Count current versions
                cur.execute("SELECT COUNT(*) FROM platform.wiki_revision WHERE wiki_id = %s;", (wiki_id,))
                count = cur.fetchone()[0]
                new_rev = count + 1

                cur.execute("SELECT researcher_id FROM platform.researcher WHERE username = 'debdeba';")
                rid = cur.fetchone()[0]

                cur.execute("""
                    UPDATE platform.research_wiki
                    SET title = %s, content = %s, wiki_type = %s, updated_at = now()
                    WHERE wiki_id = %s;
                """, (req.title, req.content, req.wiki_type, wiki_id))

                cur.execute("""
                    INSERT INTO platform.wiki_revision (wiki_id, revision_number, title, content, author_id)
                    VALUES (%s, %s, %s, %s, %s);
                """, (wiki_id, new_rev, req.title, req.content, rid))

                conn.commit()
                return {"status": "success", "revision_number": new_rev}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/notebook/search")
def search_notebook(
    q: str = Query(..., min_length=2),
    project_code: Optional[str] = Query(None),
    entry_type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> List[Dict[str, Any]]:
    """Full-text keyword search across notebook entries (title + content + tags)."""
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                pattern = f"%{q}%"
                query = """
                    SELECT ne.entry_id, p.project_code, s.sample_code, ne.title,
                           ne.pipeline_stage, ne.content, ne.conclusions, ne.issues_found,
                           ne.next_steps, ne.tags, ne.entry_type, ne.visibility_level,
                           ne.created_at, r.full_name
                    FROM platform.notebook_entry ne
                    JOIN core.project p ON ne.project_id = p.project_id
                    LEFT JOIN core.sample s ON ne.sample_id = s.sample_id
                    JOIN platform.researcher r ON ne.author_id = r.researcher_id
                    WHERE (
                        ne.title ILIKE %s OR
                        ne.content ILIKE %s OR
                        ne.conclusions ILIKE %s OR
                        ne.issues_found ILIKE %s OR
                        ne.next_steps ILIKE %s OR
                        %s = ANY(ne.tags)
                    )
                """
                params: list = [pattern, pattern, pattern, pattern, pattern, q]
                if project_code:
                    query += " AND p.project_code = %s"
                    params.append(project_code)
                if entry_type:
                    query += " AND ne.entry_type = %s"
                    params.append(entry_type)
                query += " ORDER BY ne.created_at DESC LIMIT %s;"
                params.append(limit)
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                return [{
                    "entry_id": str(r[0]),
                    "project_code": r[1],
                    "sample_code": r[2],
                    "title": r[3],
                    "pipeline_stage": r[4],
                    "content": r[5],
                    "conclusions": r[6],
                    "issues_found": r[7],
                    "next_steps": r[8],
                    "tags": r[9],
                    "entry_type": r[10],
                    "visibility_level": r[11],
                    "created_at": r[12].isoformat(),
                    "author_name": r[13],
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.delete("/notebook/{entry_id}")
def delete_notebook_entry(entry_id: str, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    """Permanently delete a notebook entry and all its revisions."""
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM platform.notebook_entry WHERE entry_id = %s RETURNING entry_id;", (entry_id,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Notebook entry not found")
                conn.commit()
                return {"status": "success", "deleted_entry_id": str(row[0])}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/wiki/{wiki_id}/revisions")
def get_wiki_revisions(wiki_id: str) -> List[Dict[str, Any]]:
    """Fetch full version history for a wiki page."""
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT wr.revision_id, wr.revision_number, wr.title, wr.content, wr.created_at,
                           r.full_name
                    FROM platform.wiki_revision wr
                    LEFT JOIN platform.researcher r ON wr.author_id = r.researcher_id
                    WHERE wr.wiki_id = %s
                    ORDER BY wr.revision_number DESC;
                """, (wiki_id,))
                rows = cur.fetchall()
                return [{
                    "revision_id": str(r[0]),
                    "revision_number": r[1],
                    "title": r[2],
                    "content": r[3],
                    "created_at": r[4].isoformat(),
                    "author_name": r[5],
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/wiki/{wiki_id}/rollback")
def rollback_wiki(wiki_id: str, revision_number: int = Query(...)) -> dict:
    """Restore a wiki page to a specific previous revision."""
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT title, content
                    FROM platform.wiki_revision
                    WHERE wiki_id = %s AND revision_number = %s;
                """, (wiki_id, revision_number))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Wiki revision not found")

                # Count current revisions to assign next number
                cur.execute("SELECT COUNT(*) FROM platform.wiki_revision WHERE wiki_id = %s;", (wiki_id,))
                next_rev = cur.fetchone()[0] + 1

                cur.execute("SELECT researcher_id FROM platform.researcher WHERE username = 'debdeba';")
                rid = cur.fetchone()[0]

                # Apply rollback to main table
                cur.execute("""
                    UPDATE platform.research_wiki
                    SET title = %s, content = %s, updated_at = now()
                    WHERE wiki_id = %s;
                """, (row[0], row[1], wiki_id))

                # Record rollback as new revision for full auditability
                cur.execute("""
                    INSERT INTO platform.wiki_revision (wiki_id, revision_number, title, content, author_id)
                    VALUES (%s, %s, %s, %s, %s);
                """, (wiki_id, next_rev, row[0], row[1], rid))

                conn.commit()
                return {"status": "success", "restored_revision": revision_number, "new_revision": next_rev}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.delete("/wiki/{wiki_id}")
def delete_wiki_page(wiki_id: str, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    """Permanently delete a wiki page and all its revisions."""
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM platform.research_wiki WHERE wiki_id = %s RETURNING wiki_id;", (wiki_id,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Wiki page not found")
                conn.commit()
                return {"status": "success", "deleted_wiki_id": str(row[0])}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/wiki/search")
def search_wiki(
    q: str = Query(..., min_length=2),
    wiki_type: Optional[str] = Query(None),
    project_code: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> List[Dict[str, Any]]:
    """Full-text keyword search across wiki pages (title + content)."""
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                pattern = f"%{q}%"
                query = """
                    SELECT w.wiki_id, w.title, w.slug, w.content, w.wiki_type,
                           p.project_code, r.full_name, w.updated_at
                    FROM platform.research_wiki w
                    LEFT JOIN core.project p ON w.project_id = p.project_id
                    LEFT JOIN platform.researcher r ON w.created_by_id = r.researcher_id
                    WHERE (w.title ILIKE %s OR w.content ILIKE %s)
                """
                params: list = [pattern, pattern]
                if wiki_type:
                    query += " AND w.wiki_type = %s"
                    params.append(wiki_type)
                if project_code:
                    query += " AND p.project_code = %s"
                    params.append(project_code)
                query += " ORDER BY w.updated_at DESC LIMIT %s;"
                params.append(limit)
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                return [{
                    "wiki_id": str(r[0]),
                    "title": r[1],
                    "slug": r[2],
                    "content": r[3],
                    "wiki_type": r[4],
                    "project_code": r[5],
                    "author_name": r[6],
                    "updated_at": r[7].isoformat(),
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/decisions/search")
def search_decisions(
    q: str = Query(..., min_length=2),
    project_code: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> List[Dict[str, Any]]:
    """Full-text keyword search across the decision registry."""
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                pattern = f"%{q}%"
                query = """
                    SELECT d.decision_id, p.project_code, d.title, d.decision_details,
                           d.rationale, d.alternatives_considered, r.full_name, d.decision_date
                    FROM platform.decision_registry d
                    JOIN core.project p ON d.project_id = p.project_id
                    LEFT JOIN platform.researcher r ON d.decided_by_id = r.researcher_id
                    WHERE (
                        d.title ILIKE %s OR
                        d.decision_details ILIKE %s OR
                        d.rationale ILIKE %s OR
                        d.alternatives_considered ILIKE %s
                    )
                """
                params: list = [pattern, pattern, pattern, pattern]
                if project_code:
                    query += " AND p.project_code = %s"
                    params.append(project_code)
                query += " ORDER BY d.decision_date DESC LIMIT %s;"
                params.append(limit)
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                return [{
                    "decision_id": str(r[0]),
                    "project_code": r[1],
                    "title": r[2],
                    "decision_details": r[3],
                    "rationale": r[4],
                    "alternatives_considered": r[5],
                    "decider_name": r[6],
                    "decision_date": str(r[7]),
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.delete("/decisions/{decision_id}")
def delete_decision(decision_id: str, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    """Permanently delete a decision registry entry."""
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM platform.decision_registry WHERE decision_id = %s RETURNING decision_id;", (decision_id,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Decision not found")
                conn.commit()
                return {"status": "success", "deleted_decision_id": str(row[0])}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.delete("/tasks/{task_id}")
def delete_task(task_id: str, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    """Permanently delete a task."""
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM platform.task WHERE task_id = %s RETURNING task_id;", (task_id,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Task not found")
                conn.commit()
                return {"status": "success", "deleted_task_id": str(row[0])}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/platform/search")
def platform_search(
    q: str = Query(..., min_length=2),
    project_code: Optional[str] = Query(None),
    include: str = Query("notebook,wiki,decisions", description="Comma-separated: notebook,wiki,decisions"),
    limit: int = Query(10, ge=1, le=50),
) -> Dict[str, Any]:
    """Unified full-text keyword search across notebook entries, wiki pages, and decisions.

    Useful for the UI global search bar — returns ranked, merged results without
    requiring a Qdrant/RAG round trip.
    """
    targets = {t.strip().lower() for t in (include or "").split(",") if t.strip()}
    out: Dict[str, Any] = {"query": q, "project_code": project_code}

    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                pattern = f"%{q}%"

                if "notebook" in targets:
                    nb_query = """
                        SELECT ne.entry_id::text, p.project_code, ne.title,
                               LEFT(ne.content, 300) AS excerpt, ne.entry_type, ne.created_at
                        FROM platform.notebook_entry ne
                        JOIN core.project p ON ne.project_id = p.project_id
                        WHERE (ne.title ILIKE %s OR ne.content ILIKE %s)
                    """
                    nb_params: list = [pattern, pattern]
                    if project_code:
                        nb_query += " AND p.project_code = %s"
                        nb_params.append(project_code)
                    nb_query += " ORDER BY ne.created_at DESC LIMIT %s;"
                    nb_params.append(limit)
                    cur.execute(nb_query, tuple(nb_params))
                    out["notebook"] = [
                        {"id": r[0], "project_code": r[1], "title": r[2],
                         "excerpt": r[3], "kind": r[4], "created_at": r[5].isoformat()}
                        for r in cur.fetchall()
                    ]

                if "wiki" in targets:
                    w_query = """
                        SELECT w.wiki_id::text, p.project_code, w.title,
                               LEFT(w.content, 300) AS excerpt, w.wiki_type, w.updated_at
                        FROM platform.research_wiki w
                        LEFT JOIN core.project p ON w.project_id = p.project_id
                        WHERE (w.title ILIKE %s OR w.content ILIKE %s)
                    """
                    w_params: list = [pattern, pattern]
                    if project_code:
                        w_query += " AND p.project_code = %s"
                        w_params.append(project_code)
                    w_query += " ORDER BY w.updated_at DESC LIMIT %s;"
                    w_params.append(limit)
                    cur.execute(w_query, tuple(w_params))
                    out["wiki"] = [
                        {"id": r[0], "project_code": r[1], "title": r[2],
                         "excerpt": r[3], "kind": r[4], "updated_at": r[5].isoformat()}
                        for r in cur.fetchall()
                    ]

                if "decisions" in targets:
                    d_query = """
                        SELECT d.decision_id::text, p.project_code, d.title,
                               LEFT(d.decision_details, 300) AS excerpt, d.decision_date
                        FROM platform.decision_registry d
                        JOIN core.project p ON d.project_id = p.project_id
                        WHERE (d.title ILIKE %s OR d.decision_details ILIKE %s OR d.rationale ILIKE %s)
                    """
                    d_params: list = [pattern, pattern, pattern]
                    if project_code:
                        d_query += " AND p.project_code = %s"
                        d_params.append(project_code)
                    d_query += " ORDER BY d.decision_date DESC LIMIT %s;"
                    d_params.append(limit)
                    cur.execute(d_query, tuple(d_params))
                    out["decisions"] = [
                        {"id": r[0], "project_code": r[1], "title": r[2],
                         "excerpt": r[3], "decision_date": str(r[4])}
                        for r in cur.fetchall()
                    ]

                total = sum(
                    len(out.get(k) or []) for k in ("notebook", "wiki", "decisions")
                )
                out["total"] = total
                return out
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/folders")
def get_folders(project_code: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT f.folder_id, p.project_code, s.sample_code, f.folder_name, f.absolute_path, f.storage_system, f.data_type, f.file_count, f.total_size_bytes
                    FROM platform.folder_catalog f
                    JOIN core.project p ON f.project_id = p.project_id
                    LEFT JOIN core.sample s ON f.sample_id = s.sample_id
                """
                params = []
                if project_code:
                    query += " WHERE p.project_code = %s"
                    params.append(project_code)
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                return [{
                    "folder_id": str(r[0]),
                    "project_code": r[1],
                    "sample_code": r[2],
                    "folder_name": r[3],
                    "absolute_path": r[4],
                    "storage_system": r[5],
                    "data_type": r[6],
                    "file_count": r[7],
                    "total_size_bytes": r[8]
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/datasets")
def get_datasets(project_code: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT d.dataset_id, p.project_code, s.sample_code, d.dataset_name, d.data_type, d.format, d.file_path, d.file_size_bytes, d.quality_status, d.notes
                    FROM platform.dataset_catalog d
                    JOIN core.project p ON d.project_id = p.project_id
                    LEFT JOIN core.sample s ON d.sample_id = s.sample_id
                """
                params = []
                if project_code:
                    query += " WHERE p.project_code = %s"
                    params.append(project_code)
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                return [{
                    "dataset_id": str(r[0]),
                    "project_code": r[1],
                    "sample_code": r[2],
                    "dataset_name": r[3],
                    "data_type": r[4],
                    "format": r[5],
                    "file_path": r[6],
                    "file_size": r[7],
                    "quality_status": r[8],
                    "notes": r[9]
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/pipeline_runs")
def get_pipeline_runs(project_code: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT pr.run_id, p.project_code, s.sample_code, pr.pipeline_stage, pr.command_used, pr.script_path, pr.status, pr.error_summary, pr.qc_result, pr.created_at
                    FROM platform.pipeline_run pr
                    JOIN core.project p ON pr.project_id = p.project_id
                    LEFT JOIN core.sample s ON pr.sample_id = s.sample_id
                """
                params = []
                if project_code:
                    query += " WHERE p.project_code = %s"
                    params.append(project_code)
                query += " ORDER BY pr.created_at DESC;"
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                return [{
                    "run_id": str(r[0]),
                    "project_code": r[1],
                    "sample_code": r[2],
                    "pipeline_stage": r[3],
                    "command_used": r[4],
                    "script_path": r[5],
                    "status": r[6],
                    "error_summary": r[7],
                    "qc_result": r[8],
                    "created_at": r[9].isoformat()
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/tasks")
def get_tasks(project_code: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT t.task_id, p.project_code, s.sample_code, r.full_name, t.title, t.description, t.status, t.priority, t.due_date
                    FROM platform.task t
                    JOIN core.project p ON t.project_id = p.project_id
                    LEFT JOIN core.sample s ON t.sample_id = s.sample_id
                    LEFT JOIN platform.researcher r ON t.assigned_to = r.researcher_id
                """
                params = []
                if project_code:
                    query += " WHERE p.project_code = %s"
                    params.append(project_code)
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                return [{
                    "task_id": str(r[0]),
                    "project_code": r[1],
                    "sample_code": r[2],
                    "assigned_to": r[3],
                    "title": r[4],
                    "description": r[5],
                    "status": r[6],
                    "priority": r[7],
                    "due_date": str(r[8]) if r[8] else None
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/tasks")
def create_task(req: TaskCreate, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT project_id FROM core.project WHERE project_code = %s;", (req.project_code,))
                pid = cur.fetchone()[0]

                sid = None
                if req.sample_code:
                    cur.execute("SELECT sample_id FROM core.sample WHERE sample_code = %s;", (req.sample_code,))
                    s_row = cur.fetchone()
                    if s_row:
                        sid = s_row[0]

                cur.execute("SELECT researcher_id FROM platform.researcher WHERE username = 'debdeba';")
                rid = cur.fetchone()[0]

                due = datetime.strptime(req.due_date, "%Y-%m-%d").date() if req.due_date else None

                cur.execute("""
                    INSERT INTO platform.task (project_id, sample_id, title, description, status, priority, due_date, assigned_to)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING task_id;
                """, (pid, sid, req.title, req.description, req.status, req.priority, due, rid))
                task_id = cur.fetchone()[0]

                # Automatically log in the notebook
                auto_log_notebook_entry(
                    conn, pid, rid,
                    title=f"Task Created: {req.title}",
                    content=f"Task assigned to debdeba.\nDetails: {req.description or ''}\nStatus: {req.status}, Priority: {req.priority}",
                    entry_type="general_note",
                    sample_id=sid
                )
                conn.commit()
                return {"status": "success", "task_id": str(task_id)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.put("/tasks/{task_id}")
def update_task(task_id: str, req: TaskUpdate, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                due = datetime.strptime(req.due_date, "%Y-%m-%d").date() if req.due_date else None
                cur.execute("""
                    UPDATE platform.task
                    SET title = %s, description = %s, status = %s, priority = %s, due_date = %s, updated_at = now()
                    WHERE task_id = %s
                    RETURNING project_id, sample_id;
                """, (req.title, req.description, req.status, req.priority, due, task_id))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Task not found")
                
                pid, sid = row[0], row[1]
                cur.execute("SELECT researcher_id FROM platform.researcher WHERE username = 'debdeba';")
                rid = cur.fetchone()[0]

                # Automatically log in the notebook
                auto_log_notebook_entry(
                    conn, pid, rid,
                    title=f"Task Updated: {req.title}",
                    content=f"Task status changed to {req.status}.\nPriority: {req.priority}",
                    entry_type="general_note",
                    sample_id=sid
                )
                conn.commit()
                return {"status": "success"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/auto_logs")
def get_auto_logs() -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT log_id, actor, event_type, description, created_at
                    FROM platform.auto_log
                    ORDER BY created_at DESC LIMIT 50;
                """)
                rows = cur.fetchall()
                return [{
                    "log_id": str(r[0]),
                    "actor": r[1],
                    "event_type": r[2],
                    "description": r[3],
                    "created_at": r[4].isoformat()
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/team")
def get_team() -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT username, full_name, role, allowed_project_codes
                    FROM platform.researcher;
                """)
                rows = cur.fetchall()
                return [{
                    "username": r[0],
                    "full_name": r[1],
                    "role": r[2],
                    "allowed_projects": r[3]
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/projects")
def create_project(req: ProjectCreate, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                # Get or create lead researcher
                cur.execute("SELECT researcher_id FROM platform.researcher WHERE full_name = %s OR username = %s LIMIT 1;", (req.project_lead, req.project_lead.lower().replace(" ", "")))
                row = cur.fetchone()
                if row:
                    lead_id = row[0]
                else:
                    username = req.project_lead.lower().replace(" ", "")[:15]
                    cur.execute("""
                        INSERT INTO platform.researcher (username, full_name, role, allowed_project_codes)
                        VALUES (%s, %s, 'researcher', ARRAY[%s]::text[])
                        RETURNING researcher_id;
                    """, (username, req.project_lead, req.project_code))
                    lead_id = cur.fetchone()[0]

                # Get PI researcher ID
                cur.execute("SELECT researcher_id FROM platform.researcher WHERE username = 'afarkkila';")
                af_row = cur.fetchone()
                pi_id = af_row[0] if af_row else lead_id

                # Insert Core project
                cur.execute("""
                    INSERT INTO core.project (project_code, project_name, project_lead, principal_investigator, disease_focus, short_description, default_sensitivity, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::core.sensitivity_level, %s::core.record_status)
                    ON CONFLICT (project_code) DO UPDATE
                    SET project_name = EXCLUDED.project_name, short_description = EXCLUDED.short_description
                    RETURNING project_id;
                """, (req.project_code, req.project_name, req.project_lead, req.principal_investigator, req.disease_focus, req.short_description, req.default_sensitivity, req.status))
                pid = cur.fetchone()[0]

                # Insert Project Extension
                cur.execute("""
                    INSERT INTO platform.project_extension (project_id, project_short_title, research_question, project_type, priority, collaborators, ethics_approval_reference, current_blockers, next_actions, project_summary, latest_update)
                    VALUES (%s, %s, %s, %s, %s, %s::text[], %s, %s, %s, %s, 'Project onboarded via wizard.')
                    ON CONFLICT (project_id) DO UPDATE
                    SET ethics_approval_reference = EXCLUDED.ethics_approval_reference,
                        current_blockers = EXCLUDED.current_blockers,
                        next_actions = EXCLUDED.next_actions,
                        project_summary = EXCLUDED.project_summary;
                """, (pid, req.project_name[:50], req.short_description, req.project_type, req.priority, req.collaborators, req.ethics_approval_reference, req.current_blockers, req.next_actions, req.project_summary))

                # Add members to project_member
                # Lead
                cur.execute("""
                    INSERT INTO platform.project_member (project_id, researcher_id, role, project_access_level, notes)
                    VALUES (%s, %s, 'project_lead', 'read_write', 'Lead researcher on project')
                    ON CONFLICT (project_id, researcher_id) DO NOTHING;
                """, (pid, lead_id))
                
                # PI
                cur.execute("""
                    INSERT INTO platform.project_member (project_id, researcher_id, role, project_access_level, notes)
                    VALUES (%s, %s, 'PI', 'admin', 'Principal Investigator oversight')
                    ON CONFLICT (project_id, researcher_id) DO NOTHING;
                """, (pid, pi_id))

                # Seeding onboarding checklist items for this new project
                checklist_items = [
                    ("project", "Project Description & Goals", "Ensure project description, scientific questions, and goals are documented."),
                    ("project", "Members & Collaborators", "Add responsible researchers and their clinical/computational roles."),
                    ("document", "Protocols & SOPs", "Link the wet-lab staining/imaging and dry-lab segmentation SOPs used."),
                    ("document", "Ethics Approvals", "Record the ethics board registry reference number."),
                    ("software", "Software Versions", "Document package versions (Cylinter, Ashlar, Mesmer, Tribus) used."),
                    ("pipeline", "Stitching Pipeline Run", "Execute and link Ashlar stitching logs/runs."),
                    ("pipeline", "Cell Segmentation Quality Check", "Verify cell boundaries and mask outputs."),
                    ("dataset", "OME-TIFF Raw Slides", "Verify raw image folders are cataloged and size computed."),
                    ("dataset", "Segmented Cell Masks", "Store and register cell masks (.tif) in object storage."),
                    ("dataset", "Quantified Cell Features Table", "Verify single-cell expression tables (.csv/.h5ad) are cataloged."),
                    ("sample", "Sample Code Verification", "Align clinical patient codes with imaging specimen codes."),
                    ("publication", "Preprint/Publication Linkage", "Track linked publications or conference poster details.")
                ]
                for category, item, desc in checklist_items:
                    cur.execute("""
                        INSERT INTO platform.onboarding_checklist (project_id, category, item_name, description, status)
                        VALUES (%s, %s, %s, %s, 'pending')
                        ON CONFLICT (project_id, category, item_name) DO NOTHING;
                    """, (pid, category, item, desc))

                # Automatically write to Digital Notebook
                auto_log_notebook_entry(
                    conn, pid, lead_id,
                    title="Project Onboarded Successfully",
                    content=f"The project '{req.project_name}' has been created with code '{req.project_code}' by Lead {req.project_lead}.\nPriority set to: {req.priority}\nEthics Reference: {req.ethics_approval_reference}",
                    entry_type="general_note"
                )

                conn.commit()
                return {"status": "success", "project_id": str(pid)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/ai-models")
def get_ai_models() -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT model_id, name, model_type, source, license, parameters, gpu_requirements, memory_requirements, local_deployment, api_deployment, use_cases, strengths, weaknesses, installation_instructions
                    FROM platform.ai_model
                    ORDER BY model_type, name;
                """)
                rows = cur.fetchall()
                return [{
                    "model_id": str(r[0]),
                    "name": r[1],
                    "model_type": r[2],
                    "source": r[3],
                    "license": r[4],
                    "parameters": r[5],
                    "gpu_requirements": r[6],
                    "memory_requirements": r[7],
                    "local_deployment": r[8],
                    "api_deployment": r[9],
                    "use_cases": r[10],
                    "strengths": r[11],
                    "weaknesses": r[12],
                    "installation_instructions": r[13]
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/infrastructure")
def get_infrastructure() -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT resource_id, name, resource_type, operating_system, cpu_specs, ram_specs, gpu_specs, storage_specs, installed_software, access_notes, maintenance_notes
                    FROM platform.infrastructure
                    ORDER BY resource_type, name;
                """)
                rows = cur.fetchall()
                return [{
                    "resource_id": str(r[0]),
                    "name": r[1],
                    "resource_type": r[2],
                    "operating_system": r[3],
                    "cpu_specs": r[4],
                    "ram_specs": r[5],
                    "gpu_specs": r[6],
                    "storage_specs": r[7],
                    "installed_software": r[8],
                    "access_notes": r[9],
                    "maintenance_notes": r[10]
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/publications")
def get_publications() -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT pub.pub_id, pub.title, pub.authors, pub.journal, pub.publication_year, pub.doi, pub.pmid, pub.abstract, p.project_code, pub.full_text_path
                    FROM platform.publication pub
                    LEFT JOIN core.project p ON pub.project_id = p.project_id
                    ORDER BY pub.publication_year DESC, pub.title;
                """)
                rows = cur.fetchall()
                return [{
                    "pub_id": str(r[0]),
                    "title": r[1],
                    "authors": r[2],
                    "journal": r[3],
                    "publication_year": r[4],
                    "doi": r[5],
                    "pmid": r[6],
                    "abstract": r[7],
                    "project_code": r[8],
                    "full_text_path": r[9]
                } for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/checklists/{project_code}")
def get_project_checklists(project_code: str) -> List[Dict[str, Any]]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT project_id FROM core.project WHERE project_code = %s;", (project_code,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Project not found")
                pid = row[0]
                cur.execute("""
                    SELECT checklist_id, category, item_name, description, status, checked_at
                    FROM platform.onboarding_checklist
                    WHERE project_id = %s
                    ORDER BY category, item_name;
                """, (pid,))
                rows = cur.fetchall()
                return [{
                    "checklist_id": str(r[0]),
                    "category": r[1],
                    "item_name": r[2],
                    "description": r[3],
                    "status": r[4],
                    "checked_at": r[5].isoformat() if r[5] else None
                } for r in rows]
    except HTTPException:
        raise
    except Exception as exc:
        # Table may be missing on fresh DB — don't break project workspace load
        if "onboarding_checklist" in str(exc) or "does not exist" in str(exc):
            return []
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/checklists/toggle")
def toggle_checklist(req: ChecklistToggleRequest, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                # Get current status and item details
                cur.execute("""
                    SELECT project_id, category, item_name, status 
                    FROM platform.onboarding_checklist 
                    WHERE checklist_id = %s;
                """, (req.checklist_id,))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Checklist item not found")
                
                pid, category, item_name, current_status = row[0], row[1], row[2], row[3]
                
                # Toggle or set status
                checked_at = datetime.now() if req.status == 'completed' else None
                cur.execute("""
                    UPDATE platform.onboarding_checklist
                    SET status = %s, checked_at = %s, updated_at = now()
                    WHERE checklist_id = %s;
                """, (req.status, checked_at, req.checklist_id))

                # Fetch researcher ID
                cur.execute("SELECT researcher_id FROM platform.researcher WHERE username = %s LIMIT 1;", (req.username,))
                res_row = cur.fetchone()
                rid = res_row[0] if res_row else None

                # Log to notebook
                auto_log_notebook_entry(
                    conn, pid, rid,
                    title=f"Checklist Item Updated: {item_name}",
                    content=f"Checklist item '{item_name}' in category '{category}' changed from '{current_status}' to '{req.status}'.",
                    entry_type="general_note"
                )

                conn.commit()
                return {"status": "success", "new_status": req.status}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
```

### `omeia/api/routers/copilot.py`

```python
from omeia.security.permissions import require_role
from omeia.security.auth import require_platform_user
from fastapi import APIRouter, Depends, Query, Path, HTTPException, Request, Response, BackgroundTasks, UploadFile, File
from omeia.api.common import *
from typing import *
from pydantic import BaseModel, Field
import psycopg

router = APIRouter()

@router.get("/api/billing-instructions")
def get_billing_instructions() -> dict:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT document_id,
                           document_type,
                           source_language,
                           author_name,
                           author_email,
                           subject,
                           raw_text,
                           structured_json
                    FROM core.documents 
                    WHERE document_type IN (
                        'billing_instruction', 
                        'order_form', 
                        'shipping_customs_statement', 
                        'shipping_instruction', 
                        'courier_service_account_instruction', 
                        'courier_service_instruction'
                    ) 
                    ORDER BY created_at DESC;
                """)
                rows = cur.fetchall()
                documents = []
                for row in rows:
                    if not row or not row[7]:
                        continue
                    structured_json = row[7] if isinstance(row[7], dict) else {}
                    document = {
                        "document_id": str(row[0]),
                        "document_type": row[1],
                        "source_language": row[2],
                        "author_name": row[3],
                        "author_email": row[4],
                        "subject": row[5],
                        "raw_text": row[6],
                        **structured_json,
                    }
                    documents.append(document)
                return {"documents": documents}
    except Exception as exc:
        LOGGER.warning("Failed to fetch billing instructions: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/ask", response_model=QuestionResponse)
def ask(req: QuestionRequest, user: dict = Depends(require_platform_user)) -> QuestionResponse:
    require_role(user, ["editor", "admin"])
    # 1. Initialize temporary LLM client dynamically if configured from frontend
    active_llm = llm_client
    if req.llm_provider and req.llm_provider != "mock":
        active_llm = LLMClient()
        active_llm.provider = req.llm_provider.lower()
        active_llm.model = req.llm_model or active_llm.model
        active_llm.api_key = req.llm_api_key or active_llm.api_key
        active_llm.base_url = req.llm_base_url or active_llm.base_url
        active_llm._init_client()

    # 2. Run privacy audit checks
    audit = PrivacyGuardrailAgent.audit_query(req.question)
    limitations = []
    
    if not audit["is_safe"]:
        limitations.append(f"Safety Alert: Potential Patient Identifiers Redacted ({', '.join(audit['violations'])}).")
        # Block forwarding query to external LLM provider if set to public
        if active_llm.provider != "ollama" and active_llm.provider != "mock":
            return QuestionResponse(
                answer="Error: User query blocked by local privacy guardrails because patient-identifiable data (PII) was detected and LLM is configured to utilize external cloud APIs. De-identify patient data and try again.",
                limitations=limitations,
                sources=[],
                database_counts={},
                is_safe=False
            )

    safe_question = audit["redacted_text"]

    # 3. Fetch structured stats from Postgres
    db_data = query_postgres_metadata(req.project_codes)

    clinical_block = _clinical_context_for_question(safe_question, req.project_codes or [])
    
    # 4. Retrieve documentation chunks using RAGAgent (use active_llm for embedding queries)
    temp_rag = RAGAgent(qdrant_client, active_llm)
    retrieved_sources = temp_rag.retrieve(safe_question, req.project_codes)

    lab_hits = search_lab_knowledge(
        safe_question,
        limit=8,
        qdrant=qdrant_client,
        llm=active_llm,
    )
    seen_ids = {src.get("chunk_id") for src in retrieved_sources}
    for hit in lab_hits:
        cid = hit.get("chunk_uid")
        if cid in seen_ids:
            continue
        seen_ids.add(cid)
        retrieved_sources.append({
            "title": hit.get("title") or hit.get("citation"),
            "source_type": "lab_knowledge",
            "source_uuid": hit.get("document_code") or hit.get("relative_path") or "",
            "chunk_id": cid,
            "text_preview": hit.get("excerpt") or "",
            "score": hit.get("score", 0.0),
        })
    retrieved_sources = retrieved_sources[:12]

    sources = [
        SourceInfo(
            title=src["title"],
            source_type=src["source_type"],
            source_uuid=src["source_uuid"],
            chunk_id=src["chunk_id"],
            text_preview=src["text_preview"],
            score=src["score"]
        ) for src in retrieved_sources
    ]

    # 5. Build prompt and generate response using active_llm
    context_str = ""
    for i, src in enumerate(sources):
        context_str += f"[{i+1}] Source: {src.title} (Type: {src.source_type})\n{src.text_preview}\n\n"
        
    system_prompt = (
        "You are the OMEIA Clinical-Spatial Biology Copilot, an expert AI platform assistant.\n"
        "Your task is to answer the researcher's query based on the database counts and documentation snippets.\n"
        "Follow these rules:\n"
        "1. Report patient/sample statistics exactly as provided in the database counts. Do NOT invent/hallucinate figures.\n"
        "2. If code installation commands or scripts are requested, return structured code blocks detailing required parameters.\n"
        "3. Cite references [1], [2], etc., corresponding to context blocks.\n"
        "4. Remain precise, professional, and highlight limitations."
    )
    
    user_content = (
        f"Database counts:\n"
        f"- Patient total: {db_data.get('patient_count', 0)}\n"
        f"- Sample total: {db_data.get('sample_count', 0)}\n"
        f"- Projects: {db_data.get('project_samples', {})}\n"
        f"- Modalities: {db_data.get('modality_samples', {})}\n\n"
        f"{('Structured clinical/feature analysis:\\n' + clinical_block + '\\n\\n') if clinical_block else ''}"
        f"Documentation Context:\n"
        f"{context_str}\n"
        f"Question: {safe_question}"
    )

    answer = active_llm.generate(user_content, system_prompt)

    if active_llm.provider == "mock":
        limitations.append("Running in local mock-synthesis mode because no LLM_API_KEY is configured.")

    # Audit conversations to DB
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                # Add default user conversation log
                cur.execute(
                    "INSERT INTO platform.conversation (title, project_code) VALUES (%s, %s) RETURNING conversation_id;",
                    ("Research Query Conversation", req.project_codes[0] if req.project_codes else "ALL")
                )
                conv_id = cur.fetchone()[0]
                
                # Insert messages
                cur.execute(
                    "INSERT INTO platform.message (conversation_id, role, content) VALUES (%s, 'user', %s);",
                    (conv_id, safe_question)
                )
                cur.execute(
                    "INSERT INTO platform.message (conversation_id, role, content, retrieved_chunks) VALUES (%s, 'assistant', %s, %s);",
                    (conv_id, answer, psycopg.types.json.Jsonb([s.model_dump() for s in sources]))
                )
    except Exception as exc:
        LOGGER.warning("Failed to log message to Postgres database: %s", exc)

    return QuestionResponse(
        answer=answer,
        limitations=limitations,
        sources=sources,
        database_counts=db_data,
        is_safe=True
    )

@router.post("/install_guide")
def install_guide(req: InstallRequest, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    guide = install_agent.get_instructions(req.tool_name, req.os_platform)
    if guide["status"] == "success":
        # Package standard script using script wrapper
        formatted_script = guide["commands"]
        if req.os_platform.lower() == "linux" or req.os_platform.lower() == "macos":
            formatted_script = script_agent.generate_bash(guide["commands"])
        return {
            "status": "success",
            "tool": guide["tool"],
            "os": guide["os"],
            "script": formatted_script,
            "verification": guide["verification"],
            "expected_output": guide["expected_output"],
            "troubleshooting": guide["troubleshooting"]
        }
    else:
        raise HTTPException(status_code=400, detail=guide["message"])

@router.post("/lumi_job")
def lumi_job(req: LumiJobRequest, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    script = hpc_agent.generate_job(req.model_dump())
    
    # Save script to database
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO platform.generated_script (script_name, script_body, target_language) VALUES (%s, %s, %s) RETURNING script_id;",
                    (req.job_name, script, "bash")
                )
                script_id = cur.fetchone()[0]
                
                # Perform basic static analysis validation
                status = "passed"
                log = "Basic validations passed: Contains set -euo pipefail, checks folders existence, sets Apptainer path."
                if "/scratch" not in script:
                    status = "warnings"
                    log += "\nWarning: No scratch paths detected in script parameters."
                
                cur.execute(
                    "INSERT INTO platform.validation_result (script_id, status, output_log) VALUES (%s, %s, %s);",
                    (script_id, status, log)
                )
    except Exception as exc:
        LOGGER.warning("Failed to audit generated Slurm script to Postgres: %s", exc)

    return {
        "status": "success",
        "script": script,
        "warnings": ["Ensure you replace project_account with active LUMI billing project allocation."]
    }

@router.post("/parse_log")
def parse_log(req: LogParseRequest, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    diagnosis = troubleshooting_agent.diagnose_log(req.log_text)
    return {
        "status": "success",
        "cause": diagnosis["cause"],
        "recommended_fix": diagnosis["fix"],
        "prevention": diagnosis["prevention"]
    }

@router.post("/run_checker")
def run_checker(req: CheckerRequest, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    script_path = checker_script(req.checker_name)
    if not script_path:
        raise HTTPException(status_code=400, detail=f"Checker script {req.checker_name} not found.")

    try:
        cmd = [str(script_path)]
        if script_path.suffix == ".py":
            cmd = ["python3", str(script_path)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=int(os.getenv("CHECKER_TIMEOUT_SECONDS", "45")), cwd=str(script_path.parent))
        status = "PASS" if res.returncode == 0 else "WARNING/FAIL"
        combined = "\n".join(filter(None, [res.stdout.strip(), res.stderr.strip()]))
        return {
            "status": status,
            "stdout": res.stdout,
            "stderr": res.stderr,
            "returncode": res.returncode,
            "execution_logs": combined or "(no output)",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to run environment verification tool: {exc}")

@router.post("/run_checker_suite")
def run_checker_suite(user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    """Run all available environment checkers and return combined report."""
    names = ["python_env", "gpu", "napari", "docker", "lumi_modules", "cylinter_inputs", "project_structure"]
    results = []
    logs = []
    for name in names:
        script_path = checker_script(name)
        if not script_path:
            results.append({"checker_name": name, "status": "SKIPPED", "execution_logs": "Script not found"})
            continue
        try:
            cmd = ["python3", str(script_path)] if script_path.suffix == ".py" else [str(script_path)]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=int(os.getenv("CHECKER_TIMEOUT_SECONDS", "45")), cwd=str(script_path.parent))
            combined = "\n".join(filter(None, [res.stdout.strip(), res.stderr.strip()]))
            status = "PASS" if res.returncode == 0 else "WARNING/FAIL"
            entry = {"checker_name": name, "status": status, "returncode": res.returncode, "execution_logs": combined or "(no output)"}
            results.append(entry)
            logs.append(f"=== {name} [{status}] ===\n{combined}\n")
        except Exception as exc:
            results.append({"checker_name": name, "status": "ERROR", "execution_logs": str(exc)})
            logs.append(f"=== {name} [ERROR] ===\n{exc}\n")

    overall = "PASS" if all(r.get("status") == "PASS" for r in results if r.get("status") != "SKIPPED") else "WARNING/FAIL"
    return {
        "status": overall,
        "checkers": results,
        "execution_logs": "\n".join(logs),
    }

@router.post("/features/seed")
def features_seed(user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    return seed_feature_warehouse()

@router.get("/features/definitions")
def features_definitions() -> dict:
    defs = list_feature_definitions()
    return {"count": len(defs), "features": defs}

@router.get("/features/matrices")
def features_matrices(project_code: Optional[str] = Query(None)) -> dict:
    matrices = list_feature_matrices(project_code)
    return {"count": len(matrices), "matrices": matrices}

@router.get("/features/sample/{sample_code}")
def features_sample(sample_code: str) -> dict:
    return get_sample_features(sample_code)

@router.post("/features/similarity")
def features_similarity(req: SimilarityRequest, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    similar = find_similar_samples(req.sample_code, limit=req.limit, project_code=req.project_code)
    result = {"query_sample": req.sample_code, "similar": similar}
    register_analysis_run("feature_similarity", req.model_dump(), result, req.project_code, title=f"Similarity: {req.sample_code}")
    return result

@router.get("/clinical/variables")
def clinical_variables() -> dict:
    vars_ = get_clinical_variables()
    return {"count": len(vars_), "variables": vars_}

@router.post("/clinical/survival")
def clinical_survival(req: SurvivalRequest, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    results = run_survival_analysis(
        duration_col=req.duration_col,
        event_col=req.event_col,
        group_col=req.group_col,
        project_code=req.project_code,
    )
    if req.register_run:
        register_analysis_run("survival", req.model_dump(), results, req.project_code, title="Kaplan-Meier survival")
    return results

@router.post("/clinical/group-compare")
def clinical_group_compare(req: GroupCompareRequest, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    results = run_group_comparison(
        feature_col=req.feature_col,
        group_col=req.group_col,
        project_code=req.project_code,
    )
    if req.register_run:
        register_analysis_run("group_compare", req.model_dump(), results, req.project_code, title=f"Compare {req.feature_col}")
    return results

@router.get("/analysis-runs")
def analysis_runs(limit: int = Query(20, ge=1, le=100)) -> dict:
    runs = list_analysis_runs(limit)
    return {"count": len(runs), "runs": runs}

@router.get("/clinical/recipe/{analysis_type}")
def clinical_recipe(analysis_type: str) -> dict:
    script = clinical_agent.get_analysis_recipe(analysis_type)
    return {"analysis_type": analysis_type, "script": script}
```

### `omeia/api/routers/vault.py`

```python
from omeia.security.permissions import require_role
from omeia.security.auth import require_platform_user
from fastapi import APIRouter, Depends, Query, Path, HTTPException, Request, Response, BackgroundTasks, UploadFile, File
from omeia.api.common import *
from typing import *
from pydantic import BaseModel, Field
import psycopg

router = APIRouter()

@router.post("/ingest-document")
def ingest_document(req: DocumentIngestRequest, user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    try:
        email = user.get("email")
        uid = user.get("uid") or user.get("sub")
        
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                # Find researcher ID securely by mapping Firebase email/uid to username
                # platform.researcher only has a 'username' column, so we match against email prefix or uid
                username_guess = email.split("@")[0] if email else uid
                cur.execute("""
                    SELECT researcher_id FROM platform.researcher 
                    WHERE username = %s OR username = %s LIMIT 1;
                """, (username_guess, email))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=403, detail="No researcher profile linked to this authenticated user.")
                rid = row[0]

                # Find project ID if project_code is provided
                pid = None
                if req.project_code:
                    cur.execute("SELECT project_id FROM core.project WHERE project_code = %s;", (req.project_code,))
                    row = cur.fetchone()
                    if row:
                        pid = row[0]

                # 1. Chunking and Embedding
                text = req.extracted_text or ""
                chunk_size = 3500
                overlap = 500
                chunks = []
                start = 0
                while start < len(text):
                    end = start + chunk_size
                    chunk = text[start:end]
                    if chunk.strip():
                        chunks.append(chunk.strip())
                    start += chunk_size - overlap
                
                # We use the existing LLMClient to embed locally without secrets if offline
                active_llm = LLMClient()
                points = []
                import hashlib
                import uuid
                
                # Check Qdrant collection
                try:
                    collections = qdrant_client.get_collections().collections
                    if not any(c.name == "doc_chunks" for c in collections):
                        qdrant_client.create_collection(
                            collection_name="doc_chunks",
                            vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE)
                        )
                except Exception as qc_err:
                    LOGGER.error("Failed to check or create Qdrant collection: %s", qc_err)
                    raise HTTPException(status_code=500, detail="Vector DB offline.")

                for idx, chunk in enumerate(chunks):
                    vec = active_llm.embed(chunk, dim=384)
                    text_hash = hashlib.md5(chunk.encode("utf-8")).hexdigest()
                    point_id_str = f"ingest_{req.filename}_{idx}_{text_hash}"
                    point_id = hashlib.md5(point_id_str.encode("utf-8")).hexdigest()
                    point_uuid = str(uuid.UUID(hex=point_id))
                    
                    points.append(models.PointStruct(
                        id=point_uuid,
                        vector=vec,
                        payload={
                            "project_code": req.project_code,
                            "researcher_id": str(rid),
                            "filename": req.filename,
                            "title": req.filename,
                            "document_title": req.filename,
                            "chunk_index": idx,
                            "chunk_id": str(idx),
                            "text": chunk,
                            "text_hash": text_hash,
                            "source_type": "ingested_document",
                        }
                    ))

                if points:
                    qdrant_client.upsert(
                        collection_name="doc_chunks",
                        points=points
                    )

                # 2. Insert document record tracking the indexing
                cur.execute("""
                    INSERT INTO platform.document_ingestion (filename, file_type, extracted_text, tags, project_id, software_associations, pipeline_stage_associations, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING doc_id;
                """, (req.filename, req.file_type, req.extracted_text, req.tags, pid, req.software_associations, req.pipeline_stage_associations, psycopg.types.json.Jsonb(req.metadata_dict)))
                doc_id = cur.fetchone()[0]

                # Update the payload with actual doc_id now that we have it (optional, we already indexed)
                # But it's fine, we used project_code and filename in Qdrant

                # Log into Digital Notebook
                auto_log_notebook_entry(
                    conn, pid, rid,
                    title=f"Document Indexed: {req.filename}",
                    content=f"Document '{req.filename}' ({req.file_type}) successfully vectorized and uploaded to Qdrant.\nChunks indexed: {len(points)}\nAssociations:\n- Software: {', '.join(req.software_associations) or 'None'}",
                    entry_type="general_note"
                )

                conn.commit()
                return {"status": "success", "doc_id": str(doc_id), "chunks_indexed": len(points)}
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.error("Ingestion failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/gap-analysis")
def gap_analysis() -> dict:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                # 1. Total projects count
                cur.execute("SELECT COUNT(*) FROM core.project;")
                total_projects = cur.fetchone()[0]

                # 2. Checklist stats
                cur.execute("SELECT COUNT(*), SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) FROM platform.onboarding_checklist;")
                total_items, completed_items = cur.fetchone()
                total_items = total_items or 0
                completed_items = completed_items or 0
                readiness_score = round((completed_items / total_items * 100), 1) if total_items > 0 else 0.0

                # 3. Project-specific scores
                cur.execute("""
                    SELECT p.project_code, p.project_name, COUNT(c.checklist_id), SUM(CASE WHEN c.status = 'completed' THEN 1 ELSE 0 END)
                    FROM core.project p
                    LEFT JOIN platform.onboarding_checklist c ON p.project_id = c.project_id
                    GROUP BY p.project_code, p.project_name
                    ORDER BY p.project_code;
                """)
                project_breakdown = []
                for code, name, t_count, c_count in cur.fetchall():
                    t_count = t_count or 0
                    c_count = c_count or 0
                    p_score = round((c_count / t_count * 100), 1) if t_count > 0 else 0.0
                    project_breakdown.append({
                        "project_code": code,
                        "project_name": name,
                        "total_items": t_count,
                        "completed_items": c_count,
                        "score": p_score
                    })

                # 4. Inventory counts
                cur.execute("SELECT COUNT(*) FROM platform.ai_model;")
                ai_models_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM platform.infrastructure;")
                infrastructure_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM platform.publication;")
                publications_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM platform.document_ingestion;")
                documents_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM platform.folder_catalog;")
                folders_count = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM platform.dataset_catalog;")
                datasets_count = cur.fetchone()[0]

                # Find missing items
                cur.execute("""
                    SELECT p.project_code, c.category, c.item_name
                    FROM platform.onboarding_checklist c
                    JOIN core.project p ON c.project_id = p.project_id
                    WHERE c.status = 'pending'
                    ORDER BY p.project_code, c.category
                    LIMIT 20;
                """)
                missing_checklist_items = [{"project_code": r[0], "category": r[1], "item_name": r[2]} for r in cur.fetchall()]

                # Generate dynamic recommendations
                recommendations = []
                if readiness_score < 50:
                    recommendations.append("Priority 1: Populate pending checklist items for active clinical cohorts (stitching runs & segmented cell masks).")
                if publications_count == 0:
                    recommendations.append("Priority 2: Seed the publication registry with lab papers to facilitate citation references for Chat Copilot.")
                if documents_count < 5:
                    recommendations.append("Priority 3: Utilize the Document Ingestion wizard to upload local multiplex staining protocols and Slurm template scripts.")
                if ai_models_count < 10:
                    recommendations.append("Priority 4: Verify the local installation scripts for segmentation models (Mesmer / SAM2) are registered.")
                
                if not recommendations:
                    recommendations.append("All core metadata fields are populated. Ready to scale to production multi-cohort processing.")

                coverage = project_catalog_coverage()

                return {
                    "total_projects": total_projects,
                    "catalog_coverage": coverage,
                    "readiness_score": readiness_score,
                    "completed_checklist_items": completed_items,
                    "total_checklist_items": total_items,
                    "project_breakdown": project_breakdown,
                    "ai_models_count": ai_models_count,
                    "infrastructure_count": infrastructure_count,
                    "publications_count": publications_count,
                    "documents_count": documents_count,
                    "folders_count": folders_count,
                    "datasets_count": datasets_count,
                    "missing_checklist_items": missing_checklist_items,
                    "recommendations": recommendations
                }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/api/vault/summary", dependencies=_FIREBASE_PROTECTED)
def vault_summary_endpoint() -> dict:
    summary = vault_summary()
    public = {k: v for k, v in summary.items() if k != "database_root"}
    missing = assert_all_section_roots_exist()
    return {"summary": public, "missing_section_roots": missing}

@router.get("/api/vault/search", dependencies=_FIREBASE_PROTECTED)
def vault_search(
    q: str = Query("", min_length=0),
    domain: Optional[str] = Query(None),
    project_hint: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    extraction_status: Optional[str] = Query(None),
    vector_status: Optional[str] = Query(None),
    uncategorized_only: bool = Query(False),
    limit: int = Query(25, ge=1, le=100),
) -> dict:
    results = search_vault(
        q,
        domain=domain,
        project_hint=project_hint,
        review_status=review_status,
        extraction_status=extraction_status,
        vector_status=vector_status,
        uncategorized_only=uncategorized_only,
        limit=limit,
    )
    return {"query": q, "count": len(results), "results": results}

@router.get("/api/vault/review-queue", dependencies=_FIREBASE_PROTECTED)
def vault_review_queue_endpoint(
    limit: int = Query(50, ge=1, le=200),
    max_confidence: float = Query(0.85, ge=0, le=1),
    queue: str = Query("low_confidence", description="low_confidence | uncategorized | failed"),
    extraction_status: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
) -> dict:
    rows = vault_review_queue(
        limit=limit,
        max_confidence=max_confidence,
        queue=queue,
        extraction_status=extraction_status,
        review_status=review_status,
    )
    return {"count": len(rows), "queue": queue, "items": rows}

@router.patch("/api/vault/review/{asset_id}", dependencies=_FIREBASE_PROTECTED)
def vault_mark_reviewed(
    asset_id: str,
    review_status: str = Query("reviewed"),
) -> dict:
    return mark_asset_reviewed(asset_id, review_status=review_status)

@router.post("/api/vault/ingest/scan", dependencies=_FIREBASE_PROTECTED)
def vault_ingest_scan(
    resume: bool = Query(False),
    confirm_full_scan: bool = Query(False, description="Required for full DATABASE_ROOT scan (safety)"),
) -> dict:
    job = platform_admin.create_ingestion_job("vault_ingest_scan", config={"resume": resume})
    if not confirm_full_scan:
        raise HTTPException(
            status_code=400,
            detail="Set confirm_full_scan=true to run a full vault scan (read-only, metadata writes only).",
        )
    try:
        result = run_ingest_scan(resume=resume, job_id=str(job["job_id"]))
        platform_admin.finish_ingestion_job(
            job["job_id"],
            items_processed=result.get("counts", {}).get("scanned"),
        )
        return {**result, "job_id": job["job_id"]}
    except Exception as exc:
        platform_admin.finish_ingestion_job(job["job_id"], status="failed", error_summary=str(exc))
        LOGGER.exception("Vault ingest scan failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.post("/api/vault/ingest/project/{project_id}", dependencies=_FIREBASE_PROTECTED)
def vault_ingest_project_endpoint(
    project_id: str,
    resume: bool = Query(False),
) -> dict:
    job = platform_admin.create_ingestion_job(
        "vault_ingest_project",
        config={"project_id": project_id, "resume": resume},
    )
    try:
        result = vault_ingest_project(project_id, resume=resume, job_id=str(job["job_id"]))
        platform_admin.finish_ingestion_job(
            job["job_id"],
            items_processed=result.get("counts", {}).get("scanned"),
        )
        return {**result, "job_id": job["job_id"]}
    except FileNotFoundError as exc:
        platform_admin.finish_ingestion_job(job["job_id"], status="failed", error_summary=str(exc))
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        platform_admin.finish_ingestion_job(job["job_id"], status="failed", error_summary=str(exc))
        LOGGER.exception("Vault project ingest failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.post("/api/digitalize/scan", dependencies=_FIREBASE_PROTECTED)
def digitalize_scan(
    dry_run: bool = Query(False),
    resume: bool = Query(False),
    max_files: Optional[int] = Query(None, ge=1, le=100000),
) -> dict:
    from omeia.api.project_digitalization_engine import run_digitalization

    try:
        return run_digitalization(mode="full", resume=resume, dry_run=dry_run, max_files=max_files)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.post("/api/digitalize/project/{project_name}", dependencies=_FIREBASE_PROTECTED)
def digitalize_project(
    project_name: str,
    resume: bool = Query(False),
    dry_run: bool = Query(False),
    max_files: Optional[int] = Query(None, ge=1, le=100000),
) -> dict:
    from omeia.api.project_digitalization_engine import run_digitalization

    try:
        return run_digitalization(
            mode="project",
            project_name=project_name,
            resume=resume,
            dry_run=dry_run,
            max_files=max_files,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.post("/api/digitalize/retry-failed", dependencies=_FIREBASE_PROTECTED)
def digitalize_retry_failed(
    project_name: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=5000),
) -> dict:
    from omeia.api.vault_ingestion_engine import retry_failed_extractions

    return retry_failed_extractions(project_hint=project_name, limit=limit)

@router.get("/api/digitalize/search", dependencies=_FIREBASE_PROTECTED)
def digitalize_search(
    q: str = Query(..., min_length=1),
    uncategorized_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    from omeia.api.project_digitalization_engine import search_knowledge

    return {"items": search_knowledge(q, uncategorized_only=uncategorized_only, limit=limit)}

@router.get("/api/digitalize/review", dependencies=_FIREBASE_PROTECTED)
def digitalize_review(
    kind: str = Query("uncategorized"),
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    from omeia.api.project_digitalization_engine import list_review_queue

    return {"kind": kind, "items": list_review_queue(kind=kind, limit=limit)}

@router.patch("/api/digitalize/review/{asset_id}", dependencies=_FIREBASE_PROTECTED)
def digitalize_patch_review(
    asset_id: str,
    user_category: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    project_candidate_id: Optional[str] = Query(None),
) -> dict:
    from omeia.api.project_digitalization_engine import patch_asset_review

    return patch_asset_review(
        asset_id,
        user_category=user_category,
        review_status=review_status,
        project_candidate_id=project_candidate_id,
    )

@router.get("/api/digitalize/runs", dependencies=_FIREBASE_PROTECTED)
def digitalize_runs(limit: int = Query(20, ge=1, le=100)) -> dict:
    from omeia.api.project_digitalization_engine import _db_conn
    import psycopg

    with psycopg.connect(_db_conn(), connect_timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT run_id, mode, storage_root, project_name, status, dry_run, started_at, finished_at
                FROM platform.digitalization_runs
                ORDER BY started_at DESC LIMIT %s;
                """,
                (limit,),
            )
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    return {"runs": rows}

@router.post("/api/vault/ingest/retry-failed", dependencies=_FIREBASE_PROTECTED)
def vault_ingest_retry_failed(
    project_hint: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=5000),
) -> dict:
    job = platform_admin.create_ingestion_job(
        "vault_ingest_retry_failed",
        config={"project_hint": project_hint, "limit": limit},
    )
    try:
        result = retry_failed_extractions(
            project_hint=project_hint,
            limit=limit,
            job_id=str(job["job_id"]),
        )
        platform_admin.finish_ingestion_job(
            job["job_id"],
            items_processed=result.get("counts", {}).get("retried"),
        )
        return {**result, "job_id": job["job_id"]}
    except Exception as exc:
        platform_admin.finish_ingestion_job(job["job_id"], status="failed", error_summary=str(exc))
        LOGGER.exception("Vault retry-failed failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.post("/api/vault/rebuild", dependencies=_FIREBASE_PROTECTED)
def vault_rebuild(user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    job = platform_admin.create_ingestion_job("vault_rebuild")
    try:
        result = vault_rebuild_inventory()
        platform_admin.finish_ingestion_job(
            job["job_id"],
            items_processed=result.get("asset_count") or result.get("count"),
        )
        return {**result, "job_id": job["job_id"]}
    except Exception as exc:
        platform_admin.finish_ingestion_job(job["job_id"], status="failed", error_summary=str(exc))
        LOGGER.exception("Vault rebuild failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.post("/api/supabase/sync/documents", dependencies=_FIREBASE_PROTECTED)
def supabase_sync_documents(
    dry_run: bool = Query(False),
    limit: Optional[int] = Query(None, ge=1, le=10_000),
    since: Optional[str] = Query(None, description="ISO timestamp for vault.updated_at filter"),
    _admin: dict = Depends(require_admin),
) -> dict:
    """Sync document metadata + truncated text from local Postgres to hosted Supabase (admin)."""
    del _admin
    job = platform_admin.create_ingestion_job(
        "supabase_document_sync",
        config={"dry_run": dry_run, "limit": limit, "since": since},
    )
    try:
        result = sync_documents_to_supabase(dry_run=dry_run, limit=limit, since=since)
        platform_admin.finish_ingestion_job(
            job["job_id"],
            items_processed=result.get("document_rows_synced") or result.get("would_sync"),
            error_summary=None if result.get("status") in ("ok", "dry_run") else result.get("message"),
        )
        return {**result, "job_id": job["job_id"]}
    except Exception as exc:
        platform_admin.finish_ingestion_job(job["job_id"], status="failed", error_summary=str(exc))
        LOGGER.exception("Supabase document sync failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.post("/api/vault/sync", dependencies=_FIREBASE_PROTECTED)
def vault_sync_postgres(user: dict = Depends(require_platform_user)) -> dict:
    require_role(user, ["editor", "admin"])
    """Phase 3: upsert JSON inventory into platform.raw_asset_vault."""
    job = platform_admin.create_ingestion_job("vault_sync")
    try:
        result = sync_inventory_to_postgres()
        platform_admin.finish_ingestion_job(
            job["job_id"],
            items_processed=result.get("upserted") or result.get("postgres_rows"),
        )
        return {**result, "job_id": job["job_id"]}
    except Exception as exc:
        platform_admin.finish_ingestion_job(job["job_id"], status="failed", error_summary=str(exc))
        LOGGER.exception("Vault sync failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get("/api/vault/dedupe-report", dependencies=_FIREBASE_PROTECTED)
def vault_dedupe_report(limit: int = Query(30, ge=1, le=100)) -> dict:
    return deduplication_report(limit=limit)

@router.get("/api/vault/manifest", dependencies=_FIREBASE_PROTECTED)
def vault_manifest(
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    return vault_manifest_page(offset=offset, limit=limit)

@router.get("/api/supabase/sync/status")
def supabase_sync_status_endpoint() -> dict:
    """Last Supabase document sync report (no secrets)."""
    status = supabase_sync_status()
    last_report = read_last_sync_report()
    return {"status": status, "last_report": last_report}
```

### `omeia/api/lab_knowledge_store.py`

```python
"""Canonical lab knowledge indexing: Postgres rag.* + Qdrant doc_chunks.

Hard rule:
- corpus=lab_operations → assimilated into app database (this module). No file streaming UI.
- corpus=project_workspace → project folder streaming (project_processor / project-files API).
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg
from qdrant_client import QdrantClient
from qdrant_client.http import models

from omeia.api import document_extraction as de
from omeia.api.database_sections import DATABASE_SECTIONS, section_root
from omeia.api.database_processor import (
    _iter_chunks_from_disk,
    get_section_record,
    load_processed_section,
)
from omeia.api.llm_client import LLMClient
from omeia.api.paths import DATABASE_ROOT

LOGGER = logging.getLogger(__name__)

LAB_CORPUS = "lab_operations"
SOURCE_TYPE_LAB = "lab_policy_document"
COLLECTION_DOC_CHUNKS = "doc_chunks"
EMBEDDING_DIM = 384
SCHEMA_VERSION = 1


def _db_conn():
    from omeia.api.supabase_config import postgres_conn

    return postgres_conn()


def _stable_document_code(section_id: str, relative_path: str) -> str:
    norm = relative_path.strip().lstrip("/").replace("\\", "/")
    digest = hashlib.sha256(f"{section_id}:{norm}".encode("utf-8")).hexdigest()[:16]
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", norm)[-80:]
    return f"lab::{section_id}::{digest}::{safe}"


def _chunk_uid(document_code: str, chunk_index: int) -> str:
    return f"{document_code}::chunk_{chunk_index:04d}"


def _qdrant_point_id(chunk_uid: str) -> str:
    return hashlib.md5(chunk_uid.encode("utf-8")).hexdigest()


def _tokenize(query: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9\u00c0-\uffff]{3,}", (query or "").lower()) if t]


def _canonical_metadata(
    *,
    section_id: str,
    section_label: str,
    relative_path: str,
    absolute_path: str,
    document_kind: str,
    sha256: str | None,
    extractor: str | None,
    file_extension: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "corpus": LAB_CORPUS,
        "section_id": section_id,
        "section_label": section_label,
        "relative_path": relative_path,
        "absolute_disk_path": absolute_path,
        "document_kind": document_kind,
        "sha256": sha256,
        "extractor": extractor,
        "file_extension": file_extension,
        "where_to_find": f"{section_label} → {relative_path}",
        "database_root": str(DATABASE_ROOT),
    }


def _canonical_qdrant_payload(
    *,
    document_id: str,
    chunk_id: str,
    chunk_uid: str,
    document_code: str,
    title: str,
    section_id: str,
    section_label: str,
    relative_path: str,
    chunk_index: int,
    text_preview: str,
    document_kind: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "corpus": LAB_CORPUS,
        "scope": "lab",
        "source_type": SOURCE_TYPE_LAB,
        "document_id": document_id,
        "source_file_id": relative_path,
        "chunk_id": chunk_uid,
        "chunk_index": chunk_index,
        "document_code": document_code,
        "title": title,
        "text_preview": text_preview[:2000],
        "text": text_preview[:8000],
        "section_id": section_id,
        "section_label": section_label,
        "relative_path": relative_path,
        "where_to_find": f"{section_label} → {relative_path}",
        "document_kind": document_kind,
        "project_code": None,
        "allowed_project_codes": [],
        "modality": ["lab_operations"],
        "sensitivity_level": "internal",
        "contains_patient_level_data": False,
        "contains_direct_identifier": False,
        "embedding_model": "llm_client_hashed_embed",
        "embedding_dimension": EMBEDDING_DIM,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _stored_checksum(cur, document_code: str) -> str | None:
    cur.execute(
        """
        SELECT metadata->>'sha256'
        FROM rag.document_source
        WHERE document_code = %s AND status = 'active';
        """,
        (document_code,),
    )
    row = cur.fetchone()
    if not row or not row[0]:
        return None
    return str(row[0])


def _upsert_document_source(
    cur,
    *,
    document_code: str,
    title: str,
    section_id: str,
    meta: dict[str, Any],
) -> uuid.UUID:
    cur.execute(
        """
        INSERT INTO rag.document_source (
            document_code, title, source_type, project_id,
            sensitivity_level, status, metadata
        ) VALUES (%s, %s, %s, NULL, 'internal', 'active', %s)
        ON CONFLICT (document_code) DO UPDATE SET
            title = EXCLUDED.title,
            source_type = EXCLUDED.source_type,
            metadata = EXCLUDED.metadata,
            status = 'active'
        RETURNING document_id;
        """,
        (document_code, title, SOURCE_TYPE_LAB, psycopg.types.json.Jsonb(meta)),
    )
    row = cur.fetchone()
    return row[0]


def _replace_document_chunks(cur, document_id: uuid.UUID, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cur.execute("DELETE FROM rag.document_chunk WHERE document_id = %s;", (document_id,))
    stored = []
    for idx, chunk in enumerate(chunks):
        text = (chunk.get("text") or "").strip()
        if not text:
            continue
        chunk_uid = chunk.get("chunk_id") or _chunk_uid(str(document_id), idx)
        section_path = chunk.get("source_file") or chunk.get("section_path") or ""
        cur.execute(
            """
            INSERT INTO rag.document_chunk (
                document_id, chunk_index, chunk_uid, section_path,
                chunk_text, token_count, sensitivity_level, metadata
            ) VALUES (%s, %s, %s, %s, %s, %s, 'internal', %s)
            RETURNING chunk_id;
            """,
            (
                document_id,
                idx,
                chunk_uid,
                section_path,
                text,
                chunk.get("word_count") or len(text.split()),
                psycopg.types.json.Jsonb({
                    "start_char": chunk.get("start_char"),
                    "end_char": chunk.get("end_char"),
                    "char_count": chunk.get("char_count"),
                }),
            ),
        )
        chunk_row_id = cur.fetchone()[0]
        stored.append({
            **chunk,
            "chunk_uid": chunk_uid,
            "db_chunk_id": str(chunk_row_id),
            "chunk_index": idx,
        })
    return stored


def ingest_section_to_database(
    section_id: str,
    *,
    qdrant: QdrantClient | None = None,
    llm: LLMClient | None = None,
    refresh_extract: bool = False,
) -> dict[str, Any]:
    """Extract (if needed), then assimilate section into rag.* and Qdrant."""
    if section_id not in DATABASE_SECTIONS:
        raise ValueError(f"Unknown section: {section_id}")

    meta_section = DATABASE_SECTIONS[section_id]
    root = section_root(section_id)

    twin = get_section_record(section_id, refresh=refresh_extract)
    if not twin:
        raise FileNotFoundError(f"No processed twin for {section_id}")

    chunks_by_path: dict[str, list[dict[str, Any]]] = {}
    for chunk in _iter_chunks_from_disk(section_id):
        path = (chunk.get("source_file") or "").replace("\\", "/")
        if path:
            chunks_by_path.setdefault(path, []).append(chunk)

    llm = llm or LLMClient()
    qdrant = qdrant or QdrantClient(url=_qdrant_url())
    _ensure_qdrant_collection(qdrant)

    stats = {
        "section_id": section_id,
        "documents_upserted": 0,
        "chunks_indexed": 0,
        "vectors_upserted": 0,
        "skipped_empty": 0,
        "skipped_unchanged": 0,
        "errors": [],
    }

    doc_index = {d["path"]: d for d in twin.get("document_index") or [] if d.get("path")}

    with psycopg.connect(_db_conn(), connect_timeout=10) as conn:
        with conn.cursor() as cur:
            job_id = _start_embedding_job(cur, section_id)

            for rel_path, doc_meta in sorted(doc_index.items()):
                file_chunks = chunks_by_path.get(rel_path, [])
                if not file_chunks:
                    excerpt = (doc_meta.get("excerpt") or "").strip()
                    if not excerpt:
                        stats["skipped_empty"] += 1
                        continue
                    file_chunks = [{
                        "chunk_id": _chunk_uid(rel_path, 0),
                        "source_file": rel_path,
                        "chunk_index": 0,
                        "text": excerpt,
                        "word_count": doc_meta.get("word_count"),
                    }]

                document_code = _stable_document_code(section_id, rel_path)
                new_checksum = (doc_meta.get("sha256") or "").strip() or None
                if new_checksum:
                    prior = _stored_checksum(cur, document_code)
                    if prior and prior == new_checksum:
                        stats["skipped_unchanged"] += 1
                        continue

                title = doc_meta.get("title") or Path(rel_path).name
                abs_path = str((root / rel_path).resolve())
                metadata = _canonical_metadata(
                    section_id=section_id,
                    section_label=meta_section["label"],
                    relative_path=rel_path,
                    absolute_path=abs_path,
                    document_kind=doc_meta.get("document_kind") or "document",
                    sha256=doc_meta.get("sha256"),
                    extractor=doc_meta.get("extractor"),
                    file_extension=doc_meta.get("extension") or Path(rel_path).suffix,
                )

                try:
                    document_id = _upsert_document_source(
                        cur,
                        document_code=document_code,
                        title=title,
                        section_id=section_id,
                        meta=metadata,
                    )
                    stored_chunks = _replace_document_chunks(cur, document_id, file_chunks)
                    stats["documents_upserted"] += 1
                    stats["chunks_indexed"] += len(stored_chunks)

                    points = []
                    for sc in stored_chunks:
                        text = sc.get("text") or ""
                        chunk_uid = sc["chunk_uid"]
                        payload = _canonical_qdrant_payload(
                            document_id=str(document_id),
                            chunk_id=sc.get("db_chunk_id", ""),
                            chunk_uid=chunk_uid,
                            document_code=document_code,
                            title=title,
                            section_id=section_id,
                            section_label=meta_section["label"],
                            relative_path=rel_path,
                            chunk_index=sc["chunk_index"],
                            text_preview=text,
                            document_kind=metadata["document_kind"],
                        )
                        vector = llm.embed(text[:4000], dim=EMBEDDING_DIM)
                        qid = _qdrant_point_id(chunk_uid)
                        points.append(models.PointStruct(
                            id=qid,
                            vector={"text": vector},
                            payload=payload,
                        ))
                        cur.execute(
                            """
                            INSERT INTO rag.vector_point_registry (
                                embedding_job_id, collection_name, qdrant_point_id,
                                source_type, source_uuid, chunk_id, project_id,
                                embedding_model, embedding_dimension, payload, status
                            ) VALUES (%s, %s, %s, %s, %s, %s, NULL, %s, %s, %s, 'active')
                            ON CONFLICT (collection_name, qdrant_point_id) DO UPDATE SET
                                payload = EXCLUDED.payload,
                                chunk_id = EXCLUDED.chunk_id,
                                status = 'active';
                            """,
                            (
                                job_id,
                                COLLECTION_DOC_CHUNKS,
                                qid,
                                SOURCE_TYPE_LAB,
                                document_id,
                                uuid.UUID(sc["db_chunk_id"]),
                                "llm_client_hashed_embed",
                                EMBEDDING_DIM,
                                psycopg.types.json.Jsonb(payload),
                            ),
                        )

                    if points:
                        qdrant.upsert(collection_name=COLLECTION_DOC_CHUNKS, points=points)
                        stats["vectors_upserted"] += len(points)

                except Exception as exc:
                    stats["errors"].append({"path": rel_path, "error": str(exc)[:300]})
                    LOGGER.exception("Failed to index %s", rel_path)

            _finish_embedding_job(cur, job_id, stats)
            conn.commit()

    return stats


def ingest_all_lab_sections(**kwargs) -> dict[str, Any]:
    results = []
    errors = []
    for section_id in DATABASE_SECTIONS:
        try:
            stats = ingest_section_to_database(section_id, **kwargs)
            results.append(stats)
        except Exception as exc:
            errors.append({"section_id": section_id, "error": str(exc)})
    return {
        "corpus": LAB_CORPUS,
        "sections_processed": len(results),
        "results": results,
        "errors": errors,
        "totals": {
            "documents": sum(r.get("documents_upserted", 0) for r in results),
            "chunks": sum(r.get("chunks_indexed", 0) for r in results),
            "vectors": sum(r.get("vectors_upserted", 0) for r in results),
        },
    }


def search_lab_knowledge(
    query: str,
    *,
    section_id: str | None = None,
    limit: int = 15,
    qdrant: QdrantClient | None = None,
    llm: LLMClient | None = None,
) -> list[dict[str, Any]]:
    """Search canonical lab index. Returns citation + excerpt + where_to_find."""
    query = (query or "").strip()
    if len(query) < 2:
        return []

    limit = max(1, min(int(limit or 15), 50))
    hits: list[dict[str, Any]] = []

    llm = llm or LLMClient()
    try:
        qdrant = qdrant or QdrantClient(url=_qdrant_url())
        vector = llm.embed(query, dim=EMBEDDING_DIM)
        must = [models.FieldCondition(key="corpus", match=models.MatchValue(value=LAB_CORPUS))]
        if section_id:
            must.append(models.FieldCondition(key="section_id", match=models.MatchValue(value=section_id)))
        response = qdrant.query_points(
            collection_name=COLLECTION_DOC_CHUNKS,
            query=vector,
            using="text",
            query_filter=models.Filter(must=must),
            limit=limit * 2,
        )
        for rank, point in enumerate(getattr(response, "points", []) or [], start=1):
            p = point.payload or {}
            if p.get("corpus") != LAB_CORPUS:
                continue
            hits.append(_format_search_hit(rank, float(point.score or 0), p, point.id))
            if len(hits) >= limit:
                return hits
    except Exception as exc:
        LOGGER.warning("Qdrant lab search failed, using Postgres: %s", exc)

    if len(hits) < limit:
        hits.extend(_search_postgres(query, section_id=section_id, limit=limit - len(hits), seen={h["chunk_uid"] for h in hits}))

    return hits[:limit]


def _search_postgres(
    query: str,
    *,
    section_id: str | None,
    limit: int,
    seen: set[str],
) -> list[dict[str, Any]]:
    tokens = _tokenize(query)
    if not tokens:
        return []

    score_params = [f"%{tok}%" for tok in tokens]
    where_score = " + ".join(
        ["CASE WHEN lower(dc.chunk_text) LIKE %s THEN 1 ELSE 0 END" for _ in tokens]
    )
    section_clause = "AND ds.metadata->>'section_id' = %s" if section_id else ""
    bind: list[Any] = [LAB_CORPUS]
    if section_id:
        bind.append(section_id)
    bind.extend(score_params)
    bind.extend(score_params)
    bind.append(limit)

    sql = f"""
        SELECT
            dc.chunk_uid, dc.chunk_text, dc.chunk_index, dc.section_path,
            ds.document_id, ds.document_code, ds.title, ds.metadata,
            ({where_score}) AS relevance
        FROM rag.document_chunk dc
        JOIN rag.document_source ds ON ds.document_id = dc.document_id
        WHERE ds.metadata->>'corpus' = %s
        {section_clause}
          AND ({where_score}) > 0
        ORDER BY relevance DESC
        LIMIT %s;
    """

    rows = []
    try:
        with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, bind)
                rows = cur.fetchall()
    except Exception as exc:
        LOGGER.warning("Postgres lab search failed: %s", exc)
        return []

    out = []
    for i, row in enumerate(rows, start=1):
        chunk_uid, text, chunk_index, section_path, doc_id, doc_code, title, metadata, relevance = row
        if chunk_uid in seen:
            continue
        meta = metadata if isinstance(metadata, dict) else {}
        payload = {
            "chunk_id": chunk_uid,
            "chunk_index": chunk_index,
            "relative_path": section_path or meta.get("relative_path"),
            "section_id": meta.get("section_id"),
            "section_label": meta.get("section_label"),
            "title": title,
            "document_code": doc_code,
            "where_to_find": meta.get("where_to_find"),
            "text_preview": text[:2000],
            "text": text[:8000],
        }
        out.append(_format_search_hit(i, float(relevance), payload, chunk_uid))
    return out


def _format_search_hit(rank: int, score: float, payload: dict[str, Any], point_id: Any) -> dict[str, Any]:
    section_label = payload.get("section_label") or payload.get("section_id") or "Lab"
    rel = payload.get("relative_path") or payload.get("source_file_id") or ""
    title = payload.get("title") or rel.split("/")[-1] or "Document"
    where = payload.get("where_to_find") or f"{section_label} → {rel}"
    text = payload.get("text_preview") or payload.get("text") or ""
    return {
        "rank": rank,
        "score": round(score, 4),
        "chunk_uid": str(payload.get("chunk_id") or point_id),
        "document_code": payload.get("document_code"),
        "document_id": payload.get("document_id"),
        "section_id": payload.get("section_id"),
        "section_label": section_label,
        "title": title,
        "relative_path": rel,
        "where_to_find": where,
        "citation": where,
        "excerpt": text[:1200],
        "full_text": text[:8000],
        "source_type": SOURCE_TYPE_LAB,
        "corpus": LAB_CORPUS,
    }


def get_lab_index_stats() -> dict[str, Any]:
    try:
        with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(DISTINCT ds.document_id), COUNT(dc.chunk_id)
                    FROM rag.document_source ds
                    LEFT JOIN rag.document_chunk dc ON dc.document_id = ds.document_id
                    WHERE ds.metadata->>'corpus' = %s;
                    """,
                    (LAB_CORPUS,),
                )
                docs, chunks = cur.fetchone()
                cur.execute(
                    """
                    SELECT ds.metadata->>'section_id' AS sid, COUNT(dc.chunk_id) AS n
                    FROM rag.document_source ds
                    JOIN rag.document_chunk dc ON dc.document_id = ds.document_id
                    WHERE ds.metadata->>'corpus' = %s
                    GROUP BY sid ORDER BY sid;
                    """,
                    (LAB_CORPUS,),
                )
                by_section = [{"section_id": r[0], "chunks": r[1]} for r in cur.fetchall()]
                return {
                    "corpus": LAB_CORPUS,
                    "documents": docs or 0,
                    "chunks": chunks or 0,
                    "by_section": by_section,
                }
    except Exception as exc:
        return {"corpus": LAB_CORPUS, "error": str(exc), "documents": 0, "chunks": 0}


def _qdrant_url() -> str:
    import os
    return os.getenv("QDRANT_URL", "http://localhost:6333")


def _ensure_qdrant_collection(client: QdrantClient) -> None:
    try:
        client.get_collection(COLLECTION_DOC_CHUNKS)
    except Exception:
        client.create_collection(
            collection_name=COLLECTION_DOC_CHUNKS,
            vectors_config={
                "text": models.VectorParams(size=EMBEDDING_DIM, distance=models.Distance.COSINE),
            },
        )


def _start_embedding_job(cur, section_id: str) -> uuid.UUID:
    code = f"lab_ingest_{section_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    cur.execute(
        """
        INSERT INTO rag.embedding_job (
            job_code, embedding_model, embedding_dimension, distance_metric,
            collection_name, started_at, status, config
        ) VALUES (%s, %s, %s, 'cosine', %s, now(), 'running', %s)
        RETURNING embedding_job_id;
        """,
        (
            code,
            "llm_client_hashed_embed",
            EMBEDDING_DIM,
            COLLECTION_DOC_CHUNKS,
            psycopg.types.json.Jsonb({"section_id": section_id, "corpus": LAB_CORPUS}),
        ),
    )
    return cur.fetchone()[0]


def _finish_embedding_job(cur, job_id: uuid.UUID, stats: dict[str, Any]) -> None:
    cur.execute(
        """
        UPDATE rag.embedding_job
        SET finished_at = now(), status = 'success', config = config || %s::jsonb
        WHERE embedding_job_id = %s;
        """,
        (psycopg.types.json.Jsonb({"stats": stats}), job_id),
    )


def _cli() -> int:
    import argparse
    import json as _json

    parser = argparse.ArgumentParser(description="Ingest lab folders into canonical rag.* database.")
    parser.add_argument("--section")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--refresh-extract", action="store_true", help="Re-scan files on disk before ingest")
    args = parser.parse_args()
    if args.all:
        print(_json.dumps(ingest_all_lab_sections(refresh_extract=args.refresh_extract), indent=2, default=str))
        return 0
    if args.section:
        print(_json.dumps(
            ingest_section_to_database(args.section, refresh_extract=args.refresh_extract),
            indent=2,
            default=str,
        ))
        return 0
    parser.error("Use --all or --section")
    return 1


if __name__ == "__main__":
    raise SystemExit(_cli())

```

### `omeia/api/raw_vault_store.py`

```python
"""Raw knowledge vault — JSON inventory + optional Postgres registry (Phases 2–3)."""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg

from omeia.api.page_registry import resolve_page_ids
from omeia.api.paths import BLUEPRINT_ROOT, DATABASE_ROOT, SCRIPTS_DIR

LOGGER = logging.getLogger(__name__)

INVENTORY_DIR = BLUEPRINT_ROOT / "omeia" / "data"
INVENTORY_JSON = INVENTORY_DIR / "raw_asset_inventory.json"
INVENTORY_SUMMARY = INVENTORY_DIR / "raw_asset_inventory_summary.json"
VAULT_SQL = BLUEPRINT_ROOT / "sql" / "111_raw_asset_vault.sql"

_PUBLIC_FIELDS = (
    "asset_id",
    "storage_provider",
    "logical_path",
    "filename",
    "extension",
    "size_bytes",
    "checksum_sha256",
    "asset_type",
    "domain",
    "project_hint",
    "section_hint",
    "sensitivity_level",
    "assignment_confidence",
    "sensitivity_confidence",
    "review_status",
    "vector_status",
    "graph_status",
    "modified_at",
    "indexed_at",
    "extraction_status",
    "mime_type",
    "page_domain_id",
    "page_section_id",
    "page_domain_label",
    "page_section_label",
    "metadata_json",
)


def _db_conn() -> str:
    from omeia.api.supabase_config import postgres_conn

    return postgres_conn()


def _public_row(row: dict[str, Any]) -> dict[str, Any]:
    out = {k: row[k] for k in _PUBLIC_FIELDS if k in row}
    conf = float(row.get("assignment_confidence") or 0)
    if conf < 0.6:
        out["review_status"] = row.get("review_status") or "raw"
    elif conf < 0.86:
        out["review_status"] = row.get("review_status") or "tentative"
    return out


def _row_from_pg(record: tuple, columns: list[str]) -> dict[str, Any]:
    row = dict(zip(columns, record))
    for key in ("assignment_confidence", "sensitivity_confidence"):
        if key in row and row[key] is not None:
            row[key] = float(row[key])
    if row.get("size_bytes") is not None:
        row["size_bytes"] = int(row["size_bytes"])
    return _public_row(row)


def ensure_vault_schema() -> None:
    from omeia.api.sql_migrations import apply_pending_migrations

    applied = apply_pending_migrations(conn_str=_db_conn())
    if applied:
        LOGGER.info("Vault schema: applied migrations %s", ", ".join(applied))


def load_summary() -> dict[str, Any]:
    if not INVENTORY_SUMMARY.exists():
        return {"asset_count": 0, "generated_at": None, "needs_review_count": 0}
    try:
        summary = json.loads(INVENTORY_SUMMARY.read_text(encoding="utf-8"))
    except Exception as exc:
        LOGGER.warning("Failed to read vault summary: %s", exc)
        return {"asset_count": 0, "error": str(exc)}
    try:
        with psycopg.connect(_db_conn(), connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM platform.raw_asset_vault;")
                summary["postgres_asset_count"] = cur.fetchone()[0]
    except Exception:
        summary["postgres_asset_count"] = None
    public = {k: v for k, v in summary.items() if k != "database_root"}
    return public


def load_inventory_rows() -> list[dict[str, Any]]:
    if not INVENTORY_JSON.exists():
        return []
    try:
        data = json.loads(INVENTORY_JSON.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception as exc:
        LOGGER.warning("Failed to read vault inventory: %s", exc)
        return []


def _search_vault_json(
    query: str,
    *,
    domain: str | None,
    project_hint: str | None,
    review_status: str | None,
    vector_status: str | None,
    extraction_status: str | None,
    uncategorized_only: bool,
    limit: int,
) -> list[dict[str, Any]]:
    q = (query or "").strip().lower()
    tokens = [t for t in q.split() if len(t) >= 2] if q else []
    hits: list[tuple[float, dict[str, Any]]] = []

    for row in load_inventory_rows():
        if domain and row.get("domain") != domain:
            continue
        if project_hint and (row.get("project_hint") or "").lower() != project_hint.lower():
            continue
        if review_status and row.get("review_status") != review_status:
            continue
        if vector_status and row.get("vector_status") != vector_status:
            continue
        if extraction_status and row.get("extraction_status") != extraction_status:
            continue
        if uncategorized_only and row.get("page_domain_id"):
            continue
        if uncategorized_only and row.get("review_status") not in (None, "uncategorized", "raw"):
            if row.get("page_domain_id"):
                continue
        blob = " ".join(
            str(row.get(k, ""))
            for k in ("logical_path", "filename", "asset_type", "domain", "section_hint", "project_hint")
        ).lower()
        if tokens:
            score = sum(2.0 if tok in blob else 0.0 for tok in tokens)
            if score <= 0:
                continue
        else:
            score = 0.0
        hits.append((score, _public_row(row)))

    hits.sort(key=lambda x: -x[0])
    return [h[1] for h in hits[:limit]]


def _search_vault_postgres(
    query: str,
    *,
    domain: str | None,
    project_hint: str | None,
    review_status: str | None,
    vector_status: str | None,
    extraction_status: str | None,
    uncategorized_only: bool,
    limit: int,
) -> list[dict[str, Any]]:
    tokens = [t for t in (query or "").lower().split() if len(t) >= 2]
    clauses = ["1=1"]
    params: list[Any] = []
    if domain:
        clauses.append("v.domain = %s")
        params.append(domain)
    if project_hint:
        clauses.append("lower(v.project_hint) = lower(%s)")
        params.append(project_hint)
    if review_status:
        clauses.append("v.review_status = %s")
        params.append(review_status)
    if vector_status:
        clauses.append("v.vector_status = %s")
        params.append(vector_status)
    if extraction_status:
        clauses.append("v.extraction_status = %s")
        params.append(extraction_status)
    if uncategorized_only:
        clauses.append("v.page_domain_id IS NULL")
    if tokens:
        ors = [
            "(lower(v.logical_path || ' ' || coalesce(v.filename, '')) LIKE %s)"
            for _ in tokens
        ]
        clauses.append(f"({' OR '.join(ors)})")
        params.extend(f"%{tok}%" for tok in tokens)

    sql = f"""
        SELECT
            v.asset_id, v.storage_provider, v.logical_path, v.filename, v.extension,
            v.size_bytes, v.checksum_sha256, v.asset_type, v.domain, v.project_hint, v.section_hint,
            v.sensitivity_level, v.assignment_confidence, v.sensitivity_confidence,
            v.review_status, v.vector_status, v.graph_status, v.extraction_status,
            v.modified_at, v.indexed_at, v.mime_type, v.page_domain_id, v.page_section_id,
            pd.label AS page_domain_label, ps.label AS page_section_label,
            v.metadata_json
        FROM platform.raw_asset_vault v
        LEFT JOIN platform.page_domain pd ON pd.page_domain_id = v.page_domain_id
        LEFT JOIN platform.page_section ps ON ps.page_section_id = v.page_section_id
        WHERE {' AND '.join(clauses)}
        ORDER BY assignment_confidence DESC, logical_path
        LIMIT %s;
    """
    params.append(limit)
    columns = [
        "asset_id", "storage_provider", "logical_path", "filename", "extension",
        "size_bytes", "checksum_sha256", "asset_type", "domain", "project_hint", "section_hint",
        "sensitivity_level", "assignment_confidence", "sensitivity_confidence",
        "review_status", "vector_status", "graph_status", "extraction_status",
        "modified_at", "indexed_at", "mime_type", "page_domain_id", "page_section_id",
        "page_domain_label", "page_section_label", "metadata_json",
    ]
    with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return [_row_from_pg(r, columns) for r in cur.fetchall()]


def search_vault(
    query: str,
    *,
    domain: str | None = None,
    project_hint: str | None = None,
    review_status: str | None = None,
    vector_status: str | None = None,
    extraction_status: str | None = None,
    uncategorized_only: bool = False,
    limit: int = 25,
) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 100))
    try:
        hits = _search_vault_postgres(
            query,
            domain=domain,
            project_hint=project_hint,
            review_status=review_status,
            vector_status=vector_status,
            extraction_status=extraction_status,
            uncategorized_only=uncategorized_only,
            limit=limit,
        )
        if hits:
            return _sanitize_metadata_in_rows(hits)
    except Exception as exc:
        LOGGER.debug("Postgres vault search unavailable: %s", exc)
    return _sanitize_metadata_in_rows(
        _search_vault_json(
            query,
            domain=domain,
            project_hint=project_hint,
            review_status=review_status,
            vector_status=vector_status,
            extraction_status=extraction_status,
            uncategorized_only=uncategorized_only,
            limit=limit,
        )
    )


def _sanitize_metadata_in_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Expose safe metadata subset; never leak original_path from metadata."""
    out: list[dict[str, Any]] = []
    for row in rows:
        r = dict(row)
        md = r.pop("metadata_json", None) or {}
        if isinstance(md, str):
            try:
                md = json.loads(md)
            except Exception:
                md = {}
        if isinstance(md, dict):
            r["metadata_preview"] = {
                k: md[k]
                for k in ("excerpt", "vault_policy", "error", "sheet_count", "line_count")
                if k in md
            }
        out.append(_public_row(r))
    return out


def review_queue(
    *,
    limit: int = 50,
    max_confidence: float = 0.85,
    queue: str = "low_confidence",
    extraction_status: str | None = None,
    review_status: str | None = None,
) -> list[dict[str, Any]]:
    """Review queues: low_confidence | uncategorized | failed."""
    limit = max(1, min(limit, 200))
    queue = (queue or "low_confidence").strip().lower()
    try:
        with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
            with conn.cursor() as cur:
                clauses: list[str] = []
                params: list[Any] = []
                if queue == "uncategorized":
                    clauses.append("(page_domain_id IS NULL OR review_status = 'uncategorized')")
                elif queue == "failed":
                    clauses.append("extraction_status = 'failed'")
                else:
                    clauses.append("assignment_confidence < %s")
                    params.append(max_confidence)
                if extraction_status:
                    clauses.append("extraction_status = %s")
                    params.append(extraction_status)
                if review_status:
                    clauses.append("review_status = %s")
                    params.append(review_status)
                params.append(limit)
                cur.execute(
                    f"""
                    SELECT
                        asset_id, storage_provider, logical_path, filename, extension,
                        size_bytes, checksum_sha256, asset_type, domain, project_hint, section_hint,
                        sensitivity_level, assignment_confidence, sensitivity_confidence,
                        review_status, vector_status, graph_status, extraction_status,
                        modified_at, indexed_at, mime_type, page_domain_id, page_section_id,
                        metadata_json
                    FROM platform.raw_asset_vault
                    WHERE {' AND '.join(clauses)}
                    ORDER BY updated_at DESC NULLS LAST, logical_path
                    LIMIT %s;
                    """,
                    params,
                )
                cols = [d[0] for d in cur.description]
                return _sanitize_metadata_in_rows([_row_from_pg(r, cols) for r in cur.fetchall()])
    except Exception as exc:
        LOGGER.debug("Postgres review queue unavailable: %s", exc)

    rows = load_inventory_rows()
    filtered: list[dict[str, Any]] = []
    for r in rows:
        if queue == "uncategorized" and r.get("page_domain_id"):
            continue
        if queue == "failed" and r.get("extraction_status") != "failed":
            continue
        if queue == "low_confidence" and float(r.get("assignment_confidence") or 0) >= max_confidence:
            continue
        if extraction_status and r.get("extraction_status") != extraction_status:
            continue
        if review_status and r.get("review_status") != review_status:
            continue
        filtered.append(_public_row(r))
    filtered.sort(key=lambda r: float(r.get("assignment_confidence") or 0))
    return filtered[:limit]


def mark_asset_reviewed(asset_id: str, *, review_status: str = "reviewed") -> dict[str, Any]:
    ensure_vault_schema()
    with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE platform.raw_asset_vault
                SET review_status = %s, updated_at = now()
                WHERE asset_id = %s
                RETURNING asset_id, review_status;
                """,
                (review_status, asset_id),
            )
            row = cur.fetchone()
            if not row:
                return {"status": "not_found", "asset_id": asset_id}
            cur.execute(
                """
                INSERT INTO platform.vault_audit_event (asset_id, event_type, actor, details)
                VALUES (%s, 'review_marked', 'api', %s::jsonb);
                """,
                (asset_id, json.dumps({"review_status": review_status})),
            )
        conn.commit()
    return {"status": "ok", "asset_id": asset_id, "review_status": review_status}


def list_failed_assets(*, project_hint: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    rows = review_queue(limit=limit, queue="failed")
    if project_hint:
        rows = [r for r in rows if (r.get("project_hint") or "").lower() == project_hint.lower()]
    return rows


def deduplication_report(*, limit: int = 30) -> dict[str, Any]:
    """Duplicate groups by checksum (logical paths only in response)."""
    by_hash: dict[str, list[str]] = defaultdict(list)
    for row in load_inventory_rows():
        digest = (row.get("checksum_sha256") or "").strip()
        if not digest:
            continue
        by_hash[digest].append(row.get("logical_path") or row.get("filename") or "?")

    groups = [
        {"checksum_sha256": h, "count": len(paths), "logical_paths": sorted(paths)[:20]}
        for h, paths in by_hash.items()
        if len(paths) > 1
    ]
    groups.sort(key=lambda g: -g["count"])
    return {
        "duplicate_checksum_groups": len(groups),
        "groups": groups[:limit],
    }


def sync_inventory_to_postgres(*, batch_size: int = 400) -> dict[str, Any]:
    rows = load_inventory_rows()
    if not rows:
        raise FileNotFoundError("Run vault rebuild first — raw_asset_inventory.json missing")

    ensure_vault_schema()
    upserted = 0
    review_created = 0
    with psycopg.connect(_db_conn(), connect_timeout=30) as conn:
        with conn.cursor() as cur:
            for i in range(0, len(rows), batch_size):
                batch = rows[i : i + batch_size]
                payloads = []
                for r in batch:
                    page_domain_id, page_section_id = resolve_page_ids(
                        domain=r.get("domain"),
                        section_hint=r.get("section_hint"),
                        logical_path=r.get("logical_path"),
                    )
                    payloads.append({
                        "asset_id": r["asset_id"],
                        "storage_provider": r.get("storage_provider", "local_database_mirror"),
                        "logical_path": r["logical_path"],
                        "filename": r["filename"],
                        "extension": r.get("extension", ""),
                        "size_bytes": r.get("size_bytes", 0),
                        "checksum_sha256": r.get("checksum_sha256") or "",
                        "mime_type": r.get("mime_type") or "application/octet-stream",
                        "asset_type": r.get("asset_type", "other"),
                        "domain": r.get("domain"),
                        "project_hint": r.get("project_hint") or "",
                        "section_hint": r.get("section_hint") or "",
                        "page_domain_id": page_domain_id,
                        "page_section_id": page_section_id,
                        "sensitivity_level": r.get("sensitivity_level", "unknown"),
                        "assignment_confidence": r.get("assignment_confidence", 0),
                        "sensitivity_confidence": r.get("sensitivity_confidence", 0),
                        "review_status": r.get("review_status", "raw"),
                        "vector_status": r.get("vector_status", "not_evaluated"),
                        "graph_status": r.get("graph_status", "not_asserted"),
                        "extraction_status": r.get("extraction_status", "not_started"),
                        "original_path": r.get("original_path"),
                        "modified_at": r.get("modified_at"),
                        "indexed_at": r.get("indexed_at"),
                        "provenance": json.dumps({"source": "build_raw_asset_inventory"}),
                    })
                cur.executemany(
                    """
                    INSERT INTO platform.raw_asset_vault (
                        asset_id, storage_provider, logical_path, filename, extension,
                        size_bytes, checksum_sha256, mime_type, asset_type, domain, project_hint, section_hint,
                        page_domain_id, page_section_id,
                        sensitivity_level, assignment_confidence, sensitivity_confidence,
                        review_status, vector_status, graph_status, extraction_status,
                        original_path, modified_at, indexed_at, provenance, updated_at
                    ) VALUES (
                        %(asset_id)s, %(storage_provider)s, %(logical_path)s, %(filename)s, %(extension)s,
                        %(size_bytes)s, %(checksum_sha256)s, %(mime_type)s, %(asset_type)s, %(domain)s,
                        %(project_hint)s, %(section_hint)s, %(page_domain_id)s, %(page_section_id)s,
                        %(sensitivity_level)s, %(assignment_confidence)s, %(sensitivity_confidence)s,
                        %(review_status)s, %(vector_status)s, %(graph_status)s, %(extraction_status)s,
                        %(original_path)s, %(modified_at)s, %(indexed_at)s,
                        %(provenance)s::jsonb, now()
                    )
                    ON CONFLICT (asset_id) DO UPDATE SET
                        storage_provider = EXCLUDED.storage_provider,
                        logical_path = EXCLUDED.logical_path,
                        filename = EXCLUDED.filename,
                        extension = EXCLUDED.extension,
                        size_bytes = EXCLUDED.size_bytes,
                        checksum_sha256 = EXCLUDED.checksum_sha256,
                        mime_type = EXCLUDED.mime_type,
                        asset_type = EXCLUDED.asset_type,
                        domain = EXCLUDED.domain,
                        project_hint = EXCLUDED.project_hint,
                        section_hint = EXCLUDED.section_hint,
                        page_domain_id = EXCLUDED.page_domain_id,
                        page_section_id = EXCLUDED.page_section_id,
                        sensitivity_level = EXCLUDED.sensitivity_level,
                        assignment_confidence = EXCLUDED.assignment_confidence,
                        sensitivity_confidence = EXCLUDED.sensitivity_confidence,
                        review_status = EXCLUDED.review_status,
                        vector_status = EXCLUDED.vector_status,
                        graph_status = EXCLUDED.graph_status,
                        extraction_status = EXCLUDED.extraction_status,
                        original_path = EXCLUDED.original_path,
                        modified_at = EXCLUDED.modified_at,
                        indexed_at = EXCLUDED.indexed_at,
                        provenance = EXCLUDED.provenance,
                        updated_at = now();
                    """,
                    payloads,
                )
                upserted += len(batch)
                cur.execute(
                    """
                    INSERT INTO platform.vault_audit_event (asset_id, event_type, actor, details)
                    VALUES (NULL, 'vault_sync_batch', 'system', %s::jsonb);
                    """,
                    (json.dumps({"batch_size": len(batch), "offset": i}),),
                )
            cur.execute(
                """
                INSERT INTO platform.review_task (asset_id, task_type, status, assignment_confidence, sensitivity_level)
                SELECT v.asset_id, 'classification_review', 'open', v.assignment_confidence, v.sensitivity_level
                FROM platform.raw_asset_vault v
                WHERE v.assignment_confidence < 0.86
                  AND NOT EXISTS (
                    SELECT 1 FROM platform.review_task rt
                    WHERE rt.asset_id = v.asset_id AND rt.status = 'open'
                  );
                """
            )
            review_created = cur.rowcount
            cur.execute(
                """
                UPDATE platform.storage_root SET configured = %s, updated_at = now()
                WHERE storage_root_id = 'local_database_mirror';
                """,
                (DATABASE_ROOT.is_dir(),),
            )
            from omeia.storage.env import datacloud_webdav_base_url

            datacloud_url = datacloud_webdav_base_url()
            cur.execute(
                """
                UPDATE platform.storage_root SET configured = %s, updated_at = now()
                WHERE storage_root_id = 'datacloud_webdav';
                """,
                (bool(datacloud_url),),
            )
        conn.commit()

    return {
        "status": "ok",
        "upserted": upserted,
        "inventory_rows": len(rows),
        "review_tasks_created": review_created,
    }


def vault_manifest_page(*, offset: int = 0, limit: int = 100) -> dict[str, Any]:
    """Paginated manifest for workers (LUMI-W110)."""
    offset = max(0, offset)
    limit = max(1, min(limit, 500))
    with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM platform.raw_asset_vault;")
            total = cur.fetchone()[0]
            cur.execute(
                """
                SELECT asset_id, logical_path, filename, storage_provider, asset_type,
                       assignment_confidence, review_status, vector_status, page_domain_id
                FROM platform.raw_asset_vault
                ORDER BY logical_path
                OFFSET %s LIMIT %s;
                """,
                (offset, limit),
            )
            items = [
                {
                    "asset_id": r[0],
                    "logical_path": r[1],
                    "filename": r[2],
                    "storage_provider": r[3],
                    "asset_type": r[4],
                    "assignment_confidence": float(r[5]) if r[5] is not None else 0,
                    "review_status": r[6],
                    "vector_status": r[7],
                    "page_domain_id": r[8],
                }
                for r in cur.fetchall()
            ]
    return {"total": total, "offset": offset, "limit": limit, "items": items}


def rebuild_inventory() -> dict[str, Any]:
    script = SCRIPTS_DIR / "build_raw_asset_inventory.py"
    if not script.is_file():
        raise FileNotFoundError(f"Inventory script not found: {script}")
    proc = subprocess.run(
        [sys.executable, str(script), "--database-root", str(DATABASE_ROOT)],
        capture_output=True,
        text=True,
        cwd=str(BLUEPRINT_ROOT),
        timeout=600,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "inventory build failed")
    return {"status": "ok", "summary": load_summary()}

```

### `omeia/api/database_processor.py`

```python
"""Extract, chunk, and persist lab database sections (Overview, Orders, Social, Wet-lab)."""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from omeia.api import document_extraction as de
from omeia.api.database_sections import DATABASE_SECTIONS, section_root
from omeia.api.paths import DATABASE_ROOT, PROCESSED_DIR, PUBLIC_PROCESSED_DIR
from omeia.api.project_processor import sync_public_processed


def _iter_chunks_from_disk(section_id: str) -> list[dict[str, Any]]:
    """Load all chunks from jsonl (complete) with JSON fallback."""
    chunks: list[dict[str, Any]] = []
    jsonl_path = processed_chunks_path(section_id)
    if jsonl_path.exists():
        try:
            with jsonl_path.open(encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    chunks.append(json.loads(line))
            return chunks
        except Exception:
            pass
    twin = load_processed_section(section_id)
    return list(twin.get("vector_chunks") or []) if twin else []


def write_lab_manifest() -> Path:
    """Small index for the UI to discover processed lab sections without API."""
    PUBLIC_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sections": list_processed_summary(),
    }
    out = PUBLIC_PROCESSED_DIR / "lab__manifest.json"
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return out

LAB_STORAGE_PREFIX = "lab__"


def storage_key(section_id: str) -> str:
    return f"{LAB_STORAGE_PREFIX}{section_id}"


def processed_json_path(section_id: str) -> Path:
    return PROCESSED_DIR / f"{storage_key(section_id)}.json"


def processed_chunks_path(section_id: str) -> Path:
    return PROCESSED_DIR / f"{storage_key(section_id)}.chunks.jsonl"


def _annotate_chunks(chunks: list[dict[str, Any]], section_id: str, section_label: str) -> list[dict[str, Any]]:
    out = []
    for chunk in chunks:
        row = dict(chunk)
        row["section_id"] = section_id
        row["section_label"] = section_label
        row["scope"] = "lab"
        row["project_code"] = None
        out.append(row)
    return out


def _folder_tree_from_assets(assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, dict[str, Any]] = defaultdict(lambda: {"file_count": 0, "extensions": set()})
    for asset in assets:
        folder = asset.get("folder") or "."
        counts[folder]["file_count"] += 1
        ext = asset.get("extension") or ""
        if ext:
            counts[folder]["extensions"].add(ext)
    rows = []
    for path, info in sorted(counts.items(), key=lambda x: x[0]):
        rows.append({
            "path": path,
            "file_count": info["file_count"],
            "categories": sorted(info["extensions"]),
        })
    return rows


def process_section(section_id: str) -> dict[str, Any]:
    if section_id not in DATABASE_SECTIONS:
        raise ValueError(f"Unknown database section: {section_id}")
    meta = DATABASE_SECTIONS[section_id]
    root = section_root(section_id)
    if not root.is_dir():
        raise FileNotFoundError(f"Section folder not found: {root}")

    file_inventory = de._scan_folder(root)
    all_assets = de._scan_all_assets(root)
    content_library = de._build_content_library(all_assets) if all_assets else {
        "sections": [], "figures_gallery": [], "totals": {}, "figure_count": 0,
    }

    document_records: list[de.ExtractionResult] = []
    vector_chunks: list[dict[str, Any]] = []
    extraction_summary: dict[str, Any] = {
        "total_scannable_assets": 0,
        "extracted_records": 0,
        "chunk_count": 0,
        "status_counts": {},
        "extractor_counts": {},
        "extension_counts": {},
        "errors": [],
    }
    if all_assets:
        document_records, vector_chunks, extraction_summary = de._extract_project_documents(root, all_assets)

    vector_chunks = _annotate_chunks(vector_chunks, section_id, meta["label"])
    combined_text = de._combine_text_records(document_records)
    document_index = [
        r.as_json(include_text=False, include_chunks=False)
        for r in document_records[: de.DEFAULT_MAX_DOCS_IN_JSON]
    ]

    extracted_count = extraction_summary.get("status_counts", {}).get("extracted", 0)
    return {
        "section_id": section_id,
        "storage_key": storage_key(section_id),
        "scope": "lab",
        "section_label": meta["label"],
        "description": meta["description"],
        "relative_root": meta["relative_root"],
        "database_root": str(DATABASE_ROOT),
        "content_root": str(root),
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "source_files_count": len(file_inventory),
        "total_assets_count": len(all_assets),
        "content_library": content_library,
        "document_index": document_index,
        "vector_chunks": vector_chunks[: de.DEFAULT_MAX_CHUNKS_IN_JSON],
        "extraction": extraction_summary,
        "folder_tree": _folder_tree_from_assets(all_assets)[:500],
        "combined_text_chars": len(combined_text),
        "metrics": {
            "document_count": len(file_inventory),
            "total_assets": len(all_assets),
            "scannable_assets": extraction_summary.get("total_scannable_assets", 0),
            "extracted_document_count": extracted_count,
            "knowledge_chunk_count": len(vector_chunks),
            "extraction_error_count": len(extraction_summary.get("errors", [])),
            "figure_count": content_library.get("figure_count", 0),
        },
    }


def save_processed_section(section_id: str, data: dict[str, Any] | None = None) -> Path:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    payload = data or process_section(section_id)
    out = processed_json_path(section_id)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    chunks = payload.get("vector_chunks") or []
    chunks_out = processed_chunks_path(section_id)
    with chunks_out.open("w", encoding="utf-8") as fh:
        for chunk in chunks:
            fh.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    sync_public_processed()
    write_lab_manifest()
    return out


def load_processed_section(section_id: str) -> dict[str, Any] | None:
    path = processed_json_path(section_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def get_section_record(section_id: str, *, refresh: bool = False) -> dict[str, Any]:
    if not refresh:
        cached = load_processed_section(section_id)
        if cached:
            return cached
    data = process_section(section_id)
    save_processed_section(section_id, data)
    return data


def _skip_on_bulk_process(section_id: str) -> bool:
    """Skip project-tree paths when bulk-processing lab corpus (projects handled separately)."""
    root = DATABASE_SECTIONS[section_id]["relative_root"]
    return root.startswith("projects/") or root == "projects"


def process_all_sections(*, refresh: bool = True) -> dict[str, Any]:
    results = []
    errors = []
    skipped: list[str] = []
    for section_id in DATABASE_SECTIONS:
        if _skip_on_bulk_process(section_id):
            skipped.append(section_id)
            continue
        try:
            twin = get_section_record(section_id, refresh=refresh)
            results.append({
                "section_id": section_id,
                "section_label": twin.get("section_label"),
                "metrics": twin.get("metrics"),
                "processed_at": twin.get("processed_at"),
                "output": str(processed_json_path(section_id)),
            })
        except Exception as exc:
            errors.append({"section_id": section_id, "error": str(exc)})
    manifest_path = write_lab_manifest()
    return {
        "processed": len(results),
        "skipped": skipped,
        "sections": results,
        "errors": errors,
        "output_dir": str(PROCESSED_DIR),
        "manifest": str(manifest_path),
    }


def _vault_asset_counts_by_section() -> dict[str, int]:
    """Count vault rows whose logical_path is under each section root (when Postgres is up)."""
    try:
        from omeia.api.supabase_sync import local_postgres_conn

        import psycopg

        counts: dict[str, int] = {sid: 0 for sid in DATABASE_SECTIONS}
        with psycopg.connect(local_postgres_conn(), connect_timeout=8) as conn:
            with conn.cursor() as cur:
                for sid, meta in DATABASE_SECTIONS.items():
                    prefix = meta["relative_root"].replace("\\", "/").rstrip("/") + "/"
                    cur.execute(
                        """
                        SELECT COUNT(*) FROM platform.raw_asset_vault
                        WHERE logical_path LIKE %s OR logical_path = %s;
                        """,
                        (prefix + "%", meta["relative_root"].replace("\\", "/")),
                    )
                    row = cur.fetchone()
                    counts[sid] = int(row[0]) if row else 0
        return counts
    except Exception:
        return {}


def _document_preview_row(
    doc: dict[str, Any],
    *,
    relative_root: str | None = None,
) -> dict[str, Any]:
    path = (doc.get("path") or doc.get("relative_path") or "").replace("\\", "/")
    title = de.document_display_title(doc)
    excerpt = de.document_display_excerpt(doc)
    row = {
        "path": path,
        "name": doc.get("name") or (Path(path).name if path else ""),
        "title": title,
        "excerpt": excerpt,
        "extraction_status": doc.get("extraction_status") or doc.get("status"),
        "extension": doc.get("extension"),
        "word_count": doc.get("word_count"),
    }
    if relative_root and path:
        row["open_url"] = de.lab_database_asset_url(relative_root, path)
    return row


def _extraction_status_label(twin: dict[str, Any]) -> str:
    if not twin:
        return "not_processed"
    metrics = twin.get("metrics") or {}
    extracted = metrics.get("extracted_document_count")
    if extracted is None:
        extracted = (twin.get("extraction") or {}).get("status_counts", {}).get("extracted", 0)
    total = metrics.get("total_assets") or len(twin.get("document_index") or [])
    if extracted and total:
        return "extracted"
    if twin.get("processed_at"):
        return "processed"
    return "unknown"


def list_lab_sections_detail() -> list[dict[str, Any]]:
    """Sections with on-disk, processed-twin, and vault counts for lab corpus UI."""
    vault_counts = _vault_asset_counts_by_section()
    rows = []
    for section_id, meta in DATABASE_SECTIONS.items():
        root = DATABASE_ROOT / meta["relative_root"]
        cached = load_processed_section(section_id)
        metrics = (cached or {}).get("metrics") or {}
        doc_index = (cached or {}).get("document_index") or []
        extracted = metrics.get("extracted_document_count")
        if extracted is None and cached:
            extracted = (cached.get("extraction") or {}).get("status_counts", {}).get("extracted", 0)
        rows.append({
            "section_id": section_id,
            "section_label": meta["label"],
            "description": meta["description"],
            "relative_root": meta["relative_root"],
            "folder_exists": root.is_dir(),
            "processed": cached is not None,
            "processed_at": cached.get("processed_at") if cached else None,
            "extraction_status": _extraction_status_label(cached),
            "metrics": metrics,
            "disk_asset_count": metrics.get("total_assets") or len(doc_index),
            "document_index_count": len(doc_index),
            "extracted_document_count": extracted or 0,
            "vault_asset_count": vault_counts.get(section_id, 0),
            "storage_key": storage_key(section_id),
            "twin_path": str(processed_json_path(section_id).name) if cached else None,
        })
    return rows


def section_detail_for_api(section_id: str, *, document_preview_limit: int = 50) -> dict[str, Any]:
    """Processed twin summary for UI — reads local JSON under processed_projects (not Supabase)."""
    if section_id not in DATABASE_SECTIONS:
        raise ValueError(f"Unknown database section: {section_id}")
    twin = load_processed_section(section_id)
    if not twin:
        raise FileNotFoundError(
            "Section not processed yet. Run database_processor --all --refresh."
        )
    meta = DATABASE_SECTIONS[section_id]
    vault_counts = _vault_asset_counts_by_section()
    doc_index = twin.get("document_index") or []
    limit = max(1, min(int(document_preview_limit or 50), 200))
    return {
        "section_id": section_id,
        "section_label": twin.get("section_label") or meta["label"],
        "description": twin.get("description") or meta["description"],
        "relative_root": meta["relative_root"],
        "storage_key": storage_key(section_id),
        "source": "local_processed_json",
        "twin_file": processed_json_path(section_id).name,
        "metrics": twin.get("metrics"),
        "processed_at": twin.get("processed_at"),
        "extraction": twin.get("extraction"),
        "extraction_status": _extraction_status_label(twin),
        "document_index_count": len(doc_index),
        "document_index_preview": [
            _document_preview_row(d, relative_root=meta["relative_root"]) for d in doc_index[:limit]
        ],
        "folder_tree": (twin.get("folder_tree") or [])[:200],
        "content_library_totals": (twin.get("content_library") or {}).get("totals"),
        "vault_asset_count": vault_counts.get(section_id, 0),
        "knowledge_search_path": f"/knowledge_search?section_id={section_id}",
    }


def section_summary_for_api(section_id: str) -> dict[str, Any]:
    """Backward-compatible alias — same payload as section_detail_for_api."""
    return section_detail_for_api(section_id)


def section_documents_for_api(
    section_id: str,
    *,
    q: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> dict[str, Any]:
    """Paginated document list from processed twin (local JSON)."""
    if section_id not in DATABASE_SECTIONS:
        raise ValueError(f"Unknown database section: {section_id}")
    twin = load_processed_section(section_id)
    if not twin:
        raise FileNotFoundError(
            "Section not processed yet. Run database_processor --all --refresh."
        )
    rel_root = DATABASE_SECTIONS[section_id]["relative_root"]
    docs = twin.get("document_index") or []
    tokens = _tokenize_query(q or "")
    if tokens:
        filtered = []
        for doc in docs:
            blob = " ".join(
                str(doc.get(k) or "")
                for k in ("path", "title", "name", "excerpt", "extension")
            ).lower()
            if any(tok in blob for tok in tokens):
                filtered.append(doc)
        docs = filtered
    total = len(docs)
    offset = max(0, int(offset or 0))
    limit = max(1, min(int(limit or 50), 200))
    page = docs[offset : offset + limit]
    return {
        "section_id": section_id,
        "query": q,
        "total": total,
        "offset": offset,
        "limit": limit,
        "documents": [_document_preview_row(d, relative_root=rel_root) for d in page],
    }


def list_processed_summary() -> list[dict[str, Any]]:
    rows = []
    for section_id, meta in DATABASE_SECTIONS.items():
        cached = load_processed_section(section_id)
        root = DATABASE_ROOT / meta["relative_root"]
        rows.append({
            "section_id": section_id,
            "section_label": meta["label"],
            "relative_root": meta["relative_root"],
            "folder_exists": root.is_dir(),
            "processed": cached is not None,
            "processed_at": cached.get("processed_at") if cached else None,
            "metrics": cached.get("metrics") if cached else None,
        })
    return rows


def _tokenize_query(query: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9\u00c0-\uffff]{3,}", (query or "").lower()) if t]


def search_section_chunks(
    query: str,
    *,
    section_id: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Keyword search over processed lab chunks (works without Qdrant)."""
    tokens = _tokenize_query(query)
    if not tokens:
        return []
    limit = max(1, min(int(limit or 20), 50))
    section_ids = [section_id] if section_id else list(DATABASE_SECTIONS.keys())
    hits: list[tuple[int, dict[str, Any]]] = []

    for sid in section_ids:
        twin = load_processed_section(sid)
        if not twin:
            continue
        label = twin.get("section_label") or sid
        for chunk in _iter_chunks_from_disk(sid):
            text = (chunk.get("text") or "").lower()
            if not text:
                continue
            score = sum(3 if tok in text else 0 for tok in tokens)
            if score <= 0:
                continue
            hits.append((score, {
                "section_id": sid,
                "section_label": label,
                "chunk_id": chunk.get("chunk_id"),
                "source_file": chunk.get("source_file"),
                "chunk_index": chunk.get("chunk_index"),
                "text_preview": chunk.get("text")[:1600],
                "score": float(score),
                "scope": "lab",
            }))

    hits.sort(key=lambda x: -x[0])
    return [h[1] for h in hits[:limit]]


def build_vector_manifest(section_id: str) -> dict[str, Any]:
    twin = get_section_record(section_id, refresh=False)
    return {
        "section_id": section_id,
        "storage_key": storage_key(section_id),
        "scope": "lab",
        "section_label": twin.get("section_label"),
        "chunk_count": len(twin.get("vector_chunks") or []),
        "chunks_jsonl": str(processed_chunks_path(section_id).resolve()),
    }


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Process lab database folders into extracted twins.")
    parser.add_argument("--section", help="Single section id (e.g. overview_personnel)")
    parser.add_argument("--all", action="store_true", help="Process every configured database section")
    parser.add_argument("--refresh", action="store_true", help="Force re-extraction")
    parser.add_argument("--list", action="store_true", help="List processing status")
    args = parser.parse_args()

    if args.list:
        print(json.dumps(list_processed_summary(), indent=2, ensure_ascii=False))
        return 0
    if args.all:
        result = process_all_sections(refresh=True)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if not result.get("errors") else 1
    if args.section:
        twin = get_section_record(args.section, refresh=args.refresh or True)
        path = save_processed_section(args.section, twin)
        print(f"wrote {path}")
        print(json.dumps({"metrics": twin.get("metrics"), "extraction": twin.get("extraction", {}).get("status_counts")}, indent=2))
        return 0
    parser.error("Provide --section ID or --all")
    return 1


if __name__ == "__main__":
    raise SystemExit(_cli())

```

### `omeia/api/agents.py`

```python
"""OMEIA copilot specialist agents.

Production-grade drop-in upgrade.

Compatibility promises:
- Keeps the public classes used by existing routers: PrivacyGuardrailAgent,
  RAGAgent, InstallationSpecialist, ScriptGeneratorAgent, LumiHpcAgent,
  TroubleshootingAgent, ImagePipelineSpecialist, ClinicalSpatialSpecialist.
- Keeps method names and return shapes compatible with the previous version.
- Does not execute generated shell/Slurm commands; it only returns scripts.

Safety / quality upgrades:
- Conservative clinical privacy redaction before external LLM calls.
- Environment-configurable, fault-tolerant Qdrant retrieval.
- Works across newer and older qdrant-client APIs where possible.
- Stable project filtering and duplicate-source suppression.
- Safer script generation and richer troubleshooting recipes.
"""
from __future__ import annotations

import logging
import os
import re
import shlex
from dataclasses import dataclass
from typing import Any, Iterable

try:  # Optional at import-time for tests/tools that do not install qdrant-client.
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qdrant_models
except Exception:  # pragma: no cover - dependency availability is environment-specific.
    QdrantClient = Any  # type: ignore[misc, assignment]
    qdrant_models = None  # type: ignore[assignment]

LOGGER = logging.getLogger(__name__)

_SAFE_TOKEN = re.compile(r"[^A-Za-z0-9_.:@/+,-=]")
_SAFE_SLURM_VALUE = re.compile(r"[^A-Za-z0-9_.:@/+,-=]")
_WORD_RE = re.compile(r"[A-Za-z0-9_+.-]+")

DEFAULT_DOC_COLLECTION = os.getenv("DOCUMENT_QDRANT_COLLECTION", "doc_chunks")
DEFAULT_QDRANT_VECTOR_NAME = os.getenv("DOCUMENT_QDRANT_VECTOR_NAME", "") or None
DEFAULT_RAG_LIMIT = int(os.getenv("RAG_RETRIEVAL_LIMIT", "5"))
MAX_RAG_LIMIT = int(os.getenv("RAG_RETRIEVAL_MAX_LIMIT", "20"))


def _clean_token(value: Any, default: str = "") -> str:
    """Return a compact label token safe for logs, Slurm fields, and paths."""
    text = str(value or default).strip()[:160]
    return _SAFE_TOKEN.sub("_", text) if text else default


def _clean_slurm_value(value: Any, default: str) -> str:
    text = str(value or default).strip()[:160]
    text = _SAFE_SLURM_VALUE.sub("_", text)
    return text or default


def _safe_int(value: Any, default: int, *, low: int, high: int) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = default
    return max(low, min(parsed, high))


def _safe_float(value: Any, default: float, *, low: float, high: float) -> float:
    try:
        parsed = float(value)
    except Exception:
        parsed = default
    return max(low, min(parsed, high))


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _normalize_project_codes(project_codes: Iterable[Any] | None) -> set[str]:
    return {str(code).strip().upper() for code in (project_codes or []) if str(code).strip()}


def _payload_text(payload: dict[str, Any], max_chars: int = 1800) -> str:
    text = (
        payload.get("text_preview")
        or payload.get("excerpt")
        or payload.get("text")
        or payload.get("content")
        or payload.get("chunk_text")
        or ""
    )
    return str(text).strip()[:max_chars]


@dataclass(frozen=True)
class RetrievalConfig:
    collection_name: str = DEFAULT_DOC_COLLECTION
    vector_name: str | None = DEFAULT_QDRANT_VECTOR_NAME
    score_threshold: float | None = None
    max_preview_chars: int = 1800

    @classmethod
    def from_env(cls) -> "RetrievalConfig":
        raw_threshold = os.getenv("RAG_SCORE_THRESHOLD", "").strip()
        threshold = None
        if raw_threshold:
            threshold = _safe_float(raw_threshold, 0.0, low=0.0, high=1.0)
        return cls(
            collection_name=os.getenv("DOCUMENT_QDRANT_COLLECTION", DEFAULT_DOC_COLLECTION).strip() or DEFAULT_DOC_COLLECTION,
            vector_name=os.getenv("DOCUMENT_QDRANT_VECTOR_NAME", "").strip() or None,
            score_threshold=threshold,
            max_preview_chars=_safe_int(os.getenv("RAG_MAX_PREVIEW_CHARS", "1800"), 1800, low=200, high=6000),
        )


class PrivacyGuardrailAgent:
    """Redact patient identifiers before external LLM calls.

    This is intentionally conservative. It aims to preserve the research intent
    while removing obvious patient/person identifiers from the text that may be
    sent to a cloud model. It is not a replacement for a clinical DLP product,
    but it prevents the most common accidental leaks in this app.
    """

    _PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
        (re.compile(r"\b\d{6}[-+A][0-9A-Z]{3,4}\b", re.I), "Finnish national ID pattern", "[REDACTED_HETU]"),
        (re.compile(r"\bMRN[:\s#-]*[A-Z0-9-]{4,}\b", re.I), "Medical record number", "[REDACTED_MRN]"),
        (re.compile(r"\b(?:patient|pt|subject)\s*#?\s*[A-Z0-9-]{3,}\b", re.I), "Patient/subject identifier", "[REDACTED_PATIENT_ID]"),
        (re.compile(r"\b(?:sample|specimen|case)\s*#?\s*[A-Z]{1,6}[-_]?\d{4,}[A-Z0-9-]*\b", re.I), "Case/sample identifier", "[REDACTED_SAMPLE_ID]"),
        (re.compile(r"\b[A-Z]{2,}\d{6,}[A-Z0-9-]*\b"), "Alphanumeric identifier", "[REDACTED_IDENTIFIER]"),
        (re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I), "Email address", "[REDACTED_EMAIL]"),
        (re.compile(r"\b(?:\+?\d[\d\s().-]{7,}\d)\b"), "Phone-like number", "[REDACTED_PHONE]"),
        (re.compile(r"\b(?:DOB|date\s*of\s*birth)[:\s-]*\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b", re.I), "Date of birth", "[REDACTED_DOB]"),
        (re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-](?:19|20)\d{2}\b"), "Specific calendar date", "[REDACTED_DATE]"),
    ]

    @classmethod
    def audit_query(cls, question: str) -> dict[str, Any]:
        redacted = str(question or "")
        violations: list[str] = []
        redaction_count = 0

        for pattern, label, replacement in cls._PATTERNS:
            matches = list(pattern.finditer(redacted))
            if not matches:
                continue
            violations.append(label)
            redaction_count += len(matches)
            redacted = pattern.sub(replacement, redacted)

        unique_violations = list(dict.fromkeys(violations))
        risk_level = "low"
        if redaction_count >= 5:
            risk_level = "high"
        elif redaction_count > 0:
            risk_level = "blocked_for_external_llm"

        return {
            "is_safe": len(unique_violations) == 0,
            "violations": unique_violations,
            "redacted_text": redacted,
            "redaction_count": redaction_count,
            "risk_level": risk_level,
        }


class RAGAgent:
    """Retrieve documentation chunks from Qdrant with safe fallbacks."""

    def __init__(self, qdrant: QdrantClient, llm_client: Any, config: RetrievalConfig | None = None):
        self.qdrant = qdrant
        self.llm = llm_client
        self.config = config or RetrievalConfig.from_env()

    def retrieve(
        self,
        question: str,
        project_codes: list[str] | None = None,
        limit: int = DEFAULT_RAG_LIMIT,
    ) -> list[dict[str, Any]]:
        question = str(question or "").strip()
        if not question or self.qdrant is None:
            return []

        limit = max(1, min(int(limit or DEFAULT_RAG_LIMIT), MAX_RAG_LIMIT))
        try:
            vector = self.llm.embed(question)
        except Exception as exc:
            LOGGER.warning("Embedding generation failed before retrieval: %s", exc)
            return []

        hits = self._query_qdrant(vector=vector, limit=limit * 4)
        return self._normalize_hits(hits, project_codes=project_codes, limit=limit)

    def _query_qdrant(self, vector: list[float], limit: int) -> list[Any]:
        collection = self.config.collection_name
        using = self.config.vector_name
        threshold = self.config.score_threshold

        # Newer qdrant-client API.
        try:
            kwargs: dict[str, Any] = {
                "collection_name": collection,
                "query": vector,
                "limit": limit,
                "with_payload": True,
            }
            if using:
                kwargs["using"] = using
            if threshold is not None:
                kwargs["score_threshold"] = threshold
            response = self.qdrant.query_points(**kwargs)
            return list(getattr(response, "points", []) or [])
        except TypeError:
            # Some qdrant versions do not support `with_payload`, `using`, or `score_threshold` here.
            pass
        except Exception as exc:
            LOGGER.debug("qdrant.query_points primary attempt failed: %s", exc)

        try:
            kwargs = {
                "collection_name": collection,
                "query": vector,
                "limit": limit,
            }
            if using:
                kwargs["using"] = using
            response = self.qdrant.query_points(**kwargs)
            return list(getattr(response, "points", []) or [])
        except Exception as exc:
            LOGGER.debug("qdrant.query_points compatibility attempt failed: %s", exc)

        # Older qdrant-client API.
        try:
            kwargs = {
                "collection_name": collection,
                "query_vector": vector,
                "limit": limit,
                "with_payload": True,
            }
            if threshold is not None:
                kwargs["score_threshold"] = threshold
            return list(self.qdrant.search(**kwargs) or [])
        except Exception as exc:
            LOGGER.warning("Qdrant retrieval failed for collection %s: %s", collection, exc)
            return []

    def _normalize_hits(
        self,
        hits: list[Any],
        project_codes: list[str] | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        allowed = _normalize_project_codes(project_codes)
        sources: list[dict[str, Any]] = []
        seen: set[str] = set()

        for hit in hits:
            payload = dict(getattr(hit, "payload", None) or {})
            if not payload:
                continue
            if not self._allowed_for_project(payload, allowed):
                continue

            chunk_id = str(payload.get("chunk_id") or payload.get("chunk_uid") or getattr(hit, "id", ""))
            source_uuid = str(
                payload.get("document_id")
                or payload.get("source_uuid")
                or payload.get("source_file_id")
                or payload.get("canonical_document_id")
                or payload.get("path")
                or payload.get("relative_path")
                or ""
            )
            dedupe_key = chunk_id or f"{source_uuid}:{payload.get('chunk_index')}"
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            text = _payload_text(payload, max_chars=self.config.max_preview_chars)
            if not text:
                continue

            score = getattr(hit, "score", None)
            try:
                score_f = float(score) if score is not None else 0.0
            except Exception:
                score_f = 0.0

            sources.append({
                "title": payload.get("title") or payload.get("document_title") or payload.get("filename") or "Document",
                "source_type": payload.get("source_type") or payload.get("document_kind") or payload.get("document_type") or "documentation",
                "source_uuid": source_uuid,
                "chunk_id": chunk_id or dedupe_key,
                "text_preview": text,
                "score": score_f,
                "project_code": payload.get("project_code"),
                "metadata": {
                    key: payload.get(key)
                    for key in ("filename", "relative_path", "section_id", "domain", "chunk_index", "ingestion_id")
                    if payload.get(key) is not None
                },
            })
            if len(sources) >= limit:
                break

        return sources

    @staticmethod
    def _allowed_for_project(payload: dict[str, Any], allowed: set[str]) -> bool:
        if not allowed:
            return True
        if payload.get("scope") == "lab":
            return True
        candidates = []
        candidates.extend(_as_list(payload.get("allowed_project_codes")))
        candidates.extend(_as_list(payload.get("project_codes")))
        candidates.extend(_as_list(payload.get("project_code")))
        normalized = _normalize_project_codes(candidates)
        # If a legacy payload has no project metadata, keep it visible rather than
        # silently hiding potentially useful lab documentation.
        return not normalized or not normalized.isdisjoint(allowed)


class InstallationSpecialist:
    """Return installation recipes for common spatial-biology tools."""

    _GUIDES: dict[str, dict[str, dict[str, Any]]] = {
        "napari": {
            "macos": {
                "status": "success",
                "commands": (
                    "curl -L -O https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-arm64.sh\n"
                    "bash Miniforge3-MacOSX-arm64.sh -b\n"
                    "source ~/miniforge3/bin/activate\n"
                    "mamba create -n napari_env python=3.10 napari pyqt -c conda-forge -y\n"
                    "conda activate napari_env\n"
                    "python - <<'PY'\nimport napari; print('napari', napari.__version__)\nPY"
                ),
                "verification": "napari --info",
                "expected_output": "Napari environment details are printed and a viewer window can be opened on a workstation.",
                "troubleshooting": "For Qt plugin failures, try `export QT_API=pyqt5`; on headless machines use a workstation, X11 forwarding, or offscreen checks only.",
            },
            "linux": {
                "status": "success",
                "commands": (
                    "mamba create -n napari_env python=3.10 napari pyqt -c conda-forge -y\n"
                    "conda activate napari_env\n"
                    "python - <<'PY'\nimport napari; print('napari', napari.__version__)\nPY"
                ),
                "verification": "napari --info",
                "expected_output": "Version and Qt backend information are printed.",
                "troubleshooting": "Install XCB libraries on Ubuntu/Debian nodes; avoid launching UI tools on compute nodes without a display.",
            },
        },
        "cylinter": {
            "linux": {
                "status": "success",
                "commands": (
                    "mamba create -n cylinter_env python=3.9 openjdk -c conda-forge -y\n"
                    "conda activate cylinter_env\n"
                    "python -m pip install --upgrade pip wheel setuptools\n"
                    "python -m pip install cylinter==0.1.5"
                ),
                "verification": "cylinter --help",
                "expected_output": "CLI help text is printed.",
                "troubleshooting": "Confirm `java -version` works inside the active environment before running image IO workflows.",
            },
        },
        "ashlar": {
            "linux": {
                "status": "success",
                "commands": (
                    "mamba create -n ashlar_env python=3.10 ashlar bioformats2raw raw2ometiff -c conda-forge -y\n"
                    "conda activate ashlar_env\n"
                    "ashlar --help"
                ),
                "verification": "ashlar --help",
                "expected_output": "Ashlar CLI help text is printed.",
                "troubleshooting": "For Bio-Formats reader errors, validate OME metadata, file naming, and channel naming before stitching.",
            },
        },
        "stardist": {
            "linux": {
                "status": "success",
                "commands": (
                    "mamba create -n stardist_env python=3.10 tensorflow stardist csbdeep tifffile -c conda-forge -y\n"
                    "conda activate stardist_env\n"
                    "python - <<'PY'\nfrom stardist.models import StarDist2D; print('StarDist OK')\nPY"
                ),
                "verification": "python -c \"from stardist.models import StarDist2D; print('ok')\"",
                "expected_output": "StarDist imports successfully.",
                "troubleshooting": "On Apple Silicon or CUDA hosts, align TensorFlow build with platform support before processing whole-slide images.",
            },
        },
        "qdrant": {
            "linux": {
                "status": "success",
                "commands": (
                    "docker run -d --name qdrant -p 6333:6333 -p 6334:6334 -v $PWD/qdrant_storage:/qdrant/storage qdrant/qdrant:latest\n"
                    "curl http://localhost:6333/collections"
                ),
                "verification": "curl http://localhost:6333/collections",
                "expected_output": "Qdrant returns a JSON collection list.",
                "troubleshooting": "If port 6333 is occupied, change the host port or stop the conflicting container.",
            }
        },
    }

    _ALIASES = {
        "basic": "ashlar",
        "basic-illumination": "ashlar",
        "stardist2d": "stardist",
        "vector-db": "qdrant",
        "vector_database": "qdrant",
    }

    def get_instructions(self, tool_name: str, os_platform: str) -> dict[str, Any]:
        tool = (tool_name or "").strip().lower().replace(" ", "_")
        tool = self._ALIASES.get(tool, tool)
        os_key = (os_platform or "linux").strip().lower()
        if os_key in {"ubuntu", "debian", "centos", "rocky"}:
            os_key = "linux"
        if os_key in {"darwin", "osx", "mac"}:
            os_key = "macos"

        guide = self._GUIDES.get(tool, {}).get(os_key)
        if not guide:
            available = {name: sorted(platforms.keys()) for name, platforms in self._GUIDES.items()}
            return {
                "status": "error",
                "message": f"No install guide for {tool_name!r} on {os_platform!r}.",
                "available_guides": available,
            }
        return {"status": "success", "tool": tool, "os": os_key, **guide}


class ScriptGeneratorAgent:
    """Generate production-safe shell wrappers."""

    def generate_bash(self, commands: str) -> str:
        body = str(commands or "").strip()
        if not body:
            body = "echo 'No commands were provided.'"
        return (
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "IFS=$'\\n\\t'\n\n"
            "log() { printf '[%s] %s\\n' \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\" \"$*\"; }\n"
            "fail() { log \"ERROR: $*\"; exit 1; }\n\n"
            "log 'Starting generated OMEIA script'\n"
            "command -v python >/dev/null 2>&1 || log 'python not found on PATH; continuing if not required'\n\n"
            f"{body}\n"
            "log 'Finished successfully'\n"
        )


class LumiHpcAgent:
    """Generate LUMI-compatible Slurm scripts from API request specs."""

    def generate_job(self, spec: dict[str, Any]) -> str:
        spec = spec or {}
        use_gpu = bool(spec.get("use_gpu", True))
        job_name = _clean_slurm_value(spec.get("job_name"), "omeia_job")
        account = _clean_slurm_value(spec.get("project_account"), os.getenv("LUMI_PROJECT_ACCOUNT", "project_462001415"))
        partition = _clean_slurm_value(spec.get("partition") or ("small-g" if use_gpu else "small"), "small-g" if use_gpu else "small")
        nodes = _safe_int(spec.get("nodes"), 1, low=1, high=64)
        ntasks = _safe_int(spec.get("ntasks"), 1, low=1, high=4096)
        cpus = _safe_int(spec.get("cpus") or spec.get("cpus_per_task"), 8, low=1, high=256)
        gpus = _safe_int(spec.get("gpus_per_node") or (1 if use_gpu else 0), 1 if use_gpu else 0, low=0, high=8)
        mem = _clean_slurm_value(spec.get("memory"), "32G")
        walltime = _clean_slurm_value(spec.get("walltime") or spec.get("time"), "02:00:00")
        scratch = str(spec.get("scratch_path") or os.getenv("LUMI_SCRATCH", f"/scratch/{account}")).rstrip("/")
        log_dir = str(spec.get("log_dir") or "logs/pipeline").strip("/")
        work_dir = str(spec.get("work_dir") or scratch).rstrip("/")
        container = str(spec.get("container_sif") or spec.get("container") or "").strip()
        command = str(spec.get("execution_command") or spec.get("command") or "echo 'Set execution_command in request body'").strip()
        module_loads = [str(m).strip() for m in _as_list(spec.get("modules")) if str(m).strip()]
        env = dict(spec.get("env") or {})

        sbatch_lines = [
            "#!/usr/bin/env bash",
            f"#SBATCH --job-name={job_name}",
            f"#SBATCH --account={account}",
            f"#SBATCH --partition={partition}",
            f"#SBATCH --nodes={nodes}",
            f"#SBATCH --ntasks={ntasks}",
            f"#SBATCH --cpus-per-task={cpus}",
            f"#SBATCH --mem={mem}",
            f"#SBATCH --time={walltime}",
            f"#SBATCH --output={shlex.quote(log_dir)}/%x-%j.out",
            f"#SBATCH --error={shlex.quote(log_dir)}/%x-%j.err",
        ]
        if gpus:
            sbatch_lines.append(f"#SBATCH --gpus-per-node={gpus}")

        body = [
            "",
            "set -euo pipefail",
            "IFS=$'\\n\\t'",
            "module --force purge || true",
        ]
        for module in module_loads:
            body.append("module load " + shlex.quote(module))
        body.extend([
            "mkdir -p " + shlex.quote(f"{scratch}/{log_dir}"),
            "export APPTAINER_CACHEDIR=${APPTAINER_CACHEDIR:-" + shlex.quote(f"{scratch}/apptainer_cache") + "}",
            "mkdir -p \"$APPTAINER_CACHEDIR\"",
            "cd " + shlex.quote(work_dir),
            "echo \"[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Job started on $(hostname)\"",
            "echo \"SLURM_JOB_ID=${SLURM_JOB_ID:-manual}\"",
            "echo \"Working directory: $(pwd)\"",
        ])
        for key, value in env.items():
            clean_key = re.sub(r"[^A-Za-z0-9_]", "_", str(key).strip()).upper()
            if clean_key:
                body.append(f"export {clean_key}={shlex.quote(str(value))}")

        if container:
            body.extend([
                "test -f " + shlex.quote(container) + " || { echo 'Container not found: " + shlex.quote(container) + "'; exit 2; }",
                "apptainer exec " + ("--nv " if gpus else "")
                + "-B " + shlex.quote(scratch) + ":" + shlex.quote(scratch) + " "
                + shlex.quote(container) + " " + command,
            ])
        else:
            body.append(command)

        body.append("echo \"[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Job finished\"")
        return "\n".join(sbatch_lines + body) + "\n"


class TroubleshootingAgent:
    """Classify common spatial/HPC/LLM failures and return actionable fixes."""

    _RULES: list[tuple[tuple[str, ...], dict[str, str]]] = [
        (("opengl", "qt platform plugin"), {
            "cause": "Graphics/Qt initialization failure, common on headless SSH or minimal Linux nodes.",
            "fix": "Run UI tools on a workstation, enable X11 forwarding, or set `QT_QPA_PLATFORM=offscreen` for non-interactive checks.",
            "prevention": "Keep Napari/Qt workflows separate from compute-node batch jobs.",
        }),
        (("cuda", "out of memory"), {
            "cause": "GPU memory exhaustion during segmentation, training, or tiling.",
            "fix": "Reduce batch size/tile size, use mixed precision where safe, or request a larger GPU partition.",
            "prevention": "Profile peak VRAM on a representative slide before full-cohort submission.",
        }),
        (("oom",), {
            "cause": "Memory exhaustion; the scheduler or kernel likely killed the process.",
            "fix": "Increase `--mem`, reduce concurrency, or process slides/ROIs in smaller batches.",
            "prevention": "Log memory usage and keep one pilot run per modality.",
        }),
        (("killed", "memory"), {
            "cause": "The process was likely terminated by memory pressure.",
            "fix": "Lower worker count/tile size or request more memory.",
            "prevention": "Add memory telemetry to each batch and keep conservative defaults for full-slide runs.",
        }),
        (("no such file",), {
            "cause": "Missing input path, stale bind mount, or wrong working directory.",
            "fix": "Add preflight `test -e` checks for inputs, container, scratch folders, and output directories.",
            "prevention": "Use absolute scratch paths and generate scripts from a validated project manifest.",
        }),
        (("permission denied",), {
            "cause": "Filesystem permission or execute-bit issue.",
            "fix": "Check ownership, ACLs, and whether shell scripts are executable (`chmod +x`).",
            "prevention": "Write outputs into project scratch/work directories rather than read-only mounts.",
        }),
        (("401", "unauthorized"), {
            "cause": "Missing or expired authentication token.",
            "fix": "Refresh the session and verify frontend calls use the authenticated apiFetch wrapper.",
            "prevention": "Centralize API access and handle token refresh/session expiry consistently.",
        }),
        (("qdrant", "collection"), {
            "cause": "Vector collection is missing, misnamed, or has an incompatible vector dimension.",
            "fix": "Verify DOCUMENT_QDRANT_COLLECTION and embedding dimension, then recreate/reindex if needed.",
            "prevention": "Create collections through a migration/startup check and store model dimension metadata.",
        }),
        (("rate limit",), {
            "cause": "LLM provider rate limit or quota throttling.",
            "fix": "Retry with exponential backoff, reduce max tokens, or fall back to a local/mock provider.",
            "prevention": "Set provider budgets and keep local retrieval/mock mode available for demos.",
        }),
    ]

    def diagnose_log(self, log_text: str) -> dict[str, str]:
        lower = str(log_text or "").lower()
        for keywords, result in self._RULES:
            if all(k in lower for k in keywords):
                return {**result, "confidence": "high"}
        return {
            "cause": "Unclassified error; inspect the first traceback and the final stderr lines.",
            "fix": "Re-run the smallest failing command with verbose logging and preflight input checks.",
            "prevention": "Capture stdout/stderr, environment variables, package versions, and Slurm metadata for every run.",
            "confidence": "low",
        }


class ImagePipelineSpecialist:
    """Image-pipeline orchestration catalog."""

    _PIPELINES = [
        "basic", "ashlar", "stardist", "mesmer", "cycif", "geomx", "xenium", "qupath", "napari", "cylinter",
    ]

    def list_pipelines(self) -> list[str]:
        return list(self._PIPELINES)


class ClinicalSpatialSpecialist:
    """Return concise, reproducible analysis recipe templates."""

    def get_analysis_recipe(self, analysis_type: str) -> str:
        key = (analysis_type or "").strip().lower().replace("-", "_")
        recipes = {
            "survival": (
                "# Kaplan-Meier / Cox workflow\n"
                "from lifelines import KaplanMeierFitter, CoxPHFitter\n"
                "kmf = KaplanMeierFitter()\n"
                "kmf.fit(df['pfs_months'], event_observed=df['pfs_event'], label='cohort')\n"
                "ax = kmf.plot_survival_function(ci_show=True)\n"
                "cph = CoxPHFitter()\n"
                "cph.fit(df[['pfs_months', 'pfs_event', 'immune_infiltration_score']], 'pfs_months', 'pfs_event')\n"
                "cph.print_summary()\n"
            ),
            "group_compare": (
                "# Group comparison with auditable summary\n"
                "import pandas as pd\n"
                "from scipy import stats\n"
                "summary = df.groupby('hrd_status')['immune_infiltration_score'].agg(['count', 'mean', 'std'])\n"
                "groups = [g['immune_infiltration_score'].dropna().to_numpy() for _, g in df.groupby('hrd_status')]\n"
                "test = stats.ttest_ind(groups[0], groups[1], equal_var=False, nan_policy='omit')\n"
            ),
            "spatial_neighbors": (
                "# Squidpy neighborhood enrichment\n"
                "import squidpy as sq\n"
                "sq.gr.spatial_neighbors(adata, coord_type='generic')\n"
                "sq.gr.nhood_enrichment(adata, cluster_key='leiden')\n"
                "sq.pl.nhood_enrichment(adata, cluster_key='leiden')\n"
            ),
            "marker_qc": (
                "# Marker QC summary\n"
                "marker_cols = [c for c in df.columns if c.startswith('marker_')]\n"
                "qc = df[marker_cols].describe(percentiles=[.01, .05, .5, .95, .99]).T\n"
                "qc['dynamic_range'] = qc['99%'] - qc['1%']\n"
                "qc.sort_values('dynamic_range', ascending=False).head(20)\n"
            ),
        }
        aliases = {"cox": "survival", "km": "survival", "ttest": "group_compare", "neighbors": "spatial_neighbors"}
        key = aliases.get(key, key)
        return recipes.get(
            key,
            f"# No bundled recipe for {analysis_type!r}.\n"
            "# Available recipes: survival, group_compare, spatial_neighbors, marker_qc.\n",
        )

```

### `omeia/api/llm_client.py`

```python
"""Provider-routed LLM client for OMEIA.

Production-grade drop-in upgrade for the original LLMClient.

Compatibility promises:
- Keeps LLMClient.generate(prompt, system_prompt), healthCheck(), and embed().
- Keeps public attributes provider/model/api_key/base_url for existing router code.
- Uses deterministic local embeddings by default so local RAG still works offline.

Safety / quality upgrades:
- Optional OpenAI SDK import so tests/tools do not crash if the dependency is absent.
- Bounded provider fallback without recursive state corruption.
- Provider-specific env resolution with no secret logging.
- OpenAI-compatible providers: OpenAI, Groq, OpenRouter, Together, DeepSeek, Ollama.
- Robust mock synthesis for offline demos and CI.
"""
from __future__ import annotations

import hashlib
import logging
import math
import os
import re
from dataclasses import dataclass
from typing import Any, List

try:
    import requests
except Exception:  # pragma: no cover - dependency availability is environment-specific.
    requests = None  # type: ignore[assignment]

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - dependency availability is environment-specific.
    OpenAI = None  # type: ignore[assignment]

LOGGER = logging.getLogger(__name__)

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "to", "in",
    "of", "for", "on", "with", "at", "by", "from", "this", "that", "these", "those",
    "it", "its", "as", "be", "can", "how", "what", "why", "when", "where", "which",
    "there", "their", "they", "we", "you", "your", "our", "about", "into", "over",
}
_TOKEN_RE = re.compile(r"[a-zA-Z0-9_+.-]+")


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _bounded_float(value: Any, default: float, low: float, high: float) -> float:
    try:
        parsed = float(value)
    except Exception:
        parsed = default
    return max(low, min(parsed, high))


def _bounded_int(value: Any, default: int, low: int, high: int) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = default
    return max(low, min(parsed, high))


@dataclass(frozen=True)
class ProviderConfig:
    provider: str
    model: str
    api_key: str = ""
    base_url: str = ""
    extra_headers: dict[str, str] | None = None

    @property
    def is_mock(self) -> bool:
        return self.provider == "mock"

    @property
    def is_local(self) -> bool:
        return self.provider in {"mock", "ollama"}


class LLMClient:
    """Small OpenAI-compatible provider router used by the API."""

    _KNOWN_PROVIDERS = {"mock", "openai", "groq", "openrouter", "together", "ollama", "deepseek"}

    def __init__(self):
        self.provider = _env("LLM_PROVIDER", "mock").lower() or "mock"
        if self.provider not in self._KNOWN_PROVIDERS:
            LOGGER.warning("Unknown LLM_PROVIDER=%s; falling back to mock", self.provider)
            self.provider = "mock"

        self.model = _env("LLM_MODEL", "mock-model") or "mock-model"
        self.api_key = _env("LLM_API_KEY", "")
        self.base_url = _env("LLM_BASE_URL", "")
        fallback_env = _env("LLM_FALLBACK_PROVIDERS", "groq,openai,openrouter,together,deepseek,ollama,mock")
        self.fallback_providers = self._normalize_provider_list(fallback_env)
        if "mock" not in self.fallback_providers:
            self.fallback_providers.append("mock")

        self.timeout_seconds = _bounded_float(_env("LLM_TIMEOUT_SECONDS", "45"), 45.0, 2.0, 240.0)
        self.max_tokens = _bounded_int(_env("LLM_MAX_TOKENS", "1400"), 1400, 64, 12000)
        self.temperature = _bounded_float(_env("LLM_TEMPERATURE", "0.0"), 0.0, 0.0, 2.0)
        self.client: Any | None = None
        self.last_provider_errors: list[str] = []
        self._init_client()

    @classmethod
    def _normalize_provider_list(cls, value: str) -> list[str]:
        providers: list[str] = []
        for raw in (value or "").split(","):
            provider = raw.strip().lower()
            if provider and provider in cls._KNOWN_PROVIDERS and provider not in providers:
                providers.append(provider)
        return providers or ["mock"]

    def _config_for(self, provider: str) -> ProviderConfig:
        provider = (provider or "mock").lower()
        if provider == "openai":
            return ProviderConfig(
                "openai",
                _env("OPENAI_MODEL", self.model if self.provider == "openai" else "gpt-4o-mini"),
                _env("OPENAI_API_KEY", self.api_key if self.provider == "openai" else ""),
                _env("OPENAI_BASE_URL", ""),
            )
        if provider == "groq":
            return ProviderConfig(
                "groq",
                _env("GROQ_MODEL", "llama-3.1-70b-versatile"),
                _env("GROQ_API_KEY", self.api_key if self.provider == "groq" else ""),
                _env("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
            )
        if provider == "openrouter":
            headers = {}
            site_url = _env("OPENROUTER_SITE_URL", "")
            app_name = _env("OPENROUTER_APP_NAME", "OMEIA")
            if site_url:
                headers["HTTP-Referer"] = site_url
            if app_name:
                headers["X-Title"] = app_name
            return ProviderConfig(
                "openrouter",
                _env("OPENROUTER_MODEL", self.model if self.provider == "openrouter" else "openai/gpt-4o-mini"),
                _env("OPENROUTER_API_KEY", self.api_key if self.provider == "openrouter" else ""),
                _env("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
                headers or None,
            )
        if provider == "together":
            return ProviderConfig(
                "together",
                _env("TOGETHER_MODEL", self.model if self.provider == "together" else "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"),
                _env("TOGETHER_API_KEY", self.api_key if self.provider == "together" else ""),
                _env("TOGETHER_BASE_URL", "https://api.together.xyz/v1"),
            )
        if provider == "deepseek":
            return ProviderConfig(
                "deepseek",
                _env("DEEPSEEK_MODEL", self.model if self.provider == "deepseek" else "deepseek-chat"),
                _env("DEEPSEEK_API_KEY", self.api_key if self.provider == "deepseek" else ""),
                _env("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            )
        if provider == "ollama":
            return ProviderConfig(
                "ollama",
                _env("OLLAMA_MODEL", self.model if self.provider == "ollama" else "llama3"),
                "ollama",
                _env("OLLAMA_BASE_URL", self.base_url or "http://localhost:11434/v1"),
            )
        return ProviderConfig("mock", "mock-model", "", "")

    def _current_config(self) -> ProviderConfig:
        if self.provider == "mock":
            return ProviderConfig("mock", "mock-model", "", "")
        if self.provider == "ollama":
            return ProviderConfig("ollama", self.model or "llama3", "ollama", self.base_url or "http://localhost:11434/v1")
        return ProviderConfig(self.provider, self.model, self.api_key, self.base_url)

    def _init_client(self) -> None:
        """Initialise the configured primary provider, falling back to mock if unavailable."""
        cfg = self._current_config()
        if cfg.provider != "mock" and not (cfg.api_key or cfg.provider == "ollama"):
            cfg = self._config_for(cfg.provider)

        if cfg.provider == "mock" or (not cfg.api_key and cfg.provider != "ollama") or OpenAI is None:
            if cfg.provider != "mock" and OpenAI is None:
                LOGGER.warning("OpenAI SDK is unavailable; LLM provider %s disabled", cfg.provider)
            self.provider, self.model, self.api_key, self.base_url = "mock", "mock-model", "", ""
            self.client = None
            return

        self.provider, self.model, self.api_key, self.base_url = cfg.provider, cfg.model, cfg.api_key, cfg.base_url
        self.client = self._client_for(cfg)

    def _client_for(self, cfg: ProviderConfig) -> Any | None:
        if OpenAI is None:
            return None
        if cfg.provider == "mock" or (not cfg.api_key and cfg.provider != "ollama"):
            return None
        kwargs: dict[str, Any] = {
            "api_key": cfg.api_key,
            "timeout": self.timeout_seconds,
            "max_retries": 1,
        }
        if cfg.base_url:
            kwargs["base_url"] = cfg.base_url
        if cfg.extra_headers:
            kwargs["default_headers"] = cfg.extra_headers
        return OpenAI(**kwargs)

    def healthCheck(self) -> bool:
        """Verify whether the current provider is responsive."""
        if self.provider == "mock":
            return True
        try:
            if self.provider == "ollama":
                if requests is None:
                    return False
                base = (self.base_url or "http://localhost:11434/v1").replace("/v1", "")
                return requests.get(base, timeout=2).status_code < 500
            if self.client:
                self.client.models.list()
                return True
        except Exception as exc:
            LOGGER.debug("LLM health check failed for %s: %s", self.provider, exc)
        return False

    # PEP-8 alias for new code; old routers may still use healthCheck().
    def health_check(self) -> bool:
        return self.healthCheck()

    def _chat_once(self, cfg: ProviderConfig, prompt: str, system_prompt: str) -> str:
        client = self._client_for(cfg)
        if client is None:
            return self._mock_generate(prompt, system_prompt)

        response = client.chat.completions.create(
            model=cfg.model,
            messages=[
                {"role": "system", "content": system_prompt or "You are a helpful research copilot."},
                {"role": "user", "content": prompt or ""},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        content = response.choices[0].message.content
        return (content or "").strip()

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """Generate conversational text with automatic fallback routing."""
        primary = self.provider or "mock"
        providers = [primary] + [p for p in self.fallback_providers if p != primary]
        errors: list[str] = []

        for provider in providers:
            cfg = self._current_config() if provider == primary else self._config_for(provider)
            if cfg.provider != "mock" and not cfg.api_key and cfg.provider != "ollama":
                continue
            if cfg.provider != "mock" and OpenAI is None:
                errors.append(f"{cfg.provider}: OpenAISDKMissing")
                continue

            try:
                result = self._chat_once(cfg, prompt, system_prompt)
                if result:
                    self.provider, self.model, self.api_key, self.base_url = cfg.provider, cfg.model, cfg.api_key, cfg.base_url
                    self.client = self._client_for(cfg)
                    self.last_provider_errors = errors
                    return result
            except Exception as exc:
                errors.append(f"{cfg.provider}: {type(exc).__name__}")
                LOGGER.warning("LLM provider %s failed: %s", cfg.provider, exc)

        self.last_provider_errors = errors
        fallback = self._mock_generate(prompt, system_prompt)
        if errors:
            fallback += "\n\n*Provider fallback note: " + "; ".join(errors[:4]) + ".*"
        return fallback

    def _extract_sources(self, prompt: str) -> list[dict[str, str]]:
        sources: list[dict[str, str]] = []
        pattern = re.compile(r"\[(\d+)\] Source:\s*(.*?)\n(.*?)(?=\n\[\d+\] Source:|\n\nQuestion:|\Z)", re.DOTALL)
        for match in pattern.finditer(prompt or ""):
            sources.append({
                "index": match.group(1),
                "title": match.group(2).strip(),
                "content": match.group(3).strip(),
            })
        return sources

    @staticmethod
    def _extract_database_count(prompt: str, label: str) -> int:
        match = re.search(rf"{re.escape(label)}:\s*(\d+)", prompt or "", re.I)
        return int(match.group(1)) if match else 0

    def _mock_generate(self, prompt: str, system_prompt: str = "") -> str:
        """Dynamic offline synthesizer for local development, demos, and CI."""
        q_match = re.search(r"Question:\s*(.*)", prompt or "", re.DOTALL | re.IGNORECASE)
        question = q_match.group(1).strip() if q_match else "General query"
        lower_q = question.lower()
        patients_cnt = self._extract_database_count(prompt, "Patient total")
        samples_cnt = self._extract_database_count(prompt, "Sample total")
        sources = self._extract_sources(prompt)

        if "napari" in lower_q and any(os_word in lower_q for os_word in ("macos", "mac", "apple")):
            return (
                "### macOS Napari installation\n\n"
                "Use a native Miniforge/Mamba environment for Qt and OpenGL stability on Apple Silicon.\n\n"
                "```bash\n"
                "curl -L -O \"https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-arm64.sh\"\n"
                "bash Miniforge3-MacOSX-arm64.sh -b\n"
                "source ~/miniforge3/bin/activate\n"
                "mamba create -n napari_env python=3.10 napari pyqt -c conda-forge -y\n"
                "conda activate napari_env\n"
                "napari --info\n"
                "```\n\n"
                + self._format_source_notes(sources, "napari")
            )

        if "cylinter" in lower_q and "linux" in lower_q:
            return (
                "### Cylinter Linux installation\n\n"
                "```bash\n"
                "mamba create -n cylinter_env python=3.9 openjdk -c conda-forge -y\n"
                "conda activate cylinter_env\n"
                "python -m pip install --upgrade pip wheel setuptools\n"
                "python -m pip install cylinter==0.1.5\n"
                "cylinter --help\n"
                "```\n\n"
                + self._format_source_notes(sources, "cylinter")
            )

        if any(k in lower_q for k in ("opengl", "qt platform plugin", "crash")):
            return (
                "### Rendering/Qt diagnostic\n\n"
                "The most likely issue is a display/Qt/OpenGL initialization problem. Try running Napari on a workstation, "
                "using X11 forwarding, or setting `QT_QPA_PLATFORM=offscreen` for non-interactive checks. Install missing XCB libraries on minimal Linux hosts.\n\n"
                + self._format_source_notes(sources, "opengl")
            )

        if any(k in lower_q for k in ("count", "sample", "patient", "how many")):
            return (
                "### Registry metadata summary\n\n"
                f"- Total patients: **{patients_cnt}**\n"
                f"- Total samples: **{samples_cnt}**\n\n"
                "These values come from the structured database-count block supplied to the model. No patient identifiers are required for this summary.\n\n"
                + self._format_source_notes(sources)
            )

        if not sources:
            return (
                "### OMEIA copilot synthesis\n\n"
                "No matching document chunks were retrieved for this query. The structured database context is still available, "
                f"with {patients_cnt} patients and {samples_cnt} samples in the active scope."
            )

        query_terms = {
            word for word in _TOKEN_RE.findall(lower_q)
            if word not in _STOPWORDS and len(word) > 2
        }
        bullets: list[str] = []
        for source in sources[:6]:
            content = source["content"]
            sentences = re.split(r"(?<=[.!?])\s+", content)
            selected = [s.strip() for s in sentences if any(term in s.lower() for term in query_terms)]
            excerpt = " ".join(selected[:2]) or content[:420]
            bullets.append(f"- **[{source['index']}] {source['title']}** — {excerpt}")

        return (
            "### OMEIA copilot synthesis\n\n"
            f"Question: *{question}*\n\n"
            + "\n".join(bullets)
            + f"\n\n*System context: {patients_cnt} patients and {samples_cnt} samples in the active scope.*"
        )

    def _format_source_notes(self, sources: list[dict[str, str]], keyword: str | None = None) -> str:
        if not sources:
            return ""
        lines = ["**References retrieved:**"]
        for source in sources:
            haystack = (source["title"] + " " + source["content"]).lower()
            if keyword and keyword.lower() not in haystack:
                continue
            excerpt = source["content"][:240].replace("\n", " ")
            lines.append(f"- [{source['index']}] {source['title']}: {excerpt}...")
        return "\n".join(lines) if len(lines) > 1 else ""

    def embed(self, text: str, dim: int = 384) -> List[float]:
        """Generate a stable L2-normalized hashed embedding for offline RAG.

        This intentionally avoids external calls by default so privacy-sensitive
        queries can still retrieve local Qdrant documentation. It is deterministic
        across processes and suitable for local/private indexing demos.
        """
        dim = _bounded_int(dim, 384, 32, 4096)
        vec = [0.0] * dim
        tokens = _TOKEN_RE.findall((text or "").lower())

        for token in tokens:
            if token in _STOPWORDS:
                continue
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
            idx = int.from_bytes(digest[:4], "big") % dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            weight = 1.0 + min(len(token), 24) / 24.0
            vec[idx] += sign * weight

            if len(token) >= 5:
                for i in range(min(len(token) - 2, 10)):
                    gram = token[i:i + 3]
                    gd = hashlib.blake2b(gram.encode("utf-8"), digest_size=8).digest()
                    vec[int.from_bytes(gd[:4], "big") % dim] += 0.22

        # Add weak document-level features so extremely short scientific strings still separate.
        for gram in self._char_ngrams((text or "").lower(), n=4, limit=64):
            gd = hashlib.blake2b(gram.encode("utf-8"), digest_size=8).digest()
            vec[int.from_bytes(gd[:4], "big") % dim] += 0.05

        norm = math.sqrt(sum(v * v for v in vec))
        if norm < 1e-9:
            seed = hashlib.blake2b((text or "empty").encode("utf-8"), digest_size=32).digest()
            vec = [((seed[i % len(seed)] / 255.0) * 2.0 - 1.0) for i in range(dim)]
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    @staticmethod
    def _char_ngrams(text: str, *, n: int = 4, limit: int = 64) -> list[str]:
        compact = re.sub(r"\s+", " ", text.strip())
        if len(compact) < n:
            return []
        return [compact[i:i + n] for i in range(min(len(compact) - n + 1, limit))]

    def embed_many(self, texts: list[str], dim: int = 384) -> list[list[float]]:
        return [self.embed(text, dim=dim) for text in texts]

    def public_status(self) -> dict[str, Any]:
        """Return safe status metadata for health endpoints without exposing secrets."""
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url_configured": bool(self.base_url),
            "api_key_configured": bool(self.api_key and self.provider not in {"mock", "ollama"}),
            "fallback_providers": [p for p in self.fallback_providers if p != "mock"] + ["mock"],
            "healthy": self.healthCheck(),
            "last_provider_errors": list(self.last_provider_errors[-4:]),
        }

```

### `omeia/api/project_digitalization_engine.py`

```python
"""Project folder digitalization: scan LAB_STORAGE_ROOT, extract, store raw knowledge layer."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import psycopg

from omeia.api import document_extraction as de
from omeia.api.paths import DATABASE_ROOT, lab_storage_root, projects_roots_for_scan
from omeia.api.raw_vault_store import ensure_vault_schema
from omeia.api.vault_ingestion_engine import (
    STORAGE_PROVIDER,
    _db_conn,
    _guess_mime,
    _jsonb_dumps,
    _utc_now,
    _write_report,
    iter_scan_files,
    stable_asset_id,
    upsert_vault_from_extraction,
)

LOGGER = logging.getLogger(__name__)

STORAGE_ROOT_ID = "lab_storage_root"
BATCH_SIZE = int(os.environ.get("INGESTION_BATCH_SIZE", "50"))
MAX_TEXT_MB = float(os.environ.get("MAX_TEXT_FILE_MB", "25"))
MAX_CHECKSUM_MB = float(os.environ.get("MAX_CHECKSUM_FILE_MB", "50"))
ENABLE_OCR = os.environ.get("ENABLE_OCR", "false").strip().lower() in ("1", "true", "yes")
ENABLE_AI = os.environ.get("ENABLE_AI_CLASSIFICATION", "false").strip().lower() in ("1", "true", "yes")
ENABLE_VECTORS = os.environ.get("ENABLE_VECTOR_EMBEDDINGS", "false").strip().lower() in ("1", "true", "yes")

FILE_CATEGORIES = frozenset({
    "uncategorized", "project_document", "protocol", "SOP", "meeting_note", "publication",
    "software_guide", "troubleshooting", "clinical_metadata", "image_processing",
    "pipeline_script", "analysis_script", "dataset", "log", "report", "figure", "unknown",
})

EXT_TYPE_MAP: dict[str, str] = {
    ".pdf": "document", ".docx": "document", ".doc": "document", ".txt": "document",
    ".md": "document", ".html": "document", ".htm": "document", ".rtf": "document",
    ".xlsx": "spreadsheet", ".xls": "spreadsheet", ".csv": "spreadsheet", ".tsv": "spreadsheet",
    ".py": "script", ".r": "script", ".ipynb": "notebook", ".sh": "script", ".slurm": "script",
    ".yaml": "config", ".yml": "config", ".json": "config", ".toml": "config", ".xml": "config",
    ".tif": "image_data", ".tiff": "image_data", ".png": "image", ".jpg": "image", ".jpeg": "image",
    ".svs": "image_data", ".ndpi": "image_data", ".czi": "image_data", ".ims": "image_data",
    ".parquet": "dataset", ".h5ad": "dataset", ".h5": "dataset", ".rds": "dataset", ".feather": "dataset",
    ".log": "log", ".out": "log", ".err": "log",
}


def ensure_digitalization_schema() -> None:
    ensure_vault_schema()
    from omeia.api.sql_migrations import apply_pending_migrations

    apply_pending_migrations()


def _project_candidate_id(name: str) -> str:
    return "proj_" + hashlib.sha1(name.encode("utf-8")).hexdigest()[:14]


def _folder_id(rel_path: str) -> str:
    return "fld_" + hashlib.sha1(rel_path.encode("utf-8")).hexdigest()[:14]


def detect_file_type(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in EXT_TYPE_MAP:
        return EXT_TYPE_MAP[ext]
    if de.is_vault_large_binary(path):
        return "image_data"
    if ext in de.EXTRACTABLE_TEXT_EXTENSIONS:
        return "document"
    return "unknown"


def rule_category(path: Path, detected_type: str) -> tuple[str, float]:
    p = str(path).lower()
    if detected_type == "log" or path.suffix.lower() in {".log", ".out", ".err"}:
        return "log", 0.7
    if detected_type in {"script", "notebook"}:
        return "pipeline_script", 0.55
    if detected_type == "spreadsheet":
        return "dataset", 0.5
    if detected_type == "image_data":
        return "figure", 0.45
    if re.search(r"protocol|sop", p):
        return "protocol", 0.6
    if re.search(r"meeting|minutes", p):
        return "meeting_note", 0.55
    return "uncategorized", 0.3


def iter_project_folders(scan_root: Path) -> Iterator[Path]:
    for child in sorted(scan_root.iterdir()):
        if child.is_dir() and not child.name.startswith("."):
            if any(part in de.SKIP_PARTS for part in child.parts):
                continue
            yield child


def _should_skip_unchanged(cur, asset_id: str, checksum: str, mtime_iso: str | None) -> bool:
    cur.execute(
        """
        SELECT ka.asset_id, v.checksum_sha256, v.modified_at::text
        FROM platform.knowledge_assets ka
        JOIN platform.raw_asset_vault v ON v.asset_id = ka.asset_id
        WHERE ka.asset_id = %s AND ka.extraction_status IN ('extracted', 'metadata_only', 'unsupported');
        """,
        (asset_id,),
    )
    row = cur.fetchone()
    if not row:
        return False
    _, old_cs, old_mt = row
    return bool(checksum and old_cs == checksum and (not mtime_iso or old_mt == mtime_iso))


def _persist_sidecars(
    cur,
    *,
    asset_id: str,
    result: de.ExtractionResult,
    project_candidate_id: str | None,
    ai_category: str,
    confidence: float,
    abs_path: Path,
    relative_path: str,
) -> None:
    meta = result.metadata or {}
    extraction_status = de.vault_extraction_status(result)
    if result.errors and extraction_status != "unsupported":
        extraction_status = "failed" if extraction_status != "metadata_only" else extraction_status

    embedding_status = "disabled"
    if ENABLE_VECTORS and result.text:
        embedding_status = "pending"

    review_status = "needs_review" if ai_category == "uncategorized" else "raw"
    err_msg = "; ".join(result.errors)[:2000] if result.errors else None

    cur.execute(
        """
        INSERT INTO platform.knowledge_assets (
            asset_id, storage_root_id, absolute_path, relative_path, filename, extension,
            file_size, modified_at, detected_type, project_candidate_id, pipeline_stage_guess,
            user_category, ai_category, confidence_score, ingestion_status, extraction_status,
            review_status, embedding_status, chunking_status, chunk_count, error_message, metadata_json
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s::timestamptz, %s, %s, %s, NULL, %s, %s,
            'processed', %s, %s, %s, 'not_started', %s, %s, %s::jsonb
        )
        ON CONFLICT (asset_id) DO UPDATE SET
            absolute_path = EXCLUDED.absolute_path,
            relative_path = EXCLUDED.relative_path,
            detected_type = EXCLUDED.detected_type,
            project_candidate_id = COALESCE(EXCLUDED.project_candidate_id, platform.knowledge_assets.project_candidate_id),
            ai_category = EXCLUDED.ai_category,
            confidence_score = EXCLUDED.confidence_score,
            extraction_status = EXCLUDED.extraction_status,
            review_status = EXCLUDED.review_status,
            embedding_status = EXCLUDED.embedding_status,
            error_message = EXCLUDED.error_message,
            metadata_json = EXCLUDED.metadata_json,
            updated_at = now();
        """,
        (
            asset_id,
            STORAGE_ROOT_ID,
            str(abs_path),
            relative_path,
            abs_path.name,
            abs_path.suffix.lower(),
            result.size_bytes,
            result.modified_at,
            detect_file_type(abs_path),
            project_candidate_id,
            meta.get("pipeline_stage_guess"),
            ai_category,
            confidence,
            extraction_status,
            review_status,
            embedding_status,
            len(result.chunks or []),
            err_msg,
            _jsonb_dumps({**meta, "engine": "project_digitalization_engine"}),
        ),
    )

    if result.text and extraction_status not in ("metadata_only", "unsupported", "skipped"):
        cur.execute(
            """
            INSERT INTO platform.extracted_texts (
                asset_id, raw_text, cleaned_text, extraction_method, quality_score,
                char_count, word_count, language_guess, ocr_needed
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            """,
            (
                asset_id,
                result.text[:500_000],
                de._clean(result.text)[:500_000],
                result.extractor,
                float(meta.get("quality_score") or (0.8 if result.char_count > 50 else 0.3)),
                result.char_count,
                result.word_count,
                meta.get("language_guess"),
                bool(meta.get("ocr_needed") or (result.extension == ".pdf" and result.char_count < 20)),
            ),
        )

    sheets = meta.get("sheets") or meta.get("excel_sheets")
    if sheets and isinstance(sheets, list):
        for sheet in sheets[:20]:
            if not isinstance(sheet, dict):
                continue
            cur.execute(
                """
                INSERT INTO platform.extracted_tables (
                    asset_id, sheet_name, row_count, column_count, column_names,
                    column_types, preview_rows, missing_summary, schema_json
                ) VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb);
                """,
                (
                    asset_id,
                    sheet.get("name"),
                    sheet.get("rows"),
                    sheet.get("columns"),
                    json.dumps(sheet.get("column_names") or []),
                    json.dumps(sheet.get("column_types") or {}),
                    json.dumps(sheet.get("preview_rows") or []),
                    json.dumps(sheet.get("missing_summary") or {}),
                    json.dumps(sheet),
                ),
            )

    if meta.get("script_summary") or result.document_kind in ("script", "notebook"):
        ss = meta.get("script_summary") or meta
        cur.execute(
            """
            INSERT INTO platform.script_metadata (
                asset_id, language, imports, functions, classes, input_paths, output_paths,
                cli_args, software_names, pipeline_stage_guess, summary_json
            ) VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s::jsonb);
            """,
            (
                asset_id,
                ss.get("language") or meta.get("language"),
                json.dumps(ss.get("imports") or []),
                json.dumps(ss.get("functions") or []),
                json.dumps(ss.get("classes") or []),
                json.dumps(ss.get("input_paths") or []),
                json.dumps(ss.get("output_paths") or []),
                json.dumps(ss.get("cli_args") or []),
                json.dumps(ss.get("software_names") or []),
                ss.get("pipeline_stage_guess"),
                json.dumps(ss),
            ),
        )

    if meta.get("log_summary") or detect_file_type(abs_path) == "log":
        ls = meta.get("log_summary") or meta
        cur.execute(
            """
            INSERT INTO platform.log_summaries (
                asset_id, job_id, software_name, error_messages, warnings, status_guess,
                failed_command, output_paths, pipeline_stage_guess, summary_json
            ) VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s::jsonb, %s, %s::jsonb);
            """,
            (
                asset_id,
                ls.get("job_id"),
                ls.get("software_name"),
                json.dumps(ls.get("error_messages") or []),
                json.dumps(ls.get("warnings") or []),
                ls.get("status_guess", "unknown"),
                ls.get("failed_command"),
                json.dumps(ls.get("output_paths") or []),
                ls.get("pipeline_stage_guess"),
                json.dumps(ls),
            ),
        )

    if project_candidate_id:
        cur.execute(
            """
            INSERT INTO platform.relationship_candidates (
                from_asset_id, relation_type, confidence_score, metadata_json
            ) VALUES (%s, 'file_belongs_to_project', 0.85, %s::jsonb);
            """,
            (asset_id, json.dumps({"project_candidate_id": project_candidate_id})),
        )


def upsert_project_candidate(cur, project_dir: Path, scan_root: Path) -> str:
    rel = str(project_dir.relative_to(scan_root)).replace("\\", "/")
    pid = _project_candidate_id(project_dir.name)
    counts = {"folders": 0, "files": 0, "documents": 0, "data": 0, "scripts": 0, "images": 0, "logs": 0}
    for p in project_dir.rglob("*"):
        if any(part in de.SKIP_PARTS for part in p.parts):
            continue
        if p.is_dir():
            counts["folders"] += 1
        elif p.is_file():
            counts["files"] += 1
            dt = detect_file_type(p)
            if dt == "document":
                counts["documents"] += 1
            elif dt in ("spreadsheet", "dataset"):
                counts["data"] += 1
            elif dt in ("script", "notebook"):
                counts["scripts"] += 1
            elif dt in ("image", "image_data"):
                counts["images"] += 1
            elif dt == "log":
                counts["logs"] += 1

    cur.execute(
        """
        INSERT INTO platform.project_candidates (
            project_candidate_id, storage_root_id, project_name, project_path, relative_path,
            folder_count, file_count, document_count, data_count, script_count, image_count, log_count
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (project_candidate_id) DO UPDATE SET
            project_path = EXCLUDED.project_path,
            folder_count = EXCLUDED.folder_count,
            file_count = EXCLUDED.file_count,
            document_count = EXCLUDED.document_count,
            data_count = EXCLUDED.data_count,
            script_count = EXCLUDED.script_count,
            image_count = EXCLUDED.image_count,
            log_count = EXCLUDED.log_count,
            updated_at = now();
        """,
        (
            pid,
            STORAGE_ROOT_ID,
            project_dir.name,
            str(project_dir),
            rel,
            counts["folders"],
            counts["files"],
            counts["documents"],
            counts["data"],
            counts["scripts"],
            counts["images"],
            counts["logs"],
        ),
    )
    return pid


def run_digitalization(
    *,
    mode: str = "project",
    project_name: str | None = None,
    resume: bool = False,
    dry_run: bool = False,
    retry_failed: bool = False,
    max_files: int | None = None,
) -> dict[str, Any]:
    ensure_digitalization_schema()
    scan_root = lab_storage_root()
    if scan_root is None:
        roots = projects_roots_for_scan()
        if not roots:
            raise FileNotFoundError(
                "NEEDS_USER_DECISION: set LAB_STORAGE_ROOT to mounted project storage or PROJECTS_ROOT"
            )
        scan_root = roots[0]

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_dig_" + uuid.uuid4().hex[:8]
    counts: dict[str, int] = {
        "folders_scanned": 0,
        "files_scanned": 0,
        "files_processed": 0,
        "files_skipped": 0,
        "files_failed": 0,
        "documents_extracted": 0,
        "tables_extracted": 0,
        "scripts_extracted": 0,
        "logs_extracted": 0,
        "large_metadata_only": 0,
        "uncategorized": 0,
        "review_needed": 0,
        "unsupported": 0,
    }

    projects: list[Path] = []
    if mode == "project" and project_name:
        for root in projects_roots_for_scan() or [scan_root]:
            candidate = root / project_name
            if candidate.is_dir():
                projects = [candidate]
                scan_root = root
                break
        if not projects:
            raise FileNotFoundError(f"Project folder not found: {project_name}")
    else:
        projects = list(iter_project_folders(scan_root))

    checkpoint_key = f"digitalization:{project_name or 'full'}"

    with psycopg.connect(_db_conn(), connect_timeout=120) as conn:
        with conn.cursor() as cur:
            if not dry_run:
                cur.execute(
                    """
                    INSERT INTO platform.digitalization_runs (run_id, mode, storage_root, project_name, dry_run, status)
                    VALUES (%s, %s, %s, %s, %s, 'running');
                    """,
                    (run_id, mode, str(scan_root), project_name, dry_run),
                )
                conn.commit()

            resume_after: str | None = None
            if resume:
                from omeia.api.vault_ingestion_engine import _load_checkpoint

                cp = _load_checkpoint(cur, checkpoint_key)
                if cp:
                    resume_after = cp.get("last_logical_path")

            for project_dir in projects:
                if dry_run:
                    for _ in project_dir.rglob("*"):
                        if _.is_file():
                            counts["files_scanned"] += 1
                    continue

                pc_id = upsert_project_candidate(cur, project_dir, scan_root)
                for abs_path, logical in iter_scan_files(
                    project_dir,
                    resume_after=resume_after,
                    all_extensions=True,
                ):
                    if max_files and counts["files_scanned"] >= max_files:
                        break
                    counts["files_scanned"] += 1

                    stat = de._safe_stat(abs_path)
                    asset_id = stable_asset_id(logical, stat["size_bytes"])

                    try:
                        if stat["size_bytes"] > MAX_TEXT_MB * 1024 * 1024 and not de.is_vault_large_binary(abs_path):
                            result = de.ExtractionResult(
                                path=logical,
                                name=abs_path.name,
                                extension=abs_path.suffix.lower(),
                                document_kind="other",
                                mime_type=_guess_mime(abs_path),
                                size_bytes=stat["size_bytes"],
                                modified_at=stat.get("modified_at"),
                                status="skipped",
                                warnings=[f"file exceeds MAX_TEXT_FILE_MB={MAX_TEXT_MB}"],
                            )
                        else:
                            result = de.extract_for_vault(abs_path, project_dir)
                    except Exception as exc:
                        result = de.ExtractionResult(
                            path=logical,
                            name=abs_path.name,
                            extension=abs_path.suffix.lower(),
                            document_kind="other",
                            mime_type=_guess_mime(abs_path),
                            size_bytes=stat["size_bytes"],
                            modified_at=stat.get("modified_at"),
                            status="failed",
                            errors=[str(exc)],
                        )

                    checksum = result.sha256 or ""
                    if not retry_failed and _should_skip_unchanged(
                        cur, asset_id, checksum, stat.get("modified_at")
                    ):
                        counts["files_skipped"] += 1
                        continue

                    ext_status = de.vault_extraction_status(result)
                    ai_cat, conf = rule_category(abs_path, detect_file_type(abs_path))
                    if ENABLE_AI:
                        ai_cat = ai_cat  # hook for future LLM classify

                    vault_counts: dict[str, int] = {}
                    asset_id = upsert_vault_from_extraction(
                        cur,
                        logical_path=logical,
                        abs_path=abs_path,
                        project_hint=project_dir.name,
                        result=result,
                        counts=vault_counts,
                    )
                    _persist_sidecars(
                        cur,
                        asset_id=asset_id,
                        result=result,
                        project_candidate_id=pc_id,
                        ai_category=ai_cat,
                        confidence=conf,
                        abs_path=abs_path,
                        relative_path=logical,
                    )

                    counts["files_processed"] += 1
                    if ext_status == "failed":
                        counts["files_failed"] += 1
                        cur.execute(
                            """
                            INSERT INTO platform.digitalization_errors (run_id, asset_id, relative_path, error_message)
                            VALUES (%s, %s, %s, %s);
                            """,
                            (run_id, asset_id, logical, "; ".join(result.errors)[:1000]),
                        )
                    elif ext_status == "metadata_only":
                        counts["large_metadata_only"] += 1
                    elif ext_status == "unsupported":
                        counts["unsupported"] += 1
                    elif ext_status == "extracted":
                        counts["documents_extracted"] += 1
                    if result.metadata.get("sheets") or result.metadata.get("excel_sheets"):
                        counts["tables_extracted"] += 1
                    if result.metadata.get("script_summary"):
                        counts["scripts_extracted"] += 1
                    if result.metadata.get("log_summary"):
                        counts["logs_extracted"] += 1
                    if ai_cat == "uncategorized":
                        counts["uncategorized"] += 1
                        counts["review_needed"] += 1

                    if counts["files_processed"] % BATCH_SIZE == 0:
                        from omeia.api.vault_ingestion_engine import _save_checkpoint

                        _save_checkpoint(
                            cur,
                            checkpoint_id=checkpoint_key,
                            scan_root=str(scan_root),
                            project_hint=project_dir.name,
                            last_logical_path=logical,
                            files_processed=counts["files_processed"],
                            status="running",
                            manifest={"run_id": run_id, "counts": counts},
                            job_id=None,
                        )
                        conn.commit()

            if not dry_run:
                cur.execute(
                    """
                    UPDATE platform.digitalization_runs
                    SET status = 'completed', finished_at = now(), report_json = %s::jsonb
                    WHERE run_id = %s;
                    """,
                    (json.dumps({"counts": counts}), run_id),
                )
                conn.commit()

    report = {
        "run_id": run_id,
        "mode": mode,
        "storage_root": str(scan_root),
        "project_name": project_name,
        "dry_run": dry_run,
        "enable_ocr": ENABLE_OCR,
        "enable_vectors": ENABLE_VECTORS,
        "finished_at": _utc_now(),
        "counts": counts,
    }
    path = _write_report(run_id, report)
    report["report_path"] = str(path)
    return report


def search_knowledge(
    q: str,
    *,
    uncategorized_only: bool = False,
    limit: int = 50,
) -> list[dict[str, Any]]:
    ensure_digitalization_schema()
    pattern = f"%{q.strip()}%"
    clauses = [
        "(ka.filename ILIKE %s OR ka.relative_path ILIKE %s OR et.cleaned_text ILIKE %s OR et.raw_text ILIKE %s)",
    ]
    params: list[Any] = [pattern, pattern, pattern, pattern]
    if uncategorized_only:
        clauses.append("(ka.ai_category = 'uncategorized' OR ka.user_category IS NULL)")
    sql = f"""
        SELECT ka.asset_id, ka.filename, ka.relative_path, ka.detected_type,
               ka.ai_category, ka.extraction_status, ka.review_status,
               left(et.cleaned_text, 400) AS text_preview
        FROM platform.knowledge_assets ka
        LEFT JOIN LATERAL (
            SELECT cleaned_text, raw_text FROM platform.extracted_texts
            WHERE asset_id = ka.asset_id ORDER BY text_id DESC LIMIT 1
        ) et ON true
        WHERE {' AND '.join(clauses)}
        ORDER BY ka.updated_at DESC
        LIMIT %s;
    """
    params.append(limit)
    with psycopg.connect(_db_conn(), connect_timeout=30) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]


def list_review_queue(kind: str = "uncategorized", limit: int = 100) -> list[dict[str, Any]]:
    ensure_digitalization_schema()
    filters = {
        "uncategorized": "ka.ai_category = 'uncategorized' OR ka.review_status = 'needs_review'",
        "failed": "ka.extraction_status = 'failed'",
        "large_files": "ka.extraction_status = 'metadata_only'",
        "tables": "EXISTS (SELECT 1 FROM platform.extracted_tables t WHERE t.asset_id = ka.asset_id)",
        "texts": "EXISTS (SELECT 1 FROM platform.extracted_texts t WHERE t.asset_id = ka.asset_id)",
        "scripts": "EXISTS (SELECT 1 FROM platform.script_metadata s WHERE s.asset_id = ka.asset_id)",
        "logs": "EXISTS (SELECT 1 FROM platform.log_summaries l WHERE l.asset_id = ka.asset_id)",
        "projects": "TRUE",
    }
    where = filters.get(kind, filters["uncategorized"])
    with psycopg.connect(_db_conn(), connect_timeout=30) as conn:
        with conn.cursor() as cur:
            if kind == "projects":
                cur.execute(
                    """
                    SELECT project_candidate_id, project_name, project_path, file_count,
                           document_count, project_status, ai_category_status
                    FROM platform.project_candidates
                    ORDER BY updated_at DESC LIMIT %s;
                    """,
                    (limit,),
                )
            else:
                cur.execute(
                    f"""
                    SELECT ka.asset_id, ka.filename, ka.relative_path, ka.detected_type,
                           ka.ai_category, ka.extraction_status, ka.review_status, ka.error_message
                    FROM platform.knowledge_assets ka
                    WHERE {where}
                    ORDER BY ka.updated_at DESC LIMIT %s;
                    """,
                    (limit,),
                )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]


def patch_asset_review(
    asset_id: str,
    *,
    user_category: str | None = None,
    review_status: str | None = None,
    project_candidate_id: str | None = None,
) -> dict[str, Any]:
    ensure_digitalization_schema()
    updates: list[str] = []
    params: list[Any] = []
    if user_category and user_category in FILE_CATEGORIES:
        updates.append("user_category = %s")
        params.append(user_category)
    if review_status:
        updates.append("review_status = %s")
        params.append(review_status)
    if project_candidate_id:
        updates.append("project_candidate_id = %s")
        params.append(project_candidate_id)
    if not updates:
        return {"asset_id": asset_id, "updated": False}
    params.append(asset_id)
    with psycopg.connect(_db_conn(), connect_timeout=30) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE platform.knowledge_assets SET {', '.join(updates)}, updated_at = now() WHERE asset_id = %s;",
                params,
            )
            conn.commit()
    return {"asset_id": asset_id, "updated": True}

```

---

<a id="part-v--frontend-source-appendix"></a>

# Part V — Frontend source appendix

Full file copies as of audit date. Paths relative to repository root.

### `apps/web/src/components/GlobalSearchOverlay.jsx`

```javascript
import React, { useState, useEffect, useRef } from 'react';
import { Search, X, Book, FileText, Scale, CheckSquare, ChevronDown, ChevronUp } from 'lucide-react';
import { apiGet } from '../api/client.js';

export default function GlobalSearchOverlay({ isOpen, onClose, API_URL }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState({ notebook: [], wiki: [], decisions: [], tasks: [] });
  const [loading, setLoading] = useState(false);
  const [expandedItem, setExpandedItem] = useState(null); // { type, id }
  const inputRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 100);
      setQuery('');
      setResults({ notebook: [], wiki: [], decisions: [], tasks: [] });
      setExpandedItem(null);
    }
  }, [isOpen]);

  useEffect(() => {
    if (!query.trim()) {
      setResults({ notebook: [], wiki: [], decisions: [], tasks: [] });
      return;
    }

    const delayDebounce = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await apiGet('/platform/search', {
          params: new URLSearchParams({ q: query })
        });
        if (data) {
          setResults({
            notebook: data.notebook || [],
            wiki: data.wiki || [],
            decisions: data.decisions || [],
            tasks: data.tasks || []
          });
        }
      } catch (err) {
        console.error('Search failed:', err);
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => clearTimeout(delayDebounce);
  }, [query]);

  if (!isOpen) return null;

  const totalResults = results.notebook.length + results.wiki.length + results.decisions.length + results.tasks.length;

  const toggleExpand = (type, id) => {
    if (expandedItem?.type === type && expandedItem?.id === id) {
      setExpandedItem(null);
    } else {
      setExpandedItem({ type, id });
    }
  };

  return (
    <div className="search-overlay-backdrop" onClick={onClose}>
      <div className="search-overlay-card" onClick={(e) => e.stopPropagation()}>
        <div className="search-input-container">
          <Search size={22} className="text-muted" />
          <input
            ref={inputRef}
            type="text"
            className="search-input-field"
            placeholder="Search notebook, wiki, decisions, or tasks..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button className="search-close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="search-results-container">
          {loading && (
            <div className="search-empty">Searching lab registry...</div>
          )}

          {!loading && !query && (
            <div className="search-empty">Type to search database...</div>
          )}

          {!loading && query && totalResults === 0 && (
            <div className="search-empty">No matching records found.</div>
          )}

          {!loading && query && totalResults > 0 && (
            <>
              {results.notebook.length > 0 && (
                <div>
                  <div className="search-section-title">📓 Notebook Logs</div>
                  {results.notebook.map((item) => {
                    const isExpanded = expandedItem?.type === 'notebook' && expandedItem?.id === item.entry_id;
                    return (
                      <div key={item.entry_id} className="search-item" onClick={() => toggleExpand('notebook', item.entry_id)}>
                        <Book size={16} style={{ marginTop: '3px', color: 'var(--color-primary)' }} />
                        <div className="search-item-content">
                          <div className="search-item-title">{item.title}</div>
                          <div className="search-item-meta">Project: {item.project_code} · {item.created_at?.slice(0, 10)}</div>
                          <div className={`search-item-body ${isExpanded ? '' : 'clamped'}`}>
                            {item.content}
                          </div>
                          {isExpanded && item.conclusions && (
                            <div style={{ marginTop: '0.5rem', background: 'rgba(52,211,153,0.05)', padding: '0.5rem', borderRadius: '4px', fontSize: '0.8rem' }}>
                              <strong style={{ color: 'var(--color-success)' }}>Conclusions:</strong> {item.conclusions}
                            </div>
                          )}
                        </div>
                        <div className="expand-icon">
                          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {results.wiki.length > 0 && (
                <div>
                  <div className="search-section-title">📚 Wiki SOPs</div>
                  {results.wiki.map((item) => {
                    const isExpanded = expandedItem?.type === 'wiki' && expandedItem?.id === item.wiki_id;
                    return (
                      <div key={item.wiki_id} className="search-item" onClick={() => toggleExpand('wiki', item.wiki_id)}>
                        <FileText size={16} style={{ marginTop: '3px', color: 'var(--color-success)' }} />
                        <div className="search-item-content">
                          <div className="search-item-title">{item.title}</div>
                          <div className="search-item-meta">Category: {item.wiki_type} · Rev {item.revision || 1}</div>
                          <div className={`search-item-body ${isExpanded ? '' : 'clamped'}`} style={{ whiteSpace: isExpanded ? 'pre-wrap' : 'normal' }}>
                            {item.content}
                          </div>
                        </div>
                        <div className="expand-icon">
                          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {results.decisions.length > 0 && (
                <div>
                  <div className="search-section-title">⚖️ Decisions Ledger</div>
                  {results.decisions.map((item) => {
                    const isExpanded = expandedItem?.type === 'decision' && expandedItem?.id === item.decision_id;
                    return (
                      <div key={item.decision_id} className="search-item" onClick={() => toggleExpand('decision', item.decision_id)}>
                        <Scale size={16} style={{ marginTop: '3px', color: 'var(--color-accent)' }} />
                        <div className="search-item-content">
                          <div className="search-item-title">{item.title}</div>
                          <div className="search-item-meta">Project: {item.project_code} · {item.decision_date}</div>
                          <div className={`search-item-body ${isExpanded ? '' : 'clamped'}`}>
                            {item.decision_details}
                          </div>
                          {isExpanded && item.rationale && (
                            <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', opacity: 0.8 }}>
                              <strong>Rationale:</strong> {item.rationale}
                            </div>
                          )}
                        </div>
                        <div className="expand-icon">
                          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {results.tasks.length > 0 && (
                <div>
                  <div className="search-section-title">☑️ Lab Tasks</div>
                  {results.tasks.map((item) => {
                    const isExpanded = expandedItem?.type === 'task' && expandedItem?.id === item.task_id;
                    return (
                      <div key={item.task_id} className="search-item" onClick={() => toggleExpand('task', item.task_id)}>
                        <CheckSquare size={16} style={{ marginTop: '3px', color: 'var(--color-warning)' }} />
                        <div className="search-item-content">
                          <div className="search-item-title">{item.title}</div>
                          <div className="search-item-meta">Project: {item.project_code} · Status: <span style={{ textTransform: 'capitalize' }}>{item.status?.replace('_', ' ')}</span></div>
                          <div className={`search-item-body ${isExpanded ? '' : 'clamped'}`}>
                            {item.description}
                          </div>
                          {isExpanded && item.assignee && (
                            <div style={{ marginTop: '0.35rem', fontSize: '0.8rem', opacity: 0.8 }}>
                              <strong>Assignee:</strong> {item.assignee}
                            </div>
                          )}
                        </div>
                        <div className="expand-icon">
                          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

```

### `apps/web/src/screens/KnowledgeSearchScreen.jsx`

```javascript

import { useState } from 'react';
import { BookOpen, Search } from 'lucide-react';
import { apiGet } from '../api/client.js';

export default function KnowledgeSearchScreen({ title, description }) {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState('hybrid');
  const [labHits, setLabHits] = useState([]);
  const [vaultHits, setVaultHits] = useState([]);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const runSearch = async () => {
    const q = query.trim();
    if (q.length < 2) return;
    setBusy(true);
    setError(null);
    try {
      if (mode === 'hybrid-lab') {
        const data = await apiGet('/api/knowledge/hybrid-search', {
          params: new URLSearchParams({ q, limit: '15' }),
        });
        setLabHits(data.lab_results || []);
        setVaultHits(data.vault_results || []);
      } else {
        const data = await apiGet('/api/search', {
          params: new URLSearchParams({ q, mode: mode === 'hybrid-lab' ? 'hybrid' : mode, limit: '20' }),
        });
        setLabHits(data.lab_results || []);
        setVaultHits(data.vault_results || []);
      }
    } catch (e) {
      setError(String(e.message || e));
      setLabHits([]);
      setVaultHits([]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="stack-md">
      <div className="panel">
        <h3 className="panel-title">
          <BookOpen size={18} /> {title || 'Knowledge search'}
        </h3>
        <p className="panel-lead prose-block">
          {description || 'Unified lab index and vault metadata search via the platform API.'}
        </p>
        <div className="disk-pad-toolbar" style={{ marginTop: '0.75rem' }}>
          <input
            type="search"
            className="input"
            placeholder="Query protocols, documents, vault metadata…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && runSearch()}
          />
          <select className="input" value={mode} onChange={(e) => setMode(e.target.value)} aria-label="Search mode">
            <option value="hybrid">Hybrid (lab + vault)</option>
            <option value="hybrid-lab">Hybrid-search endpoint</option>
            <option value="semantic">Semantic (lab)</option>
            <option value="metadata">Metadata (vault)</option>
            <option value="exact">Exact</option>
          </select>
          <button type="button" className="btn btn-primary btn-sm" onClick={runSearch} disabled={busy}>
            <Search size={14} /> {busy ? 'Searching…' : 'Search'}
          </button>
        </div>
        {error && <p className="text-footnote citation-footnote" style={{ color: 'var(--color-danger)' }}>{error}</p>}
      </div>

      {labHits.length > 0 && (
        <div className="panel">
          <h4 className="text-title-3">Lab corpus ({labHits.length})</h4>
          <ul className="stack-sm" style={{ listStyle: 'none', padding: 0 }}>
            {labHits.map((h, i) => (
              <li key={h.section_id || h.path || i} className="text-footnote">
                <strong>{h.title || h.filename || h.section_id}</strong>
                {h.snippet && <span className="muted"> — {h.snippet.slice(0, 120)}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {vaultHits.length > 0 && (
        <div className="panel">
          <h4 className="text-title-3">Vault metadata ({vaultHits.length})</h4>
          <ul className="stack-sm" style={{ listStyle: 'none', padding: 0 }}>
            {vaultHits.map((h) => (
              <li key={h.asset_id} className="text-footnote">
                {h.filename} <span className="muted">— {h.logical_path}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

```

### `apps/web/src/components/DocumentFileSearch.jsx`

```javascript
import { Search } from 'lucide-react';

/** Compact file search for the module shell header (top-right). */
export default function DocumentFileSearch({
  value,
  onChange,
  fileCount,
  searchPlaceholder,
  searchAria,
  filesLabel,
  compact = false,
}) {
  return (
    <label
      className={`module-doc-search${compact ? ' module-doc-search--compact' : ''}`}
      aria-label={searchAria}
    >
      <Search size={compact ? 9 : 12} className="module-doc-search-icon" aria-hidden />
      <input
        type="search"
        className="module-doc-search-input"
        placeholder={searchPlaceholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      <span className="module-doc-search-count" title={filesLabel}>
        {fileCount}
      </span>
    </label>
  );
}

```

### `apps/web/src/utils/documentBrowserUtils.js`

```javascript
/** Shared helpers for lab document browsers (billing, overview, etc.). */

import { normalizeDocPath, normalizeRelPath } from './folderBrowserUtils.js';

/** Canonical lab corpus sections — preferred when the same path appears in multiple twins. */
const CANONICAL_SECTION_PRIORITY = {
  overview_documents: 90,
  overview_guidelines: 90,
  overview_onboarding: 90,
  overview_cleaning: 85,
  overview_personnel: 85,
  overview_research_materials: 80,
  orders_billing: 70,
  orders_archive: 70,
  meetings: 65,
  wet_lab_files: 60,
  social_misc: 50,
};

function documentRichnessScore(doc) {
  let score = 0;
  const excerpt = String(doc?.excerpt || doc?.summary || '');
  const inline = String(doc?.inlineContent || doc?.content || '');
  score += Math.min(excerpt.length, 8000);
  score += Math.min(inline.length, 12000) * 1.2;
  if (doc?.display_title) score += 12;
  if (doc?.document_id) score += 8;
  if (doc?.page_count) score += 4;
  const section = doc?.sourceSection || '';
  score += CANONICAL_SECTION_PRIORITY[section] || 0;
  return score;
}

/** Keep one record per normalized path, preferring richer metadata and canonical sections. */
export function deduplicateDocumentsByPath(docs) {
  const byPath = new Map();

  for (const doc of docs) {
    const key = normalizeDocPath(doc?.path);
    if (!key) continue;
    const existing = byPath.get(key);
    if (!existing) {
      byPath.set(key, doc);
      continue;
    }
    byPath.set(
      key,
      documentRichnessScore(doc) >= documentRichnessScore(existing) ? doc : existing,
    );
  }

  return [...byPath.values()];
}

const PROJECT_ASSET_KEYS = [
  'documents',
  'figures',
  'presentations',
  'data_files',
  'text_files',
  'videos',
  'code_scripts',
];

export function collectProjectDocuments(twin, { categorizePath, documentTitle, tabFilter }) {
  const lib = twin?.content_library;
  if (!lib?.sections?.length) return [];

  const indexByPath = new Map();
  for (const entry of twin?.document_index || []) {
    const p = normalizeRelPath(entry.path);
    if (p) indexByPath.set(p, entry);
  }

  const seen = new Set();
  const docs = [];

  for (const section of lib.sections) {
    for (const key of PROJECT_ASSET_KEYS) {
      for (const item of section[key] || []) {
        const path = normalizeRelPath(item.path);
        if (!path || seen.has(path)) continue;
        if (tabFilter && !tabFilter(path)) continue;
        seen.add(path);
        const indexed = indexByPath.get(path);
        const merged = { ...item, ...(indexed || {}), path, section_label: section.label };
        docs.push({
          ...merged,
          display_title: documentTitle(merged),
          categoryId: categorizePath(path),
          asset_bucket: item.asset_type || key,
        });
      }
    }
    for (const doc of section.documents || []) {
      const path = normalizeRelPath(doc.path);
      if (!path || seen.has(path)) continue;
      if (tabFilter && !tabFilter(path)) continue;
      seen.add(path);
      const indexed = indexByPath.get(path);
      const merged = { ...doc, ...(indexed || {}), path, section_label: section.label };
      docs.push({
        ...merged,
        display_title: documentTitle(merged),
        categoryId: categorizePath(path),
        asset_bucket: doc.asset_type || 'documents',
      });
    }
  }

  for (const entry of twin?.document_index || []) {
    const path = normalizeRelPath(entry.path || entry.relative_path);
    if (!path || seen.has(path)) continue;
    if (tabFilter && !tabFilter(path)) continue;
    seen.add(path);
    docs.push({
      ...entry,
      path,
      display_title: documentTitle({ ...entry, path }),
      categoryId: categorizePath(path),
      asset_bucket: entry.asset_type || 'document_index',
    });
  }

  return docs;
}

export function collectSectionDocuments(twin, { categorizePath, documentTitle }) {
  const lib = twin?.content_library;
  if (!lib?.sections?.length) return [];

  const indexByPath = new Map();
  for (const entry of twin?.document_index || []) {
    const p = (entry.path || '').replace(/\\/g, '/');
    if (p) indexByPath.set(p, entry);
  }

  const seen = new Set();
  const docs = [];

  for (const section of lib.sections) {
    for (const doc of section.documents || []) {
      const path = (doc.path || '').replace(/\\/g, '/');
      if (!path || seen.has(path)) continue;
      seen.add(path);
      const indexed = indexByPath.get(path);
      docs.push({
        ...doc,
        ...(indexed || {}),
        path,
        display_title: documentTitle({ path, ...doc, ...(indexed || {}) }),
        categoryId: categorizePath(path),
      });
    }
  }

  return docs;
}

export function groupDocumentsByCategory(docs, categoryOrder) {
  const grouped = Object.fromEntries(categoryOrder.map((id) => [id, []]));
  for (const doc of docs) {
    const cat = doc.categoryId || categoryOrder[0];
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(doc);
  }
  for (const id of Object.keys(grouped)) {
    grouped[id].sort((a, b) => (a.path || '').localeCompare(b.path || ''));
  }
  return grouped;
}

export function findCategoryMeta(categoryGroups, categoryId) {
  for (const group of categoryGroups) {
    const cat = group.categories.find((c) => c.id === categoryId);
    if (cat) return { ...cat, groupLabel: group.label };
  }
  return null;
}

export function flattenCategoryOrder(categoryGroups) {
  return categoryGroups.flatMap((g) => g.categories.map((c) => c.id));
}

/** Filter documents by search query (path + display title). */
export function filterDocsByQuery(docs, fileQuery, documentTitle) {
  const q = String(fileQuery || '').trim().toLowerCase();
  if (!q) return docs;
  return docs.filter((doc) => {
    const title = documentTitle(doc).toLowerCase();
    return doc.path.toLowerCase().includes(q) || title.includes(q);
  });
}

const MIN_CATEGORIES_FOR_TAB_ROW = 2;
const MIN_FILES_FOR_SUBFOLDER_TABS = 6;
const MIN_SUBFOLDERS_FOR_TAB_ROW = 2;

/**
 * Build navigable group → category structure with file counts (search-aware).
 */
export function buildDocumentCategoryBlocks(categoryGroups, grouped, fileQuery, documentTitle) {
  const blocks = [];

  for (const group of categoryGroups) {
    const categories = group.categories
      .map((cat) => {
        const files = filterDocsByQuery(grouped[cat.id] || [], fileQuery, documentTitle);
        if (!files.length) return null;
        return { cat, files };
      })
      .filter(Boolean);

    if (!categories.length) continue;

    blocks.push({
      groupId: group.id,
      groupLabel: group.label,
      categories,
      fileCount: categories.reduce((sum, { files }) => sum + files.length, 0),
    });
  }

  return blocks;
}

export function shouldShowGroupTabs(blocks) {
  return blocks.length > 1;
}

export function shouldShowCategoryTabs(categories, fileCount) {
  return categories.length >= MIN_CATEGORIES_FOR_TAB_ROW && fileCount >= 4;
}

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

export function extractSubfolderKey(path) {
  const parts = String(path || '').replace(/\\/g, '/').split('/').filter(Boolean);
  if (parts.length < 2) return null;
  return parts.length >= 3 ? parts[parts.length - 2] : parts[0];
}

function humanizeSubfolderLabel(folder) {
  return String(folder || '')
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatDayMonth(day, monthIndex, year) {
  const month = MONTH_NAMES[Math.max(0, Math.min(11, monthIndex - 1))];
  if (!month) return `${day} ${year}`.trim();
  return `${Number(day)} ${month} ${year}`.trim();
}

/** Turn raw folder names into human-friendly album titles. */
export function parseAlbumFolderName(folderId) {
  const raw = String(folderId || '').replace(/_/g, ' ').replace(/\s+/g, ' ').trim();
  const lower = raw.toLowerCase();

  const retreatMatch = lower.match(
    /(\d{1,2})[-\s](\d{1,2})\.(\d{1,2})\.?(\d{4})?\.?\s*(\d{4})?\s*lab\s*retreat\s*nuuksio/
  );
  if (retreatMatch) {
    const [, startDay, endDay, month, yearAttached, yearSpaced] = retreatMatch;
    const year = yearAttached || yearSpaced || (Number(month) >= 9 ? '2025' : '2024');
    const start = formatDayMonth(startDay, Number(month), year);
    const end = formatDayMonth(endDay, Number(month), year);
    return {
      title: 'Lab Retreat · Nuuksio',
      subtitle: start === end ? start : `${start} – ${end}`,
      kind: 'retreat',
      sortKey: `${year}-${month.padStart(2, '0')}-${startDay.padStart(2, '0')}`,
    };
  }

  if (/photoshoot/i.test(lower)) {
    const when = raw.match(/(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{4}/i);
    return {
      title: 'Lab Photoshoot',
      subtitle: when ? when[0] : raw.replace(/färkkilä lab photoshoot/i, '').trim() || null,
      kind: 'photoshoot',
      sortKey: when?.[0] || raw,
    };
  }

  if (/group photo/i.test(lower)) {
    const year = raw.match(/\b(20\d{2})\b/)?.[1];
    return {
      title: 'Group Photo',
      subtitle: year ? `Biomedicum · ${year}` : 'Team portrait',
      kind: 'group',
      sortKey: year || raw,
    };
  }

  if (/halloween/i.test(lower)) {
    return { title: 'Halloween Party', subtitle: null, kind: 'event', sortKey: raw };
  }

  if (/grilling/i.test(lower)) {
    return { title: 'Grilling Party', subtitle: null, kind: 'event', sortKey: raw };
  }

  const generic = humanizeSubfolderLabel(folderId);
  return { title: generic, subtitle: null, kind: 'folder', sortKey: generic };
}

/** Nested albums within a category — not top-level tabs. */
export function deriveSubfolderAlbums(files) {
  if (!files?.length) return [];

  const counts = new Map();
  for (const doc of files) {
    const key = extractSubfolderKey(doc.path);
    if (!key) continue;
    counts.set(key, (counts.get(key) || 0) + 1);
  }

  if (counts.size < MIN_SUBFOLDERS_FOR_TAB_ROW) return [];

  return [...counts.entries()]
    .map(([id, count]) => {
      const meta = parseAlbumFolderName(id);
      return {
        id,
        count,
        title: meta.title,
        subtitle: meta.subtitle,
        kind: meta.kind,
        sortKey: meta.sortKey || id,
      };
    })
    .sort((a, b) => String(b.sortKey).localeCompare(String(a.sortKey)));
}

/** @deprecated Use deriveSubfolderAlbums */
export function deriveSubfolderTabs(files) {
  return deriveSubfolderAlbums(files).map((album) => ({
    id: album.id,
    label: album.subtitle ? `${album.title} · ${album.subtitle}` : album.title,
    count: album.count,
  }));
}

export function filterFilesBySubfolder(files, subfolderId) {
  if (!subfolderId) return files;
  return files.filter((doc) => extractSubfolderKey(doc.path) === subfolderId);
}

```

### `apps/web/src/components/ChatWidget.jsx`

```javascript
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  Database,
  Layers,
  Loader2,
  RefreshCw,
  Send,
  Sparkles,
} from 'lucide-react';
import { apiFetch } from '../api/client.js';
import AiAssistant3DScene from './AiAssistant3DScene.jsx';

const WELCOME_MESSAGE = {
  id: 'assistant-welcome',
  role: 'assistant',
  content:
    'Hello! I am OMEIA Research Copilot. Ask me about staining methodology, spatial deconvolution parameters, ROI selection, Gate normalization, SPACEStat, Ashlar stitching, Stardist segmentation masks, or indexed lab documents.',
};

function makeMessage(role, content, extra = {}) {
  return {
    id: `${role}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    content,
    createdAt: new Date().toISOString(),
    ...extra,
  };
}

function normalizeProjectCode(project) {
  if (typeof project === 'string') return project;
  return project?.project_code || project?.code || project?.id || '';
}

function getDefaultProjects(dbProjects = []) {
  const codes = dbProjects.map(normalizeProjectCode).filter(Boolean);
  if (codes.includes('EyeMT')) return ['EyeMT'];
  if (codes.includes('SPACE')) return ['SPACE'];
  return codes.length ? [codes[0]] : ['EyeMT'];
}

function formatAssistantPayload(data) {
  const answer = data?.answer || 'No answer was returned by the copilot.';
  const sources = Array.isArray(data?.sources) ? data.sources : [];
  const limitations = Array.isArray(data?.limitations) ? data.limitations.filter(Boolean) : [];

  return {
    content: answer,
    sources,
    limitations,
    databaseCounts: data?.database_counts || {},
    isSafe: data?.is_safe !== false,
  };
}

function MarkdownLite({ text }) {
  const content = String(text || '');
  const lines = content.split('\n');

  return (
    <div className="chat-rich-text">
      {lines.map((line, index) => {
        const trimmed = line.trim();

        if (!trimmed) {
          return <div key={`space-${index}`} className="chat-rich-spacer" aria-hidden="true" />;
        }

        if (trimmed.startsWith('### ')) {
          return <h3 key={index}>{trimmed.replace(/^###\s+/, '')}</h3>;
        }

        if (trimmed.startsWith('## ')) {
          return <h2 key={index}>{trimmed.replace(/^##\s+/, '')}</h2>;
        }

        if (trimmed.startsWith('- ')) {
          return <p key={index} className="chat-rich-bullet">• {trimmed.slice(2)}</p>;
        }

        return <p key={index}>{line}</p>;
      })}
    </div>
  );
}

function SourceList({ sources }) {
  if (!sources?.length) return null;

  return (
    <details className="chat-sources">
      <summary>
        <Database size={13} aria-hidden="true" />
        Sources & citations
        <span>{sources.length}</span>
      </summary>

      <ol>
        {sources.map((source, index) => (
          <li key={`${source.chunk_id || source.title || 'source'}-${index}`}>
            <strong>{source.title || 'Untitled source'}</strong>
            {source.score !== undefined && source.score !== null ? (
              <span className="chat-source-score">
                score {Number(source.score).toFixed(3)}
              </span>
            ) : null}
            {source.text_preview ? <p>{source.text_preview}</p> : null}
          </li>
        ))}
      </ol>
    </details>
  );
}

function ProjectScopePicker({ projects, selected, onToggle }) {
  const options = projects.length
    ? projects
    : [{ project_code: 'EyeMT' }, { project_code: 'SPACE' }, { project_code: 'KRAS' }];

  return (
    <section className="assistant-scope-panel" aria-label="RAG scope project selection">
      <div className="assistant-scope-panel__header">
        <div>
          <span className="assistant-eyebrow">RAG scope</span>
          <h3>Project memory</h3>
        </div>
        <div className="assistant-scope-count">
          <Layers size={14} aria-hidden="true" />
          {selected.length || 0} active
        </div>
      </div>

      <div className="assistant-project-chip-grid">
        {options.map((project) => {
          const code = normalizeProjectCode(project);
          if (!code) return null;

          const checked = selected.includes(code);

          return (
            <label
              key={code}
              className={`assistant-project-chip${checked ? ' is-active' : ''}`}
            >
              <input
                type="checkbox"
                checked={checked}
                onChange={() => onToggle(code)}
              />
              <span>{code}</span>
            </label>
          );
        })}
      </div>
    </section>
  );
}

export default function ChatWidget({ dbProjects = [], API_URL }) {
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [selProjs, setSelProjs] = useState(() => getDefaultProjects(dbProjects));

  const projectCodes = useMemo(
    () => dbProjects.map(normalizeProjectCode).filter(Boolean),
    [dbProjects],
  );

  useEffect(() => {
    if (!selProjs.length) {
      setSelProjs(getDefaultProjects(dbProjects));
      return;
    }

    if (!projectCodes.length) return;

    setSelProjs((current) => {
      const stillValid = current.filter((code) => projectCodes.includes(code));
      return stillValid.length ? stillValid : getDefaultProjects(dbProjects);
    });
  }, [dbProjects, projectCodes, selProjs.length]);

  const toggleProject = useCallback((code) => {
    setSelProjs((current) => {
      if (current.includes(code)) {
        const next = current.filter((item) => item !== code);
        return next.length ? next : current;
      }

      return [...current, code];
    });
  }, []);

  const sendQuestion = useCallback(
    async (question, { appendUserMessage = true } = {}) => {
      const textToSend = String(question || '').trim();
      if (!textToSend || loading) return;

      if (appendUserMessage) {
        setMessages((prev) => [...prev, makeMessage('user', textToSend)]);
        setInput('');
      }

      setLoading(true);

      try {
        const data = await apiFetch('/ask', {
          method: 'POST',
          body: {
            question: textToSend,
            project_codes: selProjs,
            mode: 'documentation_only',
          },
        });

        const formatted = formatAssistantPayload(data);

        setMessages((prev) => [
          ...prev,
          makeMessage('assistant', formatted.content, {
            sources: formatted.sources,
            limitations: formatted.limitations,
            databaseCounts: formatted.databaseCounts,
            isSafe: formatted.isSafe,
          }),
        ]);
      } catch (error) {
        const isAuthError = error?.status === 401 || error?.status === 403;

        setMessages((prev) => [
          ...prev,
          makeMessage(
            'assistant',
            isAuthError
              ? 'Your session expired. Please sign in again.'
              : 'Connection timed out or API offline. You can retry this message without retyping it.',
            {
              isError: true,
              originalQuestion: textToSend,
              errorStatus: error?.status,
            },
          ),
        ]);
      } finally {
        setLoading(false);
      }
    },
    [loading, selProjs],
  );

  const handleSend = useCallback(
    (event) => {
      event?.preventDefault();
      sendQuestion(input);
    },
    [input, sendQuestion],
  );

  const retryMessage = useCallback(
    (question) => {
      sendQuestion(question, { appendUserMessage: false });
    },
    [sendQuestion],
  );

  const heroStats = useMemo(
    () => [
      { label: 'Mode', value: 'RAG' },
      { label: 'Scope', value: `${selProjs.length || 0}` },
      { label: 'Status', value: loading ? 'Thinking' : 'Ready' },
    ],
    [loading, selProjs.length],
  );

  return (
    <section className="assistant-chat-shell" aria-label="OMEIA Research Copilot">
      <AiAssistant3DScene
        title="OMEIA Research Copilot"
        subtitle="3D spatial-biology assistant for indexed protocols, lab knowledge, vector search, and analysis reasoning."
        stats={heroStats}
        compact
      />

      <ProjectScopePicker
        projects={dbProjects}
        selected={selProjs}
        onToggle={toggleProject}
      />

      <div className="chat-container assistant-chat-container">
        <div className="chat-messages assistant-chat-messages">
          {messages.map((message) => (
            <article
              key={message.id}
              className={`chat-bubble ${message.role} ${message.isError ? 'error-state' : ''}`}
            >
              <div className="chat-bubble__meta">
                <span>
                  {message.role === 'assistant' ? (
                    <>
                      <Sparkles size={13} aria-hidden="true" />
                      OMEIA
                    </>
                  ) : (
                    'You'
                  )}
                </span>
              </div>

              <MarkdownLite text={message.content} />

              {message.limitations?.length ? (
                <div className="chat-limitations">
                  <AlertTriangle size={13} aria-hidden="true" />
                  <span>{message.limitations.join(' ')}</span>
                </div>
              ) : null}

              <SourceList sources={message.sources} />

              {message.isError && message.originalQuestion ? (
                <button
                  type="button"
                  onClick={() => retryMessage(message.originalQuestion)}
                  className="btn btn-sm btn-secondary chat-retry-btn"
                  disabled={loading}
                >
                  <RefreshCw size={13} aria-hidden="true" />
                  Retry message
                </button>
              ) : null}
            </article>
          ))}

          {loading && (
            <article className="chat-bubble assistant assistant-thinking-bubble" aria-live="polite">
              <Loader2 size={15} className="spin" aria-hidden="true" />
              <span>Scanning vector collections, ranking sources, and composing answer…</span>
            </article>
          )}
        </div>

        <form onSubmit={handleSend} className="chat-input-area assistant-chat-input-area">
          <input
            type="text"
            placeholder="Ask about CycIF gating, SPACEStat, Ashlar, StarDist, GeoMx, protocols..."
            className="form-input assistant-chat-input"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            disabled={loading}
            aria-label="Ask OMEIA Research Copilot"
          />

          <button
            type="submit"
            className="btn btn-primary assistant-send-btn"
            disabled={loading || !input.trim()}
          >
            {loading ? <Loader2 size={16} className="spin" aria-hidden="true" /> : <Send size={16} aria-hidden="true" />}
            Send
          </button>
        </form>
      </div>
    </section>
  );
}

```

### `apps/web/src/api/client.js`

```javascript
/**
 * Shared API client — base URL from VITE_API_URL, Bearer token when available.
 */

import {
  AUTH_SKIP_HEADER_VALUE,
  isAuthSkipActive,
} from '../utils/authSkip.js';

const TOKEN_KEY = 'farkki_id_token';

export function getApiUrl() {
  // Dev: same-origin so Vite proxies /api → backend (works at localhost:5173 and LAN IP:5173).
  if (import.meta.env.DEV && typeof window !== 'undefined') {
    return '';
  }
  const fromEnv = import.meta.env.VITE_API_URL;
  if (fromEnv && String(fromEnv).trim()) {
    return String(fromEnv).replace(/\/$/, '');
  }
  if (typeof window !== 'undefined') {
    return `http://${window.location.hostname}:8000`;
  }
  return 'http://127.0.0.1:8000';
}

export function getAuthToken() {
  try {
    return window.localStorage.getItem(TOKEN_KEY) || null;
  } catch {
    return null;
  }
}

export function setAuthToken(token) {
  try {
    if (token) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    // ignore
  }
}

export function clearAuthToken() {
  setAuthToken(null);
}

export function apiUrl(path, params) {
  const base = getApiUrl();
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  const query = params ? `?${params.toString()}` : '';
  return `${base}${cleanPath}${query}`;
}

function buildHeaders(extra = {}, body) {
  const headers = { Accept: 'application/json', ...extra };
  const token = getAuthToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  else if (isAuthSkipActive()) headers['X-Platform-Auth-Skip'] = AUTH_SKIP_HEADER_VALUE;
  if (body !== undefined && body !== null && !(body instanceof FormData)) {
    if (!headers['Content-Type']) headers['Content-Type'] = 'application/json';
  }
  return headers;
}

export async function apiFetch(path, options = {}) {
  const { params, timeoutMs = 30_000, signal: parentSignal, body, ...rest } = options;
  const url = apiUrl(path, params);
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  const onParentAbort = () => controller.abort(parentSignal?.reason);
  if (parentSignal) {
    if (parentSignal.aborted) onParentAbort();
    else parentSignal.addEventListener('abort', onParentAbort, { once: true });
  }

  const init = {
    ...rest,
    signal: controller.signal,
    headers: buildHeaders(rest.headers, body),
  };
  if (body !== undefined) {
    init.body = body instanceof FormData || typeof body === 'string' ? body : JSON.stringify(body);
  }

  try {
    const response = await fetch(url, init);
    const contentType = response.headers.get('content-type') || '';
    const isJson = contentType.includes('application/json');
    const data = isJson ? await response.json().catch(() => null) : null;
    if (!response.ok) {
      const detail = data?.detail ?? data?.message ?? response.statusText;
      const err = new Error(typeof detail === 'string' ? detail : `${response.status} ${response.statusText}`);
      err.status = response.status;
      err.data = data;
      throw err;
    }
    return data;
  } finally {
    window.clearTimeout(timeout);
    parentSignal?.removeEventListener?.('abort', onParentAbort);
  }
}

export async function apiGet(path, options = {}) {
  return apiFetch(path, { ...options, method: 'GET' });
}

export async function apiPost(path, options = {}) {
  return apiFetch(path, { ...options, method: 'POST' });
}

export async function apiPatch(path, options = {}) {
  return apiFetch(path, { ...options, method: 'PATCH' });
}

export async function apiPut(path, options = {}) {
  return apiFetch(path, { ...options, method: 'PUT' });
}

export async function apiDelete(path, options = {}) {
  return apiFetch(path, { ...options, method: 'DELETE' });
}

```

### `apps/web/src/App.jsx`

```javascript
import React, { lazy, Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import Sidebar from './components/Sidebar';
import ModuleShell from './components/ModuleShell';
import ErrorBoundary from './components/ErrorBoundary';
import DashboardScreen from './screens/DashboardScreen';
import GlobalSearchOverlay from './components/GlobalSearchOverlay';
import ProjectsScreen from './screens/ProjectsScreen';
import NotebookWikiScreen from './screens/NotebookWikiScreen';
import DecisionsScreen from './screens/DecisionsScreen';
import TasksScreen from './screens/TasksScreen';
import BioinformaticsHubScreen from './screens/BioinformaticsHubScreen';
import AiLabAssistantScreen from './screens/AiLabAssistantScreen';
import FeatureClinicalScreen from './screens/FeatureClinicalScreen';
import LabKnowledgeScreen from './screens/LabKnowledgeScreen';
const DataStorageScreen = lazy(() => import('./screens/DataStorageScreen'));
import AdministrationScreen from './screens/AdministrationScreen';
import IngestionDashboard from './screens/IngestionDashboard';
import DigitalizationDashboard from './screens/DigitalizationDashboard';
import KnowledgeSearchScreen from './screens/KnowledgeSearchScreen';
import LabCorpusBrowser from './components/LabCorpusBrowser.jsx';
import { getApiUrl, apiFetch } from './api/client.js';
import { useApiContext } from './api/ApiContext.jsx';
import CycifScreen from './screens/CycifScreen';
import { TaskpadProvider } from './contexts/TaskpadContext.jsx';
import TaskpadSheet from './components/TaskpadSheet.jsx';
import { CENTRAL_WORKER_ID, TASKPAD_SCOPES } from './utils/taskpadRegistry.js';

import {
  OrdersTasksPanel,
  OrdersRegisterPanel,
  OrdersRelatedPanel,
  OrdersBillingPanel,
  OrdersArchivePanel,
} from './screens/OrdersHubScreen';
import OverviewDocumentsScreen from './screens/OverviewDocumentsScreen.jsx';
import SectionDocumentsScreen from './screens/SectionDocumentsScreen.jsx';
import { getSectionDocumentsConfig } from './utils/sectionDocumentsConfig.js';
import {
  WetLabProtocolsPanel,
  WetLabTasksPanel,
  WetLabInventoryPanel,
} from './screens/WetLabScreen';
import { projectsCatalog } from './data/projectsCatalog.js';
import { teamDirectory } from './data/teamDirectory.js';
import { activityLogs } from './data/activityLogs.js';
import { platformStats } from './data/platformStats.js';
import { mergeProjectRecord } from './utils/projectUtils.js';
import {
  COMPUTATIONAL_LEGACY_NESTED,
  findMainNav,
  findSubNav,
  parseNavFromStorage,
} from './config/navigation';
import { useGuiT } from './i18n/useGuiT.js';
import { initFirebaseAnalytics } from './config/firebase.js';
import LoginScreen from './screens/LoginScreen.jsx';
import './App.css';

const DEFAULT_PROJECT_CODES = Object.freeze(['SPACE', 'EyeMT', 'KRAS']);
const DEFAULT_STATS = Object.freeze({
  patient_count: 0,
  sample_count: 0,
  project_samples: {},
});

const NAV_STORAGE_KEY = 'farkki_nav_v2';

const API_URL = getApiUrl();

function safeStorageGet(key, fallback) {
  try {
    return window.localStorage.getItem(key) || fallback;
  } catch {
    return fallback;
  }
}

function safeStorageSet(key, value) {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // ignore
  }
}

function resolveComputationalNav(raw) {
  if (raw.main === 'computational' && raw.sub === 'utilities' && raw.hubNested === 'tools') {
    return { main: raw.main, sub: 'tools', hubNested: null };
  }
  const legacy = COMPUTATIONAL_LEGACY_NESTED[raw.sub];
  if (raw.main === 'computational' && legacy) {
    return { main: raw.main, sub: legacy.tab, hubNested: legacy.section };
  }
  if (raw.main === 'computational' && raw.sub === 'tools') {
    return { main: raw.main, sub: 'tools', hubNested: null };
  }
  return { main: raw.main, sub: raw.sub, hubNested: null };
}

function migrateLegacyNav(stored) {
  const legacy = parseNavFromStorage(stored);
  if (legacy) {
    if (
      legacy.main === 'overview' &&
      (legacy.sub === 'dashboard' || legacy.sub === 'research')
    ) {
      return { main: 'overview', sub: 'get_started' };
    }
    return legacy;
  }
  const map = {
    dashboard: { main: 'overview', sub: 'get_started' },
    projects: { main: 'projects_data', sub: 'portfolio' },
    notebook: { main: 'projects_data', sub: 'notebook' },
    chat: { main: 'ai_assistant', sub: 'copilot' },
    decisions: { main: 'projects_data', sub: 'decisions' },
    tasks: { main: 'projects_data', sub: 'portfolio' },
    bioinformatics: { main: 'computational', sub: 'onboarding' },
    features: { main: 'projects_data', sub: 'features' },
    ai_assistant: { main: 'ai_assistant', sub: 'prompts' },
  };
  return map[stored] || { main: 'overview', sub: 'get_started' };
}

function normalizeProjectCodes(value) {
  const list = Array.isArray(value) ? value : DEFAULT_PROJECT_CODES;
  const seen = new Set();
  return list
    .map((code) => String(code || '').trim())
    .filter(Boolean)
    .filter((code) => {
      const key = code.toUpperCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
}

async function fetchJson(path, { signal, timeoutMs = 12_000, params } = {}) {
  return apiFetch(path, { signal, timeoutMs, params });
}

function mergeProjectsWithCatalog(remoteProjects = []) {
  const remote = Array.isArray(remoteProjects) ? remoteProjects : [];
  const merged = remote.map((project) => mergeProjectRecord(project));
  const seen = new Set(merged.map((project) => project.project_code));
  for (const catalogProject of projectsCatalog) {
    if (!seen.has(catalogProject.project_code)) {
      merged.push(mergeProjectRecord(catalogProject));
    }
  }
  return merged.sort((a, b) => (a.project_index || 999) - (b.project_index || 999));
}

function App() {
  const {
    API_URL: contextApiUrl,
    authReady,
    isAuthenticated,
    authDisabled,
    firebaseAuthEnabled,
    onAuthToken,
    authUser,
    userProfile,
    signOut,
  } = useApiContext();
  const { t, nav } = useGuiT();
  const resolvedApiUrl = contextApiUrl || API_URL;
  const initialResolved = resolveComputationalNav(migrateLegacyNav(safeStorageGet(NAV_STORAGE_KEY, '')));
  const [navMain, setNavMain] = useState(initialResolved.main);
  const [navSub, setNavSub] = useState(initialResolved.sub);
  const [sidebarExpandedMain, setSidebarExpandedMain] = useState(null);
  const [hubNestedSection, setHubNestedSection] = useState(initialResolved.hubNested);
  const [selectedProject, setSelectedProject] = useState(null);
  const [dbProjects, setDbProjects] = useState(() => mergeProjectsWithCatalog(projectsCatalog));
  const [projectCodes, setProjectCodesState] = useState(DEFAULT_PROJECT_CODES);
  const [stats, setStats] = useState(platformStats || DEFAULT_STATS);
  const [team, setTeam] = useState(teamDirectory || []);
  const [auditLogs, setAuditLogs] = useState(activityLogs || []);
  const [loadState, setLoadState] = useState({ phase: 'idle' });
  const [apiHealth, setApiHealth] = useState(null);
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setIsSearchOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const activeTitle = nav.sectionTitle(navMain, navSub);
  const isLoading = loadState.phase === 'loading' || loadState.phase === 'refreshing';
  const subNav = findSubNav(navMain, navSub);
  const localizedSub = nav.findSub(navMain, navSub);
  const loadMessage = useMemo(() => {
    if (loadState.phase === 'loading' || loadState.phase === 'refreshing') {
      return t('common.syncing');
    }
    if (loadState.phase === 'ready') return t('common.projectsSynced');
    if (loadState.phase === 'warning') return t('common.syncWarning');
    return t('common.ready');
  }, [loadState.phase, t]);

  const setProjectCodes = useCallback((nextValue) => {
    setProjectCodesState((previous) => {
      const resolved = typeof nextValue === 'function' ? nextValue(previous) : nextValue;
      const normalized = normalizeProjectCodes(resolved);
      return normalized.length ? normalized : [...DEFAULT_PROJECT_CODES];
    });
  }, []);

  const resetProject = useCallback(() => setSelectedProject(null), []);

  const handleNavChange = useCallback((main, sub) => {
    const mainItem = findMainNav(main);
    let subId = sub || mainItem.defaultSub;
    let nested = null;
    if (mainItem.id === 'computational') {
      const legacy = COMPUTATIONAL_LEGACY_NESTED[subId];
      if (legacy) {
        nested = legacy.section;
        subId = legacy.tab;
      }
    }
    setNavMain(mainItem.id);
    setNavSub(subId);
    setHubNestedSection(nested);
    setSidebarExpandedMain(mainItem.id);
    if (!mainItem.keepsProject) setSelectedProject(null);
  }, []);

  const handleMainNavClick = useCallback((main) => {
    const mainItem = findMainNav(main);
    if (main === navMain && sidebarExpandedMain === main) {
      setSidebarExpandedMain(null);
      return;
    }
    if (main === navMain) {
      setSidebarExpandedMain(main);
      return;
    }
    handleNavChange(main, mainItem.defaultSub);
  }, [navMain, sidebarExpandedMain, handleNavChange]);

  const commonProps = useMemo(() => ({ dbProjects, API_URL: resolvedApiUrl }), [dbProjects, resolvedApiUrl]);

  const fetchProjects = useCallback(async (signal) => {
    const data = await fetchJson('/projects', { signal, timeoutMs: 14_000 });
    if (Array.isArray(data) && data.length > 0) {
      setDbProjects(mergeProjectsWithCatalog(data));
    } else {
      setDbProjects(mergeProjectsWithCatalog(projectsCatalog));
    }
  }, []);

  const refreshReferenceData = useCallback(async (signal, phase = 'refreshing') => {
    setLoadState({ phase });
    try {
      await fetchProjects(signal);
      setLoadState({ phase: 'ready' });
    } catch (err) {
      setLoadState({ phase: 'warning' });
    }
  }, [fetchProjects]);

  const renderScreenBody = () => {
    const screen = subNav.screen;

    switch (screen) {
      case 'dashboard':
        return (
          <DashboardScreen
            stats={stats}
            team={team}
            auditLogs={auditLogs}
            projectCodes={projectCodes}
            setProjectCodes={setProjectCodes}
            dbProjects={dbProjects}
            API_URL={resolvedApiUrl}
            hideHeader
            onNavigate={handleNavChange}
          />
        );
      case 'lab_knowledge':
        if (navMain === 'overview') {
          return (
            <OverviewDocumentsScreen
              subId={navSub}
              title={localizedSub.label}
              description={localizedSub.description}
              onSubChange={(sub) => handleNavChange('overview', sub)}
              onNavigate={handleNavChange}
              onRefresh={handleManualRefresh}
              isRefreshing={isLoading}
            />
          );
        }
        if (getSectionDocumentsConfig(navMain, navSub)) {
          // overview, social, wet_lab, cycif document-backed tabs
          return (
            <SectionDocumentsScreen
              mainId={navMain}
              subId={navSub}
              title={localizedSub.label}
              description={localizedSub.description}
            />
          );
        }
        return (
          <LabKnowledgeScreen
            subId={navSub}
            navSub={subNav}
            API_URL={resolvedApiUrl}
            title={localizedSub.label}
            description={localizedSub.description}
          />
        );
      case 'data_storage':
        return (
          <Suspense fallback={<div className="panel module-loading-fallback">Loading data &amp; storage…</div>}>
            <DataStorageScreen
              key={`data-storage-${navSub}`}
              title={localizedSub.label}
              description={localizedSub.description}
              section={subNav.dataSection || navSub || 'landscape'}
              onNavigate={handleNavChange}
            />
          </Suspense>
        );
      case 'digitalization':
        return (
          <DigitalizationDashboard title={subNav.label} description={subNav.description} />
        );
      case 'ingestion_dashboard':
        return (
          <IngestionDashboard title={subNav.label} description={subNav.description} />
        );
      case 'knowledge_search':
        return (
          <KnowledgeSearchScreen title={subNav.label} description={subNav.description} />
        );
      case 'lab_corpus':
        return (
          <LabCorpusBrowser title={subNav.label} description={subNav.description} />
        );
      case 'administration':
        return (
          <AdministrationScreen
            title={localizedSub.label}
            description={localizedSub.description}
            onNavigate={handleNavChange}
          />
        );
      case 'tasks':
        return <OrdersTasksPanel {...commonProps} hideHeader />;
      case 'orders_billing':
        return <OrdersBillingPanel API_URL={resolvedApiUrl} />;
      case 'orders_archive':
        return <OrdersArchivePanel />;
      case 'orders_register':
        return <OrdersRegisterPanel />;
      case 'orders_related':
        return <OrdersRelatedPanel auditLogs={auditLogs} />;
      case 'projects':
        return (
          <ProjectsScreen
            dbProjects={dbProjects}
            selectedProject={selectedProject}
            setSelectedProject={setSelectedProject}
            fetchProjects={() => refreshReferenceData(new AbortController().signal)}
            API_URL={API_URL}
          />
        );
      case 'notebook':
        return <NotebookWikiScreen {...commonProps} hideHeader />;
      case 'decisions':
        return <DecisionsScreen {...commonProps} hideHeader />;
      case 'features':
        return <FeatureClinicalScreen {...commonProps} hideHeader />;
      case 'wet_protocols':
        return <WetLabProtocolsPanel API_URL={resolvedApiUrl} />;
      case 'wet_tasks':
        return <WetLabTasksPanel {...commonProps} hideHeader categoryFilter="Wet_Lab" />;
      case 'wet_inventory':
        return <WetLabInventoryPanel />;
      case 'cycif_pipeline':
        return <CycifScreen {...commonProps} variant="pipeline" embedded />;
      case 'cycif_install':
        return <CycifScreen {...commonProps} variant="install" embedded />;
      case 'cycif_structure':
        return <CycifScreen {...commonProps} variant="structure" embedded />;
      case 'cycif_knowledge':
        return <CycifScreen {...commonProps} variant="knowledge" embedded />;
      case 'bioinformatics':
        return (
          <BioinformaticsHubScreen
            key={`bio-${navSub}-${hubNestedSection || 'root'}`}
            {...commonProps}
            activeSubTab={subNav.bioSub || navSub}
            hubNestedSection={hubNestedSection}
            hideChrome
            onNavigate={handleNavChange}
          />
        );
      case 'computational_tools':
        return (
          <BioinformaticsHubScreen
            {...commonProps}
            activeSubTab="tools"
            hideChrome
            onNavigate={handleNavChange}
          />
        );
      case 'chat':
        return (
          <AiLabAssistantScreen
            {...commonProps}
            activeSubTab="copilot"
            hideChrome
          />
        );
      case 'ai_assistant':
        return (
          <AiLabAssistantScreen
            {...commonProps}
            activeSubTab={subNav.aiSub || navSub}
            hideChrome
          />
        );
      default:
        return null;
    }
  };

  const handleManualRefresh = useCallback(() => {
    refreshReferenceData(new AbortController().signal, 'refreshing');
  }, [refreshReferenceData]);

  useEffect(() => {
    initFirebaseAnalytics();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    apiFetch('/health', { signal: controller.signal, timeoutMs: 8_000 })
      .then((data) => {
        if (data?.status === 'ok') {
          setApiHealth(data);
        } else {
          setApiHealth({ status: 'unreachable', database_connected: false });
        }
      })
      .catch(() => setApiHealth({ status: 'unreachable', database_connected: false }));
    return () => controller.abort();
  }, [resolvedApiUrl]);

  useEffect(() => {
    document.title = `${activeTitle} · ${t('common.documentTitleSuffix')}`;
  }, [activeTitle, t]);

  useEffect(() => {
    safeStorageSet(NAV_STORAGE_KEY, `${navMain}:${navSub}`);
  }, [navMain, navSub]);

  useEffect(() => {
    const controller = new AbortController();
    refreshReferenceData(controller.signal, 'loading');
    return () => controller.abort();
  }, [refreshReferenceData]);



  const requireLogin = firebaseAuthEnabled && !authDisabled;

  if (firebaseAuthEnabled && !authReady) {
    return (
      <div className="auth-boot-screen" role="status" aria-live="polite">
        <p>{t('common.syncing')}</p>
      </div>
    );
  }

  if (requireLogin && authReady && !isAuthenticated) {
    return <LoginScreen onAuthenticated={onAuthToken} />;
  }

  const displayUser =
    userProfile?.name ||
    authUser?.displayName ||
    (authUser?.email ? authUser.email.split('@')[0] : null) ||
    'Guest';

  const useModuleShell = navMain !== 'projects_data' || navSub !== 'portfolio' || !selectedProject;
  const useWideContentShell = navMain === 'data_storage' && navSub === 'documents';

  const activeScreen = useModuleShell ? (
    <ModuleShell
      mainId={navMain}
      subId={navSub}
      onSubChange={(sub) => handleNavChange(navMain, sub)}
      onRefresh={handleManualRefresh}
      isRefreshing={isLoading}
      compact={navMain === 'computational'}
      landing
    >
      {renderScreenBody()}
    </ModuleShell>
  ) : (
    renderScreenBody()
  );

  return (
    <TaskpadProvider>
      <div className="app-container" data-loading={isLoading ? 'true' : 'false'}>
        <a className="skip-link" href="#main-content">
          {t('common.skipToWorkspace')}
        </a>

      <Sidebar
        navMain={navMain}
        navSub={navSub}
        sidebarExpandedMain={sidebarExpandedMain}
        onNavChange={handleNavChange}
        onMainNavClick={handleMainNavClick}
        onResetProject={resetProject}
        apiHealth={apiHealth}
        apiUrl={resolvedApiUrl}
        onOpenSearch={() => setIsSearchOpen(true)}
        userLabel={displayUser}
        userEmail={authUser?.email || userProfile?.email}
        onSignOut={requireLogin ? signOut : null}
      />

      <main
        id="main-content"
        className="main-content"
        tabIndex={-1}
        aria-busy={isLoading}
        aria-labelledby="app-current-section"
      >
        <div className={`app-content-shell${useWideContentShell ? ' app-content-shell--wide' : ''}`}>
          <span className="sr-only" id="app-current-section" role="status" aria-live="polite">
            {activeTitle} — {loadMessage}
          </span>
          {!useModuleShell ? (
            <button
              type="button"
              className="app-refresh-fab"
              onClick={handleManualRefresh}
              disabled={isLoading}
              aria-label={isLoading ? t('common.syncing') : t('common.refreshAria')}
              title={isLoading ? t('common.syncing') : t('common.refresh')}
            >
              <RefreshCw size={15} className={isLoading ? 'spin' : undefined} aria-hidden />
            </button>
          ) : null}

          <ErrorBoundary>{activeScreen}</ErrorBoundary>
        </div>
      </main>

        <GlobalSearchOverlay
          isOpen={isSearchOpen}
          onClose={() => setIsSearchOpen(false)}
          API_URL={resolvedApiUrl}
        />

        <div className="app-central-taskpad-host" aria-live="polite">
          <TaskpadSheet scope={TASKPAD_SCOPES.CENTRAL} workerId={CENTRAL_WORKER_ID} />
        </div>
      </div>
    </TaskpadProvider>
  );
}

export default App;

```

### `apps/web/src/components/Sidebar.jsx`

```javascript
import React, { useMemo } from 'react';
import {
  ChevronDown,
  Dna,
  GitBranch,
  LogOut,
  Moon,
  Search,
  Sun,
} from 'lucide-react';
import LanguageSwitcher from './LanguageSwitcher.jsx';
import { useGuiT } from '../i18n/useGuiT.js';
import { useTaskpad } from '../contexts/TaskpadContext.jsx';
import { useTheme } from '../contexts/ThemeContext.jsx';

function getInitials(label = 'Guest') {
  return label
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('') || 'G';
}

export default function Sidebar({
  navMain,
  navSub,
  sidebarExpandedMain = null,
  onNavChange,
  onMainNavClick,
  apiHealth,
  onOpenSearch,
  userLabel = 'Guest',
  userEmail = null,
  onSignOut = null,
}) {
  const { t, nav } = useGuiT();
  const { openCentralTaskpad } = useTaskpad();
  const { theme: activeTheme, cycleTheme, availableThemes, themeMeta } = useTheme();

  const activeMain = navMain;
  const currentIndex = availableThemes.indexOf(activeTheme);
  const nextTheme = availableThemes[(currentIndex + 1) % availableThemes.length];

  const currentThemeMeta = themeMeta[activeTheme] || themeMeta.dark;
  const nextThemeMeta = themeMeta[nextTheme] || themeMeta.dark;
  const CurrentThemeIcon = currentThemeMeta.icon;

  const apiStatus = useMemo(() => {
    if (!apiHealth) {
      return {
        label: 'Offline',
        tone: 'muted',
      };
    }

    if (apiHealth.ok || apiHealth.status === 'ok' || apiHealth.status === 'healthy') {
      return {
        label: 'Online',
        tone: 'success',
      };
    }

    if (apiHealth.status === 'degraded') {
      return {
        label: 'Degraded',
        tone: 'warning',
      };
    }

    return {
      label: 'Check',
      tone: 'danger',
    };
  }, [apiHealth]);

  const handleThemeToggle = () => {
    cycleTheme();
  };

  return (
    <aside className="sidebar" aria-label={t('common.mainNavAria')}>
      <header className="sidebar-header">
        <div className="sidebar-brand">
          <div className="sidebar-logo-mark" aria-hidden="true">
            <Dna size={17} strokeWidth={2.25} />
          </div>

          <div className="sidebar-logo-copy">
            <span className="sidebar-eyebrow">{t('common.appOrg')}</span>
            <span className="sidebar-title">{t('common.appLabName')}</span>
          </div>
        </div>

        <button
          type="button"
          className="sidebar-search-btn"
          onClick={onOpenSearch}
          aria-label={t('common.searchRegistry')}
        >
          <Search size={14} className="sidebar-search-icon" aria-hidden="true" />
          <span className="sidebar-search-label">{t('common.searchRegistry')}</span>
          <kbd className="sidebar-search-kbd">⌘K</kbd>
        </button>
      </header>

      <nav className="sidebar-menu" aria-label={t('common.mainNavAria')}>
        {nav.mainNav.map((item) => {
          const Icon = item.icon;
          const isActive = activeMain === item.id;
          const hasChildren = item.children?.length > 1;
          const isExpanded = sidebarExpandedMain === item.id;
          const showChildren = isExpanded && hasChildren;
          const handleMainClick = onMainNavClick || ((main) => onNavChange(main, item.defaultSub));

          return (
            <div
              key={item.id}
              className={`sidebar-group${isExpanded ? ' sidebar-group--active' : ''}${isActive ? ' sidebar-group--current' : ''}`}
            >
              <button
                type="button"
                className={`sidebar-item sidebar-item-main${isActive ? ' active' : ''}${isExpanded ? ' expanded' : ''}`}
                aria-current={isActive && !showChildren ? 'page' : undefined}
                aria-expanded={hasChildren ? isExpanded : undefined}
                onClick={() => handleMainClick(item.id)}
              >
                <span
                  className={`sidebar-item-icon sidebar-item-icon--${item.id}`}
                  aria-hidden="true"
                >
                  <Icon size={17} strokeWidth={2.1} />
                </span>
                <span className="sidebar-item-label">{item.sidebarLabel || item.label}</span>
                {hasChildren ? (
                  <ChevronDown
                    size={14}
                    className="sidebar-item-chevron"
                    aria-hidden="true"
                  />
                ) : null}
              </button>

              {showChildren ? (
                <div className="sidebar-subnav-wrap">
                  <p className="sidebar-subnav-heading">{t('common.sectionPages')}</p>
                  <ul className="sidebar-subnav" aria-label={t('common.sectionTabsAria')}>
                    {item.children.map((child) => {
                      const childActive = navSub === child.id;
                      const childLabel = child.sidebarLabel || child.label;
                      return (
                        <li key={child.id} className="sidebar-subnav-item">
                          <button
                            type="button"
                            className={`sidebar-item sidebar-item-sub${childActive ? ' active' : ''}`}
                            aria-current={childActive ? 'page' : undefined}
                            onClick={() => onNavChange(item.id, child.id)}
                            title={child.label}
                          >
                            <span className="sidebar-subnav-dot" aria-hidden="true" />
                            <span className="sidebar-item-label">{childLabel}</span>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              ) : null}
            </div>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <button
          type="button"
          className="sidebar-central-taskpad-btn"
          onClick={openCentralTaskpad}
          title={t('taskpad.centralTitle')}
        >
          <GitBranch size={15} aria-hidden="true" />
          <span>{t('taskpad.centralTitle')}</span>
        </button>

        <div className="sidebar-footer-profile">
          <div className="sidebar-user-avatar" aria-hidden="true">
            {getInitials(userLabel)}
          </div>

          <div className="sidebar-user-copy">
            <span className="sidebar-user-label">{t('common.user')}</span>
            <strong className="sidebar-user-name" title={userEmail || userLabel}>
              {userLabel}
            </strong>
            {userEmail ? <span className="sidebar-user-email">{userEmail}</span> : null}
          </div>

          <span
            className={`sidebar-api-dot sidebar-api-dot--${apiStatus.tone}`}
            title={`API: ${apiStatus.label}`}
            aria-label={`API ${apiStatus.label}`}
          />
        </div>

        <div className="sidebar-footer-toolbar" role="toolbar" aria-label={t('common.sidebarToolbarAria', 'Sidebar settings')}>
          <div className="sidebar-footer-toolbar-lang">
            <LanguageSwitcher variant="select" showLabel={false} />
          </div>

          <div className="sidebar-footer-toolbar-actions">
            <button
              type="button"
              onClick={handleThemeToggle}
              className="theme-toggle-btn sidebar-icon-btn"
              title={`${currentThemeMeta.label} — switch to ${nextThemeMeta.label}`}
              aria-label={`Switch to ${nextThemeMeta.label} theme`}
            >
              <CurrentThemeIcon size={17} aria-hidden="true" />
            </button>

            {onSignOut ? (
              <button
                type="button"
                className="theme-toggle-btn sidebar-icon-btn sidebar-icon-btn--danger"
                onClick={onSignOut}
                title="Sign out"
                aria-label="Sign out"
              >
                <LogOut size={17} aria-hidden="true" />
              </button>
            ) : null}
          </div>
        </div>
      </div>
    </aside>
  );
}

```

### `apps/web/src/components/ProjectFolderBrowser.jsx`

```javascript
import { lazy, Suspense, useEffect, useMemo, useState } from 'react';
import {
  Archive,
  BarChart3,
  BookOpen,
  Calendar,
  ChevronDown,
  ChevronRight,
  ClipboardList,
  FileText,
  FlaskConical,
  FolderOpen,
  FolderTree,
  HardDrive,
  LayoutGrid,
  Loader2,
  Menu,
  Search,
  Users,
} from 'lucide-react';
import MediaViewer from './MediaViewer.jsx';
import { getMediaPreviewKind } from '../utils/mediaPreviewKind.js';

const ModelViewer3D = lazy(() => import('./ModelViewer3D.jsx'));
import {
  collectFolderEntries,
  filesForFolderEntry,
  filesUnderTreePath,
  formatFileSize,
  formatModifiedAt,
  getChunkTextForProjectFile,
  getDocumentIndexEntry,
  getFilePreviewStatus,
  isAssetPreviewable,
  isExtractPreviewable,
  isTextPreviewable,
  normalizeRelPath,
  sortProjectFiles,
} from '../utils/folderBrowserUtils.js';
import { inferExtension } from '../utils/fileTypeMeta.js';
import { projectAssetUrl } from '../utils/digitalTwinUtils.js';
import FileTypeBadge from './FileTypeBadge.jsx';
import CopyPathButton from './CopyPathButton.jsx';
import SmartLink from './SmartLink.jsx';
import DataPadEditor from './DataPadEditor.jsx';
import DocumentFormatter from './DocumentFormatter.jsx';
import { useTaskpad } from '../contexts/TaskpadContext.jsx';
import { fetchDatapadSectionSummary } from '../api/datapad.js';
import { folderSectionToWorkspaceTab } from '../utils/taskpadUtils.js';

const PREVIEW_LIMIT = 12000;

const SECTION_ICONS = {
  management: ClipboardList,
  methods: FlaskConical,
  data_figures: BarChart3,
  writing: BookOpen,
  meetings: Users,
  archive: Archive,
  guidelines: FileText,
  root: FolderOpen,
};

function groupFolders(folders) {
  const library = folders.filter((f) => f.source === 'content_library');
  const tree = folders.filter((f) => f.source === 'folder_tree');
  return [
    { id: 'library', label: 'Content sections', items: library },
    { id: 'tree', label: 'Folder tree', items: tree },
  ].filter((g) => g.items.length > 0);
}

function buildApiUrl(API_URL, path, params) {
  const base = (API_URL || '').replace(/\/$/, '');
  const q = params ? `?${params.toString()}` : '';
  return `${base}${path.startsWith('/') ? path : `/${path}`}${q}`;
}

function folderIcon(folder) {
  const Icon = SECTION_ICONS[folder?.id] || (folder?.source === 'folder_tree' ? FolderTree : FolderOpen);
  return Icon;
}

async function fetchVaultExcerpt(API_URL, filePath, projectCode) {
  if (!API_URL) return null;
  const name = (filePath || '').split('/').pop() || filePath;
  const q = name.replace(/\.[^.]+$/, '').slice(0, 80) || name;
  try {
    const params = new URLSearchParams({ q, limit: '12' });
    const res = await fetch(buildApiUrl(API_URL, '/api/vault/search', params));
    if (!res.ok) return null;
    const data = await res.json();
    const hits = data.results || data.hits || [];
    const norm = normalizeRelPath(filePath);
    const match =
      hits.find((h) => normalizeRelPath(h.relative_path || h.logical_path || h.path || '') === norm) ||
      hits.find(
        (h) =>
          (h.project_hint || h.project_id || h.project_code || '') === projectCode &&
          (h.filename || '').toLowerCase() === name.toLowerCase()
      ) ||
      hits.find((h) => (h.filename || '').toLowerCase() === name.toLowerCase()) ||
      hits[0];
    if (!match) return null;
    const md = match.metadata_preview || {};
    const text = (
      match.excerpt ||
      md.excerpt ||
      match.full_text ||
      match.text ||
      ''
    ).trim();
    if (!text) return null;
    return { content: text, source: 'vault search' };
  } catch {
    return null;
  }
}

export default function ProjectFolderBrowser({ twin, projectCode, API_URL, projectName }) {
  const folders = useMemo(() => collectFolderEntries(twin), [twin]);
  const docIndexByPath = useMemo(() => {
    const map = new Map();
    for (const doc of twin?.document_index || []) {
      if (doc?.path) map.set(normalizeRelPath(doc.path), doc);
    }
    return map;
  }, [twin]);

  const displayName = projectName || twin?.identity?.project_name || projectCode;

  const [selectedId, setSelectedId] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [previewSource, setPreviewSource] = useState(null);
  const [previewMeta, setPreviewMeta] = useState(null);
  const [previewExpanded, setPreviewExpanded] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(null);
  const [assetUrl, setAssetUrl] = useState(null);
  const [folderQuery, setFolderQuery] = useState('');
  const [fileQuery, setFileQuery] = useState('');
  const [fileSort, setFileSort] = useState('name');
  const [collapsedGroups, setCollapsedGroups] = useState(() => new Set());
  const [foldersDrawerOpen, setFoldersDrawerOpen] = useState(false);
  const [sectionSummary, setSectionSummary] = useState(null);
  const { openTaskpad } = useTaskpad();

  const contentRoot = twin?.content_root || twin?.folder_path || null;
  const folderGroups = useMemo(() => groupFolders(folders), [folders]);

  const totalFiles = useMemo(
    () => folders.reduce((sum, f) => sum + (f.file_count || 0), 0),
    [folders]
  );

  useEffect(() => {
    if (folders.length && !selectedId) {
      setSelectedId(folders[0].id);
    }
  }, [folders, selectedId]);

  const selectedFolder = folders.find((f) => f.id === selectedId);

  useEffect(() => {
    if (!projectCode || !selectedFolder?.id) {
      setSectionSummary(null);
      return;
    }
    let cancelled = false;
    fetchDatapadSectionSummary(projectCode, selectedFolder.id)
      .then((data) => {
        if (!cancelled) setSectionSummary(data);
      })
      .catch(() => {
        if (!cancelled) setSectionSummary(null);
      });
    return () => {
      cancelled = true;
    };
  }, [projectCode, selectedFolder?.id]);

  const folderFiles = useMemo(() => {
    if (!selectedFolder) return [];
    if (selectedFolder.section) return filesForFolderEntry(selectedFolder);
    if (selectedFolder.source === 'folder_tree') {
      return filesUnderTreePath(twin, selectedFolder.path);
    }
    return [];
  }, [selectedFolder, twin]);

  const sortedFiles = useMemo(() => sortProjectFiles(folderFiles, fileSort), [folderFiles, fileSort]);

  const filteredGroups = useMemo(() => {
    const q = folderQuery.trim().toLowerCase();
    if (!q) return folderGroups;
    return folderGroups
      .map((g) => ({
        ...g,
        items: g.items.filter((f) => f.label.toLowerCase().includes(q) || f.path.toLowerCase().includes(q)),
      }))
      .filter((g) => g.items.length > 0);
  }, [folderGroups, folderQuery]);

  const visibleFiles = useMemo(() => {
    const q = fileQuery.trim().toLowerCase();
    if (!q) return sortedFiles;
    return sortedFiles.filter(
      (f) =>
        (f.name || '').toLowerCase().includes(q) ||
        (f.path || '').toLowerCase().includes(q)
    );
  }, [sortedFiles, fileQuery]);

  const groupedFiles = useMemo(() => {
    const groups = {
      documents: [],
      figures: [],
      data_files: [],
      code_scripts: [],
      other: []
    };
    
    visibleFiles.forEach(file => {
      const ext = inferExtension(file.name, file.extension);
      let cat = 'other';
      
      if (file.asset_type) {
        if (['documents', 'writing', 'presentations'].includes(file.asset_type)) cat = 'documents';
        else if (['figures', 'images', 'videos'].includes(file.asset_type)) cat = 'figures';
        else if (['data_files', 'tables'].includes(file.asset_type)) cat = 'data_files';
        else if (['text_files', 'scripts'].includes(file.asset_type)) cat = 'code_scripts';
        else cat = 'other';
      } else {
         if (['.pdf', '.doc', '.docx', '.rtf', '.txt', '.md'].includes(ext)) cat = 'documents';
         else if (['.png', '.jpg', '.jpeg', '.svg', '.tif', '.tiff', '.gif'].includes(ext)) cat = 'figures';
         else if (['.csv', '.tsv', '.xlsx', '.xls', '.json', '.h5', '.rds'].includes(ext)) cat = 'data_files';
         else if (['.py', '.r', '.sh', '.js', '.ipynb'].includes(ext)) cat = 'code_scripts';
      }
      
      groups[cat].push(file);
    });
    
    return groups;
  }, [visibleFiles]);

  const breadcrumbParts = useMemo(() => {
    const parts = [displayName, 'Data Pad'];
    if (selectedFolder) parts.push(selectedFolder.label);
    if (selectedFile) parts.push(selectedFile.name);
    return parts;
  }, [displayName, selectedFolder, selectedFile]);

  const filePreviewStatus = useMemo(() => {
    if (!selectedFile?.path) return null;
    return getFilePreviewStatus(selectedFile, twin, normalizeRelPath(selectedFile.path));
  }, [selectedFile, twin]);

  useEffect(() => {
    setSelectedFile(null);
    setPreview(null);
    setPreviewSource(null);
    setPreviewMeta(null);
    setPreviewError(null);
    setAssetUrl(null);
    setPreviewExpanded(false);
    setFileQuery('');
  }, [selectedId]);

  const toggleGroup = (groupId) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupId)) next.delete(groupId);
      else next.add(groupId);
      return next;
    });
  };

  const selectFolder = (id) => {
    setSelectedId(id);
    setFoldersDrawerOpen(false);
  };

  const loadFilePreview = async (file) => {
    setSelectedFile(file);
    setPreview(null);
    setPreviewSource(null);
    setPreviewMeta(null);
    setPreviewError(null);
    setAssetUrl(null);
    setPreviewExpanded(false);

    if (!file?.path) return;

    const ext = inferExtension(file.name, file.extension);
    const normPath = normalizeRelPath(file.path);
    const status = getFilePreviewStatus(file, twin, normPath);
    setPreviewMeta(status);

    const fromChunks = getChunkTextForProjectFile(twin, normPath);
    if (fromChunks) {
      setPreview(fromChunks);
      setPreviewSource('indexed chunks');
      return;
    }

    const indexed = docIndexByPath.get(normPath) || getDocumentIndexEntry(twin, normPath);
    if (indexed?.excerpt) {
      const title = (indexed.title || '').trim();
      const body =
        title && !indexed.excerpt.startsWith(title.slice(0, 40))
          ? `${title}\n\n${indexed.excerpt}`
          : indexed.excerpt;
      setPreview(body);
      setPreviewSource('document index');
      if (indexed.extractor) setPreviewMeta({ ...status, extractor: indexed.extractor });
      return;
    }

    if (file.excerpt) {
      setPreview(file.excerpt);
      setPreviewSource('digital twin metadata');
      return;
    }

    if (isAssetPreviewable(ext) && !isTextPreviewable(ext)) {
      setAssetUrl(projectAssetUrl(projectCode, normPath, API_URL, contentRoot));
      if (ext !== '.pdf') {
        setPreviewSource('image');
        return;
      }
    }

    setPreviewLoading(true);
    try {
      if (isTextPreviewable(ext) && API_URL) {
        const params = new URLSearchParams({
          project_code: projectCode,
          relative_path: normPath,
        });
        const res = await fetch(buildApiUrl(API_URL, '/api/project-files/read', params));
        if (res.ok) {
          const data = await res.json();
          setPreview(data.content || '');
          setPreviewSource('file on disk');
          return;
        }
        if (res.status === 410) {
          const vault = await fetchVaultExcerpt(API_URL, normPath, projectCode);
          if (vault) {
            setPreview(vault.content);
            setPreviewSource(vault.source);
            return;
          }
        }
      }

      if (API_URL) {
        const params = new URLSearchParams({
          project_code: projectCode,
          relative_path: normPath,
        });
        const res = await fetch(buildApiUrl(API_URL, '/api/project-files/preview-text', params));
        if (res.ok) {
          const data = await res.json();
          setPreview(data.content || '');
          setPreviewSource(data.source || 'extracted');
          if (data.extractor || data.status) {
            setPreviewMeta({
              ...status,
              extractor: data.extractor,
              status: data.status,
            });
          }
          return;
        }
        if (res.status === 410) {
          const vault = await fetchVaultExcerpt(API_URL, normPath, projectCode);
          if (vault) {
            setPreview(vault.content);
            setPreviewSource(vault.source);
            return;
          }
        }
        const err = await res.json().catch(() => ({}));
        if (res.status !== 422) {
          throw new Error(err.detail || res.statusText);
        }
      }

      const vault = await fetchVaultExcerpt(API_URL, normPath, projectCode);
      if (vault) {
        setPreview(vault.content);
        setPreviewSource(vault.source);
        return;
      }

      if (isExtractPreviewable(ext)) {
        setPreviewError(
          'No extracted text yet. Run “Scan project folder” to index this file, or open the original below.'
        );
      } else if (isAssetPreviewable(ext)) {
        if (!assetUrl) {
          setAssetUrl(projectAssetUrl(projectCode, normPath, API_URL, contentRoot));
        }
      } else {
        setPreviewError(
          'No indexed preview for this type. Open the file directly, or re-scan the project folder.'
        );
      }
    } catch (e) {
      setPreviewError(String(e.message || e));
    } finally {
      setPreviewLoading(false);
    }
  };

  if (!twin) {
    return (
      <section className="panel workspace-section data-pad">
        <header className="data-pad-hierarchy">
          <h3 className="panel-title">
            <HardDrive size={18} /> Data Pad
          </h3>
        </header>
        <p className="text-footnote muted workspace-empty-state">
          Load the digital record to browse project folders and preview extracted text from documents.
        </p>
      </section>
    );
  }

  if (!folders.length) {
    return (
      <section className="panel workspace-section data-pad">
        <header className="data-pad-hierarchy">
          <h3 className="panel-title">
            <HardDrive size={18} /> Data Pad
          </h3>
        </header>
        <p className="text-footnote muted workspace-empty-state">
          No indexed folders yet. Click ↻ Scan project folder to scan the project directory.
        </p>
      </section>
    );
  }

  const previewSlice = preview
    ? previewExpanded || preview.length <= PREVIEW_LIMIT
      ? preview
      : `${preview.slice(0, PREVIEW_LIMIT)}\n…`
    : null;

  const selectedExt = selectedFile ? inferExtension(selectedFile.name, selectedFile.extension) : '';
  const sectionEditableCount =
    sectionSummary?.sections?.[0]?.editable_count ??
    (selectedFolder ? visibleFiles.filter((f) => ['.md', '.txt', '.html', '.rtf'].includes(inferExtension(f.name, f.extension))).length : 0);
  const isPdf = selectedExt === '.pdf';
  const mediaKind = getMediaPreviewKind(selectedExt);
  const layoutClass = `pfb-layout${selectedFile ? ' pfb-layout--file-open' : ''}${foldersDrawerOpen ? ' pfb-layout--folders-open' : ''}`;

  return (
    <section className="panel workspace-section data-pad project-folder-browser">
      <header className="data-pad-hierarchy">
        <div className="data-pad-hierarchy-main">
          <h3 className="panel-title">
            <HardDrive size={18} /> Data Pad
          </h3>
          <nav className="data-pad-breadcrumb" aria-label="Location">
            {breadcrumbParts.map((part, i) => (
              <span key={`${part}-${i}`} className="data-pad-crumb">
                {i > 0 && <ChevronRight size={12} className="data-pad-crumb-sep" aria-hidden />}
                <span className={i === breadcrumbParts.length - 1 ? 'data-pad-crumb-current' : ''}>
                  {part}
                </span>
              </span>
            ))}
          </nav>
        </div>
        <div className="data-pad-hierarchy-stats">
          <span className="data-pad-stat">
            <FolderOpen size={14} /> {folders.length} sections
          </span>
          <span className="data-pad-stat">
            <FileText size={14} /> {totalFiles} files
          </span>
          {selectedFolder && (
            <span className="data-pad-stat">
              <LayoutGrid size={14} /> {visibleFiles.length} shown
            </span>
          )}
        </div>
      </header>

      {contentRoot && (
        <div className="data-pad-root">
          <SmartLink href={contentRoot} showCopy maxLabelLen={48} />
        </div>
      )}

      <div className="data-pad-filter-bar">
        <button
          type="button"
          className="btn btn-secondary btn-sm data-pad-drawer-toggle"
          onClick={() => setFoldersDrawerOpen((v) => !v)}
          aria-expanded={foldersDrawerOpen}
        >
          <Menu size={14} /> Sections
        </button>
        <label className="data-pad-filter-field">
          <Search size={14} aria-hidden />
          <input
            type="search"
            className="form-input data-pad-filter-input"
            placeholder="Filter sections…"
            aria-label="Filter sections"
            value={folderQuery}
            onChange={(e) => setFolderQuery(e.target.value)}
          />
        </label>
        <label className="data-pad-filter-field">
          <Search size={14} aria-hidden />
          <input
            type="search"
            className="form-input data-pad-filter-input"
            placeholder="Filter files in section…"
            aria-label="Filter files in section"
            value={fileQuery}
            onChange={(e) => setFileQuery(e.target.value)}
            disabled={!selectedFolder}
          />
        </label>
        <select
          className="form-select data-pad-sort-select"
          value={fileSort}
          onChange={(e) => setFileSort(e.target.value)}
          aria-label="Sort files"
          disabled={!selectedFolder}
        >
          <option value="name">Sort: name</option>
          <option value="type">Sort: type</option>
          <option value="modified">Sort: modified</option>
          <option value="size">Sort: size</option>
        </select>
      </div>

      <div className={layoutClass}>
        <aside
          className="pfb-column pfb-folder-list pfb-column--resizable"
          aria-label="Content sections"
        >
          {filteredGroups.map((group) => {
            const collapsed = collapsedGroups.has(group.id);
            return (
              <div key={group.id} className="pfb-folder-group">
                <button
                  type="button"
                  className="pfb-folder-group-header"
                  onClick={() => toggleGroup(group.id)}
                  aria-expanded={!collapsed}
                >
                  {collapsed ? <ChevronRight size={16} /> : <ChevronDown size={16} />}
                  <span>{group.label}</span>
                  <span className="pfb-folder-count">{group.items.length}</span>
                </button>
                {!collapsed &&
                  group.items.map((folder) => {
                    const Icon = folderIcon(folder);
                    return (
                      <button
                        key={folder.id}
                        type="button"
                        className={`pfb-folder-item ${selectedId === folder.id ? 'active' : ''}`}
                        onClick={() => selectFolder(folder.id)}
                        title={folder.path}
                      >
                        <Icon size={14} className="pfb-folder-icon" />
                        <span className="pfb-folder-label">{folder.label}</span>
                        <span className="pfb-folder-count">{folder.file_count}</span>
                      </button>
                    );
                  })}
              </div>
            );
          })}
        </aside>

        <div className="pfb-column pfb-files-pane pfb-column--resizable">
          {selectedFolder ? (
            <>
              <div className="pfb-files-header">
                <h4 className="workspace-subpanel-title">{selectedFolder.label}</h4>
                <span className="pfb-files-meta muted text-footnote">
                  {visibleFiles.length} of {folderFiles.length} files
                  {sectionEditableCount > 0 && ` · ${sectionEditableCount} editable`}
                </span>
              </div>
              {visibleFiles.length === 0 ? (
                <p className="muted text-footnote workspace-empty-state">
                  {folderFiles.length === 0
                    ? 'No files indexed in this section.'
                    : 'No files match your filter.'}
                </p>
              ) : (
                <div className="pfb-file-grouped-wrap">
                  {Object.entries(groupedFiles).map(([category, files]) => {
                    if (!files.length) return null;
                    const labels = {
                      documents: 'Documents & Writing',
                      figures: 'Figures & Imaging',
                      data_files: 'Data Assets',
                      code_scripts: 'Scripts & Code',
                      other: 'Other Files'
                    };
                    return (
                      <div key={category} className="pfb-file-category">
                        <h5 className="pfb-category-title">
                          {labels[category]} <span className="muted">({files.length})</span>
                        </h5>
                        <div className="pfb-file-grid">
                          {files.map((file) => {
                            const norm = normalizeRelPath(file.path);
                            const rowStatus = getFilePreviewStatus(file, twin, norm);
                            return (
                              <div
                                key={file.path}
                                className={`pfb-file-card ${selectedFile?.path === file.path ? 'active' : ''}`}
                                onClick={() => loadFilePreview(file)}
                                title={file.path}
                              >
                                <div className="pfb-file-card-header">
                                  <div className="pfb-file-card-icon">
                                    <FileTypeBadge file={file} />
                                  </div>
                                  <div className="pfb-file-card-info">
                                    <span className="pfb-file-name">{file.name}</span>
                                    <span className="pfb-file-meta">
                                      {formatFileSize(file.size_bytes)} • {formatModifiedAt(file.modified_at)}
                                    </span>
                                  </div>
                                </div>
                                <div className="pfb-file-card-footer">
                                  <span className={`pfb-index-badge tone-${rowStatus.tone}`}>
                                    {rowStatus.label}
                                  </span>
                                  <FileText size={14} className="muted" aria-hidden />
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          ) : (
            <p className="muted text-footnote workspace-empty-state">Select a content section.</p>
          )}
        </div>

        <div className="pfb-column pfb-preview-pane pfb-column--resizable">
          <h4 className="workspace-subpanel-title">Preview</h4>
          {!selectedFile ? (
            <div className="pfb-preview-empty">
              <FileText size={32} className="pfb-preview-empty-icon" aria-hidden />
              <p className="muted text-footnote">
                Select a file from the list to preview extracted text, PDFs, or images.
              </p>
              <p className="text-footnote muted">
                Tip: run <strong>Scan project folder</strong> to refresh the digital twin index.
              </p>
            </div>
          ) : (
            <>
              <div className="pfb-preview-header">
                <div className="pfb-preview-title-row">
                  <b className="pfb-preview-filename">{selectedFile.name}</b>
                  <FileTypeBadge file={selectedFile} />
                </div>
                {filePreviewStatus && (
                  <div className="pfb-preview-status-row">
                    <span className={`pfb-index-badge tone-${filePreviewStatus.tone}`}>
                      {filePreviewStatus.label}
                    </span>
                    {previewSource && (
                      <span className="text-footnote muted">Loaded via {previewSource}</span>
                    )}
                    {previewMeta?.extractor && (
                      <span className="text-footnote muted">· {previewMeta.extractor}</span>
                    )}
                  </div>
                )}
                <div className="pfb-preview-path-row">
                  <SmartLink href={selectedFile.path} showCopy maxLabelLen={80} />
                </div>
                <div className="pfb-preview-actions">
                  <a
                    href={projectAssetUrl(projectCode, selectedFile.path, API_URL)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-secondary btn-sm"
                    download={!isPdf && !mediaKind ? selectedFile.name : undefined}
                  >
                    Open file
                  </a>
                  <CopyPathButton value={selectedFile.path} label="Copy relative path" />
                </div>
              </div>
              {previewLoading && (
                <p className="text-loading pfb-preview-loading">
                  <Loader2 size={14} className="spin" /> Loading preview…
                </p>
              )}
              {previewError && !previewLoading && (
                <p className="text-callout pfb-preview-error">{previewError}</p>
              )}
              {['.md', '.txt', '.html', '.rtf'].includes(selectedExt) && preview != null && !previewLoading && (
                <DataPadEditor
                  projectCode={projectCode}
                  relativePath={normalizeRelPath(selectedFile.path)}
                  fileName={selectedFile.name}
                  sectionLabel={selectedFolder?.label}
                  initialContent={preview}
                  onSaved={(text) => {
                    setPreview(text);
                    setPreviewSource('Data Pad (saved)');
                  }}
                />
              )}
              {previewSlice && !['.md', '.txt', '.html', '.rtf'].includes(selectedExt) && (
                <>
                  <div className="surface-inset" style={{ padding: '1.5rem' }}>
                    <DocumentFormatter 
                      text={previewSlice} 
                      onCreateTask={(text) =>
                        openTaskpad(text, {
                          section: folderSectionToWorkspaceTab(selectedFolder?.id),
                          filePath: selectedFile.path,
                          fileName: selectedFile.name,
                        })
                      }
                    />
                  </div>
                  {preview.length > PREVIEW_LIMIT && (
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => setPreviewExpanded((v) => !v)}
                    >
                      {previewExpanded ? 'Show less' : `Show full preview (${preview.length.toLocaleString()} chars)`}
                    </button>
                  )}
                </>
              )}
              {assetUrl && isPdf && (
                <iframe title={selectedFile.name} src={assetUrl} className="database-pdf-frame pfb-pdf-frame" />
              )}
              {assetUrl && mediaKind === 'model3d' && !previewSlice && !previewLoading && (
                <Suspense fallback={<p className="text-footnote muted">Loading 3D viewer…</p>}>
                  <ModelViewer3D url={assetUrl} title={selectedFile.name} />
                </Suspense>
              )}
              {assetUrl && mediaKind && mediaKind !== 'model3d' && !previewSlice && !previewLoading && (
                <MediaViewer
                  url={assetUrl}
                  title={selectedFile.name}
                  kind={mediaKind}
                  labels={{
                    loading: 'Loading…',
                    failed: 'Could not load image.',
                    videoLoading: 'Loading video…',
                    videoFailed: 'Could not load video.',
                  }}
                />
              )}
              {assetUrl && isPdf && !previewSlice && !previewLoading && !previewError && (
                <p className="text-footnote muted" style={{ marginTop: '0.5rem' }}>
                  PDF shown above. Re-scan the project for searchable extracted text below.
                </p>
              )}
            </>
          )}
        </div>
      </div>
    </section>
  );
}

```

### `apps/web/src/components/LabDocumentsBrowser.jsx`

```javascript
import { useEffect, useMemo, useState } from 'react';
import { FileText, Loader2, Lock } from 'lucide-react';
import DocumentPreviewPane from './DocumentPreviewPane.jsx';
import DocumentFileSearch from './DocumentFileSearch.jsx';
import SmartLink from './SmartLink.jsx';
import {
  documentDisplayExcerpt,
  fetchLabSectionProcessed,
  getChunkTextForFile,
  labDatabaseAssetUrl,
} from '../utils/labDatabaseUtils.js';
import { isJunkPreviewText } from '../utils/textCleanup.js';
import { inferExtension } from '../utils/fileTypeMeta.js';
import { getMediaPreviewKind } from '../utils/mediaPreviewKind.js';
import { buildMediaGallery, mergeGalleryItem } from '../utils/mediaGalleryUtils.js';
import { useSpreadsheetPreview } from '../hooks/useSpreadsheetPreview.js';
import { useRawFilePreview } from '../hooks/useRawFilePreview.js';
import { useCatalogDocumentPreview } from '../hooks/useCatalogDocumentPreview.js';
import { getFilePreviewKind } from '../utils/filePreviewKind.js';
import { useTaskpad } from '../contexts/TaskpadContext.jsx';
import {
  collectProjectDocuments,
  deduplicateDocumentsByPath,
  flattenCategoryOrder,
  groupDocumentsByCategory,
} from '../utils/documentBrowserUtils.js';
import { normalizeDocPath } from '../utils/folderBrowserUtils.js';
import DocumentCategoryFileList, {
  countGroupedFiles,
} from './DocumentCategoryFileList.jsx';
import { useGuiT } from '../i18n/useGuiT.js';
import { useModuleShellHeaderSlot } from '../contexts/ModuleShellHeaderSlotContext.jsx';

export default function LabDocumentsBrowser({
  sectionId,
  sectionIds,
  title: _title,
  description: _description,
  icon: _Icon = FileText,
  categoryGroups,
  defaultCategory,
  categorizePath,
  documentTitle,
  categoryIcons = {},
  className = 'lab-documents-browser',
  topPanel = null,
  sensitiveCategories = [],
  documentFilter = null,
  syntheticDocs = [],
  syntheticPreviewField = 'inlineContent',
  folderHintResolver = null,
  layoutVariant = 'catalog',
}) {
  const [twins, setTwins] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedPath, setSelectedPath] = useState(null);
  const [fileQuery, setFileQuery] = useState('');
  const [revealSensitive, setRevealSensitive] = useState(false);
  const { openTaskpad } = useTaskpad();
  const { t, localizeCategories } = useGuiT();

  const ids = sectionIds?.length ? sectionIds : [sectionId];

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);

    Promise.all(ids.map((id) => fetchLabSectionProcessed(id).then((data) => [id, data])))
      .then((pairs) => {
        if (!mounted) return;
        const loaded = pairs.filter(([, data]) => data);
        const map = Object.fromEntries(loaded);
        if (!Object.keys(map).length) {
          throw new Error('No document sections could be loaded.');
        }
        setTwins(map);
        setLoading(false);
      })
      .catch((err) => {
        if (!mounted) return;
        setError(err.message || 'Failed to load documents.');
        setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [ids.join(',')]);

  const primaryTwin = twins[ids[0]];

  const allDocs = useMemo(() => {
    const docs = [];
    for (const id of ids) {
      const twin = twins[id];
      if (!twin) continue;
      const sectionDocs = collectProjectDocuments(twin, {
        categorizePath: (path) => categorizePath(path, id),
        documentTitle,
      });
      for (const doc of sectionDocs) {
        if (documentFilter && !documentFilter(doc.path)) continue;
        docs.push({
          ...doc,
          sourceSection: id,
          folderHint:
            folderHintResolver?.(id)
            || (ids.length > 1 ? id.replace('overview_', '').replace(/_/g, ' ') : null),
        });
      }
    }
    for (const doc of syntheticDocs) {
      if (documentFilter && !documentFilter(doc.path)) continue;
      docs.push(doc);
    }
    return deduplicateDocumentsByPath(docs);
  }, [twins, ids, categorizePath, documentTitle, documentFilter, syntheticDocs, folderHintResolver]);

  const localizedCategoryGroups = useMemo(
    () => localizeCategories(categoryGroups),
    [categoryGroups, localizeCategories]
  );

  const categoryOrder = useMemo(
    () => flattenCategoryOrder(localizedCategoryGroups),
    [localizedCategoryGroups]
  );
  const grouped = useMemo(
    () => groupDocumentsByCategory(allDocs, categoryOrder),
    [allDocs, categoryOrder]
  );

  const visibleFileCount = useMemo(
    () =>
      countGroupedFiles(localizedCategoryGroups, grouped, fileQuery, documentTitle),
    [localizedCategoryGroups, grouped, fileQuery, documentTitle]
  );

  const setHeaderSlot = useModuleShellHeaderSlot();

  useEffect(() => {
    if (!setHeaderSlot) return undefined;
    setHeaderSlot(
      <DocumentFileSearch
        value={fileQuery}
        onChange={setFileQuery}
        fileCount={visibleFileCount}
        searchPlaceholder={t('docs.searchPlaceholder')}
        searchAria={t('docs.searchFiles')}
        filesLabel={t('docs.filesInSection', '', { count: visibleFileCount })}
      />
    );
    return () => setHeaderSlot(null);
  }, [setHeaderSlot, fileQuery, visibleFileCount, t]);

  const selectedDoc = useMemo(() => {
    if (!selectedPath) return null;
    const key = normalizeDocPath(selectedPath);
    return allDocs.find((d) => normalizeDocPath(d.path) === key) || null;
  }, [allDocs, selectedPath]);

  const selectedCategoryId = selectedDoc?.categoryId;
  const isSensitive = sensitiveCategories.includes(selectedCategoryId);

  const selectedTwin = selectedDoc?.sourceSection
    ? twins[selectedDoc.sourceSection]
    : primaryTwin;

  const maskSensitiveText = (text) => {
    if (!text) return '';
    return text
      .split('\n')
      .map((line) => {
        if (/\b(password|passcode|secret|username|credential|token|api key)\b/i.test(line)) {
          const sep = line.search(/[:=]/);
          if (sep >= 0) return `${line.slice(0, sep + 1)} [hidden]`;
          return '[hidden sensitive line]';
        }
        return line;
      })
      .join('\n');
  };

  const selectedExt = selectedDoc
    ? inferExtension(selectedDoc.name, selectedDoc.extension)
    : '';
  const isPdf = selectedExt === '.pdf';
  const mediaKind = getMediaPreviewKind(selectedExt);
  const previewKind = getFilePreviewKind(selectedExt, selectedDoc?.path);
  const isSpreadsheet = previewKind === 'spreadsheet';

  const relativeRoot = selectedTwin?.relative_root || primaryTwin?.relative_root;
  const assetUrl = useMemo(
    () =>
      selectedDoc && relativeRoot
        ? labDatabaseAssetUrl(relativeRoot, selectedDoc.path)
        : null,
    [selectedDoc, relativeRoot]
  );

  const twinPreviewText = useMemo(() => {
    if (!selectedDoc) return null;
    if (selectedDoc.isSynthetic && selectedDoc[syntheticPreviewField]) {
      const raw = String(selectedDoc[syntheticPreviewField]).trim();
      return isSensitive && !revealSensitive ? maskSensitiveText(raw) : raw;
    }
    if (!selectedTwin) return null;
    const fromChunks = getChunkTextForFile(selectedTwin, selectedDoc.path);
    const excerpt = selectedDoc.excerpt || documentDisplayExcerpt(selectedDoc, 12000);
    const raw = (fromChunks || excerpt || '').trim();
    if (!raw || isJunkPreviewText(raw)) return null;
    return isSensitive && !revealSensitive ? maskSensitiveText(raw) : raw;
  }, [selectedDoc, selectedTwin, isSensitive, revealSensitive, syntheticPreviewField]);

  const catalogPreview = useCatalogDocumentPreview(
    selectedDoc?.path,
    selectedDoc?.name,
    Boolean(selectedDoc?.path)
  );

  const spreadsheetPreview = useSpreadsheetPreview(
    isSpreadsheet && assetUrl ? assetUrl : null,
    selectedExt
  );
  const rawFilePreview = useRawFilePreview(assetUrl, previewKind, {
    fallbackText: twinPreviewText,
  });

  const mergedSpreadsheetPreview = useMemo(() => {
    if (!isSpreadsheet) return null;
    const fileSheets = spreadsheetPreview.sheets;
    const catalogSheets = catalogPreview.sheets;
    const sheets = fileSheets?.length ? fileSheets : catalogSheets;
    const fromCatalog = Boolean(!fileSheets?.length && catalogSheets?.length);
    const loading =
      !sheets?.length && (spreadsheetPreview.loading || catalogPreview.loading);
    const error =
      !sheets?.length &&
      !loading &&
      !catalogPreview.displayText &&
      spreadsheetPreview.error
        ? spreadsheetPreview.error
        : null;
    return {
      loading,
      sheets,
      repairNotes: [
        ...(spreadsheetPreview.repairNotes || []),
        ...(fromCatalog ? ['Rendered from lab catalog extraction.'] : []),
      ],
      error,
      strategy: fileSheets?.length ? spreadsheetPreview.strategy : fromCatalog ? 'catalog' : null,
    };
  }, [isSpreadsheet, spreadsheetPreview, catalogPreview]);

  const spreadsheetReady = Boolean(mergedSpreadsheetPreview?.sheets?.length);

  const previewText = twinPreviewText || catalogPreview.displayText || null;
  const previewFromCatalog = Boolean(
    !twinPreviewText && (catalogPreview.displayText || catalogPreview.sheets?.length)
  );
  const previewLoading =
    !previewText &&
    !spreadsheetReady &&
    (catalogPreview.loading || (isSpreadsheet && spreadsheetPreview.loading));

  const siblingPdf = useMemo(() => {
    if (!selectedDoc || isPdf) return null;
    const stem = selectedDoc.path.replace(/\.[^.]+$/, '');
    const pdfPath = `${stem}.pdf`;
    return allDocs.find((doc) => doc.path === pdfPath) || null;
  }, [selectedDoc, allDocs, isPdf]);

  const pdfPreviewUrl = useMemo(() => {
    if (!relativeRoot) return null;
    if (isPdf && assetUrl) return assetUrl;
    if (siblingPdf) return labDatabaseAssetUrl(relativeRoot, siblingPdf.path);
    return null;
  }, [isPdf, assetUrl, siblingPdf, relativeRoot]);

  const mediaGallery = useMemo(() => {
    if (!selectedDoc || !relativeRoot || !mediaKind) return [];
    const resolveUrl = (doc) => labDatabaseAssetUrl(relativeRoot, doc.path);
    const siblings = buildMediaGallery(selectedDoc, allDocs, resolveUrl, documentTitle);
    return mergeGalleryItem(selectedDoc, siblings, resolveUrl, documentTitle);
  }, [selectedDoc, allDocs, relativeRoot, mediaKind, documentTitle]);

  const contentRoot = primaryTwin?.content_root;

  if (loading) {
    return (
      <div className="panel" style={{ padding: '2rem', textAlign: 'center' }}>
        <Loader2 size={20} className="spin-inline" /> {t('docs.loading')}
      </div>
    );
  }

  if (error) {
    return (
      <div className="panel" style={{ padding: '2rem', color: 'var(--mac-destructive)' }}>
        {error}
      </div>
    );
  }

  const resolvedLayoutVariant = layoutVariant === 'default' ? 'catalog' : layoutVariant;
  const isSplitCatalogLayout =
    resolvedLayoutVariant === 'protocols' || resolvedLayoutVariant === 'catalog';
  const browserClassName = [
    className,
    isSplitCatalogLayout ? 'catalog-space-browser lab-documents-browser--catalog' : '',
  ]
    .filter(Boolean)
    .join(' ');

  const previewPane = (
    <div className="pfb-column pfb-preview-pane pfb-preview-pane--editor-focus">
      {!selectedDoc ? (
        <div className="lab-doc-preview-placeholder">
          <p className="text-footnote muted">{t('docs.selectFile')}</p>
          {isSplitCatalogLayout ? (
            <p className="text-footnote muted lab-doc-preview-placeholder-hint">
              {t('docs.catalogPreviewHint')}
            </p>
          ) : null}
        </div>
      ) : previewLoading ? (
        <div className="panel" style={{ padding: '2rem', textAlign: 'center' }}>
          <Loader2 size={20} className="spin-inline" /> {t('docs.loadingPreview')}
        </div>
      ) : (
        <DocumentPreviewPane
                  onBackToFiles={() => setSelectedPath(null)}
                  title={documentTitle(selectedDoc)}
                  path={selectedDoc.path}
                  extension={selectedDoc.extension || inferExtension(selectedDoc.name)}
                  previewKind={previewKind}
                  rawFilePreview={rawFilePreview}
                  previewText={previewText}
                  previewFallbackNote={
                    previewFromCatalog &&
                    (mergedSpreadsheetPreview?.strategy === 'catalog' ||
                      rawFilePreview?.error ||
                      spreadsheetPreview.error)
                      ? t('docs.offlineExtractPreview')
                      : null
                  }
                  pdfPreviewUrl={pdfPreviewUrl}
                  pdfThumbLabel={isPdf ? 'PDF' : 'PDF copy'}
                  mediaKind={mediaKind}
                  mediaUrl={assetUrl}
                  mediaAlt={documentTitle(selectedDoc)}
                  mediaGallery={mediaGallery}
                  onMediaNavigate={setSelectedPath}
                  mediaLabels={{
                    loading: t('docs.mediaLoading'),
                    failed: t('docs.mediaFailed'),
                    videoLoading: t('docs.videoLoading'),
                    videoFailed: t('docs.videoFailed'),
                    modelLoading: t('docs.modelLoading'),
                    zoomIn: t('docs.mediaZoomIn'),
                    zoomOut: t('docs.mediaZoomOut'),
                    fit: t('docs.mediaFit'),
                    actualSize: t('docs.mediaActualSize'),
                    rotate: t('docs.mediaRotate'),
                    fullscreen: t('docs.mediaFullscreen'),
                    download: t('docs.openOriginal'),
                    previous: t('docs.mediaPrevious'),
                    next: t('docs.mediaNext'),
                    hint: t('docs.modelHint'),
                    play: t('docs.modelPlay'),
                    pause: t('docs.modelPause'),
                    autoRotate: t('docs.modelAutoRotate'),
                    reset: t('docs.modelReset'),
                  }}
                  spreadsheetPreview={isSpreadsheet ? mergedSpreadsheetPreview : null}
                  spreadsheetFileUrl={
                    isSpreadsheet && spreadsheetPreview.sheets?.length ? assetUrl : null
                  }
                  spreadsheetLabels={{
                    loading: t('docs.spreadsheetLoading'),
                    repaired: t('docs.spreadsheetRepaired'),
                    truncated: t('docs.spreadsheetTruncated'),
                    empty: t('docs.spreadsheetEmpty'),
                    failed: t('docs.spreadsheetFailed'),
                    openOriginal: t('docs.openOriginal'),
                  }}
                  codeLabels={{
                    loading: t('docs.codeLoading'),
                    failed: t('docs.codeFailed'),
                  }}
                  emptyHint="No text preview available. Expand the PDF thumbnail or open the original file."
                  onCreateTask={(text) =>
                    openTaskpad(text, {
                      section: sectionId,
                      filePath: selectedPath || undefined,
                      fileName: selectedDoc?.name || selectedDoc?.title,
                    })
                  }
                  actions={
                    <>
                      {assetUrl ? (
                        <a
                          href={assetUrl}
                          className="btn btn-secondary btn-sm"
                          target="_blank"
                          rel="noreferrer"
                        >
                          {t('docs.openOriginal')}
                        </a>
                      ) : null}
                      {isSensitive ? (
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          onClick={() => setRevealSensitive((v) => !v)}
                        >
                          {revealSensitive ? t('docs.hideSensitive') : t('docs.revealSensitive')}
                        </button>
                      ) : null}
                    </>
                  }
                />
      )}
    </div>
  );

  const sensitiveNote = isSensitive ? (
    <p className="lab-doc-sensitive-note">
      <Lock size={14} /> {t('docs.sensitiveMasked')}
    </p>
  ) : null;

  const fileList = (
    <DocumentCategoryFileList
      categoryGroups={localizedCategoryGroups}
      grouped={grouped}
      fileQuery={fileQuery}
      documentTitle={documentTitle}
      selectedPath={selectedPath}
      onSelectFile={setSelectedPath}
      categoryIcons={categoryIcons}
      sensitiveCategories={sensitiveCategories}
      categoryLayout={isSplitCatalogLayout ? 'horizontal-top' : 'inline'}
      renderPreview={
        isSplitCatalogLayout
          ? (fileBody) => (
              <div
                className={`lab-docs-catalog-split pfb-layout lab-docs-layout lab-docs-layout--compact lab-docs-layout--catalog${selectedDoc ? ' pfb-layout--editor-focus pfb-layout--doc-full' : ''}`}
              >
                <div className="pfb-column pfb-files-pane lab-doc-files-panel lab-doc-files-panel--catalog">
                  {sensitiveNote}
                  {fileBody}
                </div>
                {previewPane}
              </div>
            )
          : null
      }
    />
  );

  return (
    <section className={`panel workspace-section data-pad data-pad--compact data-pad--embedded ${browserClassName}`}>
      {topPanel}

      {contentRoot ? (
        <div className="data-pad-root data-pad-root--inline">
          <SmartLink href={contentRoot} showCopy maxLabelLen={48} />
        </div>
      ) : null}

      <div className={`lab-docs-section-layout lab-docs-section-layout--grouped${isSplitCatalogLayout ? ' lab-docs-section-layout--catalog' : ''}`}>
        <div className="lab-docs-section-main">
          {isSplitCatalogLayout ? (
            <div className="lab-docs-catalog-shell">
              {fileList}
            </div>
          ) : (
            <div
              className={`pfb-layout lab-docs-layout lab-docs-layout--compact${selectedDoc ? ' pfb-layout--editor-focus pfb-layout--doc-full' : ''}`}
            >
              <div className="pfb-column pfb-files-pane lab-doc-files-panel">
                {sensitiveNote}
                {fileList}
              </div>
              {previewPane}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

```

### `apps/web/src/screens/AiLabAssistantScreen.jsx`

```javascript
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  BookOpen,
  Bot,
  Check,
  Clipboard,
  Cpu,
  Database,
  FileText,
  Layers,
  Loader2,
  Sparkles,
  UploadCloud,
} from 'lucide-react';
import ChatWidget from '../components/ChatWidget.jsx';
import AiAssistant3DScene from '../components/AiAssistant3DScene.jsx';
import { apiFetch } from '../api/client.js';

const FALLBACK_PROJECTS = ['SPACE', 'EyeMT', 'KRAS'];

function normalizeProjectCode(project) {
  if (typeof project === 'string') return project;
  return project?.project_code || project?.code || project?.id || '';
}

function getProjectOptions(dbProjects = []) {
  const fromDb = dbProjects.map(normalizeProjectCode).filter(Boolean);
  return Array.from(new Set([...fromDb, ...FALLBACK_PROJECTS]));
}

function statusToneFromMessage(message) {
  const text = String(message || '').toLowerCase();
  if (!text) return 'neutral';
  if (text.includes('failed') || text.includes('error') || text.includes('expired') || text.includes('unauthorized')) return 'danger';
  if (text.includes('success') || text.includes('indexed') || text.includes('completed')) return 'success';
  if (text.includes('stored only') || text.includes('queued')) return 'warning';
  return 'neutral';
}

export default function AiLabAssistantScreen({
  API_URL,
  activeSubTab,
  hideChrome = false,
  dbProjects = [],
}) {
  const [subTab, setSubTab] = useState(activeSubTab || 'copilot');
  const [models, setModels] = useState([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [modelsError, setModelsError] = useState('');

  const [docTitle, setDocTitle] = useState('');
  const [docContent, setDocContent] = useState('');
  const [docProject, setDocProject] = useState('SPACE');
  const [ingesting, setIngesting] = useState(false);
  const [ingestStatus, setIngestStatus] = useState('');

  const projectOptions = useMemo(() => getProjectOptions(dbProjects), [dbProjects]);

  useEffect(() => {
    if (activeSubTab) setSubTab(activeSubTab);
  }, [activeSubTab]);

  useEffect(() => {
    if (!projectOptions.includes(docProject)) {
      setDocProject(projectOptions[0] || 'SPACE');
    }
  }, [docProject, projectOptions]);

  const fetchModels = useCallback(async () => {
    setLoadingModels(true);
    setModelsError('');

    try {
      const data = await apiFetch('/ai-models');
      setModels(Array.isArray(data) ? data : data?.models || []);
    } catch (error) {
      console.error('[AiLabAssistantScreen] Failed to fetch model registry:', error);
      setModelsError(
        error?.status === 401 || error?.status === 403
          ? 'Your session expired or you do not have permission to view model records.'
          : error?.message || 'Could not load model registry.',
      );
    } finally {
      setLoadingModels(false);
    }
  }, []);

  useEffect(() => {
    if (subTab === 'models') {
      fetchModels();
    }
  }, [fetchModels, subTab]);

  const handleIngest = useCallback(
    async (event) => {
      event.preventDefault();

      const cleanTitle = docTitle.trim();
      const cleanText = docContent.trim();

      if (!cleanTitle || !cleanText || ingesting) return;

      setIngesting(true);
      setIngestStatus('Queued document for parsing, chunking, embedding, and vector indexing…');

      try {
        const data = await apiFetch('/ingest-document', {
          method: 'POST',
          body: {
            project_code: docProject,
            filename: cleanTitle,
            file_type: 'txt',
            extracted_text: cleanText,
          },
        });

        const chunkCount = data?.chunk_count ?? data?.chunks_indexed ?? data?.indexed_chunks ?? 0;
        const indexed =
          data?.indexed === true ||
          data?.status === 'indexed' ||
          data?.status === 'completed' ||
          (data?.status === 'success' && Number(chunkCount) > 0);

        if (indexed) {
          setIngestStatus(
            `Success — document indexed for RAG retrieval.\nChunks indexed: ${chunkCount || 'reported by backend'}\nCollection: ${data?.qdrant_collection || data?.collection || 'doc_chunks'}`,
          );
          setDocTitle('');
          setDocContent('');
        } else if (data?.status === 'queued') {
          setIngestStatus(`Queued — backend accepted the document. Ingestion ID: ${data?.ingestion_id || data?.doc_id || 'pending'}`);
        } else if (data?.status === 'stored_only') {
          setIngestStatus('Stored only — backend saved the text but did not confirm vector indexing.');
        } else {
          setIngestStatus(`Completed with unknown indexing status: ${data?.status || 'unknown'}`);
        }
      } catch (error) {
        setIngestStatus(
          error?.status === 401 || error?.status === 403
            ? 'Your session expired or unauthorized. Please sign in again.'
            : `Connection error: ${error?.message || 'Unknown backend error'}`,
        );
      } finally {
        setIngesting(false);
      }
    },
    [docContent, docProject, docTitle, ingesting],
  );

  const menuItems = [
    {
      id: 'copilot',
      label: 'Chat Copilot',
      desc: 'Ask indexed lab memory',
      icon: Bot,
    },
    {
      id: 'prompts',
      label: 'Prompt Templates',
      desc: 'Writing and analysis helpers',
      icon: BookOpen,
    },
    {
      id: 'ingest',
      label: 'Ingest RAG Docs',
      desc: 'Chunk, embed, index',
      icon: UploadCloud,
    },
    {
      id: 'models',
      label: 'Model Registry',
      desc: 'AI tools and hardware',
      icon: Cpu,
    },
  ];

  const heroStats = useMemo(
    () => [
      { label: 'Services', value: menuItems.length },
      { label: 'Projects', value: projectOptions.length },
      { label: 'Mode', value: subTab === 'copilot' ? 'Live' : 'Tools' },
    ],
    [menuItems.length, projectOptions.length, subTab],
  );

  return (
    <section className={`ai-lab-assistant${hideChrome ? ' ai-lab-assistant--embedded' : ''}`}>
      {!hideChrome && (
        <aside className="ai-lab-rail" aria-label="AI assistant services">
          <AiAssistant3DScene
            title="AI Lab Assistant"
            subtitle="A 3D command center for RAG search, document indexing, prompt workflows, and model intelligence."
            stats={heroStats}
            compact
            className="ai-lab-rail-hero"
          />

          <div className="ai-lab-rail-label">Assistant services</div>

          <nav className="ai-lab-menu">
            {menuItems.map((item) => {
              const Icon = item.icon;
              const active = subTab === item.id;

              return (
                <button
                  key={item.id}
                  type="button"
                  className={`ai-lab-menu-item${active ? ' active' : ''}`}
                  onClick={() => setSubTab(item.id)}
                  aria-current={active ? 'page' : undefined}
                >
                  <span className="ai-lab-menu-item__icon">
                    <Icon size={17} aria-hidden="true" />
                  </span>
                  <span className="ai-lab-menu-item__copy">
                    <strong>{item.label}</strong>
                    <small>{item.desc}</small>
                  </span>
                </button>
              );
            })}
          </nav>
        </aside>
      )}

      <main className="ai-lab-main">
        {hideChrome && subTab === 'copilot' ? null : (
          <div className="ai-lab-top-hero">
            <AiAssistant3DScene
              title={
                subTab === 'copilot'
                  ? 'Research Copilot'
                  : subTab === 'ingest'
                    ? 'RAG Document Indexer'
                    : subTab === 'models'
                      ? 'Deep Learning Registry'
                      : 'Prompt Engineering Library'
              }
              subtitle={
                subTab === 'copilot'
                  ? 'Ask questions across Qdrant vectors, database counts, and lab knowledge.'
                  : subTab === 'ingest'
                    ? 'Paste or prepare protocols, scripts, and SOP text for vector retrieval.'
                    : subTab === 'models'
                      ? 'Track model families, frameworks, tasks, and target compute environments.'
                      : 'Reusable expert prompts for manuscript writing, logbooks, code review, and analysis.'
              }
              stats={heroStats}
              compact
            />
          </div>
        )}

        {subTab === 'copilot' && <ChatWidget dbProjects={dbProjects} API_URL={API_URL} />}
        {subTab === 'prompts' && <PromptsLibraryTab />}

        {subTab === 'ingest' && (
          <section className="ai-lab-tab-panel">
            <div className="page-header ai-lab-page-header">
              <span className="assistant-eyebrow">
                <Database size={14} aria-hidden="true" />
                Vector memory
              </span>
              <h2>Ingest & index RAG documents</h2>
              <p>Paste SOP protocols, scripts, methods notes, or manual transcripts into the authenticated RAG pipeline.</p>
            </div>

            <div className="panel ai-ingest-panel">
              <div className="ai-panel-title-row">
                <h3 className="panel-title">
                  <UploadCloud size={18} aria-hidden="true" />
                  Document vector ingestion
                </h3>
                <span className="ai-status-pill">
                  <Sparkles size={13} aria-hidden="true" />
                  Qdrant-ready
                </span>
              </div>

              <form onSubmit={handleIngest} className="ai-ingest-form">
                <div className="form-group">
                  <label className="form-label" htmlFor="ai-doc-project">Scope project code</label>
                  <select
                    id="ai-doc-project"
                    className="form-select"
                    value={docProject}
                    onChange={(event) => setDocProject(event.target.value)}
                  >
                    {projectOptions.map((code) => (
                      <option key={code} value={code}>{code}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="ai-doc-title">Document title</label>
                  <input
                    id="ai-doc-title"
                    type="text"
                    className="form-input"
                    required
                    value={docTitle}
                    onChange={(event) => setDocTitle(event.target.value)}
                    placeholder="e.g. GeoMx staining protocol batch 4"
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="ai-doc-content">Raw text content</label>
                  <textarea
                    id="ai-doc-content"
                    className="form-textarea ai-ingest-textarea"
                    value={docContent}
                    onChange={(event) => setDocContent(event.target.value)}
                    rows={10}
                    required
                    placeholder="Paste full document, SOP, protocol, code notes, or manual transcript here..."
                  />
                </div>

                <div className="ai-ingest-actions">
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={ingesting || !docTitle.trim() || !docContent.trim()}
                  >
                    {ingesting ? <Loader2 size={16} className="spin" aria-hidden="true" /> : <UploadCloud size={16} aria-hidden="true" />}
                    {ingesting ? 'Indexing…' : 'Run vector ingestion'}
                  </button>

                  <span className="ai-ingest-hint">
                    Text is sent through the authenticated backend. Success only means indexed if backend confirms chunks.
                  </span>
                </div>
              </form>

              {ingestStatus && (
                <div className={`ai-ingest-status ai-ingest-status--${statusToneFromMessage(ingestStatus)}`}>
                  {statusToneFromMessage(ingestStatus) === 'danger' ? (
                    <AlertTriangle size={16} aria-hidden="true" />
                  ) : statusToneFromMessage(ingestStatus) === 'success' ? (
                    <Check size={16} aria-hidden="true" />
                  ) : (
                    <Layers size={16} aria-hidden="true" />
                  )}
                  <span>{ingestStatus}</span>
                </div>
              )}
            </div>
          </section>
        )}

        {subTab === 'models' && (
          <section className="ai-lab-tab-panel">
            <div className="page-header ai-lab-page-header">
              <span className="assistant-eyebrow">
                <Cpu size={14} aria-hidden="true" />
                Registry
              </span>
              <h2>Deep learning model registry</h2>
              <p>Overview of neural network models active on local workstations, servers, and regional cluster environments.</p>
            </div>

            <div className="panel ai-models-panel">
              <div className="ai-panel-title-row">
                <h3 className="panel-title">
                  <Cpu size={18} aria-hidden="true" />
                  Active models
                </h3>

                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={fetchModels}
                  disabled={loadingModels}
                >
                  {loadingModels ? <Loader2 size={14} className="spin" aria-hidden="true" /> : <Database size={14} aria-hidden="true" />}
                  Refresh
                </button>
              </div>

              {loadingModels ? (
                <div className="ai-empty-state">
                  <Loader2 size={26} className="spin" aria-hidden="true" />
                  <p>Loading registry records…</p>
                </div>
              ) : modelsError ? (
                <div className="ai-empty-state ai-empty-state--danger">
                  <AlertTriangle size={26} aria-hidden="true" />
                  <p>{modelsError}</p>
                </div>
              ) : models.length === 0 ? (
                <div className="ai-empty-state">
                  <FileText size={28} aria-hidden="true" />
                  <p>No AI models registered in PostgreSQL schemas.</p>
                </div>
              ) : (
                <div className="ai-model-card-grid">
                  {models.map((model) => (
                    <article key={model.model_id || `${model.model_name}-${model.version}`} className="ai-model-card">
                      <div className="ai-model-card__header">
                        <div>
                          <h4>🤖 {model.model_name}</h4>
                          <p>v{model.version || 'unknown'}</p>
                        </div>
                        <span>{model.framework || 'framework n/a'}</span>
                      </div>

                      <p className="ai-model-card__desc">{model.description || 'No description recorded.'}</p>

                      <div className="ai-model-card__meta">
                        <div>Task area: <strong>{model.task_type || 'unknown'}</strong></div>
                        <div>Target environment: <code>{model.target_hardware || 'not specified'}</code></div>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </div>
          </section>
        )}
      </main>
    </section>
  );
}

function PromptsLibraryTab() {
  const [copiedIndex, setCopiedIndex] = useState(null);

  const prompts = [
    {
      title: 'Paper abstract improver',
      icon: '✍️',
      desc: 'Paste raw results, cohort counts, and spatial findings to generate a professional abstract.',
      prompt:
        'Act as an expert bioinformatician and clinical-spatial oncology scientist. Review the following raw research observations and draft a cohesive, highly structured abstract suitable for EACR/AACR. Structure: Background, Methods, Results with statistics, and Conclusions.',
    },
    {
      title: 'Code script refactoring',
      icon: '⚙️',
      desc: 'Optimize Python or R scripts for memory, parallelism, readability, and reproducibility.',
      prompt:
        'Analyze the following Python/R script for cell phenotyping or spatial clustering. Optimize it for large data arrays, add clear comments, modularize operations, and minimize memory pressure to prevent OOM errors.',
    },
    {
      title: 'Logbook summarizer',
      icon: '📓',
      desc: 'Compile meeting notes and lab updates into a clean system-of-record entry.',
      prompt:
        'Given these meeting updates and raw notebook items, synthesize them into one formal system-of-record note. Include: 1) what was discussed, 2) major gating or panel exclusions, 3) action checklist with assignees, and 4) timeline milestones.',
    },
  ];

  const copyPrompt = async (prompt, index) => {
    try {
      await navigator.clipboard.writeText(prompt);
      setCopiedIndex(index);
      window.setTimeout(() => setCopiedIndex(null), 1400);
    } catch {
      setCopiedIndex(null);
    }
  };

  return (
    <section className="ai-lab-tab-panel">
      <div className="page-header ai-lab-page-header">
        <span className="assistant-eyebrow">
          <Clipboard size={14} aria-hidden="true" />
          Prompt system
        </span>
        <h2>AI prompt engineering library</h2>
        <p>Templates to improve manuscript writing, computational workflows, and structured research documentation.</p>
      </div>

      <div className="ai-prompt-grid">
        {prompts.map((prompt, index) => (
          <article key={prompt.title} className="panel ai-prompt-card">
            <div className="ai-prompt-card__header">
              <span>{prompt.icon}</span>
              <div>
                <h4>{prompt.title}</h4>
                <p>{prompt.desc}</p>
              </div>
            </div>

            <div className="ai-prompt-template">
              <div className="ai-prompt-template__label">Prompt template</div>
              <p>{prompt.prompt}</p>

              <button
                type="button"
                className="btn btn-secondary btn-sm ai-copy-template-btn"
                onClick={() => copyPrompt(prompt.prompt, index)}
              >
                {copiedIndex === index ? <Check size={14} aria-hidden="true" /> : <Clipboard size={14} aria-hidden="true" />}
                {copiedIndex === index ? 'Copied' : 'Copy'}
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

```

### `apps/web/src/screens/LabKnowledgeScreen.jsx`

```javascript

import { useCallback, useEffect, useState } from 'react';
import { BookOpen, Loader2, FileText, ChevronRight, Search, Folder, AlertCircle } from 'lucide-react';
import DocumentViewer from '../components/DocumentViewer.jsx';
import { databaseSectionIdForSub } from '../config/databaseSections.js';
import { teamDirectory } from '../data/teamDirectory.js';
import LabTeamRoster from '../components/LabTeamRoster.jsx';
import { activityLogs } from '../data/activityLogs.js';
import { Users, Activity } from 'lucide-react';

export default function LabKnowledgeScreen({ subId, navSub, API_URL, title, description }) {
  const sectionId = databaseSectionIdForSub(subId, navSub);
  
  const [catalog, setCatalog] = useState(null);
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [catalogError, setCatalogError] = useState(null);
  
  const [selectedDocId, setSelectedDocId] = useState(null);
  const [query, setQuery] = useState('');
  const [expandedSections, setExpandedSections] = useState({});

  useEffect(() => {
    let mounted = true;
    setLoadingCatalog(true);
    fetch('/database/catalog.json')
      .then(res => {
        if (!res.ok) throw new Error('Failed to load static database catalog.');
        return res.json();
      })
      .then(data => {
        if (mounted) {
          setCatalog(data);
          // Auto-expand all sections initially
          const initialExpand = {};
          Object.keys(data.sections || {}).forEach(sec => {
            initialExpand[sec] = true;
          });
          setExpandedSections(initialExpand);
          setLoadingCatalog(false);
        }
      })
      .catch(err => {
        if (mounted) {
          console.error(err);
          setCatalogError(err.message);
          setLoadingCatalog(false);
        }
      });
      
    return () => mounted = false;
  }, []);

  const toggleSection = (sec) => {
    setExpandedSections(prev => ({ ...prev, [sec]: !prev[sec] }));
  };

  const getFilteredSections = () => {
    if (!catalog || !catalog.sections) return {};
    const q = query.trim().toLowerCase();
    
    // Map legacy sectionId to new sections.
    // We want to hardcode the scoping so that searches don't bleed across tabs.
    let allowedSections = [];
    
    if (!sectionId || sectionId?.startsWith('overview_') || sectionId === 'get_started') {
      allowedSections = ['01_Overview', '00_General_Knowledge'];
    } else if (sectionId?.startsWith('orders_')) {
      allowedSections = ['02_Orders'];
    } else if (sectionId?.startsWith('social_')) {
      allowedSections = ['03_Social'];
    } else if (sectionId === 'wet_lab_files') {
      allowedSections = ['04_Wet_Lab'];
    } else {
      allowedSections = Object.keys(catalog.sections);
    }

    const filtered = {};
    for (const sec of allowedSections) {
      const docs = catalog.sections[sec] || [];
      const matchedDocs = docs.filter(doc => 
        doc.title.toLowerCase().includes(q) || 
        doc.path.toLowerCase().includes(q)
      );
      if (matchedDocs.length > 0) {
        filtered[sec] = matchedDocs;
      }
    }
    return filtered;
  };

  const filteredSections = getFilteredSections();

  return (
    <div className="stack-md lab-knowledge-screen" style={{ height: 'calc(100vh - 60px)', display: 'flex', flexDirection: 'column' }}>
      {/* Top Special Legacy Panels */}
      {sectionId === 'overview_personnel' && (
        <div className="panel" style={{ flexShrink: 0 }}>
          <h3 className="panel-title">
            <Users size={18} /> Team Directory
          </h3>
          <p className="panel-lead prose-block">
            {description || 'Personnel records and support documents.'}
          </p>
          <LabTeamRoster members={teamDirectory} className="lab-team-panel__roster lab-team-panel__roster--spaced" />
        </div>
      )}

      {sectionId === 'social_misc' && (
        <div className="panel" style={{ flexShrink: 0 }}>
          <h3 className="panel-title">
            <Activity size={18} /> Platform Activity & Social
          </h3>
          <p className="panel-lead prose-block">
            {description || 'Recent events and platform logs.'}
          </p>
          <ul className="stack-sm text-footnote" style={{ listStyle: 'none', padding: 0, marginTop: '1rem' }}>
            {activityLogs.map((log) => (
              <li key={log.log_id} className="overview-news-row" style={{ flexDirection: 'column', alignItems: 'flex-start' }}>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  <strong className="text-body">{log.actor}</strong>
                  <span className="text-caption muted">{new Date(log.created_at).toLocaleString()}</span>
                </div>
                <span className="text-caption" style={{ marginTop: '0.25rem' }}>{log.event_type}</span>
                <p className="text-caption" style={{ marginTop: '0.25rem' }}>{log.description}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Main Master-Detail UI */}
      {sectionId !== 'overview_personnel' && sectionId !== 'social_misc' && (
        <div className="panel" style={{ flexShrink: 0 }}>
          <h3 className="panel-title">
            <BookOpen size={18} /> {title || 'Static Knowledge Database'}
          </h3>
          <p className="panel-lead prose-block">
            {description || 'Explore digitized files securely extracted from the internal file systems. Content is loaded statically without API calls.'}
          </p>
          <div className="disk-pad-toolbar" style={{ marginTop: '1rem' }}>
            <input
              type="search"
              className="input"
              placeholder='Search file names or paths...'
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Search catalog"
            />
          </div>
        </div>
      )}

      <div className="lab-knowledge-layout" style={{ flex: 1, minHeight: 0, display: 'flex', gap: '1rem', marginTop: sectionId === 'overview_personnel' ? '1rem' : 0 }}>
        {/* Master Sidebar */}
        <div className="lab-knowledge-sidebar panel" style={{ flex: '0 0 320px', overflowY: 'auto', padding: '1rem' }}>
          {loadingCatalog && (
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', color: 'var(--mac-ink-muted)' }}>
              <Loader2 size={16} className="spin" /> Loading catalog...
            </div>
          )}
          {catalogError && (
            <div style={{ color: 'var(--mac-destructive)' }}>
              <AlertCircle size={16} /> {catalogError}
            </div>
          )}
          
          {!loadingCatalog && !catalogError && Object.keys(filteredSections).length === 0 && (
            <p className="text-caption muted">No matching files found.</p>
          )}

          {!loadingCatalog && !catalogError && Object.keys(filteredSections).map(sec => (
            <div key={sec} style={{ marginBottom: '1rem' }}>
              <button 
                className="section-header-btn" 
                onClick={() => toggleSection(sec)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '0.5rem', width: '100%', 
                  background: 'none', border: 'none', cursor: 'pointer', textAlign: 'left',
                  padding: '0.25rem 0', color: 'var(--mac-ink)', fontWeight: 600, fontSize: '0.9rem'
                }}
              >
                {expandedSections[sec] ? <ChevronRight size={14} style={{ transform: 'rotate(90deg)' }}/> : <ChevronRight size={14} />}
                <Folder size={16} style={{ color: 'var(--mac-blue)' }} />
                {sec.replace(/^[0-9]+_/, '').replace(/_/g, ' ')} ({filteredSections[sec].length})
              </button>
              
              {expandedSections[sec] && (
                <ul style={{ listStyle: 'none', padding: 0, margin: '0.25rem 0 0 1.5rem', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                  {filteredSections[sec].map(doc => (
                    <li key={doc.id}>
                      <button
                        className={`doc-list-btn ${selectedDocId === doc.id ? 'active' : ''}`}
                        onClick={() => setSelectedDocId(doc.id)}
                        style={{
                          display: 'flex', alignItems: 'flex-start', gap: '0.5rem', width: '100%', 
                          background: selectedDocId === doc.id ? 'var(--mac-blue-alpha)' : 'none', 
                          border: 'none', cursor: 'pointer', textAlign: 'left',
                          padding: '0.35rem 0.5rem', borderRadius: '4px',
                          color: selectedDocId === doc.id ? 'var(--mac-blue)' : 'var(--mac-ink)',
                          fontSize: '0.85rem'
                        }}
                      >
                        <FileText size={14} style={{ flexShrink: 0, marginTop: '2px' }} />
                        <span style={{ wordBreak: 'break-word', lineHeight: 1.3 }}>{doc.title}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>

        {/* Detail View */}
        <div className="lab-knowledge-detail" style={{ flex: 1, minWidth: 0 }}>
          <DocumentViewer documentId={selectedDocId} />
        </div>
      </div>
    </div>
  );
}

```

### `apps/web/src/components/ProjectDocumentsBrowser.jsx`

```javascript
import { useEffect, useMemo, useState } from 'react';
import {
  Archive,
  BarChart3,
  BookOpen,
  Calendar,
  ClipboardList,
  FileText,
  FlaskConical,
  FolderOpen,
  Loader2,
  Users,
} from 'lucide-react';
import DocumentPreviewPane from './DocumentPreviewPane.jsx';
import DocumentFileSearch from './DocumentFileSearch.jsx';
import SmartLink from './SmartLink.jsx';
import {
  documentDisplayExcerpt,
  getChunkTextForFile,
  labDatabaseAssetUrl,
} from '../utils/labDatabaseUtils.js';
import { isJunkPreviewText } from '../utils/textCleanup.js';
import { inferExtension } from '../utils/fileTypeMeta.js';
import { getChunkTextForProjectFile, normalizeRelPath } from '../utils/folderBrowserUtils.js';
import { getMediaPreviewKind } from '../utils/mediaPreviewKind.js';
import { buildMediaGallery, mergeGalleryItem } from '../utils/mediaGalleryUtils.js';
import { useSpreadsheetPreview } from '../hooks/useSpreadsheetPreview.js';
import { useRawFilePreview } from '../hooks/useRawFilePreview.js';
import { getFilePreviewKind, shouldFetchRawFile } from '../utils/filePreviewKind.js';
import { projectAssetUrl } from '../utils/digitalTwinUtils.js';
import { useTaskpad } from '../contexts/TaskpadContext.jsx';
import {
  collectProjectDocuments,
  flattenCategoryOrder,
  groupDocumentsByCategory,
} from '../utils/documentBrowserUtils.js';
import {
  buildProjectTabCategoryGroups,
  getProjectTabDocumentConfig,
  projectDocumentTitle,
} from '../utils/projectDocumentCategories.js';
import { findProjectLogFile, isProjectLogFile } from '../utils/projectLogUtils.js';
import { getProjectLogContentFromTwin } from '../utils/projectLogContent.js';
import {
  getResearchMaterialsForProject,
  loadResearchMaterialsTwin,
} from '../utils/researchMaterialsRouting.js';
import DocumentCategoryFileList, {
  countGroupedFiles,
} from './DocumentCategoryFileList.jsx';
import { useGuiT } from '../i18n/useGuiT.js';

const CATEGORY_ICONS = {
  root: FolderOpen,
  wet_lab: FlaskConical,
  dry_lab: BarChart3,
  protocols: FileText,
  schedules: Calendar,
  figures: BarChart3,
  abstracts: BookOpen,
  posters: BookOpen,
  manuscripts: BookOpen,
  peer_review: FileText,
  meeting_notes: ClipboardList,
  archive_root: Archive,
};

const EDITABLE_EXTENSIONS = new Set(['.md', '.txt', '.html', '.rtf']);

function resolveDocumentTitle(doc) {
  if (doc?.isResearchMaterial && doc.display_title) return doc.display_title;
  return projectDocumentTitle(doc);
}

export default function ProjectDocumentsBrowser({
  twin,
  projectCode,
  API_URL,
  workspaceTab,
  defaultCategory: defaultCategoryProp,
  className = 'project-documents-browser',
  taskpadMenuItems,
  onSelectedPathChange,
}) {
  const [selectedPath, setSelectedPath] = useState(null);
  const [fileQuery, setFileQuery] = useState('');
  const [researchDocs, setResearchDocs] = useState([]);
  const [researchTwin, setResearchTwin] = useState(null);
  const { openTaskpad, openProjectLogTaskpad } = useTaskpad();
  const { t, localizeCategories } = useGuiT();

  useEffect(() => {
    if (workspaceTab !== 'writing' || !projectCode) {
      setResearchDocs([]);
      setResearchTwin(null);
      return undefined;
    }

    let alive = true;
    getResearchMaterialsForProject(projectCode)
      .then((docs) => {
        if (!alive) return;
        setResearchDocs(docs);
      })
      .catch(() => {
        if (alive) setResearchDocs([]);
      });

    loadResearchMaterialsTwin().then((twin) => {
      if (alive) setResearchTwin(twin);
    });

    return () => {
      alive = false;
    };
  }, [workspaceTab, projectCode]);

  const projectLogFile = useMemo(() => findProjectLogFile(twin), [twin]);

  const allDocs = useMemo(() => {
    if (!twin) return workspaceTab === 'writing' ? [...researchDocs] : [];
    const config = getProjectTabDocumentConfig(workspaceTab, [], projectCode);
    const projectDocs = collectProjectDocuments(twin, {
      categorizePath: config.categorizePath,
      documentTitle: projectDocumentTitle,
      tabFilter: config.tabFilter,
    });
    if (workspaceTab !== 'writing' || !researchDocs.length) return projectDocs;

    const seen = new Set(projectDocs.map((d) => d.path));
    const merged = [...projectDocs];
    for (const doc of researchDocs) {
      if (!seen.has(doc.path)) merged.push(doc);
    }
    return merged;
  }, [twin, workspaceTab, projectCode, researchDocs]);

  const categoryGroups = useMemo(
    () => buildProjectTabCategoryGroups(workspaceTab, allDocs),
    [workspaceTab, allDocs]
  );

  const localizedCategoryGroups = useMemo(
    () => localizeCategories(categoryGroups),
    [categoryGroups, localizeCategories]
  );

  const categoryOrder = useMemo(
    () => flattenCategoryOrder(localizedCategoryGroups),
    [localizedCategoryGroups]
  );
  const grouped = useMemo(
    () => groupDocumentsByCategory(allDocs, categoryOrder),
    [allDocs, categoryOrder]
  );

  useEffect(() => {
    const logPath = projectLogFile?.path;
    if (workspaceTab === 'log' && logPath && (grouped.project_log || []).some((d) => d.path === logPath)) {
      setSelectedPath(logPath);
    } else {
      setSelectedPath(null);
    }
    setFileQuery('');
  }, [workspaceTab, categoryOrder.join(','), twin?.processed_at, projectLogFile?.path, grouped]);

  useEffect(() => {
    onSelectedPathChange?.(selectedPath);
  }, [selectedPath, onSelectedPathChange]);

  const visibleFileCount = useMemo(
    () =>
      countGroupedFiles(localizedCategoryGroups, grouped, fileQuery, resolveDocumentTitle),
    [localizedCategoryGroups, grouped, fileQuery]
  );

  const fileSearchControl = (
    <DocumentFileSearch
      compact
      value={fileQuery}
      onChange={setFileQuery}
      fileCount={visibleFileCount}
      searchPlaceholder={t('docs.searchPlaceholder')}
      searchAria={t('docs.searchFiles')}
      filesLabel={t('docs.filesInSection', '', { count: visibleFileCount })}
    />
  );

  const selectedDoc = useMemo(
    () => allDocs.find((d) => d.path === selectedPath) || null,
    [allDocs, selectedPath]
  );

  const selectedExt = selectedDoc
    ? inferExtension(selectedDoc.name, selectedDoc.extension)
    : '';
  const isPdf = selectedExt === '.pdf';
  const mediaKind = getMediaPreviewKind(selectedExt);
  const previewKind = getFilePreviewKind(selectedExt, selectedDoc?.path);
  const isSpreadsheet = previewKind === 'spreadsheet';
  const isEditable = EDITABLE_EXTENSIONS.has(selectedExt);

  const previewText = useMemo(() => {
    if (!selectedDoc) return null;
    const fromChunks = selectedDoc.isResearchMaterial
      ? getChunkTextForFile(researchTwin, selectedDoc.researchMaterialOriginalPath)
      : getChunkTextForProjectFile(twin, selectedDoc.path);
    const excerpt = selectedDoc.excerpt || documentDisplayExcerpt(selectedDoc, 12000);
    const raw = (fromChunks || excerpt || '').trim();
    if (!raw || isJunkPreviewText(raw)) return null;
    return raw;
  }, [selectedDoc, twin, researchTwin]);

  const assetUrl = useMemo(() => {
    if (!selectedDoc) return null;
    if (selectedDoc.isResearchMaterial) {
      return labDatabaseAssetUrl(
        selectedDoc.researchMaterialRoot,
        selectedDoc.researchMaterialOriginalPath
      );
    }
    return projectAssetUrl(projectCode, selectedDoc.path, API_URL, twin?.content_root);
  }, [selectedDoc, projectCode, API_URL, twin?.content_root]);

  const spreadsheetPreview = useSpreadsheetPreview(
    isSpreadsheet && assetUrl ? assetUrl : null,
    selectedExt
  );
  const scriptFallbackText = useMemo(() => {
    if (!selectedDoc || !twin || !shouldFetchRawFile(previewKind)) return null;
    const fromChunks = getChunkTextForProjectFile(twin, selectedDoc.path);
    if (fromChunks?.trim()) return fromChunks;
    const excerpt = selectedDoc.excerpt || documentDisplayExcerpt(selectedDoc, 12000);
    const raw = (excerpt || '').trim();
    return raw && !isJunkPreviewText(raw) ? raw : null;
  }, [selectedDoc, twin, previewKind]);

  const rawFilePreview = useRawFilePreview(assetUrl, previewKind, {
    projectCode,
    relativePath: selectedDoc?.path,
    fallbackText: scriptFallbackText,
  });

  const siblingPdf = useMemo(() => {
    if (!selectedDoc || isPdf) return null;
    const stem = selectedDoc.path.replace(/\.[^.]+$/, '');
    const pdfPath = `${stem}.pdf`;
    return allDocs.find((doc) => doc.path === pdfPath) || null;
  }, [selectedDoc, allDocs, isPdf]);

  const pdfPreviewUrl = useMemo(() => {
    if (isPdf && assetUrl) return assetUrl;
    if (siblingPdf) {
      return projectAssetUrl(projectCode, siblingPdf.path, API_URL, twin?.content_root);
    }
    return null;
  }, [isPdf, assetUrl, siblingPdf, projectCode, API_URL, twin?.content_root]);

  const resolveDocAssetUrl = useMemo(
    () => (doc) => {
      if (!doc) return null;
      if (doc.isResearchMaterial) {
        return labDatabaseAssetUrl(doc.researchMaterialRoot, doc.researchMaterialOriginalPath);
      }
      return projectAssetUrl(projectCode, doc.path, API_URL, twin?.content_root);
    },
    [projectCode, API_URL, twin?.content_root]
  );

  const mediaGallery = useMemo(() => {
    if (!selectedDoc || !mediaKind) return [];
    const siblings = buildMediaGallery(
      selectedDoc,
      allDocs,
      resolveDocAssetUrl,
      resolveDocumentTitle
    );
    return mergeGalleryItem(selectedDoc, siblings, resolveDocAssetUrl, resolveDocumentTitle);
  }, [selectedDoc, allDocs, mediaKind, resolveDocAssetUrl, resolveDocumentTitle]);

  const contentRoot = twin?.content_root || twin?.folder_path || null;

  if (!twin) {
    return (
      <div className="panel" style={{ padding: '2rem', textAlign: 'center' }}>
        <Loader2 size={20} className="spin-inline" /> {t('docs.loadingProject')}
      </div>
    );
  }

  if (!allDocs.length) {
    return (
      <section className={`panel workspace-section data-pad data-pad--compact ${className}`}>
        <p className="text-footnote muted">{t('docs.noProjectFiles')}</p>
      </section>
    );
  }

  return (
    <section className={`panel workspace-section data-pad data-pad--compact data-pad--embedded ${className}`}>
      {contentRoot ? (
        <div className="data-pad-root data-pad-root--inline">
          <SmartLink href={contentRoot} showCopy maxLabelLen={48} />
        </div>
      ) : null}

      <div className="lab-docs-section-layout lab-docs-section-layout--grouped">
        <div className="lab-docs-section-main">

          <div
            className={`pfb-layout lab-docs-layout lab-docs-layout--compact lab-docs-layout--project${selectedDoc ? ' pfb-layout--editor-focus pfb-layout--doc-full' : ''}`}
          >
            <div className="pfb-column pfb-files-pane lab-doc-files-panel">
              <DocumentCategoryFileList
                categoryGroups={localizedCategoryGroups}
                grouped={grouped}
                fileQuery={fileQuery}
                documentTitle={resolveDocumentTitle}
                selectedPath={selectedPath}
                onSelectFile={setSelectedPath}
                categoryIcons={CATEGORY_ICONS}
                categoryLayout="horizontal-top"
                toolbarAfterTabs={fileSearchControl}
              />
            </div>

        <div className="pfb-column pfb-preview-pane pfb-preview-pane--editor-focus">
          {!selectedDoc ? (
            <p className="text-footnote muted" style={{ marginTop: '1rem' }}>
              {t('docs.selectFileEdit')}
            </p>
          ) : (
            <DocumentPreviewPane
              onBackToFiles={() => setSelectedPath(null)}
              title={resolveDocumentTitle(selectedDoc)}
              path={selectedDoc.path}
              extension={selectedDoc.extension || inferExtension(selectedDoc.name)}
              previewKind={previewKind}
              rawFilePreview={rawFilePreview}
              previewText={previewText}
              pdfPreviewUrl={pdfPreviewUrl}
              pdfThumbLabel={isPdf ? 'PDF' : 'PDF copy'}
              mediaKind={mediaKind}
              mediaUrl={assetUrl}
              mediaAlt={resolveDocumentTitle(selectedDoc)}
              mediaGallery={mediaGallery}
              onMediaNavigate={setSelectedPath}
              mediaLabels={{
                loading: t('docs.mediaLoading'),
                failed: t('docs.mediaFailed'),
                videoLoading: t('docs.videoLoading'),
                videoFailed: t('docs.videoFailed'),
                modelLoading: t('docs.modelLoading'),
                zoomIn: t('docs.mediaZoomIn'),
                zoomOut: t('docs.mediaZoomOut'),
                fit: t('docs.mediaFit'),
                actualSize: t('docs.mediaActualSize'),
                rotate: t('docs.mediaRotate'),
                fullscreen: t('docs.mediaFullscreen'),
                download: t('docs.openOriginal'),
                previous: t('docs.mediaPrevious'),
                next: t('docs.mediaNext'),
                hint: t('docs.modelHint'),
                play: t('docs.modelPlay'),
                pause: t('docs.modelPause'),
                autoRotate: t('docs.modelAutoRotate'),
                reset: t('docs.modelReset'),
              }}
              isEditable={isEditable && !isProjectLogFile(selectedDoc.path)}
              editorProps={
                isEditable && previewText && !isProjectLogFile(selectedDoc.path)
                  ? {
                      projectCode,
                      relativePath: normalizeRelPath(selectedDoc.path),
                      fileName: selectedDoc.name,
                      sectionLabel: selectedDoc.section_label,
                      initialContent: previewText,
                      onSaved: () => {},
                    }
                  : null
              }
              editorHint={
                isProjectLogFile(selectedDoc.path)
                  ? t('docs.taskpadEditorHint')
                  : null
              }
              spreadsheetPreview={isSpreadsheet ? spreadsheetPreview : null}
              spreadsheetFileUrl={isSpreadsheet ? assetUrl : null}
              spreadsheetLabels={{
                loading: t('docs.spreadsheetLoading'),
                repaired: t('docs.spreadsheetRepaired'),
                truncated: t('docs.spreadsheetTruncated'),
                empty: t('docs.spreadsheetEmpty'),
                failed: t('docs.spreadsheetFailed'),
                openOriginal: t('docs.openOriginal'),
              }}
              codeLabels={{
                loading: t('docs.codeLoading'),
                failed: t('docs.codeFailed'),
              }}
              emptyHint={t('docs.noTextPreview')}
              onCreateTask={(text) =>
                openTaskpad(text, {
                  section: workspaceTab,
                  projectCode,
                  filePath: selectedPath || undefined,
                  fileName: selectedDoc?.name || selectedDoc?.title,
                })
              }
              actions={
                <>
                  {isProjectLogFile(selectedDoc.path) ? (
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      onClick={() =>
                        openProjectLogTaskpad({
                          ...selectedDoc,
                          projectCode,
                          excerpt:
                            getProjectLogContentFromTwin(twin, selectedDoc)?.content ||
                            selectedDoc.excerpt ||
                            '',
                        })
                      }
                    >
                      {t('docs.editInTaskpad')}
                    </button>
                  ) : null}
                  {assetUrl ? (
                    <a
                      href={assetUrl}
                      className="btn btn-secondary btn-sm"
                      target="_blank"
                      rel="noreferrer"
                    >
                      {t('docs.openOriginal')}
                    </a>
                  ) : null}
                </>
              }
            />
          )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

```

---

*End of unified search audit bundle.*
