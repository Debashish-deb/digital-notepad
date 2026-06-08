# Scientific Image Viewer — Package References

Short registry for Phase 7 / 13. Long prose stays in docs, not production code.

| Package | Why OMEIA uses it | Reference | Not used for |
|---------|-------------------|-----------|--------------|
| **tifffile** | TIFF/OME-TIFF header read, pyramid tiles, series axes | https://github.com/cgohlke/tifffile | Full-file browser load |
| **imagecodecs** | LZW/JPEG/deflate TIFF page decode | https://github.com/cgohlke/imagecodecs | UI rendering |
| **Pillow** | Thumbnail + tile PNG/JPEG encode | https://python-pillow.org | Scientific analysis |
| **numpy** | Tile array buffers | https://numpy.org | — |
| **pyvips** | Fast region decode (optional worker) | https://www.libvips.org | Default API path |
| **openslide-python** | Whole-slide .svs/.ndpi (optional) | https://openslide.org | CycIF OME-TIFF default |
| **zarr / fsspec** | Future OME-Zarr cloud tiles | https://zarr.dev | Current MVP |
| **DeepCell / Mesmer** | Segmentation workers (LUMI pipeline) | https://deepcell.org | In-browser viewer |
| **StarDist** | Nuclei segmentation alternative | https://github.com/stardist/stardist | In-browser viewer |
| **Ashlar** | CycIF tile stitching → OME-TIFF | https://github.com/labsyspharm/ashlar | Viewer API |

## OMEIA viewer architecture

- Frontend: `ImageTileViewer.jsx` — canvas tiles, channels, Z/T (not Napari embedded).
- Backend: `asset_id` only — never `logical_path` / disk paths in API responses.
- Optional: “Open in Napari” export workflow (future), not embedded GUI.

See [IMAGE_STREAMING_API.md](./IMAGE_STREAMING_API.md), [IMAGING_PACKAGES_GUIDE.md](./IMAGING_PACKAGES_GUIDE.md).
