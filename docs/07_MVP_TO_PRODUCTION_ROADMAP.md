# 07 — MVP to Production Roadmap

## Phase 0 — Documentation-only foundation

Inputs:

- project docs
- SOPs
- scripts
- README files
- marker panels
- folder trees
- column dictionaries
- synthetic rows

Outputs:

- project registry
- document manifest
- script inventory
- vector search over docs/scripts
- missing-information checklist

## Phase 1 — Database and registry

Tasks:

1. Deploy PostgreSQL/Qdrant/Neo4j dev stack.
2. Apply SQL schemas.
3. Load project registry.
4. Load manifest templates.
5. Generate synthetic patients/samples.
6. Create vector collections.
7. Create audit skeleton.

## Phase 2 — Pipeline metadata integration

Tasks:

1. Register existing image-processing scripts.
2. Register channel maps.
3. Register expected outputs.
4. Add run manifests.
5. Add file checksums.
6. Register QC metrics.
7. Register cell table manifests.

## Phase 3 — Feature warehouse

Tasks:

1. Define feature dictionary.
2. Create sample-level feature matrix template.
3. Create ROI/community feature matrix template.
4. Add feature vectors for similarity search.
5. Add feature registry and lineage.

## Phase 4 — Clinical/statistical tool layer

Tasks:

1. Build clinical dictionary.
2. Implement clinical curation import.
3. Implement survival tool wrapper.
4. Implement group comparison wrapper.
5. Implement analysis run registry.
6. Add plot/table outputs.

## Phase 5 — Research copilot MVP

Tasks:

1. FastAPI endpoint.
2. Streamlit UI.
3. Intent router.
4. PostgreSQL retriever.
5. Qdrant retriever.
6. Neo4j retriever.
7. Python/R tool runner.
8. Answer trace.
9. Five pilot questions.

## Phase 6 — Secure production

Tasks:

1. Authentication.
2. Project-level access.
3. Audit review.
4. Backup/restore.
5. Monitoring.
6. Governance approval.
7. Data retention policy.
8. Team onboarding.

## Suggested 90-day sequence

```text
Days 1–15: docs/scripts inventory + schema setup
Days 16–30: vector DB + documentation search
Days 31–45: pipeline manifest integration
Days 46–60: synthetic feature warehouse + clinical dictionary
Days 61–75: API/UI + retrieval/tool stubs
Days 76–90: pilot project with approved de-identified summaries
```

## MVP definition of done

- documentation search works with citations
- synthetic project/sample/feature query works
- no real patient data required
- Qdrant collections exist
- PostgreSQL schema applies
- answer traces are logged
- access filters are designed and testable
- first five test questions pass
