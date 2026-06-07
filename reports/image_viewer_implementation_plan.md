# OME-TIFF / Tile Viewer — Implementation Plan

Date: 2026-06-07  
Status: **Plan only** (placeholder screen exists; full viewer not implemented)

## Current state

| Layer | Status |
|-------|--------|
| `ImageViewerPlaceholderScreen.jsx` | Loads manifest + metadata + thumbnail; shows static preview |
| `imageAssetsClient.js` | `fetchImageManifest`, `fetchImageMetadata`, `loadThumbnailBlobUrl`, hash routing |
| `image_assets.py` router | `metadata`, `manifest`, `thumbnail`, `tile`, `stream` endpoints |
| `ImageStreamingService` | Tile generation, pyramid levels, channel/z/t/series params |
| `imageViewerContract.js` | JSDoc types for manifest/metadata |

**Gap:** No interactive canvas — no zoom/pan, no tile pyramid rendering, no channel UI.

## Target UX

1. Open from `#viewer/image/{assetId}` or Scientific File Explorer “Streaming viewer”
2. Full-screen or module panel with:
   - Pyramid tile canvas (zoom 0.1×–40×, pan, fit)
   - Channel / marker selector (OME multi-channel)
   - Z-stack and time slider when `series_count` / dimensions warrant
   - Metadata sidebar (dimensions, dtype, pyramid levels, OME-XML flag, streaming status)
   - Loading skeletons per tile region; error retry banner
   - Thumbnail strip or overview navigator (optional phase 2)

## Implementation phases

### Phase A — Tile canvas core (MVP)

**Frontend**

- New `ImageTileViewer.jsx` + `useImageTileLoader.js`
- Replace placeholder body with `<canvas>` or WebGL layer (prefer canvas + `drawImage` for phase A)
- Load manifest on mount; compute visible tile grid from viewport + zoom
- Request tiles: `GET /api/assets/{id}/image/tile?level=&x=&y=&width=&height=&channel=&z=&t=&series=`
- Debounce tile fetches; LRU cache (Map, max ~200 tiles); revoke blob URLs on unmount
- Wheel zoom centered on cursor; drag pan; double-click fit

**Reuse**

- `fetchImageManifest`, `loadThumbnailBlobUrl` from `imageAssetsClient.js`
- Add `buildTileUrl(assetId, params)` helper (auth headers same as thumbnail)

**States**

- `loading` — manifest fetch
- `ready` — tiles painting
- `degraded` — `tile_ready=false`, show thumbnail + message
- `error` — manifest/tile failure with retry

### Phase B — Channel & Z/T controls

- Read `channels`, `pyramid_levels`, manifest `dimensions.axes`
- UI: channel chips; z/t sliders bound to tile query params
- Persist last channel in sessionStorage per assetId

### Phase C — Metadata panel

- Collapsible right rail using existing metadata JSON
- Link to admin readiness (`fetchImageReadiness`) for editors only
- Show `streaming_status`, errors array, file size

### Phase D — Performance & polish

- WebWorker for tile decode (if PNG/jpeg bottleneck)
- Prefetch adjacent tiles
- Minimap from thumbnail
- Keyboard shortcuts (+/− zoom, arrow pan)

## API contract (already implemented)

```
GET /api/assets/{asset_id}/image/manifest
GET /api/assets/{asset_id}/image/metadata
GET /api/assets/{asset_id}/image/thumbnail
GET /api/assets/{asset_id}/image/tile?level&x&y&width&height&channel&z&t&series&format=png
```

Max tile edge: 512px (`MAX_TILE_EDGE` in `image_streaming/constants.py`).

## Files to add/change (when implementing)

| File | Action |
|------|--------|
| `components/ImageTileViewer.jsx` | **New** — canvas + controls |
| `hooks/useImageTileLoader.js` | **New** — cache + fetch queue |
| `api/imageAssetsClient.js` | Add `buildTileUrl`, `loadTileBlobUrl` |
| `screens/ImageViewerPlaceholderScreen.jsx` | Swap preview for `ImageTileViewer` |
| `ImageViewerPlaceholderScreen.css` | Layout for toolbar + canvas + sidebar |

## Risks / dependencies

- Large OME-TIFFs require `tile_ready` jobs completed (`ImageJobQueue`)
- Auth on every tile request (Bearer or auth-skip header) — batch carefully
- Memory on high channel count — limit concurrent channel loads
- Three.js **not required** for 2D tile viewer (keep three-vendor lazy on pipeline/login only)

## Out of scope for first PR

- Annotation layers
- Colormap / contrast UI
- Side-by-side multi-asset compare
- Full OME-XML channel name parsing (use numeric indices first)
