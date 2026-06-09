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

## Phases 2–12 (implemented)

- **Phase 2:** Dtype-aware histograms, LUT picker (solid + Viridis/Inferno/Magma/Plasma/Turbo), Tumor Microenvironment panel
- **Phase 3:** Polygon/circle/line ROI tools, backend ROI measure, CSV/JSON export
- **Phase 4:** OME-Zarr documented (`supports_ome_zarr: false`), LOD label, window_min/max tile params
- **Phase 5:** Segmentation overlay contours on canvas, cell search by phenotype
- **Phase 6:** Spatial nearest-neighbor and tumor–immune distance analysis
- **Phase 7:** `imaging_knowledge_bridge.py`, `GET /api/imaging/markers/graph`
- **Phase 8:** Annotation learning categories + thumbs feedback in `image_viewer_store`
- **Phase 9:** Strategy sidebar tab with imaging-context chat
- **Phase 10:** `POST /api/imaging/council/analyze`
- **Phase 11:** Council guardrails + interpretation disclaimer
- **Phase 12:** `scripts/imaging/validate_scientific_instrument.py`, validation docs + pytest

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
