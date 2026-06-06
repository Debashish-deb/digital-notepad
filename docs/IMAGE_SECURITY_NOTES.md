# Image Security Notes

## Identifier-only access

- Clients pass `asset_id` only
- Server resolves `storage_provider` + `logical_path` + `disk_path` internally
- API responses strip `disk_path`, `logical_path`, `provider`, `original_path`

## Authorization

`can_access_image_asset(user, asset_row)`:

1. `can_download_file(user, logical_path, project_code=project_hint)`
2. Restricted/confidential sensitivity → admin/editor only

Admin inspect/readiness requires `require_admin_user`.

## Audit trail

Image open/stream events logged:

```
SECURITY: Image access - User {email} {action} asset {asset_id}
```

Actions: `metadata`, `manifest`, `thumbnail`, `tile/...`, `stream`

## Tile bounds

- Max tile edge: 512 px
- Max tile pixels: 262144
- Prevents arbitrary huge region reads

## Streaming

- `Range` header validated; 416 on invalid range
- No directory listing or path traversal (inherits secure path resolution)

## Rate limiting (recommended)

Production should add per-user limits on:

- `/image/tile` — e.g. 120 req/min
- `/image/stream` — e.g. 30 req/min

Simple in-memory counter keyed by `user.email` is sufficient for single-instance deployments.

## Frontend

- Thumbnails fetched via `fetch` + Bearer token → blob URL (img tags do not send Authorization)
- Do not embed `logical_path` in viewer routes
