#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Filter stitched OME-TIFF marker channels and quantify filtered marker images.

Scientific behavior matches the local workstation filtered-image workflow:
  - read one marker/channel from the stitched image
  - apply skimage.morphology.white_tophat with disk(size)
  - save <sample>.ome_<MARKER>_tophat.tif
  - quantify filtered marker mean intensities per labelled cell mask
  - output CSV columns in the exact order produced by the original
    `pipeline/4_filter_images/filter_image_script.py`:
      CellID, marker0, Y_centroid, X_centroid, Area, Eccentricity,
              marker1, marker2, ..., markerN-1

Subcommands
-----------
filter-one
    Reads one channel from a stitched OME-TIFF, applies white-tophat filtering,
    and writes a 2D TIFF.

quantify-one
    Reads a mask and filtered marker images, then writes per-object intensity
    and morphology features to CSV.
"""

import argparse
import json
import time
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import tifffile
from skimage import measure
from skimage.morphology import disk, white_tophat


MORPH_PROPS = ["label", "centroid", "area", "eccentricity"]
MORPH_COLUMNS = ["Y_centroid", "X_centroid", "Area", "Eccentricity"]


def log(msg: str) -> None:
    print(msg, flush=True)


def read_single_channel(image_path: Path, channel: int) -> np.ndarray:
    """
    Read one 2D channel from TIFF/OME-TIFF.

    Designed for stitched Ashlar OME-TIFFs where the common layout is CYX
    with one 2D TIFF page per channel. Falls back to zarr/array slicing only
    when needed.
    """
    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    if channel < 0:
        raise ValueError(f"Channel index must be >= 0, got {channel}")

    log(f"Reading channel {channel} from: {image_path}")

    with tifffile.TiffFile(str(image_path)) as tif:
        series = tif.series[0]
        axes = series.axes
        shape = series.shape

        log(f"TIFF series shape: {shape}")
        log(f"TIFF series axes : {axes}")
        log(f"TIFF pages       : {len(series.pages)}")

        # Common Ashlar OME-TIFF case: one 2D page per channel.
        if len(series.pages) > channel:
            arr = np.asarray(series.pages[channel].asarray())
            arr = np.squeeze(arr)

            if arr.ndim == 2:
                log(f"Read page {channel}: shape={arr.shape}, dtype={arr.dtype}")
                return arr

        # Safer fallback for large OME-TIFF/pyramidal TIFFs:
        # use zarr if available to avoid loading all channels unnecessarily.
        try:
            import zarr

            store = tif.aszarr(series=0)
            z = zarr.open(store, mode="r")

            if isinstance(z, zarr.Group):
                if "0" in z:
                    z = z["0"]
                else:
                    arrays = list(z.arrays())
                    if not arrays:
                        raise ValueError("zarr group contains no arrays")
                    z = arrays[0][1]

            if "C" in axes:
                c_axis = axes.index("C")

                if channel >= z.shape[c_axis]:
                    raise IndexError(
                        f"Requested channel={channel}, but C axis has size {z.shape[c_axis]} "
                        f"for image {image_path}"
                    )

                slicer = [slice(None)] * len(z.shape)
                slicer[c_axis] = channel
                arr = np.asarray(z[tuple(slicer)])

            elif len(z.shape) == 3:
                if channel >= z.shape[0]:
                    raise IndexError(
                        f"Requested channel={channel}, but first axis has size {z.shape[0]} "
                        f"for image {image_path}"
                    )
                arr = np.asarray(z[channel, :, :])

            elif len(z.shape) == 2:
                if channel != 0:
                    raise ValueError(
                        f"Image appears 2D but requested channel={channel}: {image_path}"
                    )
                arr = np.asarray(z[:, :])

            else:
                raise ValueError(
                    f"Cannot infer channel axis from zarr shape={z.shape}, axes={axes}"
                )

            arr = np.squeeze(arr)

            if arr.ndim != 2:
                raise ValueError(
                    f"Expected 2D channel after zarr slicing, got shape={arr.shape}"
                )

            log(f"Read channel via zarr: shape={arr.shape}, dtype={arr.dtype}")
            return arr

        except Exception as zarr_error:
            log(f"WARNING: zarr channel read failed, trying full-series fallback: {zarr_error}")

        # Last fallback: load series and slice.
        arr = np.asarray(series.asarray())
        arr = np.squeeze(arr)

        if arr.ndim == 2:
            if channel != 0:
                raise ValueError(
                    f"Image appears 2D but requested channel={channel}: {image_path}"
                )
            log(f"Read 2D image directly: shape={arr.shape}, dtype={arr.dtype}")
            return arr

        if "C" in axes:
            c_axis = axes.index("C")

            if channel >= arr.shape[c_axis]:
                raise IndexError(
                    f"Requested channel={channel}, but C axis has size {arr.shape[c_axis]} "
                    f"for image {image_path}"
                )

            arr = np.take(arr, channel, axis=c_axis)
            arr = np.squeeze(arr)

            if arr.ndim != 2:
                raise ValueError(
                    f"Expected 2D channel after C-axis slicing, got shape={arr.shape}, "
                    f"axes={axes}, image={image_path}"
                )

            log(f"Read channel via full C-axis array: shape={arr.shape}, dtype={arr.dtype}")
            return arr

        if arr.ndim == 3:
            if channel >= arr.shape[0]:
                raise IndexError(
                    f"Requested channel={channel}, but first axis has size {arr.shape[0]} "
                    f"for image {image_path}"
                )

            arr = np.squeeze(arr[channel, :, :])

            if arr.ndim != 2:
                raise ValueError(
                    f"Expected 2D channel after first-axis slicing, got shape={arr.shape}"
                )

            log(f"Read channel via full first-axis array: shape={arr.shape}, dtype={arr.dtype}")
            return arr

        raise ValueError(
            f"Could not infer channel layout for {image_path}. "
            f"Series shape={shape}, axes={axes}, array ndim={arr.ndim}"
        )


def read_2d_tiff(path: Path, name: str = "image") -> np.ndarray:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"{name} file not found: {path}")

    arr = np.asarray(tifffile.imread(str(path)))
    arr = np.squeeze(arr)

    if arr.ndim != 2:
        raise ValueError(f"Expected 2D {name}, got shape={arr.shape}: {path}")

    return arr


def write_tiff(path: Path, arr: np.ndarray) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    tifffile.imwrite(
        str(path),
        arr,
        photometric="minisblack",
        tile=(512, 512),
        compression="zlib",
        metadata={"axes": "YX"},
        description="axes=YX",
    )


def apply_white_tophat(image: np.ndarray, size: int) -> np.ndarray:
    if size < 1:
        raise ValueError(f"Tophat size must be >= 1, got {size}")

    footprint = disk(size)

    try:
        filtered = white_tophat(image, footprint=footprint)
    except TypeError:
        # Older scikit-image compatibility.
        filtered = white_tophat(image, selem=footprint)

    return np.asarray(filtered).astype(np.uint16, copy=False)


def filter_one(
    image_file: Path,
    output_file: Path,
    marker: str,
    channel: int,
    size: int,
) -> None:
    start = time.time()

    image_file = Path(image_file)
    output_file = Path(output_file)

    log("============================================================")
    log("Filter one marker")
    log(f"Image file  : {image_file}")
    log(f"Output file : {output_file}")
    log(f"Marker      : {marker}")
    log(f"Channel     : {channel}")
    log(f"Tophat size : {size}")
    log("============================================================")

    if output_file.exists() and output_file.stat().st_size > 0:
        log(f"Output already exists, skipping: {output_file}")
        return

    img = read_single_channel(image_file, channel)

    log(f"Input channel shape: {img.shape}")
    log(f"Input channel dtype: {img.dtype}")
    log(f"Input min/max      : {float(np.min(img))} / {float(np.max(img))}")

    log("Applying white-tophat filter")
    filtered = apply_white_tophat(img, size=size)

    log(f"Filtered shape  : {filtered.shape}")
    log(f"Filtered dtype  : {filtered.dtype}")
    log(f"Filtered min/max: {float(np.min(filtered))} / {float(np.max(filtered))}")

    write_tiff(output_file, filtered)

    elapsed = time.time() - start
    log(f"SUCCESS: wrote {output_file}")
    log(f"Elapsed seconds: {elapsed:.1f}")


def normalize_mask(mask: np.ndarray) -> np.ndarray:
    mask = np.asarray(mask)
    mask = np.squeeze(mask)

    if mask.ndim != 2:
        raise ValueError(f"Expected 2D mask, got shape={mask.shape}")

    if not np.issubdtype(mask.dtype, np.integer):
        mask = mask.astype(np.uint32)

    return mask


def parse_marker_images_json(marker_images_json: str) -> Dict[str, str]:
    try:
        marker_images = json.loads(marker_images_json)
    except Exception as e:
        raise ValueError(f"Could not parse marker_images_json: {e}")

    if not isinstance(marker_images, dict) or not marker_images:
        raise ValueError("marker_images_json must be a non-empty JSON object")

    parsed = {}

    for marker, path in marker_images.items():
        marker_name = str(marker)

        if not marker_name:
            raise ValueError("Marker name cannot be empty")

        parsed[marker_name] = str(path)

    return parsed


def _final_column_order(marker_names: List[str]) -> List[str]:
    """
    Match the original `filter_image_script.py` column order exactly:

        CellID, marker0, Y_centroid, X_centroid, Area, Eccentricity,
                marker1, marker2, ..., markerN-1

    The original puts the morphology block right after the first marker
    because per-cell morphology is only attached to the first marker's
    DataFrame inside the merge loop. We reproduce that order here so any
    downstream tool relying on positional column access keeps working.
    """
    if not marker_names:
        return ["CellID"] + MORPH_COLUMNS

    head = ["CellID", marker_names[0]] + MORPH_COLUMNS
    tail = list(marker_names[1:])
    return head + tail


def empty_filtered_quantification_csv(
    output_csv: Path,
    marker_names: List[str],
) -> None:
    columns = _final_column_order(marker_names)
    empty = pd.DataFrame(columns=columns)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    empty.to_csv(output_csv, index=False)


def quantify_one(
    slide_name: str,
    mask_file: Path,
    marker_images_json: str,
    output_csv: Path,
) -> None:
    start = time.time()

    mask_file = Path(mask_file)
    output_csv = Path(output_csv)

    marker_images = parse_marker_images_json(marker_images_json)
    marker_names = list(marker_images.keys())

    log("============================================================")
    log("Quantify filtered marker images")
    log(f"Slide name : {slide_name}")
    log(f"Mask file  : {mask_file}")
    log(f"Output CSV : {output_csv}")
    log(f"Markers    : {marker_names}")
    log("============================================================")

    mask = normalize_mask(read_2d_tiff(mask_file, name="mask"))

    log(f"Mask shape : {mask.shape}")
    log(f"Mask dtype : {mask.dtype}")
    log(f"Mask labels: max={int(mask.max())}")

    output_csv.parent.mkdir(parents=True, exist_ok=True)

    if int(mask.max()) == 0:
        log("WARNING: no labeled objects found in mask")
        empty_filtered_quantification_csv(output_csv, marker_names)
        log(f"SUCCESS: wrote empty CSV {output_csv}")
        return

    # Morphology table, matching local workstation feature names.
    morph_df = pd.DataFrame(
        measure.regionprops_table(
            mask,
            properties=MORPH_PROPS,
        )
    )

    morph_df = morph_df.rename(
        columns={
            "label": "CellID",
            "centroid-0": "Y_centroid",
            "centroid-1": "X_centroid",
            "area": "Area",
            "eccentricity": "Eccentricity",
        }
    )

    # Start with CellID so marker columns can be added next.
    df = morph_df[["CellID"]].copy()

    for marker, img_path in marker_images.items():
        img_path = Path(img_path)

        log(f"Quantifying marker {marker}: {img_path}")

        img = read_2d_tiff(img_path, name=f"marker image {marker}")

        if img.shape != mask.shape:
            raise ValueError(
                f"Shape mismatch for marker={marker}: "
                f"mask shape={mask.shape}, image shape={img.shape}, file={img_path}"
            )

        marker_table = pd.DataFrame(
            measure.regionprops_table(
                mask,
                intensity_image=img,
                properties=["label", "mean_intensity"],
            )
        ).rename(
            columns={
                "label": "CellID",
                "mean_intensity": str(marker),
            }
        )

        df = df.merge(
            marker_table[["CellID", str(marker)]],
            on="CellID",
            how="left",
        )

    # Attach morphology so the final reorder can place it right after the
    # first marker, matching the original script's output layout exactly.
    df = df.merge(
        morph_df[["CellID"] + MORPH_COLUMNS],
        on="CellID",
        how="left",
    )

    # Enforce exact original column order:
    #   CellID, marker0, Y_centroid, X_centroid, Area, Eccentricity, marker1, ...
    final_columns = _final_column_order(marker_names)
    df = df[final_columns]

    log(f"Writing CSV: {output_csv}")
    df.to_csv(output_csv, index=False)

    elapsed = time.time() - start

    log(f"SUCCESS: wrote {output_csv}")
    log(f"Rows: {len(df)}")
    log(f"Columns: {list(df.columns)}")
    log(f"Elapsed seconds: {elapsed:.1f}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Filter marker images and quantify filtered marker intensities."
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_filter = sub.add_parser("filter-one")
    p_filter.add_argument("--image-file", required=True)
    p_filter.add_argument("--output-file", required=True)
    p_filter.add_argument("--marker", required=True)
    p_filter.add_argument("--channel", required=True, type=int)
    p_filter.add_argument("--size", required=True, type=int)

    p_quant = sub.add_parser("quantify-one")
    p_quant.add_argument("--slide-name", required=True)
    p_quant.add_argument("--mask-file", required=True)
    p_quant.add_argument("--marker-images-json", required=True)
    p_quant.add_argument("--output-csv", required=True)

    return parser.parse_args()


def main():
    args = parse_args()

    if args.command == "filter-one":
        filter_one(
            image_file=Path(args.image_file),
            output_file=Path(args.output_file),
            marker=args.marker,
            channel=args.channel,
            size=args.size,
        )

    elif args.command == "quantify-one":
        quantify_one(
            slide_name=args.slide_name,
            mask_file=Path(args.mask_file),
            marker_images_json=args.marker_images_json,
            output_csv=Path(args.output_csv),
        )

    else:
        raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"ERROR: {e}")
        raise
