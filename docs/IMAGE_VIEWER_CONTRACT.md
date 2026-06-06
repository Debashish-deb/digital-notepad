# Image Viewer Contract

Frontend type definitions live in `app_skeleton/ui/react_frontend/src/types/imageViewerContract.js`.

## ImageViewerAsset

Emitted by document library preview for streamable TIFF assets:

```javascript
{
  asset_id: string,
  is_streamable_image: true,
  image_metadata: ImageMetadata,
  thumbnail_url: '/api/assets/{id}/image/thumbnail',
  viewer_url: '#viewer/image/{id}'
}
```

## ImageMetadata

Populated after inspect job or stubbed before inspect:

| Field | Type | Notes |
|-------|------|-------|
| `format` | string | `tiff`, `ome_tiff` |
| `streaming_status` | string | Pipeline state |
| `dimensions.shape` | number[] | tifffile series shape |
| `pyramid_levels` | number | 1 + SubIFD count |
| `ome_xml_present` | boolean | OME-XML in TIFF |
| `tile_ready` | boolean | Tile API safe to call |

## ImageViewerManifest

Fetched by placeholder viewer at `#viewer/image/{assetId}`:

- Use `tile_size` and `pyramid_levels` to plan tile grid
- Use `thumbnail_url` for overview (via authenticated blob fetch)
- Use `stream_url` only for download/raw access — not for in-browser full load

## Future full viewer consumption

1. Load manifest
2. If `tile_ready`, request tiles: `GET .../tile?level=&x=&y=&width=&height=`
3. Composite tiles in canvas/WebGL layer
4. Fall back to `thumbnail_url` when `streaming_status` is `metadata_only`
5. Never construct URLs from `logical_path` — only `asset_id`
