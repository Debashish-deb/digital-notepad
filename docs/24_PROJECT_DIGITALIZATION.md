# Project folder digitalization engine

Digitalizes lab project storage into the **Raw Knowledge Vault** before RAG, vectors, or chatbot features.

## Storage root

Set in `configs/.env` (never hardcode):

```env
LAB_STORAGE_ROOT=/path/to/mounted/notebook/root
```

Falls back to `PROJECTS_ROOT` / `database/projects` when unset.

## Run

```bash
cd farkki_ai_platform_blueprint
.venv-local/bin/python scripts/project_digitalize.py --project MyProjectFolder
.venv-local/bin/python scripts/project_digitalize.py --full --resume
.venv-local/bin/python scripts/project_digitalize.py --dry-run --project MyProjectFolder
.venv-local/bin/python scripts/project_digitalize.py --retry-failed --project MyProjectFolder
```

## API

- `POST /api/digitalize/project/{name}`
- `POST /api/digitalize/scan`
- `GET /api/digitalize/search?q=`
- `GET /api/digitalize/review?kind=uncategorized|failed|large_files|tables|texts|scripts|logs|projects`
- `PATCH /api/digitalize/review/{asset_id}`

## Database

Migration `sql/119_project_digitalization.sql`: `project_candidates`, `knowledge_assets`, `extracted_texts`, `extracted_tables`, `script_metadata`, `log_summaries`, entity/relationship candidates, `digitalization_runs`.

## Principles

- No delete/move/rename of originals
- No forced categorization (`uncategorized` default)
- Large TIFF/OME-TIFF/H5/RDS → metadata only
- `ENABLE_VECTOR_EMBEDDINGS=false` by default

See `docs/15_STORAGE_MASTER_PLAN.md` and `processor.txt` for related pipeline code.
