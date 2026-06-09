# Image Streaming API

All endpoints require platform authentication (`require_platform_user`). Admin endpoints require admin role.

## Asset endpoints

### `GET /api/assets/{asset_id}/image/metadata`

Returns format and cached `image_metadata`. No filesystem paths.

### `GET /api/assets/{asset_id}/image/manifest`

Viewer-oriented manifest:

```json
{
  "asset_id": "asset_abc",
  "format": "tiff",
  "streaming_status": "tile_ready",
  "width": 2048,
  "height": 2048,
  "pyramid_levels": 3,
  "tile_size": 256,
  "tile_ready": true,
  "thumbnail_url": "/api/assets/asset_abc/image/thumbnail",
  "metadata_url": "/api/assets/asset_abc/image/metadata",
  "stream_url": "/api/assets/asset_abc/image/stream",
  "viewer_route": "#viewer/image/asset_abc"
}
```

Additional Phase 7B manifest fields:

- `channel_names` — from OME-XML when present
- `physical_pixel_size_um` / `pixel_size_um` — micron calibration
- `dtype`, `bit_depth`, `value_min`, `value_max`, `is_float_dtype` — scientific encoding (Phase 1 instrument)
- `viewer_mode` — `scientific_instrument`
- `inspected_at` — last header inspect timestamp
- `viewer_flags` — `{ low_resource_mode, heatmaps, segmentation_overlays, roi_annotations }`
- `supports_ome_zarr` — `false` (OME-Zarr planned as future primary large-image store)
- `ome_zarr_route` — `null` until OME-Zarr is enabled
- `lod_hint` — `pyramid_viewport_tiles` (viewport-only pyramid tile loading)

### `GET /api/assets/{asset_id}/image/pixel`

Raw pixel probe at image coordinates (preserves source dtype).

Query: `x`, `y` (required), optional `z`, `t`, `level`.

Returns per-channel `raw_value`, physical µm coordinates when calibrated, and dtype profile.

### `GET /api/assets/{asset_id}/image/rois`

List user ROIs (auth + asset access). POST creates; DELETE removes by `roi_id`.

### `GET /api/assets/{asset_id}/image/overlays`

List segmentation overlays referencing `overlay_asset_id`.

### `GET /api/users/me/image/channel-presets`

User channel presets. POST save; DELETE by `preset_id`.

### `GET /api/assets/{asset_id}/image/cells/{cell_id}`

Cell inspection metrics (stub or overlay metadata).

### `GET /api/assets/{asset_id}/image/histogram`

Sample histogram for a tile region (`channel`, `x`, `y`, `width`, `height`, `bins`).

See `docs/SCIENTIFIC_VIEWER_FEATURE_REFERENCES.md` for feature rationale and Linux validation.

### `GET /api/assets/{asset_id}/image/thumbnail`

Returns `image/jpeg`. Generates on first request via `tifffile` region read + Pillow resize. Cached per asset_id.

### `GET /api/assets/{asset_id}/image/tile`

Query parameters:

| Param | Default | Max |
|-------|---------|-----|
| `level` | 0 | 32 |
| `x`, `y` | 0 | — |
| `width`, `height` | 256 | 512 |
| `channel`, `z`, `t`, `series` | 0 | — |
| `format` | `png` | `png` or `jpeg` |
| `window_min`, `window_max` | — | Optional dtype-preserving display window (skips per-tile min-max normalize) |

Returns 400 if tile exceeds 512×512 pixels.

### Future: OME-Zarr

Large whole-slide and multiplex datasets will use OME-Zarr as the primary read path. Until `supports_ome_zarr` is `true`, TIFF/OME-TIFF pyramid tiles remain the production transport.

### `POST /api/assets/{asset_id}/image/measure`

ROI measurements from raw file regions: area, perimeter, mean/median/min/max/std, integrated intensity; µm/µm² when calibrated.

### `GET /api/imaging/markers/graph`

Channel marker nodes linked to research KB entities.

### `POST /api/imaging/council/analyze`

Multi-agent imaging council (literature, biomarker, spatial, critic) with guardrails.

See `docs/SCIENTIFIC_INSTRUMENT_VALIDATION.md` for Napari/QuPath/OMERO checklists.

### `GET /api/assets/{asset_id}/image/stream`

Full file stream. Supports `Range: bytes=start-end` (206 Partial Content).

## Admin endpoints

### `GET /api/admin/image-streaming/readiness`

Counts TIFF assets, inspection coverage, job queue status, dependency availability.

### `POST /api/admin/image-streaming/inspect`

Body: `{ "asset_ids": ["asset_abc", ...] }` (max 100). Runs synchronous header inspect per asset.

### `POST /api/admin/image-streaming/retry-failed`

Resets failed jobs to `pending`.

## Document library integration

`GET /api/document-library/preview/{asset_id}` includes for `.tif`/`.tiff`/`.ome.tif`:

- `is_streamable_image: true`
- `image_metadata` from cache
- `thumbnail_url`, `viewer_url`

## Rate limiting

Not enforced in code yet. Recommended: per-user counter on tile/stream endpoints in production (see `IMAGE_SECURITY_NOTES.md`).
