# 16 — Storage connector design

## Stack (active)

| Layer | Provider ID | Role |
|-------|-------------|------|
| Primary blobs | `datacloud_webdav` | Canonical originals under `/farkkila/LAB-ASSISTANT-PLATFORM` |
| Secondary blobs | `pdrive_smb` | Mounted lab share (`PDRIVE_MOUNT_PATH`) |
| Metadata | `supabase_postgres` | Vault, permissions, vectors, jobs |
| Small files | `supabase_storage` | Avatars, UI assets, previews under size cap |
| Dev mirror | `local_database_mirror` | `DATABASE_ROOT` evidence |

**Deprecated:** `cloudflare_r2` — stub in `r2_preview.py` only; not in `STORAGE_PROVIDERS`.

## Module map

| Module | Responsibility |
|--------|----------------|
| `app_skeleton/storage/env.py` | Canonical env names + aliases |
| `app_skeleton/storage/datacloud_webdav.py` | PROPFIND, MKCOL, PUT, GET stream, scan, manifest |
| `app_skeleton/storage/pdrive_smb.py` | Read-only mount scan/manifest |
| `app_skeleton/storage/ingestion.py` | Manifest → `platform.storage_objects` |
| `app_skeleton/api/paths.py` | Public provider registry (no secrets) |
| `app_skeleton/api/connector_status.py` | Production readiness flags |

## API surface (backend-only I/O)

| Endpoint | Safe op | Notes |
|----------|---------|-------|
| `GET /api/storage/datacloud/list` | List | Logical paths |
| `GET /api/storage/datacloud/scan` | Scan | Read-only |
| `GET /api/storage/datacloud/manifest` | Manifest | Ingestion input |
| `GET /api/storage/datacloud/download` | Download | Stream; auth when enabled |
| `GET /api/storage/pdrive/*` | Same shape | Mount required |
| `POST /api/storage/ingest/{provider}` | Ingest | Upserts `storage_objects` |

## Dangerous operations policy

| Operation | Allowed in v1 | Gate |
|-----------|---------------|------|
| PROPFIND / list / scan | Yes | Read-only |
| GET / download | Yes | Auth + sensitivity |
| PUT / upload | Module only | Admin job + path allowlist |
| MKCOL / mkdir | Module only | Under approved prefix |
| DELETE / MOVE / RENAME | **No** | `NEEDS_USER_DECISION` + manual DataCloud UI |

## Response contract

- Never return: WebDAV URL, username, password, `original_path`, UNC paths.
- Always return: `logical_path`, `storage_provider`, `size_bytes`, `type`, optional `page_domain_id` after mapping.

See `docs/22_STORAGE_SAFETY_PERMISSIONS.md`.
