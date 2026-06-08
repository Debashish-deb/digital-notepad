# DataCloud WebDAV setup

**Role:** Primary research file storage for the OMEIA Lab Assistant Platform.  
**Flow:** Frontend → Backend API → Firebase verify → Supabase permissions → `datacloud_webdav` connector.

## Canonical endpoints

| Item | Value |
|------|--------|
| WebDAV base | `https://datacloud.example.org/remote.php/dav/files/YOUR_USERNAME` |
| Logical root | `/farkkila/LAB-ASSISTANT-PLATFORM` |

## Environment variables (canonical names)

```bash
DATACLOUD_WEBDAV_BASE_URL=https://datacloud.example.org/remote.php/dav/files/YOUR_USERNAME
DATACLOUD_ROOT=/farkkila/LAB-ASSISTANT-PLATFORM
DATACLOUD_USERNAME=<helsinki username>
DATACLOUD_APP_PASSWORD=<Nextcloud app password>
```

Legacy aliases still read by the backend if canonical names are empty:

- `DATACLOUD_WEBDAV_URL` → `DATACLOUD_WEBDAV_BASE_URL`
- `DATACLOUD_WEBDAV_USER` → `DATACLOUD_USERNAME`
- `DATACLOUD_WEBDAV_PASSWORD` → `DATACLOUD_APP_PASSWORD`

Copy names from `configs/.env.example` into `configs/.env` only (never commit secrets).

## Security rules

- WebDAV credentials and raw private URLs are **backend-only**.
- API responses expose **logical paths** under `/farkkila/LAB-ASSISTANT-PLATFORM`, never host paths or DAV URLs.
- Do not configure WebDAV in the React app or Vite env.

## Connector capabilities (server)

Module: `omeia/storage/datacloud_webdav.py`

| Operation | API (examples) |
|-----------|----------------|
| List | `GET /api/storage/datacloud/list?relative_path=` |
| Scan | `GET /api/storage/datacloud/scan` |
| Manifest | `GET /api/storage/datacloud/manifest` |
| Upload / download | Worker-only (Python module); not exposed without auth middleware |

## Verification

```bash
# After filling .env
curl -s "http://localhost:8000/api/storage/connectors/status" | jq '.connectors[] | select(.provider_id=="datacloud_webdav")'
```

## NEEDS_USER_DECISION

| Blocker | Why | Info needed | Safe fallback |
|---------|-----|---------------|---------------|
| Missing username/password | PROPFIND cannot authenticate | `DATACLOUD_USERNAME`, `DATACLOUD_APP_PASSWORD` from Nextcloud app password | Connector reports `configured: false`; vault uses `local_database_mirror` |
| Root access failure | Wrong base URL or folder not shared | Confirm folder exists at `/farkkila/LAB-ASSISTANT-PLATFORM` in DataCloud UI | Scan returns empty; document mapping in `docs/18_DATACLOUD_FOLDER_VALIDATION.md` |

See also: `docs/16_STORAGE_CONNECTOR_DESIGN.md`, `docs/18_DATACLOUD_FOLDER_VALIDATION.md`.
