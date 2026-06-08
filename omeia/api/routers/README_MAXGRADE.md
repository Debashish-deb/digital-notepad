# OMEIA Backend Router Maxgrade Patch

This package contains upgraded versions of the uploaded FastAPI router files:

- `copilot.py`
- `datapad.py`
- `digitalization.py`
- `health.py`
- `knowledge.py`
- `research.py`
- `storage.py`
- `vault.py`

## Main upgrades

- Adds global authenticated access to internal router files.
- Fixes the missing `require_role` import in `digitalization.py`.
- Removes hardcoded `debdeba` researcher attribution from `research.py`.
- Makes notebook/wiki/task/checklist audit attribution use the authenticated platform user.
- Reworks `vault.py` document ingestion so it stores the DB record, chunks text, embeds chunks, creates/uses Qdrant collection, upserts vectors, and returns real indexing status.
- Makes the Qdrant document collection configurable via `DOCUMENT_QDRANT_COLLECTION`, defaulting to `doc_chunks`.
- Hardens `copilot.py` source normalization and removes browser-supplied LLM API key use.
- Keeps public health/auth config endpoints in `health.py`, while protecting stats/connectors.
- Preserves existing route paths and mostly preserves response shapes.

## Validation performed here

All included Python files were syntax-compiled with Python `compile(...)` successfully. Full app import/runtime tests were not run because the full `omeia` package, database, Qdrant service, and environment secrets are not available in this sandbox.

## Important integration note

Replace the corresponding router files in your project, then run:

```bash
python -m compileall omeia/api/routers
pytest
npm run build
```

Then manually verify login-protected routes, document ingestion, Qdrant retrieval, and the Digital AI Lab Assistant chat flow.
