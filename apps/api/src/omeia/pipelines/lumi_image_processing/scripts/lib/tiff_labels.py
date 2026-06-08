#!/usr/bin/env python3
"""Write 2D label-mask TIFFs with headers Napari, QuPath, and tifffile accept."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import tifffile


def write_label_mask_tiff(
    path: str | Path,
    labels: np.ndarray,
    *,
    mpp: float = 0.325,
    label_name: str = "Labels",
) -> None:
    """
    Save a 2D instance-label image as a well-formed tiled TIFF.

    Avoids nested ``metadata['Channel']`` blobs that break ImageDescription JSON
    and trigger Napari / bioio "missing headers" warnings.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    arr = np.asarray(labels)
    if arr.ndim != 2:
        raise ValueError(f"Expected 2D label image, got shape {arr.shape}")

    if arr.dtype not in (np.uint16, np.uint32, np.int32, np.int64):
        if arr.max() <= np.iinfo(np.uint16).max:
            arr = arr.astype(np.uint16, copy=False)
        else:
            arr = arr.astype(np.uint32, copy=False)

    resolution = (10000.0 / mpp, 10000.0 / mpp) if mpp and mpp > 0 else None

    tifffile.imwrite(
        str(path),
        arr,
        photometric="minisblack",
        compression="zlib",
        tile=(512, 512),
        dtype=arr.dtype,
        resolution=resolution,
        resolutionunit="CENTIMETER" if resolution else None,
        metadata={
            "axes": "YX",
            "unit": "um",
            "spacing": float(mpp) if mpp else 1.0,
            "name": label_name,
        },
        description=f"axes=YX;labels={label_name}",
    )
