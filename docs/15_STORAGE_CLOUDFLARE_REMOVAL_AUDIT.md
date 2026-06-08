# 15 — Cloudflare R2 removal audit

**Date:** 2026-06-03  
**Mandate:** Remove Cloudflare R2 from production architecture. Previews and small assets use Supabase Storage or backend-generated derivatives.

## Summary

| Area | Action |
|------|--------|
| Architecture | R2 removed; stack is DataCloud WebDAV → P-drive mount → Supabase Postgres metadata → Supabase Storage (optional small files) |
| `configs/.env.example` | R2 variables removed |
| `omeia/storage/r2_preview.py` | Marked `deprecated_storage_provider`; always `configured: false` |
| `omeia/api/paths.py` | `cloudflare_r2` removed from `STORAGE_PROVIDERS` |
| `omeia/api/connector_status.py` | R2 removed from `production_connectors_summary`; `storage_primary` only |
| `sql/114_storage_roots.sql` | Legacy row remains; `sql/117_storage_objects.sql` marks deprecated |
| UI | Data & Storage hides deprecated connectors |
| Docs `14`, `16–23` | Updated stack |

## Files touched (grep audit)

| Path | Notes |
|------|--------|
| `configs/.env.example` | R2 block removed |
| `omeia/api/paths.py` | No R2 in active providers |
| `omeia/api/connector_status.py` | Deprecated flag only |
| `omeia/api/main.py` | Connector docstring; scan/manifest endpoints for DataCloud/P-drive |
| `omeia/storage/r2_preview.py` | Stub |
| `sql/117_storage_architecture.sql` | `storage_objects` + deprecates `cloudflare_r2` row |
| `omeia/ui/.../navigation.js` | No R2 in description |
| `omeia/ui/.../DataStorageScreen.jsx` | Filters deprecated connectors |
| `docs/14_PRODUCTION_DECISIONS.md` | R2 removed from production table |

## Intentionally not changed

- `docs/12_*`, `docs/13_*`, `prompts/high_end_architect_agent_prompt.md` — historical references; superseded by this doc and `docs/16`.
- `node_modules/` Firebase “Cloudflare Worker” strings — unrelated.
- `BioinformaticsHubScreen.jsx` rclone DataCloud examples — university storage guidance, not R2.

## Replacement for previews

1. **Supabase Storage** — avatars, UI assets, PDF thumbnails under size cap (see `docs/16`).
2. **Backend streaming** — authenticated download via API from DataCloud/P-drive without public CDN.
3. **Local dev** — no preview CDN; optional static mirror under `DATABASE_ROOT`.

## NEEDS_USER_DECISION

None for removal itself. If old vault rows reference `storage_provider = 'cloudflare_r2'`, run a one-time metadata migration to `supabase_storage` or `unknown` after human review — **do not auto-rewrite** production vault rows.
