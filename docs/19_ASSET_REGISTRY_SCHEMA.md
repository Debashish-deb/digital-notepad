# 19 — Asset registry schema

## Primary table: `platform.raw_asset_vault` (migration `111`)

| Column | Type | Notes |
|--------|------|-------|
| `asset_id` | text PK | Stable id (hash or slug) |
| `storage_provider` | text | `datacloud_webdav`, `pdrive_smb`, `local_database_mirror`, `supabase_storage`, `local_dev`, `unknown` |
| `logical_path` | text | UI-safe path; no host prefix |
| `filename` | text | Basename |
| `extension` | text | Lowercase ext |
| `size_bytes` | bigint | |
| `checksum_sha256` | text | Dedup key |
| `asset_type` | text | document, image, code, … |
| `domain` | text | Legacy domain hint |
| `page_domain_id` | text FK | → `page_domain` (113) |
| `page_section_id` | text FK | → `page_section` (113) |
| `sensitivity_level` | text | unknown → reviewed |
| `review_status` | text | raw, approved, … |
| `vector_status` | text | eligible / blocked for OME-TIFF |
| `original_path` | text | **Server only** — never in API JSON |

## Index table: `platform.storage_objects` (migration `117`)

Logical objects discovered by connector scans before vault promotion.

| Column | Purpose |
|--------|---------|
| `storage_provider` + `logical_path` | Unique key |
| `conflict_flags` | jsonb array of mapping conflicts |
| `needs_user_decision` | Blocks automated promotion |
| `scan_status` | discovered, ingested, stale |

## Storage roots: `platform.storage_root` (114 + 117)

Active rows: `datacloud_webdav`, `pdrive_smb`, `supabase_storage`, `supabase_postgres`, `local_database_mirror`.  
Deprecated row: `cloudflare_r2` (role `deprecated`).

## Provider enum (application)

Defined in `app_skeleton/storage/env.py` — `VALID_STORAGE_PROVIDERS` and `DEPRECATED_STORAGE_PROVIDERS`.

## API exposure

- `GET /api/vault/search`, `/api/vault/manifest` — `_public_row()` strips `original_path`.
- Rebuild: `POST /api/vault/rebuild` (local mirror).
- Sync: `POST /api/vault/sync` (inventory → Postgres).
