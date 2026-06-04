# Supabase document sync policy

Most lab assets are **documents** (PDF, Office, text, scripts with summaries). **Images and large binaries** stay on local disk (later P-drive SMB with auth). This policy defines what syncs to **hosted Supabase Postgres** and what never touches **Supabase Storage**.

## What syncs to Supabase (Postgres only)

When `SUPABASE_DB_PASSWORD` is set and `SUPABASE_SYNC_ENABLED=true`:

| Target table | Content |
|--------------|---------|
| `platform.raw_asset_vault` | Registry fields: paths, types, checksums, review/vector status, **truncated** `metadata_json` (text previews only) |
| `platform.knowledge_assets` | Digitalization registry when present locally |
| `platform.extracted_texts` | **Truncated** `raw_text` / `cleaned_text` previews (not full corpora) |

Sync source is always **local Postgres** (`POSTGRES_CONN`). Destination is the **Supabase pooler** URI built from `SUPABASE_DB_PASSWORD` (see `app_skeleton/api/supabase_config.py`).

Upserts are **idempotent** by `asset_id`.

## What stays local

| Asset class | `storage_provider` | `extraction_status` | Notes |
|-------------|-------------------|---------------------|-------|
| Images (`.png`, `.tiff`, …) | `local_dev` or `local_database_mirror` | `metadata_only` | Never Supabase Storage blobs |
| Large binaries / OME-TIFF / video | same | `metadata_only` + `vault_policy: large_binary_metadata_only` | Metadata row may sync only if a **text preview** exists and policy allows |
| Original files on disk / DataCloud / P-drive | `datacloud_webdav`, `pdrive_smb`, `local_*` | — | Binaries are not uploaded by this job |

**Do not** upload large binaries or images to **Supabase Storage**. Use DataCloud / mounted paths for originals.

## Eligibility (document sync job)

Included when **all** of the following hold:

- Not an image extension / `asset_type=image` when `SUPABASE_SKIP_IMAGE_SYNC=true` (default)
- Not `storage_provider=supabase_storage`
- Not `metadata_only` large-binary policy without extractable text
- Document kind **or** non-empty extracted text / metadata text preview

Excluded: PNG/TIFF/etc., metadata-only large files, storage blobs.

## Free tier guardrails

Supabase free tier is roughly **500 MB database** and limited egress. This platform defaults to conservative sync:

| Variable | Default | Purpose |
|----------|---------|---------|
| `SUPABASE_SYNC_ENABLED` | `false` | Opt-in — no accidental full sync |
| `SUPABASE_MAX_TEXT_BYTES` | `50000` | Max UTF-8 bytes per text field in a row |
| `SUPABASE_SYNC_BATCH_SIZE` | `100` | Rows per upsert batch |
| `SUPABASE_SKIP_IMAGE_SYNC` | `true` | Skip image extensions |
| `SUPABASE_MAX_DB_MB` | `450` | Skip sync if `pg_database_size` estimate exceeds this |

Operational notes:

- Avoid Supabase Storage for lab corpora (egress + size).
- Run `python scripts/sync_documents_to_supabase.py --dry-run` before first production sync.
- **Do not** run a full ~4800-row sync until `SUPABASE_DB_PASSWORD` is in `configs/.env` and migrations are applied.

## Reports and status

- Last run: `app_skeleton/data/ingestion_reports/sync_run_report.json`
- API / connectors: `supabase_sync` block in `GET /api/platform/connectors`

## Enable sync (checklist)

1. Set `SUPABASE_DB_PASSWORD` (and keys) in `configs/.env` — see `configs/SUPABASE_SETUP.md`
2. `python scripts/apply_sql_migrations.py`
3. Ingest vault locally (`vault_ingest` / digitalization) so local Postgres is populated
4. Set `SUPABASE_SYNC_ENABLED=true`
5. Dry run: `python scripts/sync_documents_to_supabase.py --dry-run --limit 200`
6. Limited sync: `python scripts/sync_documents_to_supabase.py --limit 500`
7. Or admin API: `POST /api/supabase/sync/documents` (requires auth when `PLATFORM_AUTH_DISABLED=false`)

## NEEDS_USER_DECISION

If `SUPABASE_DB_PASSWORD` is **missing**, the sync job returns `needs_user_decision` and does not write to hosted Postgres. Add the database password from Supabase Dashboard → Settings → Database, then re-run migrations and a dry run.

## Firebase (future — images metadata only)

Image **files** remain local / SMB. Optional future: Firebase for **image metadata** only (dimensions, channel names, project links) — not file bytes.

| Variable | Default |
|----------|---------|
| `FIREBASE_IMAGE_METADATA_ENABLED` | `false` |

No Firebase image sync is implemented in this phase.
