# Scientific Viewer Feature References

Conceptual inspiration for OMEIA Phase 7B research imaging viewer. No third-party code is embedded; this document explains *why* each capability exists and how researchers use comparable tools.

## Design lineage

| Tool | Relevant concepts | Why it matters |
|------|-------------------|----------------|
| **Napari** | Multi-channel layers, blending, Z/T sliders, lazy tile loading | Standard for Python microscopy; researchers expect channel toggles and additive compositing |
| **QuPath** | ROI annotations, cell classification, measurement in µm | Pathology workflows need calibrated measurements and persistent ROIs |
| **ImageJ/Fiji** | Histogram windowing, line/area tools, pixel inspector | Decades of training; min/max and gamma are muscle memory for contrast |
| **CellProfiler** | Segmentation overlays, per-object metrics | Links imaging to quantitative pipelines (area, eccentricity, marker intensity) |
| **OMERO** | Asset-centric access, metadata from OME-XML, no raw paths | Matches our `asset_id` API model and OME-TIFF channel naming |

## Feature mapping in OMEIA

### Channel manager
Researchers multiplex markers (CD3, CD8, DAPI) and need per-channel color, visibility, and intensity windowing before publication figures. Presets (Immune/Tumor/Macrophage panels) mirror common CODEX/IMC panels.

**References:** Schapiro et al., *histocat* / multiplex imaging best practices; Napari layer model (Sofroniew et al., 2021).

### Histogram panel
Windowing via draggable min/max reduces saturation in bright autofluorescence. Gamma correction helps dim cytoplasmic signal.

**References:** Gonzalez & Woods, *Digital Image Processing*; ImageJ brightness/contrast documentation.

### Pixel inspector
Hover readouts validate co-registration and staining quality at single-pixel level during QC.

### Scale bar
Physical pixel size from OME-XML (`PhysicalSizeX`) enables µm/mm scale bars required for peer review.

**References:** OME Data Model (Goldberg et al., 2005); SWG recommendation for pixel calibration metadata.

### Segmentation overlays
Mesmer, StarDist, and nucleus masks are displayed by reference (`overlay_asset_id`) without merging rasters into the base TIFF stream.

**References:** Stringer et al., CellPose/StarDist; Greenwald et al., Mesmer (Vizgen/Vizgen ecosystem).

### ROI manager
Rectangles/polygons/freehand ROIs with project tags support tumor microenvironment sampling and downstream export to analysis notebooks.

**References:** Bankhead et al., QuPath (2017).

### Cell inspector
Per-cell area, eccentricity, centroid, and marker intensities bridge viewer and single-cell tables.

**References:** Carpenter et al., CellProfiler (2006).

### Measurement tools
Distance, area, and perimeter in calibrated units support quick size checks without leaving the viewer.

### Spatial analysis (stub)
Neighborhood and immune–tumor proximity maps are planned for Phase 8+; QuPath and spatial transcriptomics tools (Squidpy, Giotto) motivate the API shape.

## Linux validation

Run on the Linux primary host after `git pull` and bootstrap.

### Prerequisites

```bash
cd ~/data4TB/digital-notepad
git pull
./scripts/deploy/linux_bootstrap_all.sh --skip-docker
# Apply schema if not yet applied:
psql "$DATABASE_URL" -f sql/152_image_viewer_extensions.sql
./scripts/start_linux.sh
```

Set in `configs/.env` (see `config/env/.env.example`):

```bash
IMAGE_ENABLE_SEGMENTATION_OVERLAYS=true
IMAGE_ENABLE_ROI_ANNOTATIONS=true
IMAGE_ENABLE_HEATMAPS=false
IMAGE_LOW_RESOURCE_MODE=false
```

### Test matrix

| Scenario | Steps | Expected |
|----------|-------|----------|
| **Standard TIFF** | Open document library → `.tif` → viewer hash | Channels tab, tile zoom/pan, thumbnail fallback if not inspected |
| **OME-TIFF** | Inspect asset via admin API; open manifest | `channel_names`, `physical_pixel_size_um`, scale bar when size present |
| **Large image** | Wide-field TIFF with pyramid | Level selection changes at zoom; status shows load progress |
| **Overlays** | POST overlay with `overlay_asset_id`; Overlays tab | Listed overlay; segmentation controls visible when flag on |
| **ROI** | ROI tab → rectangle → draw → save | GET `/image/rois` lists ROI; persists after reload (Postgres or JSON fallback) |
| **Cell inspect** | Overlays → demo cell or `/image/cells/{id}` | Returns area, eccentricity, centroid JSON |
| **Low resource** | `IMAGE_LOW_RESOURCE_MODE=true` | Preset save UI hidden; lighter sidebar |
| **Performance** | Pan/zoom 2048²+ image | Tiles cache; no filesystem paths in network tab |

### API smoke tests

```bash
python -m pytest tests/test_image_viewer_phase7b.py tests/test_image_streaming.py -q
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/assets/ASSET_ID/image/manifest" | jq .viewer_flags
```

Browser: `http://$(tailscale ip -4):5173#viewer/image/ASSET_ID`

## Rollback via feature flags

Disable capabilities without reverting code:

| Flag | Effect when `false` |
|------|---------------------|
| `IMAGE_ENABLE_ROI_ANNOTATIONS` | ROI POST/DELETE return 403; ROI UI shows disabled message |
| `IMAGE_ENABLE_SEGMENTATION_OVERLAYS` | Segmentation panel disabled |
| `IMAGE_ENABLE_HEATMAPS` | Heatmap stub hidden |
| `IMAGE_LOW_RESOURCE_MODE` | Hides preset persistence UI; reduces histogram fetches |

Core tile streaming (`metadata` → `manifest` → `tile` → `stream`) is unchanged.

## Future enhancements

- GPU-accelerated compositing and WebGL pyramid renderer
- Real overlay geometry fetch and canvas rasterization from `overlay_asset_id`
- Spatial analysis: k-nearest immune distances, Ripley's K
- OMERO-style bulk ROI export (GeoJSON, QuPath JSON)
- Integrated quality eval hooks for viewer latency metrics
