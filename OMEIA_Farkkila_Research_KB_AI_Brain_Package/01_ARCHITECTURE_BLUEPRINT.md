# Architecture Blueprint

## Product goal

Turn the AI Lab Assistant into a source-grounded research brain for Färkkilä Lab and related ovarian cancer spatial biology.

The assistant should know:

- public lab identity and research programs
- lab publications and related datasets
- worldwide literature around HGSC, TLS, MHC class II, spatial biology, and patient-derived models
- internal protocols and computational workflows
- structured relationships between projects, publications, technologies, datasets, markers, cell types, and clinical endpoints

## Target stack

```txt
FastAPI backend
PostgreSQL metadata + knowledge graph
Qdrant vector database
LLM provider / local model
React frontend
Unified search overlay
AI Lab Assistant chat UI
```

## Data planes

### Public data plane

- website pages
- public publications
- public datasets
- public code repositories
- public metadata APIs

Access level: `public`

### Internal data plane

- lab SOPs
- orientation documents
- protocols
- notebooks
- decisions
- project folders
- pipeline scripts
- internal datasets

Access level: `internal` or `restricted`

### Clinical/patient data plane

- sample metadata
- clinical features
- patient-derived model metadata

Access level: strict; never send identifiable text to external LLM APIs.

## Retrieval flow

```txt
User question
  ↓
Privacy audit
  ↓
Query understanding / entity detection
  ↓
Unified Search Service
  ↓
Qdrant semantic search + PostgreSQL metadata + knowledge graph
  ↓
Rerank and filter by permissions
  ↓
LLM answer with source citations
  ↓
UI renders source cards + open actions
```

## Why knowledge graph matters

RAG retrieves text. A knowledge graph adds relations:

- Paper USES Technology
- Dataset SUPPORTS Publication
- Marker IDENTIFIES CellType
- Finding ASSOCIATED_WITH ClinicalEndpoint
- Protocol GENERATES DataType

This lets the assistant answer relation questions such as:

- Which technologies support this finding?
- Which datasets can validate this claim?
- Which lab protocols generated this type of data?
- Which papers support MHC class II as a biomarker?

## Index freshness

Every source should have:

- fetched_at
- last_checked_at
- checksum
- vector_status
- chunk_count
- entity_count
- relation_count
- error_message

## Recommended refresh cadence

- Website: weekly
- Publications: weekly
- Dataset registry: monthly
- Internal docs: on file upload/change
- Qdrant health: daily
- Evaluation tests: after every ingest
