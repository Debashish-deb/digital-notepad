# OMEIA / Färkkilä Lab Research Knowledge Base + AI Brain Master Dossier

Created: 2026-06-06

## Purpose

This document and folder package gives a coding AI everything needed to build a professional source-grounded research knowledge base for the OMEIA / Färkkilä Lab Assistant.

The recommended approach is **not** to fine-tune first. The correct architecture is:

```txt
Unified Search + RAG + Knowledge Graph + Evaluation + Scheduled Refresh
```

## Why this architecture

A scientific assistant must know where every answer came from. Fine-tuning alone cannot guarantee accurate publication links, dataset accessions, protocol versions, or internal project relationships. RAG and knowledge graph infrastructure can be updated continuously and evaluated.

## Contents of this package

- Master prompt for coding AI
- Architecture blueprint
- Source seed map
- SQL migration
- Backend scaffolds
- Frontend scaffolds
- Config assets
- CSV templates
- Evaluation questions
- Runbooks
- Privacy/copyright policy

## Quick start

1. Give `COPY_THIS_MASTER_PROMPT_TO_AI.md` to your coding AI.
2. Tell it to inspect your existing OMEIA codebase first.
3. Ask it to implement Phase 1 only first.
4. Require complete changed files and test output.
5. Do not accept claims of accuracy without evaluation.

## The core instruction

Every scientific claim from the assistant must be backed by a source citation.

---


# COPY THIS MASTER PROMPT TO YOUR CODING AI

You are building the **Färkkilä Lab Research Knowledge Base and AI Assistant Brain** for the OMEIA / Färkkilä Lab Assistant platform.

This is a React + FastAPI + PostgreSQL + Qdrant + LLM/RAG application used as a research-lab operating system. The goal is to make the assistant deeply knowledgeable about the lab’s public research area, publications, public datasets, internal orientation material, protocols, spatial biology workflows, and worldwide recent research in ovarian cancer spatial biology.

This must not be a simple chatbot. Build a **source-grounded research knowledge infrastructure**.

The assistant must answer with:

- accurate factual content
- source citations
- publication links
- dataset links
- relation-aware explanations
- confidence/uncertainty behavior
- clear distinction between public knowledge and internal/private lab knowledge
- app navigation actions where relevant

The assistant must not hallucinate.
The assistant must not claim facts without sources.
The assistant must not expose private internal documents to unauthorized users.
The assistant must not send patient-identifiable data to public LLM APIs.

---

## Domain to learn

Primary lab:

- Färkkilä Lab, University of Helsinki
- Public website: https://www.farkkilab.org

Important public pages:

- https://www.farkkilab.org/
- https://www.farkkilab.org/research
- https://www.farkkilab.org/publications
- https://www.farkkilab.org/clinic
- https://www.farkkilab.org/research/computational-tools
- https://www.farkkilab.org/news

Core domain:

- ovarian cancer
- high-grade serous ovarian cancer / HGSC / HGSOC
- precision oncology
- spatial biology
- single-cell analysis
- tumor microenvironment
- tertiary lymphoid structures / TLS
- MHC class II
- antigen presentation
- immune ecosystems
- chemotherapy response
- immunotherapy response
- patient-derived models
- clinical-translational oncology
- multiplex imaging
- tCyCIF / CyCIF
- GeoMx
- Visium spatial transcriptomics
- scRNA-seq
- multi-omics
- spatial statistics
- cellular neighborhoods
- digital pathology
- Qdrant/RAG/search infrastructure

---

## System goal

Create a complete ingestion, indexing, retrieval, and evaluation system for the AI assistant.

The system must include:

1. Public Färkkilä Lab website ingestion
2. Publication ingestion
3. Worldwide literature discovery/metadata ingestion
4. Dataset registry ingestion
5. Internal lab document ingestion
6. Knowledge graph extraction
7. Qdrant vector indexing
8. PostgreSQL metadata storage
9. Unified search integration
10. AI assistant RAG integration
11. Source citation and answer verification
12. Evaluation set for accuracy testing
13. Scheduled refresh pipeline

---

## Recommended architecture

Use this architecture:

```txt
Public Website / Publications / Datasets / Internal Docs
      ↓
Crawler + Fetchers + Parsers
      ↓
Scientific Cleaner + Metadata Extractor
      ↓
Entity/Relation Extraction
      ↓
PostgreSQL registry + Knowledge Graph
      ↓
Chunking + Embeddings
      ↓
Qdrant named-vector index
      ↓
Unified Search Service
      ↓
AI Assistant RAG + Citation Cards + App Navigation
      ↓
Evaluation + Query Logs + Refresh Jobs
```

---

## Hard rules

1. Do not build another isolated search/chat system.
2. Reuse the unified search/search-hit architecture where possible.
3. Keep public and internal knowledge separated by access level.
4. Do not leak server paths, API keys, credentials, or patient identifiers.
5. Do not scrape or store copyrighted full texts unless allowed by license or user-provided access rights.
6. For closed-access papers, store bibliographic metadata, abstract, short allowed snippets, and source link only.
7. Use source citations for every scientific claim.
8. If evidence is missing, say so.
9. Do not claim Qdrant indexing succeeded unless upsert and retrieval are verified.
10. Do not claim tests passed unless they were run.
11. Keep dark/light/academic themes working.
12. Add evaluation before claiming accuracy.

---

## Database and storage targets

PostgreSQL tables:

- platform.research_source
- platform.research_document
- platform.research_chunk
- platform.research_dataset
- platform.knowledge_entity
- platform.knowledge_relation
- platform.research_ingestion_job
- platform.research_query_eval

Qdrant:

- collection: `research_knowledge`
- named vector: `text`
- vector size: from configured embedding model
- payload includes source_id, document_id, chunk_id, title, source_type, source_url, DOI, PMID, dataset accession, project_code, visibility, section, entities, relations, text, text_hash.

---

## Public website crawler

Implement a polite crawler.

Seed URLs:

- https://www.farkkilab.org/
- https://www.farkkilab.org/research
- https://www.farkkilab.org/publications
- https://www.farkkilab.org/clinic
- https://www.farkkilab.org/news
- https://www.farkkilab.org/research/computational-tools

Rules:

- Respect robots.txt.
- Use polite rate limiting.
- Do not overload the site.
- Store page title, URL, text, links, metadata.
- De-duplicate by canonical URL and checksum.
- Use Playwright fallback only if normal HTML fetch does not capture useful text.
- Do not crawl private/internal URLs.

---

## Publication ingestion

Discover publications using:

- Färkkilä Lab publications page
- PubMed
- Crossref
- OpenAlex
- Semantic Scholar if configured
- DOI metadata
- publisher pages where allowed

Search queries:

- `Anniina Färkkilä ovarian cancer`
- `Färkkilä spatial biology ovarian cancer`
- `Färkkilä high-grade serous ovarian cancer`
- `Färkkilä MHC class II Cancer Discovery`
- `Färkkilä tertiary lymphoid structures ovarian cancer`
- `Färkkilä patient-derived ovarian cancer models`
- `Färkkilä CyCIF ovarian cancer`

For each publication store:

- title
- authors
- journal
- year
- DOI
- PMID
- abstract
- keywords
- source URL
- citation
- related datasets
- data availability
- methods summary
- key findings
- limitations
- lab relevance summary

Prioritize:

- Single-cell spatial atlas of HGSC and MHC class II
- TLS atlas in ovarian cancer
- single-cell/spatial tumor microenvironment in HGSC
- patient-derived immuno-oncology models/platforms
- chemotherapy response and spatial immune context
- multi-omics ovarian cancer atlases

---

## Worldwide literature ingestion

Create a curated worldwide corpus, not a blind dump.

Use queries:

- `high-grade serous ovarian cancer spatial transcriptomics`
- `ovarian cancer tertiary lymphoid structures spatial biology`
- `HGSOC single-cell atlas tumor microenvironment`
- `MHC class II ovarian cancer immune response`
- `spatial transcriptomics ovarian cancer subclones microenvironment`
- `multiplex immunofluorescence ovarian cancer immune microenvironment`
- `patient derived ovarian cancer immunotherapy platform`
- `ovarian cancer chemotherapy resistance single-cell spatial`

Include:

- peer-reviewed papers
- reputable preprints
- review articles
- dataset papers
- landmark papers
- recent 2023–2026 papers
- papers directly relevant to the lab domain

Exclude:

- SEO pages
- unsourced blogs
- low-quality summaries
- unrelated general oncology

Rank:

1. Färkkilä Lab papers
2. direct collaborators / closely related papers
3. datasets with reusable data
4. landmark reviews
5. methods papers
6. general background

---

## Dataset registry ingestion

Search and register public datasets from:

- GEO
- ArrayExpress
- EGA
- cBioPortal
- TCGA
- CPTAC
- HTAN
- Figshare
- Zenodo
- paper supplementary pages

Queries:

- `HGSOC spatial transcriptomics GEO`
- `high-grade serous ovarian cancer single cell RNA seq GEO`
- `ovarian cancer CyCIF dataset`
- `ovarian cancer spatial proteomics dataset`
- `MHC class II HGSC dataset`
- `tertiary lymphoid structures ovarian cancer dataset`
- `TCGA OV high grade serous ovarian cancer`
- `CPTAC ovarian cancer proteomics`

For each dataset:

- accession
- title
- modality
- disease
- sample count
- patient count
- tissue type
- platform
- access level
- URL
- related paper
- usability notes
- limitations
- preprocessing requirements

Starting datasets:

- GEO GSE211956
- EGA phs002262
- TCGA-OV
- CPTAC ovarian cancer proteomics
- any datasets linked from Färkkilä Lab publications

---

## Document parsing

Support:

- HTML
- PDF
- PubMed XML/abstract
- Crossref JSON
- OpenAlex JSON
- DOCX
- TXT
- Markdown
- CSV/TSV metadata

Extract:

- title
- abstract
- methods
- results
- data availability
- figure/table captions where legally allowed
- citation
- source URL
- clean text
- key findings
- limitations

Copyright rule:

- Do not store full copyrighted papers unless open-access license or user-provided rights allow it.
- For closed-access papers, store metadata, abstract, short allowed snippets, and source link.

---

## Chunking strategy

Use scientific-aware chunking:

- preserve headings
- title/abstract/methods/results chunks
- target 800–1200 tokens
- overlap 100–200 tokens
- keep figure/table captions separate if available
- store section_title
- store chunk_index
- store text_hash

Qdrant payload:

```json
{
  "source_id": "...",
  "document_id": "...",
  "chunk_id": "...",
  "title": "...",
  "source_type": "publication",
  "source_url": "...",
  "doi": "...",
  "pmid": "...",
  "dataset_accession": "...",
  "journal": "...",
  "year": 2026,
  "authors": [],
  "section_title": "...",
  "text": "...",
  "visibility": "public",
  "domain": "ovarian_cancer_spatial_biology",
  "entities": [],
  "relations": [],
  "text_hash": "...",
  "created_at": "..."
}
```

---

## Embeddings and reranking

Use a real embedding model when possible.

Recommended options:

- OpenAI `text-embedding-3-large` or `text-embedding-3-small`
- BGE-M3
- E5-large
- Jina embeddings
- local sentence-transformers fallback

Qdrant collection:

- `research_knowledge`
- named vector: `text`

Upsert format:

```python
models.PointStruct(
    id=point_id,
    vector={"text": embedding},
    payload=payload,
)
```

Query format:

```python
qdrant_client.query_points(
    collection_name="research_knowledge",
    query=embedding,
    using="text",
    limit=limit,
    query_filter=filter,
)
```

Add reranking:

- cross-encoder if available
- otherwise LLM rerank top 20
- combine semantic, keyword, recency, lab-priority, citation quality

---

## Knowledge graph extraction

Extract entities:

- diseases
- cancer subtypes
- genes/proteins
- biomarkers
- cell types
- immune structures
- technologies
- datasets
- methods
- clinical endpoints
- treatments
- model systems
- publications
- projects

Extract relations:

- Paper STUDIES Disease
- Paper USES Technology
- Paper REPORTS Finding
- Finding ASSOCIATED_WITH Outcome
- Biomarker PREDICTS Outcome
- Dataset SUPPORTS Paper
- Technology MEASURES Entity
- Marker IDENTIFIES CellType
- Protocol GENERATES DataType
- Project USES Protocol
- ModelSystem TESTS Treatment

Every relation must include evidence text and source_id.

---

## Answering rules

The AI assistant must answer like this:

1. Direct answer
2. Evidence summary
3. Source citations
4. Related publications/datasets
5. Limitations
6. Suggested next search or analysis

Rules:

- Never invent source links.
- Never cite a source that was not retrieved.
- If evidence is weak, say so.
- If internal data is needed, ask user to ingest/select project.
- If question is clinical/medical, state that it is research support, not medical advice.
- If patient-identifiable text is present, redact before external LLM use.
- Separate public knowledge from internal lab knowledge.

---

## Accuracy target

Do not promise 100% accuracy.
Do not claim 98% accuracy until evaluation proves it.

Target:

- 95–98% source-grounded correctness for covered/indexed topics
- 100% citation requirement for scientific claims
- refusal/qualification when source coverage is missing

Build evaluation:

- 100 core questions
- expected publications
- expected datasets
- expected entities
- expected relations
- automatic grading
- manual review mode

---

## Scheduled refresh

Implement refresh jobs:

- website crawl: weekly
- publication search: weekly
- PubMed/OpenAlex metadata update: weekly
- dataset registry update: monthly
- internal docs: on upload/change
- Qdrant index health: daily
- evaluation tests: after every ingest

---

## Admin UI

Create Research Knowledge Admin screen with:

1. Source registry
2. Publications
3. Datasets
4. Knowledge graph
5. Ingestion jobs
6. Index freshness
7. Evaluation results
8. Failed documents
9. Search test console

For each source show:

- status
- last checked
- chunks indexed
- entities extracted
- relations extracted
- source URL
- errors
- re-index button

---

## Backend routes

Add:

- `GET /api/research-knowledge/status`
- `POST /api/research-knowledge/crawl/farkkila`
- `POST /api/research-knowledge/ingest-publications`
- `POST /api/research-knowledge/ingest-datasets`
- `POST /api/research-knowledge/ingest-url`
- `POST /api/research-knowledge/reindex`
- `GET /api/research-knowledge/sources`
- `GET /api/research-knowledge/publications`
- `GET /api/research-knowledge/datasets`
- `GET /api/research-knowledge/entities`
- `GET /api/research-knowledge/relations`
- `GET /api/research-knowledge/search`
- `POST /api/research-knowledge/evaluate`
- `GET /api/research-knowledge/evaluation-results`

All write/admin routes require admin/editor role.
Read routes require platform auth.

---

## Frontend routes

Add:

- `research_knowledge_admin`
- `publication_browser`
- `dataset_registry`
- `knowledge_graph_browser`
- `research_search`

Integrate with:

- AI Lab Assistant
- Unified Search Overlay
- Document Viewer
- Project pages

---

## Implementation order

Phase 1:

1. Create DB migration.
2. Create registry models.
3. Create crawler/fetcher skeleton.
4. Ingest Färkkilä website pages.
5. Ingest publication metadata.
6. Create Qdrant collection.
7. Index chunks.
8. Add search endpoint.

Phase 2:

1. Add dataset registry ingestion.
2. Add knowledge graph extraction.
3. Add admin UI.
4. Connect to unified search.

Phase 3:

1. Connect to AI assistant.
2. Add citation cards.
3. Add evaluation set.
4. Add scheduled refresh.

Phase 4:

1. Add reranking.
2. Add relation-aware answers.
3. Add dashboard.
4. Improve accuracy tests.

---

## Build and test

Run:

```bash
python -m compileall app_skeleton/api
pytest
npm run build
```

Manual tests:

1. Crawl Färkkilä website.
2. Ingest publications.
3. Search `MHC class II HGSC`.
4. Verify Cancer Discovery paper appears.
5. Search `tertiary lymphoid structures ovarian cancer`.
6. Verify TLS sources appear.
7. Search `GSE211956`.
8. Verify dataset registry result appears.
9. Ask AI `What is Färkkilä Lab known for?`
10. Verify answer cites sources.
11. Ask AI `Which datasets can train HGSOC spatial models?`
12. Verify dataset citations.
13. Ask AI `What is the evidence for MHC class II in HGSC?`
14. Verify source-grounded answer.
15. Ask a question outside coverage.
16. Verify the assistant admits uncertainty.
17. Test private internal document visibility.
18. Test no absolute paths leak.
19. Test Qdrant status.
20. Test re-index job.

---

## Output required from coding AI

Return:

1. Architecture summary
2. Files changed
3. Complete code for each new/changed file
4. SQL migrations
5. Environment variables
6. Commands run
7. Test results
8. Remaining limitations
9. Manual QA checklist
10. Next recommended improvements

Do not claim tests passed unless run.
Do not fake ingestion/indexing.
Do not hallucinate citations.
Build this as a real professional research knowledge infrastructure.
