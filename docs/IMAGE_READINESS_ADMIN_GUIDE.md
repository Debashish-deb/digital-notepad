# Image Readiness Admin Guide

## Access

Profile → **Image streaming** (or Administration → Open readiness dashboard).

Requires admin role for inspect/retry endpoints.

## Readiness dashboard

Shows:

- **TIFF asset count** — inventory rows with `.tif`/`.tiff`/`.ome.tif` extensions
- **Inspected** — assets with `inspected_at` in metadata cache
- **Thumbnail ready** / **Tile ready** — post-inspect flags
- **Status breakdown** — counts per `streaming_status`
- **Pending/failed jobs** — job queue state
- **Package availability** — from `GET /api/admin/image-streaming/capabilities`
- **Recommendations** — missing packages and where to install them

See also [IMAGING_PACKAGES_GUIDE.md](./IMAGING_PACKAGES_GUIDE.md).

## Inspect workflow

1. Find `asset_id` from document library (preview or search)
2. Paste into **Inspect assets** textarea (comma or newline separated)
3. Click **Run inspect**
4. Refresh — status should move toward `tile_ready`

Inspect reads TIFF headers only (no full image load).

## Retry failed jobs

Click **Retry failed jobs** to reset failed queue entries to `pending`. Re-run inspect for assets that failed.

## When assets stay `metadata_only`

- File ≥ 50 MB and not yet inspected
- `tifffile` not installed
- File missing on disk (DATABASE_ROOT path)
- Corrupt or unsupported compression (install `imagecodecs`)

## Manual QA checklist

- [ ] TIFF file in explorer shows ImageMetadataCard
- [ ] Thumbnail loads in preview panel
- [ ] `#viewer/image/{assetId}` opens placeholder with manifest
- [ ] Non-TIFF asset returns 404 on image metadata endpoint
- [ ] Viewer role without project access gets 403
- [ ] API responses contain no `logical_path` or `disk_path`
