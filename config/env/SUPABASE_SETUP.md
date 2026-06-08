# Supabase — farkki digital platform

Hosted project for production Postgres and API keys. Secrets live only in `configs/.env` (gitignored).

## Project (from dashboard)

| Field | Value |
|--------|--------|
| Name | farkki digital platform |
| Project ref | `ccpvupyiqxubcupvtrtp` |
| Region | `eu-central-1` (Frankfurt) |
| API URL | `https://ccpvupyiqxubcupvtrtp.supabase.co` |
| Pooler (transaction) | `aws-1-eu-central-1.pooler.supabase.com:6543` |

## Three different credentials

Do not mix these up:

1. **Anon key** (`SUPABASE_ANON_KEY`) — Settings → API → `anon` `public`. Safe for browser clients with RLS.
2. **Service role key** (`SUPABASE_SERVICE_ROLE_KEY`) — Settings → API → `service_role` `secret`. Server only; bypasses RLS.
3. **Database password** (`SUPABASE_DB_PASSWORD`) — Settings → Database → database password. Used for direct/psycopg migrations, not the JWT keys.

Your pooler URI shape:

```text
postgresql://postgres.ccpvupyiqxubcupvtrtp:[PASSWORD]@aws-1-eu-central-1.pooler.supabase.com:6543/postgres
```

The platform builds this automatically when `SUPABASE_DB_PASSWORD` is set (see `omeia/api/supabase_config.py`). Until then, `POSTGRES_CONN` keeps pointing at local Docker Postgres.

## `configs/.env` checklist

```env
SUPABASE_URL=https://ccpvupyiqxubcupvtrtp.supabase.co
SUPABASE_PROJECT_REF=ccpvupyiqxubcupvtrtp
SUPABASE_ANON_KEY=<paste anon JWT here>
SUPABASE_SERVICE_ROLE_KEY=<paste service_role JWT here>
SUPABASE_DB_PASSWORD=<database password only>
```

Legacy name `SERVICE_ROLE_KEY` is still read but prefer `SUPABASE_SERVICE_ROLE_KEY`.

## After the database password is set

From the blueprint root:

```bash
cd farkki_ai_platform_blueprint
source ../.venv-local/bin/activate   # or your venv
python scripts/database/apply_sql_migrations.py
```

Restart the API (`start.sh` or uvicorn), then check:

- `GET /health` → `database_connected: true`
- `GET /api/platform/connectors` → `supabase.hosted_configured: true`, `has_anon_key: true`, `db_password_set: true`

Optional: re-sync vault inventory to hosted DB via Administration or `sync_inventory_to_postgres`.

## Document sync (free tier)

Policy: `docs/25_SUPABASE_SYNC_POLICY.md`. Sync copies **metadata + truncated text** from **local** Postgres to **hosted** Postgres. It does **not** upload images or large files to Supabase Storage.

| Variable | Default | Notes |
|----------|---------|--------|
| `SUPABASE_SYNC_ENABLED` | `false` | Must opt in |
| `SUPABASE_MAX_TEXT_BYTES` | `50000` | Per-field UTF-8 cap |
| `SUPABASE_SYNC_BATCH_SIZE` | `100` | Upsert batch size |
| `SUPABASE_SKIP_IMAGE_SYNC` | `true` | Skip `.png`, `.tiff`, etc. |
| `SUPABASE_MAX_DB_MB` | `450` | Skip if DB size estimate high |

Free tier: ~**500 MB** database; avoid Storage egress for lab corpora.

```bash
# After SUPABASE_DB_PASSWORD + migrations + local vault ingest:
python scripts/sync/sync_documents_to_supabase.py --dry-run --limit 200
# Enable in .env: SUPABASE_SYNC_ENABLED=true
python scripts/sync/sync_documents_to_supabase.py --limit 500
```

Admin API (when `PLATFORM_AUTH_DISABLED=false`): `POST /api/supabase/sync/documents?dry_run=true`

Status: `GET /api/platform/connectors` → `supabase.supabase_sync`

**NEEDS_USER_DECISION:** Without `SUPABASE_DB_PASSWORD`, do not run a full ~4800-row sync; the CLI/API return `needs_user_decision`.

## Security

- Never commit `.env`, service role key, or database password.
- Do not put the service role key in the React frontend; use `SUPABASE_ANON_KEY` only if you add a Supabase client later.
