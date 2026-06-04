# 11 - Laboratory Digital Twin Report

Generated from the original local evidence corpus under `/Users/debashishdeb/Downloads/OMEIA-AI/database` and the current platform implementation under `farkki_ai_platform_blueprint`.

This report follows the rule that files, folders, processed catalogs, code, schemas, and UI modules are evidence. It does not treat inferred relationships as final truth. Anything below confidence 0.86 requires human review before becoming canonical platform knowledge.

## 1. Evidence Base

Confirmed source roots:

| Evidence source | Role | Confidence |
| --- | --- | --- |
| `database/projects` | Project folders, project scripts, figures, manuscripts, meeting notes, data outputs | 0.95 |
| `database/WET_LAB` | Protocols, GeoMx/Xenium/tCycIF materials, inventories, wet-lab operational records | 0.95 |
| `database/Overview` | Personnel, permits, forms, onboarding, lab cleaning, guidelines | 0.90 |
| `database/ORDERS & RELATED INFORMATION` | Ordering, billing, vendor and archive records | 0.95 |
| `database/SOCIAL & MISCELLANEOUS` | Lab photos, retreats, visits, outreach, social memory | 0.90 |
| `farkki_ai_platform_blueprint/app_skeleton/data/projects_catalog.json` | Existing 37-project catalog with project leads, categories, status, modalities | 0.80 |
| `farkki_ai_platform_blueprint/app_skeleton/data/processed_projects/*.json` | Extracted digital-twin records and chunk indexes from project and lab sections | 0.85 |
| SQL files under `farkki_ai_platform_blueprint/sql` | Current database design and implemented schema intent | 0.90 |
| API/UI code under `app_skeleton` | Implemented platform capabilities | 0.90 |

Corpus scale from filesystem scan:

| Metric | Count |
| --- | ---: |
| Files under `database` | 4,800 |
| Folders under `database` | 1,029 |
| Files in `database/projects` | 3,913 |
| Files in `database/WET_LAB` | 483 |
| Files in `database/SOCIAL & MISCELLANEOUS` | 222 |
| Files in `database/Overview` | 112 |
| Files in `database/ORDERS & RELATED INFORMATION` | 70 |

Dominant file types:

| Type | Count | Digital-twin handling |
| --- | ---: | --- |
| `.png` | 1,310 | Image asset, thumbnail/preview metadata, no full text vectorization |
| `.pdf` | 681 | Text extraction and vectorization when readable |
| `.svg` | 530 | Figure/plot asset, metadata summary |
| `.docx` | 493 | Text extraction and vectorization |
| `.xlsx` | 341 | Registry/table extraction, metadata summary, selective vectorization |
| `.pptx` | 247 | Slide text extraction and vectorization |
| `.md` | 208 | Direct text vectorization |
| `.ipynb` | 115 | Code/markdown extraction, pipeline or analysis evidence |
| `.jpg` / `.jpeg` / `.heic` | 211 | Image asset, metadata summary |
| `.csv` | 92 | Table/manifest evidence, schema-aware import when possible |
| `.dcc` | 84 | GeoMx/spatial transcriptomics technical artifact, metadata-first handling |
| `.py` / `.r` | 125 | Pipeline/code evidence, script vectorization |

## 2. Reconstructed Laboratory Graph

### People

Confirmed:

- The platform is for a closed research group centered on Anniina Farkkila's laboratory, with approximately 30 Helsinki University users according to the user brief.
- The project catalog lists named project leads and collaborators for many projects.
- `database/Overview/PERSONNEL` is the canonical evidence area for personnel records.

Current limitation:

- Personnel should not be canonicalized solely from filenames or old project documents. People extracted from project catalogs should be marked `probable` until reconciled against the personnel folder or a user-approved roster.

Recommended entities:

- `Person`
- `LabRole`
- `ProjectMembership`
- `OperationalResponsibility`
- `AccessGroup`

### Projects

The existing catalog contains 37 project records:

| Category | Count |
| --- | ---: |
| External collaboration | 11 |
| Spatial and multi-omics | 9 |
| Computational tool | 4 |
| Platform model | 3 |
| Flagship | 3 |
| Genomics | 3 |
| Infrastructure | 2 |
| Clinical collaboration | 1 |
| Support | 1 |

Status distribution:

| Status | Count |
| --- | ---: |
| Active | 32 |
| Completed | 3 |
| Discontinued | 2 |

Projects with strong processed-evidence density include Fanconi, CellCycle, NKI, TLS, iPDC 1.0, iPDC 2.0, SPACE, Tribus, KRAS, Sequencing, Auria, and EyeMT. Projects with zero processed assets in the current extracted records, including LeppaCollab, Organoids, Ovca_VTE, sciSet, VanharantaCollab, SideProjects, Endometrial_HRD, and Mesenchymal_Ovca, must remain `NEEDS_USER_CONFIRMATION` or `missing_source_mapping` until folder paths are verified.

### Storage

Confirmed logical storage domains from the user brief and local corpus:

- Primary canonical storage: University of Helsinki DataCloud WebDAV.
- Secondary storage: P-drive SMB.
- Optional storage: OneDrive and Google Drive.
- Thumbnail storage: Cloudflare R2.
- Metadata: Supabase PostgreSQL.
- Local evidence mirror: `/Users/debashishdeb/Downloads/OMEIA-AI/database`.

Current local database sections:

| Section | Evidence role |
| --- | --- |
| `projects` | Project memory, research outputs, methods, scripts, figures |
| `WET_LAB` | Protocols, experiments, inventories, wet-lab operations |
| `Overview` | Personnel, onboarding, forms, permits, guidelines |
| `ORDERS & RELATED INFORMATION` | Procurement, billing, vendor archive |
| `SOCIAL & MISCELLANEOUS` | Lab social memory and institutional continuity |

### Computational Structure

Confirmed code/script evidence:

- `project_scripts/KRAS-main`
- `project_scripts/SPACE-main`
- `project_scripts/cellcycle-main`
- `project_scripts/geomx-processing-main`
- `project_scripts/SPACEstat-main`
- `project_scripts/clinical_data_curation-main`
- `project_scripts/tribus-master`
- `project_scripts/FINPROVE-main`
- `project_scripts/eyeMT-main`
- `project_scripts/CEFIIRA-main`
- `database/projects/compiled_scripts`
- top-level `scripts` with tCycIF/Snakemake-related utilities

Discovered computational domains:

- Image preprocessing and illumination correction
- Ashlar stitching
- tCycIF quantification
- Spatial statistics and SPACEstat
- Tribus computational tooling
- Clinical data curation
- GeoMx processing
- scRNA-seq and Xenium analysis for selected projects
- HPC/Snakemake operational scripts

### Knowledge Flows

Observed flow:

```text
Project folders / wet-lab folders / overview docs / orders archive
  -> file inventory and text extraction
  -> processed project or lab-section twin JSON
  -> chunk JSONL for search and future vectorization
  -> API endpoints for browsing, extraction, search, digital twin views
  -> React UI modules for project, lab, orders, decisions, notebooks, tasks, assistant
```

Target production flow:

```text
DataCloud / P-drive / optional Drive sources
  -> raw knowledge vault
  -> review queue with confidence scoring
  -> canonical registries and graph assertions
  -> vector and hybrid search indexes
  -> project and lab digital twins
  -> audited AI assistant and operational workflows
```

## 3. Real Asset Survey Model

Every asset should enter a raw vault before classification. Minimum canonical record:

| Field | Purpose |
| --- | --- |
| `asset_id` | Stable UUID or deterministic hash ID |
| `original_path` | Untouched source path |
| `storage_provider` | DataCloud, P-drive, local mirror, OneDrive, Google Drive, R2, GitHub |
| `logical_path` | Normalized path inside lab ontology |
| `filename` | Original filename |
| `extension` | Lowercase extension |
| `size_bytes` | Storage and sensitivity signal |
| `sha256` | Deduplication and provenance |
| `asset_type` | Document, image, figure, table, code, notebook, binary output, video, archive |
| `project_id` | Nullable project assignment |
| `section_id` | Lab section assignment if not project-specific |
| `owner_person_id` | Nullable, confidence-scored |
| `sensitivity_level` | Public, internal, sensitive, restricted, clinical, unknown |
| `review_status` | Raw, triaged, confirmed, rejected, superseded |
| `confidence` | Overall assignment confidence |
| `vector_status` | Not eligible, pending, embedded, failed |
| `graph_status` | Not asserted, candidate, asserted, rejected |
| `provenance` | Extractor, timestamp, source snapshot |

Confidence policy:

| Confidence | Meaning | Action |
| --- | --- | --- |
| 0.00-0.30 | Unknown | Keep only in raw vault |
| 0.31-0.60 | Weak | Candidate only, no canonical assignment |
| 0.61-0.85 | Probable | Tentative assignment and review queue |
| 0.86-1.00 | High | Auto assign with audit record |

## 4. Semantic Cluster Discovery

High-confidence clusters:

| Cluster | Evidence | Confidence |
| --- | --- | ---: |
| tCycIF image analysis | `WET_LAB/tCycIF projects`, project folders, image preprocessing and quantification scripts | 0.90 |
| Spatial statistics | SPACEstat project, SPACEstat scripts, SPACE/SPACEjoint relationship | 0.88 |
| GeoMx and spatial transcriptomics | `WET_LAB/NanoString GeoMx`, `GeoMx projects`, `geomx-processing-main`, `.dcc` files | 0.88 |
| Ovarian/HGSC translational research | SPACE, NKI, KRAS, TLS, ADC, FINPROVE, sequencing projects | 0.85 |
| Patient-derived models | iPDC, organoids, related protocols and project folders | 0.78 |
| Procurement and billing operations | Orders folder, billing instructions, archive | 0.92 |
| Onboarding and personnel operations | Overview/personnel/onboarding/guidelines | 0.86 |
| Lab social memory | photos, retreats, visits, outreach folders | 0.90 |

Clusters requiring review:

- Hidden duplicate project folders from dated zip exports, for example `38_ADC_project` and `38_ADC_project-20260602T172138Z-3-001`.
- Generic lifecycle folders exported as standalone folders, such as `2. Methods and experiments-20260602T110526Z-3-001` and `6. Archive-20260602T110541Z-3-001`.
- Empty or unmapped catalog projects with no current processed assets.

## 5. Implementation Audit

| Capability | Status | Evidence | Recommendation |
| --- | --- | --- | --- |
| Project registry/catalog | Partially implemented | `projects_catalog.json`, `/projects`, catalog merge logic | Reuse, add source provenance and review status |
| Project digital twins | Partially implemented | `project_processor.py`, `/api/projects/{project_code}/digital-twin`, processed JSON files | Reuse, add confidence scoring per field |
| Lab section processing | Partially implemented | `database_processor.py`, lab processed JSON/chunks | Reuse, fix section path drift for `Overview/GENERAL LAB INFORMATION` if absent in local corpus |
| Raw knowledge vault | Planned/partial | extraction outputs exist but no true raw vault table | Add dedicated vault schema/table before further canonicalization |
| Document extraction | Partially implemented | `document_extraction.py` supports PDF/DOCX/PPTX/XLSX/IPYNB/images | Reuse, add extractor status QA dashboard |
| Vector search | Prototype/partial | Qdrant client, chunk JSONL, `lab_knowledge_store.py` | Reuse, replace pseudo vectors with approved embeddings for production |
| Knowledge graph | Planned | docs describe Neo4j/kg, but no mature graph assertion workflow found | Build evidence-backed assertion registry first |
| Search architecture | Partially implemented | API text search, Qdrant, database search endpoints | Refactor into exact, metadata, folder, semantic, hybrid, graph modes |
| Notebook/wiki/tasks/decisions | Partially implemented | API endpoints and UI screens | Reuse as operational memory layer |
| Orders hub | Partially implemented | Orders UI screens and lab section ingestion | Reuse, add vendor/order sensitivity policy |
| Wet-lab hub | Partially implemented | Wet-lab UI screens and section ingestion | Reuse, add protocol versioning |
| Feature warehouse | Prototype | feature endpoints and synthetic data | Keep as prototype until real feature matrices are registered |
| Clinical analysis | Prototype | survival/group comparison endpoints | Restrict to approved de-identified dictionaries and audited tool runs |
| Specialist agents | Prototype | agents for privacy, HPC, installation, pipelines, logs | Reuse as rule-based assistants, not authoritative systems |
| Auth/permissions | Planned | brief specifies Firebase allowlist; docs mention security schemas | Implement before any shared deployment |
| Audit/security | Partial design | SQL/docs/audit logs exist | Make audit mandatory for ingestion, search, write, and AI responses |

## 6. Target Ontology

### Entity Types

- `Person`
- `Role`
- `Team`
- `Project`
- `ProjectMembership`
- `Cohort`
- `PatientPseudonym`
- `Specimen`
- `Sample`
- `Assay`
- `Panel`
- `Marker`
- `Image`
- `RegionOfInterest`
- `CellTable`
- `FeatureMatrix`
- `Pipeline`
- `PipelineRun`
- `SoftwareRepository`
- `Document`
- `Protocol`
- `SOP`
- `Publication`
- `Meeting`
- `Decision`
- `Task`
- `Order`
- `Vendor`
- `StorageLocation`
- `Asset`
- `VectorChunk`
- `GraphAssertion`
- `ReviewEvent`

### Relationship Types

- `MEMBER_OF`
- `LEADS`
- `COLLABORATES_ON`
- `OWNS`
- `USES_PROTOCOL`
- `GENERATED_BY`
- `DERIVED_FROM`
- `STORED_AT`
- `REFERENCES`
- `MENTIONS`
- `USES_MARKER`
- `HAS_ASSAY`
- `HAS_SAMPLE`
- `HAS_COHORT`
- `PRODUCED_PUBLICATION`
- `HAS_DECISION`
- `HAS_TASK`
- `ORDERED_FOR`
- `SUPERSEDES`
- `DUPLICATE_OF`
- `NEEDS_REVIEW`

### Required Domains

- Lab Operations
- Computational Hub
- Research Hub
- Orders and Procurement
- Projects
- Data and Storage
- Publications
- Clinical Research
- Image Analysis
- Knowledge Base
- Administration

## 7. Database Design Delta

Existing schema direction is strong: `core`, `clinical`, `assay`, `features`, `rag`, `spatial`, `platform`, `audit`, and related docs already exist. The missing production-critical layer is a first-class raw vault and review workflow.

Recommended new schemas/tables:

```sql
CREATE SCHEMA IF NOT EXISTS vault;
CREATE SCHEMA IF NOT EXISTS review;
CREATE SCHEMA IF NOT EXISTS kg;

CREATE TABLE vault.asset (
  asset_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  stable_key text NOT NULL UNIQUE,
  original_path text NOT NULL,
  storage_provider text NOT NULL,
  logical_path text,
  filename text NOT NULL,
  extension text,
  size_bytes bigint,
  sha256 text,
  asset_type text NOT NULL DEFAULT 'unknown',
  sensitivity_level text NOT NULL DEFAULT 'unknown',
  project_code text,
  section_id text,
  owner_hint text,
  confidence numeric(3,2) NOT NULL DEFAULT 0.00,
  review_status text NOT NULL DEFAULT 'raw',
  vector_status text NOT NULL DEFAULT 'not_evaluated',
  graph_status text NOT NULL DEFAULT 'not_asserted',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE review.asset_review (
  review_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  asset_id uuid NOT NULL REFERENCES vault.asset(asset_id) ON DELETE CASCADE,
  reviewer_id uuid,
  decision text NOT NULL,
  notes text,
  previous_values jsonb NOT NULL DEFAULT '{}'::jsonb,
  new_values jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE kg.assertion (
  assertion_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  subject_type text NOT NULL,
  subject_id text NOT NULL,
  predicate text NOT NULL,
  object_type text NOT NULL,
  object_id text NOT NULL,
  confidence numeric(3,2) NOT NULL,
  evidence_asset_id uuid REFERENCES vault.asset(asset_id) ON DELETE SET NULL,
  review_status text NOT NULL DEFAULT 'candidate',
  created_at timestamptz NOT NULL DEFAULT now()
);
```

## 8. Search Architecture

Search must be layered:

| Search mode | Use case | Index |
| --- | --- | --- |
| Exact search | Filename, project code, sample code, marker | PostgreSQL btree/trigram |
| Metadata search | Asset type, owner, section, sensitivity, status | PostgreSQL JSONB and relational columns |
| Folder search | Browse original structure and neighboring files | Vault path index |
| Semantic search | SOPs, protocols, notes, reports, publications | Qdrant vector chunks |
| Hybrid search | User-facing knowledge discovery | PostgreSQL + Qdrant rerank |
| Graph search | Relationships among projects, people, samples, pipelines | `kg.assertion` or Neo4j |
| Agent search | Multi-step reasoning with audit trail | Orchestrated exact + metadata + semantic + graph retrieval |

Vectorization policy:

Vectorize:

- SOPs
- Protocols
- Publications
- Meeting notes
- Reports
- Markdown documentation
- Code comments and pipeline scripts
- Notebook markdown/code summaries

Do not vectorize raw binary payloads:

- OME-TIFF and other heavy microscopy images
- Masks and segmentation arrays
- Videos
- Model weights
- Raw binary outputs
- Full PHI-bearing clinical extracts

For non-vectorized assets, generate metadata summaries and link them to projects, samples, assays, and pipeline runs when evidence supports it.

## 9. Storage Intelligence Rules

Never decide storage from extension alone. Use:

- Size
- Sensitivity
- Source provider
- Access frequency
- Relationship density
- Need for thumbnails/previews
- Need for audit and versioning
- Collaboration scope

Recommended dispositions:

| Asset class | Primary storage | Metadata | Preview |
| --- | --- | --- | --- |
| OME-TIFF, masks, large imaging outputs | DataCloud/P-drive | Supabase vault registry | R2 thumbnails |
| Protocols/SOPs | DataCloud | Supabase + vector index | Optional PDF preview |
| Project figures | DataCloud/P-drive | Supabase asset registry | R2 thumbnails |
| Publications/manuscripts | DataCloud | Supabase + vector index | PDF preview |
| Notebooks/scripts | GitHub/DataCloud | Supabase + vector index | Code preview |
| Orders/billing docs | DataCloud restricted area | Supabase restricted metadata | Usually no public preview |
| Clinical extracts | Restricted storage only | Minimal approved metadata | No unrestricted preview |

## 10. Bottlenecks and Risks

| Risk | Evidence | Severity | Recommendation |
| --- | --- | --- | --- |
| Duplicate export folders | Dated zip-export suffixes and duplicate ADC folders | High | Deduplicate by hash and logical project mapping |
| Empty/missing project mappings | Several catalog projects have zero processed assets | Medium | Add `missing_source_mapping` review status |
| Section path drift | `database_sections.py` references `Overview/GENERAL LAB INFORMATION`, while local tree shows direct `Overview/...` folders | High | Normalize section roots and add existence tests |
| Premature canonicalization | Catalog/project enrichment mixes evidence and inferred metadata | High | Add field-level confidence and source IDs |
| Sensitive operational docs | Orders, personnel, permits, billing may contain restricted details | High | Apply sensitivity-first review before vectorization |
| Clinical/statistical hallucination | Clinical endpoints exist but real dictionaries and curation rules are not complete | High | Use only approved tool outputs with answer traces |
| Image assets overwhelm text systems | 1,000+ images and many figures | Medium | Metadata and thumbnail pipeline before semantic indexing |
| Knowledge graph missing review loop | Graph design exists but assertion lifecycle is immature | Medium | Build `kg.assertion` with evidence and review state |

## 11. Immediate Next Actions

1. Create a raw vault manifest for all 4,800 files with stable IDs, hashes, storage domain, section/project guesses, and confidence.
2. Fix and test lab section roots against the actual local folder structure.
3. Add field-level provenance to processed project JSON and catalog-derived values.
4. Mark zero-asset catalog projects as `NEEDS_USER_CONFIRMATION`.
5. Build a deduplication report for dated export folders and duplicate project roots.
6. Add sensitivity rules before indexing orders, personnel, permits, billing, and clinical-adjacent files.
7. Convert existing processed project/lab JSON files into vault-backed records.
8. Implement the review queue before pushing candidate project ownership, people, or graph relationships into canonical tables.
9. Split UI search into exact, folder, metadata, semantic, and hybrid modes.
10. Treat the AI assistant as a retrieval and operating layer over the digital twin, not as the source of truth.

## 12. Confidence Summary

High confidence:

- The lab corpus is project-heavy, with major operational domains for wet lab, overview/personnel/onboarding, orders, and social memory.
- The current codebase already implements a serious prototype for processing folders into digital twin records and exposing them through API/UI modules.
- A raw vault and review workflow are required before production canonicalization.

Probable but needs review:

- Project ownership and collaborator records from the existing catalog.
- Project categories for folders with limited or no extracted assets.
- Sensitivity levels for personnel, orders, and clinical-adjacent files.
- Relationships among scripts, assays, datasets, and publications.

Unknown:

- Final DataCloud canonical paths for every local mirror asset.
- Current authoritative personnel roster.
- Approved project-level permissions.
- Which files contain direct or indirect patient identifiers.
- Which dated export folders are superseded versus independently meaningful snapshots.
