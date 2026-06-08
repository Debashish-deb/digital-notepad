# TIFF/OME-TIFF Streaming Implementation Plan

## Current API summary

OMEIA already exposes:

- **Document library** (`/api/document-library/*`) — inventory search, facets, preview metadata from `raw_asset_inventory.json`
- **Secure files** (`/api/files/download|preview|metadata`) — provider + logical_path (not used for image streaming; asset_id only)
- **Thumbnails** (`thumbnail_service.py`) — Pillow-based cache under `12_APP_PREVIEWS`
- **TIFF hints** (`document_extraction.py`) — optional `tifffile` header reads during digitalization

## New image streaming layer

Authenticated endpoints under `/api/assets/{asset_id}/image/*`:

| Endpoint | Purpose |
|----------|---------|
| `GET .../metadata` | Cached/stub image metadata |
| `GET .../manifest` | Viewer contract (dimensions, tile size, URLs) |
| `GET .../thumbnail` | JPEG thumbnail (lazy generation) |
| `GET .../tile` | Region tile (max 512×512) |
| `GET .../stream` | Raw byte stream with `Range` support |
| `GET /api/admin/image-streaming/readiness` | Admin coverage stats |
| `POST /api/admin/image-streaming/inspect` | Inspect selected asset_ids |
| `POST /api/admin/image-streaming/retry-failed` | Reset failed jobs |

## Required metadata fields (`metadata.image` cache)

Stored in `omeia/data/image_metadata_cache.json`:

- `format` — `tiff` | `ome_tiff`
- `streaming_status` — `unknown`, `metadata_only`, `thumbnail_ready`, `tile_ready`, `failed`
- `dimensions`, `width`, `height`, `channels`, `dtype`
- `pyramid_levels`, `pyramidal`, `ome_xml_present`
- `tile_ready`, `thumbnail_ready`, `inspected_at`, `errors`

## Frontend changes

1. `get_preview` adds `is_streamable_image`, `image_metadata`, `thumbnail_url`, `viewer_url`
2. `ScientificFileExplorer` — `ImageMetadataCard` for TIFF assets
3. Hash route `#viewer/image/{assetId}` — placeholder viewer screen
4. Admin readiness dashboard under Profile → Image streaming

## Security

- Only `asset_id` in URLs; disk/logical paths never returned from image APIs
- `can_access_image_asset` wraps `can_download_file` + project/sensitivity checks
- All routes require `require_platform_user`; admin routes require admin role
- Tile width/height capped at 512px
- Audit logging via `log_image_access`

## Risks

| Risk | Mitigation |
|------|------------|
| Large TIFF memory use | Header-only inspect; tile region reads only |
| Missing `tifffile` | Graceful stub metadata; readiness dashboard flags |
| Auth on `<img>` tags | Blob URL fetch with Bearer token |
| Compressed TIFF codecs | Document `imagecodecs` optional dep; metadata-only fallback |
| No DB migration | JSON sidecar cache keyed by asset_id |

## Phases not in scope

- Full pan/zoom viewer, annotations, Research OS integration
- Bulk auto-processing of all TIFFs (inspect is admin-triggered)
- Exposing raw storage paths to frontend
