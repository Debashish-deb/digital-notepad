# Imaging packages — what to install where

OMEIA TIFF/OME-TIFF streaming reads files from your database mirror. **There is no public cloud API that replaces local TIFF decoding** — the backend (or a Docker sidecar on your Linux workstation) must have the libraries installed.

## Tier 1 — Core (install everywhere the API runs)

**Mac dev or Linux API host** — small pip wheels (~30–80 MB):

```bash
pip install -r app_skeleton/api/requirements-imaging-core.txt
```

| Package | Role | API-only alternative? |
|---------|------|------------------------|
| `tifffile` | Header read, tiles, OME-XML | **None** — required |
| `imagecodecs` | JPEG/LZW/deflate TIFF pages | **None** for compressed TIFF |
| `numpy` | Tile arrays | bundled with above |
| `Pillow` | Thumbnail JPEG encode | **None** for thumbnails |

Check status: `GET /api/admin/image-streaming/capabilities` (admin).

## Tier 2 — Extended (optional pip)

```bash
pip install -r app_skeleton/api/requirements-imaging-extended.txt
```

| Package | Role |
|---------|------|
| `zarr`, `fsspec` | Future OME-Zarr |
| `dask` | Large array tiling |
| `scikit-image` | Light processing |
| `deeptile` | ML tiling/stitching prep (not used by viewer API yet) |

## Tier 3 — Workstation / Docker (heavy)

Install on **Linux workstation only** — not needed on Mac thin client:

```bash
pip install -r app_skeleton/api/requirements-imaging-workstation.txt
# plus system libs:
# sudo apt install libvips-dev openslide-tools libopenslide-dev libtiff-dev libjpeg-dev
```

| Package | Role |
|---------|------|
| `pyvips` | Fast region decode |
| `openslide-python` | Whole-slide (.svs, .ndpi) |
| `aicsimageio` | Unified microscopy reader |
| `bioformats2raw`, `raw2ometiff`, `ashlar` | CycIF stitching pipeline |

### Docker (recommended for heavy stack)

```bash
# Standalone — works on Linux even if docker-compose.yml has no imaging-worker:
docker compose -f docker-compose.imaging.yml build
docker compose -f docker-compose.imaging.yml run --rm imaging-worker

# Or use the helper script:
./scripts/docker/build_imaging_worker.sh
```

**Sync from Mac to Linux** (if `digital-notepad` is behind):

```bash
# On Mac, from OMEIA-AI repo:
./scripts/imaging/sync_imaging_worker_to_linux.sh debdeba@dx9-3049-11090:~/data4TB/digital-notepad
```

If you see `no such service: imaging-worker`, you used the **wrong compose file**. Do **not** use `--profile imaging` on root `docker-compose.yml` alone — use `-f docker-compose.imaging.yml` instead.

Slim image without napari: `IMAGING_INCLUDE_NAPARI=0 ./scripts/docker/build_imaging_worker.sh`

**Apple Silicon / `linux-aarch64`:** `bioformats2raw`, `raw2ometiff`, and `ashlar` are skipped (not on conda-forge for ARM). Core TIFF streaming stack still builds. For full CycIF tooling, build the image on your **x86 Linux workstation** (`linux/amd64`).

Mounts `DATABASE_ROOT` read-only for future worker-side inspect jobs.

## Tier 4 — Desktop GUI (not on API server)

| Package | Where |
|---------|-------|
| `napari`, `pyqt` | Analyst desktop / Docker with display |
| `napari-tiler`, `napari-stitcher` | Optional plugins |

The streaming API does **not** import napari.

## What the app uses today

| Endpoint | Packages |
|----------|----------|
| `/image/metadata`, `/manifest` | `tifffile` |
| `/image/thumbnail` | `tifffile`, `Pillow` |
| `/image/tile` | `tifffile`, `imagecodecs`, `Pillow` |
| `/image/stream` | filesystem only |

## Quick install (this Mac)

```bash
cd /path/to/OMEIA-AI
pip install tifffile imagecodecs
python -c "from app_skeleton.api.imaging_capabilities import probe_imaging_stack; import json; print(json.dumps(probe_imaging_stack(), indent=2))"
```

## Linux workstation (persistent)

```bash
pip install -r app_skeleton/api/requirements-imaging-core.txt
# When you need whole-slide / napari ecosystem:
docker compose --profile imaging build imaging-worker
```
