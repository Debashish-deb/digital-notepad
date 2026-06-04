# 23 — Storage worker implementation checklist

## Environment

- [ ] `DATACLOUD_WEBDAV_BASE_URL`, `DATACLOUD_ROOT`, `DATACLOUD_USERNAME`, `DATACLOUD_APP_PASSWORD`
- [ ] `PDRIVE_ENABLED`, `PDRIVE_MOUNT_PATH` (optional)
- [ ] `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_DB_PASSWORD`
- [ ] `FIREBASE_SERVICE_ACCOUNT_PATH`, `PLATFORM_AUTH_DISABLED=false` for prod
- [ ] Apply SQL through `116` + `117_storage_architecture.sql`

## Connector smoke tests

- [ ] `GET /api/storage/connectors/status` — datacloud + pdrive + supabase_storage; no active R2
- [ ] `GET /api/storage/datacloud/list` — returns children or empty if unconfigured
- [ ] `GET /api/storage/datacloud/manifest` — `truncated` flag understood
- [ ] `POST /api/storage/ingest/datacloud_webdav` — upserts `storage_objects`
- [ ] P-drive scan when mount present

## Ingestion

- [ ] Run folder validation (`docs/18`)
- [ ] Map domains (`docs/21`) — mark conflicts `needs_user_decision`
- [ ] `POST /api/vault/rebuild` (local) → `POST /api/vault/sync`
- [ ] Review queue under confidence threshold

## Safety

- [ ] Confirm no DELETE/MOVE in automated jobs
- [ ] API responses grep-clean for `/Users/`, `\\\\`, WebDAV host
- [ ] Clinical paths blocked from vectorize

## UI

- [ ] Data & Storage — roots + connectors (deprecated hidden)
- [ ] Administration — production connectors panel

## Tests

- [ ] `pytest tests/test_lab_storage_api.py -q` from blueprint root

## NEEDS_USER_DECISION log

| Item | Owner |
|------|-------|
| Live DataCloud tree vs doc 18 table | Lab PI / IT |
| PDRIVE_MOUNT_PATH on server | IT |
| Supabase anon key for client features | Developer |
| Vault rows with legacy `cloudflare_r2` provider | Admin review |
