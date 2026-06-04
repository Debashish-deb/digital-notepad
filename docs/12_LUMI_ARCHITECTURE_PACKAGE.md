# 12 — LUMI / Lab Assistant Platform — Chief Architecture Package

**Role:** Chief Knowledge Architect deliverable (evidence-grounded).  
**Evidence corpus:** `/Users/debashishdeb/Downloads/OMEIA-AI/database` (4,800 files, 1,029 directories, surveyed 2026-06-03).  
**Implementation mirror:** `farkki_ai_platform_blueprint/` (FastAPI + React + local Postgres/Qdrant).  
**Production target (user brief):** DataCloud WebDAV `https://datacloud.helsinki.fi/remote.php/dav/files/debdeba%40helsinki.fi` → canonical root `/farkkila/LAB-ASSISTANT-PLATFORM`; metadata in Supabase; auth Firebase Email/Password; ~30 allowlisted users.

**Confidence key:** High ≥0.86 · Probable 0.61–0.85 · Weak 0.31–0.60 · Unknown ≤0.30.

---

## Evidence used (search protocol)

| Source | Finding |
|--------|---------|
| `raw_asset_inventory_summary.json` | 4,800 assets; domains: project 3913, lab_operations 483, social 222, administration 112, orders 70 |
| `find database -maxdepth 3` | Top corpus: `database/projects`, `Overview`, `WET_LAB`, `ORDERS & RELATED INFORMATION`, `SOCIAL & MISCELLANEOUS` |
| `navigation.js` + `App.jsx` | 8 top nav areas; lab sections → `lab_knowledge`; projects → `projects` + digital twin APIs |
| `database_sections.py` | 9 lab section roots (fixed Overview paths, no `GENERAL LAB INFORMATION`) |
| `main.py` | 60+ endpoints; vault, lab knowledge, project-files; lab file tree **410** |
| `sql/*.sql` + `111_raw_asset_vault.sql` | core, platform, rag, security, assay, features; `platform.raw_asset_vault` (dev) |
| `projects_catalog.json` | 37 catalog projects; 7 catalog-only without disk folder (validation warning) |
| `processed_projects/` | 47 project twins + 9 `lab__*` section twins |
| Docs 00–11 | Prior architecture direction; doc 11 is primary twin report |

**Not evidenced in repo:** Live Firebase integration, DataCloud connector I/O, P-drive connector, R2 upload pipeline, Supabase hosted project URL, authoritative 30-user allowlist, admin email values.

---

## 1. Laboratory Digital Twin Report

The laboratory is modeled as a **partially observed knowledge graph** where every file, folder, page, schema row, and API route is evidence—not canonical truth until reviewed.

### 1.1 Observed institutional domains (filesystem)

| Corpus section | Files (inventory) | Primary knowledge role |
|----------------|-------------------|-------------------------|
| `database/projects/**` | ~3,913 | Research memory: methods, figures, scripts, meetings, writing |
| `database/WET_LAB/**` | ~483 (lab_operations) | Protocols, inventories, GeoMx/Xenium notes |
| `database/Overview/**` | subset of administration 112 | Onboarding, guidelines, permits, personnel, cleaning |
| `database/ORDERS & RELATED INFORMATION/**` | 70 | Procurement, billing, vendor archive |
| `database/SOCIAL & MISCELLANEOUS/**` | 222 | Social memory, outreach, photos, retreats |
| `database/projects/RESEARCH MATERIALS/**` | inside project domain | Posters, abstracts, peer-review—**logically project-adjacent** |

### 1.2 Digital twin layers

```text
Evidence layer (DataCloud / local mirror / optional P-drive)
  → Raw Knowledge Vault (immediate ingest, no perfect category required)
  → Review queue (confidence < 0.86 or sensitive paths)
  → Document registry (extracted text + chunks)
  → Asset registry (metadata + checksums + storage provider)
  → Canonical entities (projects, samples, protocols — only after review)
  → Knowledge graph assertions (candidate → asserted)
  → Search indexes (metadata + vectors + future graph)
  → Page/domain views (UI lenses, not storage roots)
```

### 1.3 Twin questions the system must answer (target)

| Question | Primary registry | Status |
|----------|------------------|--------|
| What exists? | `platform.raw_asset_vault`, `rag.document_source` | Partial (local) |
| Where is it? | `logical_path`, `where_to_find`, project twin | Partial |
| Who owns it? | `platform.researcher`, project members | Prototype (catalog/DB) |
| What generated it? | `platform.pipeline_run`, provenance JSON | Partial |
| What page/domain? | **Gap:** `platform.page_domain` not implemented | Missing |
| What breaks if it changes? | KG + dependency edges | Planned (Neo4j designed, weak runtime) |

**Implementation implication:** Prioritize vault + document registry + page-domain registry before expanding RAG personas.

---

## 2. Page-Level Architecture

### 2.1 Target top-level domains (approved working model)

Fifteen target domains from brief. **Current UI** implements **8** top-level nav groups (`navigation.js`). Mapping:

| Target domain | Current UI home | Status |
|---------------|-----------------|--------|
| Dashboard | Overview → Lab dashboard | Partial |
| Overview / Lab Operations | Overview (lab_knowledge subs) | Partial |
| Research Hub | *No dedicated hub* | **Missing** (see CANDIDATE) |
| Projects | Projects & Data → portfolio | Implemented |
| Data & Storage | *No top-level* | **Missing** (API only: `/api/storage/roots`, `/api/vault/*`) |
| Computational Hub | Computational Hub | Implemented (BioinformaticsHub) |
| CyCIF / Image Analysis | CyCif | Partial (pipeline/install/structure) |
| Wet Lab | Wet-lab | Partial |
| Orders & Procurement | Orders & related | Partial |
| Social & Miscellaneous | Social | Partial |
| Knowledge Base | *Merged into lab_knowledge* | Partial |
| Notebook / Wiki | notebook, wiki, decisions | Partial |
| Tasks & Decisions | tasks, decisions | Partial |
| AI Lab Assistant | AI Lab Assistant | Implemented (copilot forward) |
| Administration | *None* | **Missing** |

### 2.2 CANDIDATE_PAGE_DOMAIN proposals

| Name | Parent | Reason | Evidence | Confidence | When |
|------|--------|--------|----------|------------|------|
| **Research Hub** | Top-level | Consolidate research themes, publications, methods—not only “General lab information” | `RESEARCH MATERIALS`, catalog disease_focus fields, doc 00 | 0.72 | Later (links to Projects) |
| **Data & Storage** | Top-level | Vault, connectors, storage health—per user brief | `/api/vault/*`, `/api/storage/roots`, doc 06 | 0.88 | **Create now** (admin-lite UI) |
| **Knowledge Base** | Top-level or under Overview | Review queue, uncategorized assets, semantic search | lab_knowledge + vault search | 0.80 | Merge with lab_knowledge until split |
| **Administration** | Top-level | Firebase allowlist, ingestion jobs, review queue | security.* schema, brief | 0.90 | **Create now** (backend-first) |
| **Lab Coats** | Overview | User brief subpage; coat policy may live in guidelines/onboarding | NEEDS_USER_CONFIRMATION — no path literal “lab coat” required in inventory | 0.45 | Later; search keywords in WET_LAB/Overview |
| **Safety** | Overview | Standard lab ops | Guidelines folder | 0.55 | Later |
| **Access Requests** | Overview | Onboarding docs | Onboarding folder | 0.60 | Later |

**NEEDS_ARCHITECT_REVIEW:** Whether `projects/RESEARCH MATERIALS` stays under Overview (`overview_research_materials`) or moves under **Projects → Research Materials** only (brief says Projects by default).

---

## 3. Page-to-Entity Map (summary)

| Page domain | Primary entities | Secondary entities |
|-------------|----------------|-------------------|
| Dashboard | Project, Task, AuditLog, ReviewTask | Asset (counts), Document |
| Overview / Lab Operations | Document, SOP, Researcher, Training Item | Protocol, Permission |
| Research Hub | Publication, Project, Method | Collaboration, Figure |
| Projects | Project, Sample, Dataset, Document, PipelineRun | Decision, Meeting, Script |
| Data & Storage | Asset, StorageLocation, StorageObject | StorageConnector, IngestionJob |
| Computational Hub | Software, Script, LUMI Job, InstallationRecipe | PipelineStage, TroubleshootingNote |
| CyCIF / Image Analysis | PipelineRun, OME-TIFF (metadata), Mask (metadata), MarkerPanel | AnalysisOutput, QC record |
| Wet Lab | Protocol, SOP, Antibody, Experiment, Reagent | Sample, Instrument |
| Orders & Procurement | Vendor, Order, Invoice, ProcurementItem | Shipment |
| Social & Miscellaneous | Event, Photo, Visitor, Website Page | Outreach Item |
| Knowledge Base | Document, Asset, KnowledgeEntity | ReviewTask |
| Notebook / Wiki | NotebookEntry, Meeting, Decision | ExperimentNote |
| Tasks & Decisions | Task, Decision, ReviewTask | AuditLog |
| AI Lab Assistant | Document chunk, Tool run trace | Conversation (low priority) |
| Administration | User, Role, Permission, IngestionJob | StorageConnector |

---

## 4. Page-to-Database Map (summary)

**Reuse existing tables** (do not duplicate):

| Page domain | Existing tables (evidence: `sql/`) | Gaps to add |
|-------------|-----------------------------------|-------------|
| Projects | `core.project`, `platform.project_extension`, `platform.project_member`, `platform.folder_catalog`, `platform.dataset_catalog`, `platform.pipeline_run` | `platform.page_domain`, project-section links |
| Knowledge / Lab | `rag.document_source`, `rag.document_chunk`, `rag.vector_point_registry`, `platform.document_ingestion` | Unified document registry view |
| Vault / Data | `platform.raw_asset_vault` (111) | `platform.storage_roots`, `platform.storage_objects`, `platform.ingestion_jobs` |
| Security / Admin | `security.user_account`, `security.role`, `security.project_access_policy` | Firebase UID mapping, `allowed_users`, `registration_requests` |
| Features / Clinical | `features.*`, `clinical.*` (per 030, 060) | Clinical dictionary completeness |
| Notebook | `platform.notebook_entry`, decisions, wiki endpoints | — |

**Local dev vs production:** Code uses `POSTGRES_CONN` (local Docker). Production target = **Supabase PostgreSQL** with identical schema migration path.

---

## 5. Page-to-Storage Map (summary)

| Page domain | Primary storage | Metadata home | Previews |
|-------------|---------------|---------------|----------|
| Projects (large binaries) | DataCloud WebDAV `/farkkila/LAB-ASSISTANT-PLATFORM/...` | Supabase asset + dataset registry | R2 thumbnails |
| Lab operations docs | DataCloud | Supabase vault + `rag.*` | R2 optional PDF |
| Orders / personnel | DataCloud **restricted** paths | Supabase metadata only; tight RBAC | Usually none |
| Social photos | DataCloud or mirror | Supabase metadata | R2 thumbnails |
| Computational scripts | DataCloud + GitHub (project_scripts) | Supabase + vectors | Code preview text |
| CyCIF OME-TIFF / masks | DataCloud / P-drive | **Never** Supabase blob | R2 thumbnail only |
| Local dev mirror | `OMEIA-AI/database` | `platform.raw_asset_vault` + processed JSON | API-served project assets |

**Absolute rules (brief):** Frontend → API → Firebase verify → Supabase permission → connector. No raw WebDAV paths in UI.

**Current violation risk (dev):** `/api/projects/{code}/asset` and `projects-static` read local disk—acceptable for dev **only** with path sanitization; production must use connector + signed URLs.

---

## 6. Real Asset Inventory Assessment

| Metric | Value | Confidence |
|--------|-------|------------|
| Total files | 4,800 | High (inventory run) |
| Needs review (confidence < 0.86) | 3,913 | High |
| Vector-eligible pending review | 2,067 | High |
| Metadata-only (figures/images/video/binary) | 2,223 | High |
| Duplicate checksum groups | NEEDS_USER_CONFIRMATION — run `/api/vault/dedupe-report` | — |

**Top extensions:** `.png` 1310, `.pdf` 681, `.svg` 530, `.docx` 493, `.xlsx` 341, `.pptx` 247.

**NEEDS_USER_CONFIRMATION:** Mapping from local mirror paths to DataCloud canonical paths under `/farkkila/LAB-ASSISTANT-PLATFORM`.

---

## 7. Ingestion Manifest Design

Every asset ingests immediately into **Raw Vault** with manifest row:

```json
{
  "asset_id": "asset_<sha1_prefix>",
  "storage_provider": "datacloud_webdav | pdrive_smb | local_database_mirror",
  "logical_path": "normalized/posix/path",
  "physical_uri": "server-only",
  "page_domain_id": "nullable",
  "page_section_id": "nullable",
  "detected_type": "document|figure|...",
  "candidate_categories": [],
  "assignment_confidence": 0.0,
  "checksum_sha256": "...",
  "extraction_status": "not_started|eligible_text|metadata_only",
  "vector_status": "not_evaluated|eligible_pending_review|embedded|blocked",
  "review_status": "raw|tentative|confirmed|rejected",
  "sensitivity_level": "unknown|internal|internal_sensitive_review|restricted_or_clinical_review",
  "provenance": {"scanner": "build_raw_asset_inventory", "snapshot_at": "ISO8601"}
}
```

**Pipeline stages (ordered):**

1. Discover (connector or mirror walk) → vault upsert  
2. Classify (rules + optional Groq **non-sensitive** assist) → update confidence  
3. Extract text (document types only) → `document_registry`  
4. Chunk → `rag.document_chunk`  
5. Vector queue → Qdrant `doc_chunks` (corpus-tagged)  
6. Graph candidates → `knowledge_relationships` (review-gated)  

**Never discard** — rejected = status only.

---

## 8. Knowledge Domain Map

| Knowledge domain | Corpus path | Page lens | Vector policy |
|------------------|-------------|-----------|---------------|
| Project workspace | `database/projects/{folder}/` | Projects | Text/docs/scripts yes; OME-TIFF/masks metadata only |
| Lab operations | `WET_LAB/` | Wet Lab + Knowledge Base | Protocols/SOPs yes |
| Administration | `Overview/` (excl. personnel optional split) | Overview | Yes; higher sensitivity review |
| Personnel | `Overview/PERSONNEL/` | Overview → Personnel | Restricted metadata-first |
| Orders | `ORDERS & RELATED INFORMATION/` | Orders | Metadata-first; billing restricted |
| Social memory | `SOCIAL & MISCELLANEOUS/` | Social | Images metadata; text docs vectorize |
| Computational | `project_scripts/`, scripts in projects | Computational Hub | Code + markdown vectorize |
| Imaging / CyCIF | Pipeline outputs under projects | CyCIF | **No** raw vectorization of TIFF/masks |

---

## 9. Current State Audit (capability matrix)

| Capability | Class | Recommendation |
|------------|-------|----------------|
| Lab canonical search (`lab_knowledge_store`) | Implemented | Reuse |
| Project digital twin + folder browser | Implemented | Reuse |
| Raw vault JSON + Postgres `raw_asset_vault` | Partial | Extend with page_domain + connectors |
| Lab file tree UI | Deprecated (410) | Remove references |
| Firebase auth | Missing | Build per brief |
| DataCloud WebDAV connector | Missing (env flags only) | Build |
| P-drive connector | Missing | Build |
| R2 previews | Missing | Build |
| Page domain registry table | Missing | Add |
| Review queue UI | Missing | Add (Admin) |
| Neo4j KG runtime | Prototype | Defer |
| `/ask` RAG copilot | Implemented | Defer expansion |
| Feature warehouse + clinical tools | Partial | Reuse |
| `security.*` tables | Schema only | Wire to Firebase |

---

## 10. Gap Analysis (priority order)

1. **Production storage connectors** (DataCloud, P-drive, R2) — blocks parity with brief.  
2. **Firebase + allowlist + admin approval** — blocks safe multi-user.  
3. **`platform.page_domain` / `page_section` registry** — blocks consistent IA.  
4. **Research Materials placement** — Overview vs Projects (NEEDS_ARCHITECT_REVIEW).  
5. **Administration UI** — ingestion/review/security.  
6. **Path mapping** local mirror → DataCloud canonical.  
7. **7 catalog-only projects** — `missing_source_mapping` (NEEDS_USER_CONFIRMATION).  
8. **Dedicated subpages** (Lab Coats, Safety, Research Hub themes) — content may exist under other folders.  
9. **KG assertion workflow** — schema designed, not operational.  
10. **Supabase hosting** — migration from local Postgres.

---

## 11. Complete Ontology (condensed)

### Entity types (48+)

Project, Sample, Patient, Dataset, Protocol, SOP, Publication, Software, PipelineStage, PipelineRun, NotebookEntry, Meeting, Decision, Researcher, StorageLocation, StorageRoot, StorageObject, Folder, Document, Asset, ImageFile, OMETiff (metadata entity), Mask (metadata), QuantificationTable, LUMIJob, CodeRepository, Script, TroubleshootingNote, ClinicalMetadata, MarkerPanel, Antibody, Experiment, Cohort, Batch, AnalysisOutput, Vendor, Order, Invoice, TrainingItem, Permission, ReviewTask, PageDomain, PageSection, WebsitePage, Event, Visitor, Photo, OutreachItem, ProcurementItem, Freezer, LNTank, SampleLocation, IngestionJob, VectorizationJob.

### Relationship types (required set)

`contains`, `belongs_to`, `stored_at`, `generated_by`, `derived_from`, `processed_by`, `references`, `uses`, `created_by`, `reviewed_by`, `approved_by`, `supersedes`, `duplicate_of`, `version_of`, `depends_on`, `has_preview`, `linked_to_page`, `assigned_to_project`, `owned_by`, `responsible_person`, `related_to_event`, `published_on_website`, `archived_in`.

**Every edge carries:** `confidence`, `source_asset_id`, `extraction_method`, `review_status`, `approval_status`.

---

## 12. PostgreSQL / Supabase Schema Plan

**Principle:** Extend `sql/001–111`; do not fork.

| Planned table | Purpose | Exists? |
|---------------|---------|---------|
| `platform.raw_asset_vault` | Raw vault | **Yes** (111) |
| `platform.storage_roots` | Connector config | No |
| `platform.storage_objects` | Logical object index | No |
| `platform.page_domains` | IA registry | No |
| `platform.page_sections` | Subpages | No |
| `platform.asset_page_links` | Asset ↔ page | No |
| `platform.ingestion_jobs` | Batch ingest | No |
| `platform.vectorization_jobs` | Queue | Partial (`rag.embedding_job`) |
| `platform.review_tasks` | Human review | No |
| `platform.allowed_users` | Firebase allowlist | No |
| `platform.registration_requests` | Pending approval | No |
| `rag.document_source` | Document registry | **Yes** |
| `rag.document_chunk` | Chunks | **Yes** |
| `security.user_account` | Users | **Yes** (not Firebase-linked) |
| `core.project` | Projects | **Yes** |

**Migration sequence for workers:** 112_page_domains.sql → 113_storage_connectors.sql → 114_ingestion_jobs.sql → 115_review_tasks.sql → 116_allowed_users.sql (names indicative; architect must approve filenames).

---

## 13. Knowledge Graph Schema

**Target:** Neo4j + Postgres assertion registry (`kg.assertion` per doc 04).

| Node label | Source evidence |
|------------|-----------------|
| Project, Document, Protocol, Software, Sample | Files + catalog |
| Person | Personnel folder — **NEEDS_USER_CONFIRMATION** for roster |
| StorageLocation | DataCloud root |

| Edge | Rule |
|------|------|
| PROJECT_HAS_DOCUMENT | confidence ≥ 0.86 auto; else review |
| DOCUMENT_DERIVED_FROM_ASSET | always |
| SCRIPT_IMPLEMENTS_STAGE | from pipeline docs |

**Do not assert clinical/patient links** without ethics approval evidence.

---

## 14. Raw Knowledge Vault Design

**Already implemented (dev):** `build_raw_asset_inventory.py` → JSON/CSV; `sync_inventory_to_postgres()` → `platform.raw_asset_vault`.

**Required additions:**

- `page_domain_id`, `page_section_id` columns (FK to page registry).  
- `access_level` column (mirror `security.project_access_policy`).  
- `mime_type` column (detected at ingest).  
- Server-only `original_path` / `physical_uri` (never in API DTO).  
- Audit trail table `platform.vault_audit_event`.

**Review queue rule:** `assignment_confidence < 0.86` OR `sensitivity_level` in restricted set → `review_tasks` row.

---

## 15. Storage Connector Architecture

```text
┌─────────────┐     JWT      ┌──────────────┐    RBAC     ┌─────────────────┐
│  React UI   │ ──────────► │ FastAPI API  │ ──────────► │ Supabase (meta) │
└─────────────┘             └──────┬───────┘             └─────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
           DataCloudWebDAV    PDriveSMB      R2S3Preview
           Connector         Connector      Connector
                    │              │              │
                    ▼              ▼              ▼
              /farkkila/...    \\pdrive\...   r2://previews/
```

| Connector | Read | Write | List | Preview handoff |
|-----------|------|-------|------|-----------------|
| DataCloudWebDAV | Yes | Yes (RBAC) | Yes | To R2 |
| PDriveSMB | Yes | Optional | Yes | To R2 |
| R2S3Preview | Yes | Preview objects only | No | Public/signed URL |
| Local mirror (dev) | Yes | Dev only | Yes | Local API |

**NEEDS_USER_CONFIRMATION:** P-drive UNC root, L-drive/G-drive policy.

---

## 16. Search Strategy

| Mode | Engine | When |
|------|--------|------|
| Exact filename/path | Postgres `raw_asset_vault` + trigram | Data & Storage, Admin |
| Metadata | SQL filters (domain, project_hint, sensitivity) | Vault, Admin |
| Page/domain | `page_domains` join `asset_page_links` | After phase 1 registry |
| Semantic | Qdrant `doc_chunks` + corpus filter | Knowledge Base, Lab |
| Hybrid | Lab vectors + vault metadata (implemented `/api/knowledge/hybrid-search`) | Lab screens |
| Graph | Neo4j | Future |

**Response DTO must include:** `source`, `logical_path`, `where_to_find`, `confidence`, `sensitivity`, `review_status` — never `original_path`.

---

## 17. Vectorization Strategy

| Eligible | Ineligible (metadata only) |
|----------|----------------------------|
| PDF, DOCX, PPTX, MD, TXT, IPYNB, code, CSV summaries | OME-TIFF, masks, `.dcc`, large PNG/TIFF, video, `.rds`, model weights, zip |

**Statuses:** `not_evaluated` → `eligible_pending_review` → `embedded` | `blocked` | `failed`.

**Corpus tags:** `lab_operations`, `project_workspace` (implemented in `lab_knowledge_store`).

---

## 18. Access-Control Strategy

| Layer | Mechanism |
|-------|-----------|
| Identity | Firebase Email/Password |
| Admission | Closed allowlist ~30 + registration queue |
| Admin | Farkkila Lab admin + Digital Pathology admin emails — **NEEDS_USER_CONFIRMATION** exact addresses |
| Authorization | Supabase RLS + `security.project_access_policy` |
| Storage | Connector credentials server-side only |
| Sensitive domains | Personnel, orders/billing, clinical-adjacent: metadata-first, no public preview |
| AI | Groq/free tier: **non-sensitive** docs only; no clinical exports |

**Existing `platform.researcher`:** Dev seed only—not production identity.

---

## 19. Review / Confidence System

| Score | Label | Action |
|-------|-------|--------|
| 0.00–0.30 | Unknown | Vault only |
| 0.31–0.60 | Weak | Vault + candidates |
| 0.61–0.85 | Probable | Tentative page/project link + review task |
| 0.86–1.00 | High | Auto-assign + audit log |

**Never discard.** `rejected` / `superseded` retain row history.

---

## 20. Decision Registry

**Existing:** `platform` decisions API + `DecisionsScreen`.

**Target:** Link decisions to `source_asset_id`, `project_id`, `meeting_id`, `confidence`, `review_status`.

**NEEDS_USER_CONFIRMATION:** Whether decision numbers follow lab legal/ETHOS format.

---

## 21. Future AI Architecture (deprioritized)

Copilot (`/ask`) remains **retrieval layer** over twin—not source of truth.

| Agent | Corpus scope | Priority |
|-------|--------------|----------|
| Lab knowledge | `lab_operations` | Low (after indexing) |
| Project assistant | `project_workspace` | Low |
| CyCIF / LUMI / Clinical | Restricted tools + traces | Low |

All agents: answer trace + citation + sensitivity banner.

---

## 22. Scalability Recommendations

- Partition Qdrant by `corpus` + optional `project_code`.  
- Batch vault ingest (400–500 rows) — proven.  
- R2 CDN for previews; never Supabase blobs for TIFF.  
- Ingestion jobs table with resumable cursors for WebDAV PROPFIND walks.  
- Read replicas on Supabase for search-heavy UI.

---

## 23. Open Questions

1. Canonical mapping: local `OMEIA-AI/database/**` → DataCloud `/farkkila/LAB-ASSISTANT-PLATFORM/**`?  
2. Confirm admin emails and full allowlist.  
3. Move `RESEARCH MATERIALS` to Projects-only navigation?  
4. Authoritative personnel roster source?  
5. Which dated `*-20260602T*` export folders are superseded duplicates?  
6. Clinical/patient content in corpus—redaction policy before vectorization?  
7. Supabase project URL + R2 bucket names for workers?

---

## 24. Page Domain Audit (15 domains)

Detailed status for worker planning. **Confidence** = overall domain mapping confidence.

### 1. Dashboard — 0.75

| Aspect | Evidence |
|--------|----------|
| Purpose | Lab status, readiness, scope, audit |
| UI | `DashboardScreen`, metrics, gap-analysis |
| API | `/stats`, `/gap-analysis`, `/team`, `/auto_logs` |
| DB | `core.*`, `platform.onboarding_checklist`, catalog_coverage |
| Storage | None direct |
| Folders | N/A |
| Missing | Vault ingest status, storage health, review counts, recent docs |
| Workers | LUMI-W020 dashboard widgets |

### 2. Overview / Lab Operations — 0.82

| Aspect | Evidence |
|--------|----------|
| UI | `lab_knowledge` subs: get_started (global search), onboarding, guidelines, documents, personnel, cleaning via sections |
| API | `/api/knowledge/lab/*`, processed section APIs |
| DB | `rag.*` corpus `lab_operations` |
| Folders | `Overview/*` (no GENERAL LAB INFORMATION on disk) |
| Missing | Lab Introduction, Mission, Contacts, Coats, Safety, Access Requests, Taskpad as first-class sections |
| Workers | Page registry rows; optional dedicated sections |

### 3. Research Hub — 0.40 (CANDIDATE)

| Aspect | Evidence |
|--------|----------|
| UI | Not separate—research materials under Overview + projects |
| Folders | `projects/RESEARCH MATERIALS` |
| Missing | Thematic hubs (Ovarian, Spatial, Clinical) |
| Workers | **Defer** until architect confirms IA split |

### 4. Projects — 0.88

| Aspect | Evidence |
|--------|----------|
| UI | `ProjectsScreen`, `ProjectFolderBrowser`, digital twin |
| API | `/api/projects/*`, `/api/project-files/*` |
| DB | `core.project`, twins on disk |
| Folders | `database/projects/*` (3913 files) |
| Missing | Timeline, Members UI, Archive subnav, logical 1–7 folder enforcement |
| Workers | Project page registry; mapping catalog codes → folders |

### 5. Data & Storage — 0.70

| Aspect | Evidence |
|--------|----------|
| API | `/api/storage/roots`, `/api/vault/*` |
| DB | `platform.raw_asset_vault` |
| Missing | Top-level UI, connectors, storage health |
| Workers | LUMI-W030 Data & Storage screen (read-only) |

### 6. Computational Hub — 0.85

| Aspect | Evidence |
|--------|----------|
| UI | `BioinformaticsHubScreen` (LUMI, Puhti, conda, install, file ops) |
| Evidence | rclone DataCloud snippets in UI copy; `project_scripts/*` |
| Missing | Roihu, file encryption/recovery as structured modules |
| Workers | Link scripts in vault to Software entities |

### 7. CyCIF / Image Analysis — 0.72

| Aspect | Evidence |
|--------|----------|
| UI | `CycifScreen` variants |
| Corpus | `.dcc`, pipeline docs, channel CSV at repo root |
| Missing | OME-TIFF registry, run manifest UI, mask policy |
| Workers | Metadata-only asset class rules (enforced in inventory) |

### 8. Wet Lab — 0.84

| Aspect | Evidence |
|--------|----------|
| UI | lab_knowledge `wet_lab_files`, protocols panel, inventory |
| Folders | `WET_LAB/` (483 files) |
| Missing | Freezers, LN tanks, GeoMx/Xenium as subpages |
| Workers | Section ingest; search validation (“lab coats” etc.) |

### 9. Orders & Procurement — 0.80

| Aspect | Evidence |
|--------|----------|
| UI | lab_knowledge billing/archive, orders register |
| Folders | `ORDERS & RELATED INFORMATION/` |
| Sensitivity | billing, orders — restricted review |
| Workers | Sensitivity rules hardening |

### 10. Social & Miscellaneous — 0.83

| Aspect | Evidence |
|--------|----------|
| UI | lab_knowledge social_browse |
| Folders | `SOCIAL & MISCELLANEOUS/` (222 files) |
| Workers | Image metadata + R2 preview pipeline |

### 11. Knowledge Base — 0.78

| Aspect | Evidence |
|--------|----------|
| UI | Merged into `LabKnowledgeScreen` |
| Missing | Review Queue UI, KG browser, Uncategorized view |
| Workers | Split admin review from lab search |

### 12. Notebook / Wiki — 0.77

| Aspect | Evidence |
|--------|----------|
| API | `/notebook`, `/wiki` |
| UI | `NotebookWikiScreen` |
| Missing | Daily notes, experiment notes taxonomy |

### 13. Tasks & Decisions — 0.76

| Aspect | Evidence |
|--------|----------|
| API | `/tasks`, `/decisions` |
| UI | Orders tasks, decisions screen |
| Missing | Approval queue, pending reviews integration |

### 14. AI Lab Assistant — 0.80

| Aspect | Evidence |
|--------|----------|
| UI | Chat, ingest, models |
| API | `/ask`, agents, install, lumi, parse_log |
| Priority | **Deprioritized** per brief |

### 15. Administration — 0.35

| Aspect | Evidence |
|--------|----------|
| UI | **Missing** |
| Schema | `security.*` partial |
| Workers | **Critical path** after vault: allowlist, jobs, review |

---

*End of Architecture Package. Worker tasks: see `13_LOW_END_WORKER_IMPLEMENTATION_PLAN.md`.*
