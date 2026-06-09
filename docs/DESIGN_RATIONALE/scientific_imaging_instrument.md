# Scientific Imaging Instrument — Design Rationale

OMEIA microscopy viewing follows **instrument-first** principles from the master implementation roadmap (Phases 1–2).

## Non-negotiable rules implemented

| Rule | Implementation |
|------|----------------|
| Scientific instrument, not photo viewer | UI labeled **Scientific Imaging Instrument**; raw probe separate from display |
| Raw data integrity | `GET /api/assets/{id}/image/pixel` reads source file dtype without display normalization |
| Display ≠ source | Tiles/windowing/gamma affect canvas only; manifest stores `dtype`, `bit_depth`, `value_min/max` |
| Reproducible measurements | Physical coordinates from OME `PhysicalSizeX`; scale bar uses µm calibration |
| Traceable AI (future) | Instrument metadata panel surfaces acquisition record for Copilot grounding |

## Phase 1 (current)

- TIFF / OME-TIFF tile streaming
- Metadata panel: dtype, bit depth, channels, Z/T, pyramid, OME-XML, pixel size
- Pixel-perfect canvas (`imageSmoothingEnabled: false`)
- Always-on pixel probe bar (raw + display intensities)
- Zoom, pan, rotate (display), fit, reset
- Multi-channel controls with dtype-aware default windows

## Phase 2 (partial)

- Channel presets: Immune, Tumor, Macrophage, **Exhaustion** panels
- Histogram + window/gamma (8-bit tile display limitation documented below)

## Known limitation (documented)

Display tiles are encoded as 8-bit PNG for transport. **Raw probe** returns true sensor values from file. Full 16-bit windowed tiles are Phase 4 (OME-Zarr / server-side normalization params).

## Validation targets

Compare against Napari, QuPath, OMERO for dimensions, metadata, and pixel probe on shared test OME-TIFFs.

## Code map

- `web/src/features/imaging/components/ImageTileViewer.jsx`
- `web/src/features/imaging/components/ScientificProbeBar.jsx`
- `web/src/features/imaging/components/ScientificMetadataPanel.jsx`
- `omeia/api/image_streaming/image_streaming_service.py` (`sample_pixel_probe`)
- `docs/IMAGE_STREAMING_API.md`
