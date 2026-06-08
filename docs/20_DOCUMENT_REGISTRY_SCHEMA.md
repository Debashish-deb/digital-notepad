# 20 — Document registry schema

## RAG corpus: `rag.document_source` + `rag.document_chunk`

Used by `omeia/api/document_registry.py` for lab operations text (not large binaries).

| Field | Source | Notes |
|-------|--------|-------|
| `document_code` | Derived from path/title | Stable id |
| `title` | File title | |
| `source_type` | file, url, … | |
| `sensitivity_level` | enum | Clinical guardrails |
| `status` | indexed, blocked, … | |
| `metadata` | jsonb | `section_id`, `relative_path`, `where_to_find` (logical) |

Chunks link via `document_id` → `rag.document_chunk`.

## API

- `GET /api/documents/registry?corpus=lab_operations&section_id=`

Responses omit disk paths; use `where_to_find` and `relative_path` under section logical roots.

## Relationship to asset vault

| Concern | Table | Blob location |
|---------|-------|---------------|
| Large files / images | `raw_asset_vault` | DataCloud / P-drive |
| Searchable text | `document_source` | Extracted text in Postgres/Qdrant |
| Scan index | `storage_objects` | External storage |

Ingestion order: register asset → extract text (if allowed) → document_source → vectorize (if reviewed).

## NEEDS_USER_DECISION

- Which PDFs/DOCX under `20_CLINICAL_RESTRICTED` may enter `document_source` (default: metadata only, no extract).
