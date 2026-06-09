# Scientific Instrument Validation

Automated and manual validation for the OMEIA Scientific Imaging Instrument (Phases 1–12).

## Automated validation (tifffile ground truth)

```bash
# Use the repo venv (system python3 lacks FastAPI)
./.venv/bin/python scripts/imaging/validate_scientific_instrument.py

# Or from repo root after bootstrap — script auto-re-execs into .venv when needed:
python3 scripts/imaging/validate_scientific_instrument.py

# Specify OME-TIFF:
SCI_VALIDATION_TIFF=/path/to/sample.ome.tif ./.venv/bin/python scripts/imaging/validate_scientific_instrument.py
```

If you see `ModuleNotFoundError: No module named 'fastapi'`, run `./scripts/deploy/linux_bootstrap_all.sh --skip-docker` once to create `.venv`, then use `./.venv/bin/python` as above.

Report: `tests/imaging_validation_last_run.json` (gitignored).

Checks:

| Check | Meaning |
|-------|---------|
| `dimensions_match` | Manifest width/height equals tifffile page shape |
| `dtype_match` | Manifest dtype matches array dtype |
| `pixel_probes_match` | Raw probe at corner/center matches direct file read |

**Equivalence note:** Napari, QuPath, and OMERO reading the same OME-TIFF should agree on dimensions, dtype, and pixel values. CLI validation uses `tifffile` as the reference reader (same bytes on disk).

## Pytest

```bash
pytest tests/test_scientific_instrument_validation.py -q
pytest tests/test_image_streaming.py tests/test_image_viewer_phase7b.py -q
```

## Manual checklist — Napari

- [ ] Open the same OME-TIFF in Napari (drag file or `napari.view_image`).
- [ ] Compare image shape (Y, X) and channel count with instrument metadata panel.
- [ ] Hover pixel: compare raw value at (0,0), center, and max corner with **Scientific probe bar**.
- [ ] Adjust contrast in Napari; confirm OMEIA display window changes do not alter raw probe.

## Manual checklist — QuPath

- [ ] Import OME-TIFF; verify width/height in image metadata.
- [ ] Use pixel inspector on identical (x, y); compare to `/api/assets/{id}/image/pixel`.
- [ ] Draw rectangle ROI; compare area in µm² when `PhysicalSizeX` is present.

## Manual checklist — OMERO

- [ ] Import or attach the same file to OMERO.iviewer.
- [ ] Confirm pyramid level count and tile dimensions vs manifest `pyramid_levels` / `tile_size`.
- [ ] Spot-check pixel intensity at shared coordinates.

## Known limitations

- Display tiles are 8-bit PNG for transport; use **raw pixel probe** and **ROI measure** endpoints for quantitative work.
- `supports_ome_zarr: false` in manifest until OME-Zarr primary store is enabled (see `docs/IMAGE_STREAMING_API.md`).
- AI council and strategy panels require literature grounding; mock provider returns structured stubs without live LLM.

## Blockers for true GUI comparison

- Headless CI cannot launch Napari/QuPath/OMERO GUIs; manual steps above are required for visual parity.
- Multi-channel OME-TIFF with non-standard axis order may differ in default channel mapping — always verify channel names in metadata.
