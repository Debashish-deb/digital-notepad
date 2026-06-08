#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import multiprocessing as mp
import time
from functools import partial
from multiprocessing import shared_memory
from pathlib import Path

import numpy as np
import pandas as pd
import tifffile
import skimage.measure as measure


# Globals populated inside multiprocessing workers via the pool initializer.
# A single mask is materialized in shared memory by the parent and attached
# read-only by every worker, so the mask is read from disk exactly once per
# image regardless of n_channels and n_workers.
_WORKER_MASK = None
_WORKER_SHM = None


# Scientifically same as original
MORPH_PROPS = ["label", "centroid", "area", "eccentricity"]
CHANNEL_PROPS = ["mean_intensity"]

# Original script appended these columns but did NOT calculate them
PLACEHOLDER_PROPS = [
    "MajorAxisLength",
    "MinorAxisLength",
    "Solidity",
    "Extent",
]


def check_channel_names(channel_names_file: str) -> list:
    """
    Same logic as original checkChannelNames():

    - Read one marker name per row
    - If a marker appears multiple times, rename all duplicates as:
      Marker_1, Marker_2, ...
    """
    channel_names_loaded = pd.read_csv(channel_names_file, header=None)
    channel_names_loaded.columns = ["marker"]
    channel_names_loaded_list = list(channel_names_loaded.marker)

    channel_names_loaded_checked = []

    for idx, val in enumerate(channel_names_loaded_list):
        if channel_names_loaded_list.count(val) > 1:
            channel_names_loaded_checked.append(
                str(val) + "_" + str(channel_names_loaded_list[:idx].count(val) + 1)
            )
        else:
            channel_names_loaded_checked.append(str(val))

    return channel_names_loaded_checked


def original_image_output_name(image_path: Path) -> str:
    """
    Match original behaviour:

        im_full_name = os.path.basename(imagePath)
        im_name = im_full_name.split('.')[0]

    Example:
        S005_iOme.ome.tif -> S005_iOme
    """
    return image_path.name.split(".")[0]


def list_tiff_files(folder: Path, recursive: bool = False) -> list[Path]:
    """
    Original script used os.listdir(), so direct files only.

    recursive=False keeps original behaviour.
    recursive=True is optional for LUMI convenience.
    """
    if recursive:
        candidates = folder.rglob("*")
    else:
        candidates = folder.iterdir()

    return sorted(
        p for p in candidates
        if p.is_file() and p.suffix.lower() in {".tif", ".tiff"}
    )


def _match_mask_for_image(image_path: Path, mask_files: list) -> Path | None:
    """
    Try to find a mask whose file name starts with the image's sample prefix.

    Sample prefix follows the original convention: `image.name.split('.')[0]`,
    so `S005_iOme.ome.tif` -> prefix `S005_iOme`. A mask is considered a match
    if its name starts with that prefix followed by either `.` or `_`. This
    matches mesmer.py's `{sample}_mask_nuclear.tif` / `{sample}_mask_whole_cell.tif`
    naming as well as `{sample}.tif`.
    """
    prefix = original_image_output_name(image_path)
    candidates = [
        m for m in mask_files
        if m.name == f"{prefix}.tif"
        or m.name == f"{prefix}.tiff"
        or m.name.startswith(f"{prefix}_")
        or m.name.startswith(f"{prefix}.")
    ]

    if len(candidates) == 1:
        return candidates[0]

    if len(candidates) > 1:
        # Prefer the most specific match: longest common prefix wins.
        candidates.sort(key=lambda p: len(p.name), reverse=False)
        return candidates[0]

    return None


def discover_pairs(
    image_dir: Path,
    mask_dir: Path,
    recursive: bool = False,
) -> list:
    """
    Hybrid pairing:

    1. First try to pair each image with a mask whose file name starts with
       the image's sample prefix. This is the safe path on real datasets
       where lexical sorting of images and masks can disagree (e.g. S2 vs
       S10, or where the segmentation step renames outputs).
    2. If that fails for any image, fall back to the original behaviour:
       sort both lists and pair by index. Counts must then match exactly,
       same as the original script.
    """
    image_files = list_tiff_files(image_dir, recursive=recursive)
    mask_files = list_tiff_files(mask_dir, recursive=recursive)

    if not image_files:
        raise FileNotFoundError(f"No TIFF images found in: {image_dir}")

    if not mask_files:
        raise FileNotFoundError(f"No TIFF masks found in: {mask_dir}")

    # 1) Try name-based pairing first.
    name_based: list = []
    used_masks = set()
    name_pairing_ok = True

    for image_path in image_files:
        match = _match_mask_for_image(image_path, mask_files)
        if match is None or match in used_masks:
            name_pairing_ok = False
            break
        used_masks.add(match)
        name_based.append(
            (image_path, match, original_image_output_name(image_path))
        )

    if name_pairing_ok and len(name_based) == len(image_files):
        print("Pairing strategy   : sample-name match", flush=True)
        for image_path, mask_path, sample in name_based:
            print(f"  {sample}: {image_path.name}  <->  {mask_path.name}", flush=True)
        return name_based

    # 2) Fall back to sorted-index pairing (original behaviour).
    print(
        "WARNING: name-based pairing incomplete; falling back to sorted-index pairing.",
        flush=True,
    )

    if len(image_files) != len(mask_files):
        print(f"Images found: {len(image_files)}", flush=True)
        print(f"Masks found : {len(mask_files)}", flush=True)
        print("Images:", flush=True)
        for p in image_files:
            print(f"  - {p}", flush=True)
        print("Masks:", flush=True)
        for p in mask_files:
            print(f"  - {p}", flush=True)

        raise ValueError(
            "Image/mask count mismatch and name-based pairing failed. "
            "Either rename masks so each starts with its image's sample prefix, "
            "or supply matching counts so sorted-index pairing is unambiguous."
        )

    print("Pairing strategy   : sorted index (fallback)", flush=True)

    pairs = []
    for image_path, mask_path in zip(image_files, mask_files):
        sample_name = original_image_output_name(image_path)
        pairs.append((image_path, mask_path, sample_name))
        print(f"  {sample_name}: {image_path.name}  <->  {mask_path.name}", flush=True)

    return pairs


# Backwards-compatible alias in case external callers import the old name.
discover_pairs_by_sorted_index = discover_pairs


def _quantify_channel_core(
    channel_names: list,
    image_path: str,
    mask: np.ndarray,
    channel_index: int,
) -> pd.DataFrame:
    """
    Scientifically same as original channelQuantification():

    - read image channel using tifffile.imread(imagePath, key=channel)
    - operate on a preloaded mask numpy array (caller is responsible for
      reading the mask exactly once per image)
    - for channel 0: morphology + mean intensity
    - for other channels: mean intensity only
    """
    print(
        f"channelQuantification step, image is {image_path}, "
        f"channel {channel_index}",
        flush=True,
    )

    channel_image_loaded = tifffile.imread(image_path, key=channel_index)

    # These checks do not change valid results.
    # They only stop silently wrong quantification.
    if channel_image_loaded.ndim != 2:
        raise ValueError(
            f"Expected 2D image plane for channel {channel_index}, "
            f"got shape {channel_image_loaded.shape} from {image_path}"
        )

    if mask.ndim != 2:
        raise ValueError(f"Expected 2D mask image, got shape {mask.shape}")

    if channel_image_loaded.shape != mask.shape:
        raise ValueError(
            f"Image/mask shape mismatch for channel {channel_index}: "
            f"image {channel_image_loaded.shape} vs mask {mask.shape}"
        )

    if channel_index == 0:
        props = MORPH_PROPS + CHANNEL_PROPS
    else:
        props = CHANNEL_PROPS

    properties = measure.regionprops_table(
        mask,
        channel_image_loaded,
        properties=props,
    )

    result = pd.DataFrame(properties)

    result.rename(
        columns={
            "mean_intensity": channel_names[channel_index],
            "label": "CellID",
            "centroid-0": "Y_centroid",
            "centroid-1": "X_centroid",
            "area": "Area",
            "eccentricity": "Eccentricity",
        },
        inplace=True,
    )

    return result


def quantify_one_channel(
    channel_names: list,
    image_path: str,
    mask_path: str,
    channel_index: int,
) -> pd.DataFrame:
    """Backwards-compatible wrapper that reads the mask itself."""
    mask = tifffile.imread(mask_path)
    return _quantify_channel_core(channel_names, image_path, mask, channel_index)


def _worker_init(shm_name: str, shape: tuple, dtype_str: str) -> None:
    """Pool initializer: attach to the shared mask array exactly once per worker."""
    global _WORKER_SHM, _WORKER_MASK
    _WORKER_SHM = shared_memory.SharedMemory(name=shm_name)
    _WORKER_MASK = np.ndarray(shape, dtype=np.dtype(dtype_str), buffer=_WORKER_SHM.buf)


def _worker_quantify(
    channel_names: list,
    image_path: str,
    channel_index: int,
) -> pd.DataFrame:
    """Worker entry point: uses the shared mask attached by `_worker_init`."""
    return _quantify_channel_core(channel_names, image_path, _WORKER_MASK, channel_index)


def quantify_one_image(
    image_path: Path,
    mask_path: Path,
    channel_names: list,
    threads: int,
) -> pd.DataFrame:
    """
    Same scientific behaviour as original imageQuantification():

    - quantify every channel listed in the channel names file
    - concatenate channel results column-wise
    - append empty MajorAxisLength, MinorAxisLength, Solidity, Extent columns

    Performance: the mask is read from disk exactly once and placed into a
    multiprocessing.shared_memory block; every channel worker attaches to the
    same buffer instead of re-reading the mask file. This keeps total mask
    memory at one copy regardless of n_workers.
    """
    print(f"Length of channels: {len(channel_names)}", flush=True)

    mask = tifffile.imread(str(mask_path))

    if mask.ndim != 2:
        raise ValueError(
            f"Expected 2D mask image, got shape {mask.shape} from {mask_path}"
        )

    n_channels = len(channel_names)

    if threads <= 1 or n_channels <= 1:
        res = [
            _quantify_channel_core(channel_names, str(image_path), mask, ch)
            for ch in range(n_channels)
        ]
    else:
        # Place the mask in shared memory so workers do not need to re-read it.
        shm = shared_memory.SharedMemory(create=True, size=mask.nbytes)
        try:
            shared = np.ndarray(mask.shape, dtype=mask.dtype, buffer=shm.buf)
            shared[:] = mask  # one memcpy from the parent's mask array
            del mask  # parent no longer needs its own copy

            with mp.Pool(
                processes=min(threads, n_channels),
                initializer=_worker_init,
                initargs=(shm.name, shared.shape, shared.dtype.str),
            ) as pool:
                res = pool.map(
                    partial(_worker_quantify, channel_names, str(image_path)),
                    range(n_channels),
                )
        finally:
            try:
                shm.close()
            finally:
                shm.unlink()

    merged_data = pd.concat(res, axis=1)

    # Match original:
    # merged_data = merged_data.reindex(
    #     columns = merged_data.columns.tolist()
    #     + ['MajorAxisLength','MinorAxisLength','Solidity', 'Extent']
    # )
    merged_data = merged_data.reindex(
        columns=merged_data.columns.tolist() + PLACEHOLDER_PROPS
    )

    return merged_data


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Scientifically original-compatible quantification script for LUMI. "
            "Calculates per-cell marker mean intensities and basic morphology."
        )
    )

    # Directory mode, similar to original script
    parser.add_argument(
        "-i",
        "--image-dir",
        help="Directory containing multichannel TIFF images",
    )
    parser.add_argument(
        "-m",
        "--mask-dir",
        help="Directory containing mask TIFF files",
    )

    # Single-file mode for Snakemake/LUMI
    parser.add_argument(
        "--image-file",
        help="Single input multichannel TIFF image",
    )
    parser.add_argument(
        "--mask-file",
        help="Single input mask TIFF",
    )
    parser.add_argument(
        "--sample-name",
        help="Sample name for output CSV in single-file mode",
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        required=True,
        help="Directory to write CSV outputs",
    )
    parser.add_argument(
        "-ch",
        "--channel-names-file",
        required=True,
        help="CSV/TXT file with one marker name per line",
    )
    parser.add_argument(
        "-c",
        "--threads",
        type=int,
        default=8,
        help="Worker processes per image",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help=(
            "Search image/mask directories recursively. "
            "Default is off to match original os.listdir() behaviour."
        ),
    )
    parser.add_argument(
        "--output-suffix",
        default="",
        help=(
            "Optional suffix before .csv. Default is empty to match original. "
            "Example: --output-suffix _nuclear"
        ),
    )

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    channel_names_file = Path(args.channel_names_file)

    if not channel_names_file.is_file():
        raise FileNotFoundError(f"Channel names file not found: {channel_names_file}")

    channel_names = check_channel_names(str(channel_names_file))

    # Decide mode
    single_mode = bool(args.image_file or args.mask_file or args.sample_name)

    if single_mode:
        if not (args.image_file and args.mask_file):
            raise ValueError(
                "Single-file mode requires both --image-file and --mask-file"
            )

        image_path = Path(args.image_file)
        mask_path = Path(args.mask_file)

        if not image_path.is_file():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        if not mask_path.is_file():
            raise FileNotFoundError(f"Mask file not found: {mask_path}")

        if args.sample_name:
            sample_name = args.sample_name
        else:
            sample_name = original_image_output_name(image_path)

        pairs = [(image_path, mask_path, sample_name)]

        image_mode_text = str(image_path)
        mask_mode_text = str(mask_path)

    else:
        if not args.image_dir or not args.mask_dir:
            raise ValueError(
                "Directory mode requires --image-dir and --mask-dir. "
                "Alternatively use --image-file and --mask-file for Snakemake."
            )

        image_dir = Path(args.image_dir)
        mask_dir = Path(args.mask_dir)

        if not image_dir.is_dir():
            raise FileNotFoundError(f"Image directory not found: {image_dir}")

        if not mask_dir.is_dir():
            raise FileNotFoundError(f"Mask directory not found: {mask_dir}")

        pairs = discover_pairs(
            image_dir=image_dir,
            mask_dir=mask_dir,
            recursive=args.recursive,
        )

        image_mode_text = str(image_dir)
        mask_mode_text = str(mask_dir)

    print("============================================================", flush=True)
    print("Quantification starting", flush=True)
    print("Scientifically compatible with original script", flush=True)
    print("============================================================", flush=True)
    print(f"Image input         : {image_mode_text}", flush=True)
    print(f"Mask input          : {mask_mode_text}", flush=True)
    print(f"Output dir          : {output_dir}", flush=True)
    print(f"Channel names file  : {channel_names_file}", flush=True)
    print(f"Threads             : {args.threads}", flush=True)
    print(f"Markers loaded      : {len(channel_names)}", flush=True)
    print(f"Matched pairs       : {len(pairs)}", flush=True)
    print(f"Recursive search    : {args.recursive}", flush=True)
    print(f"Output suffix       : '{args.output_suffix}'", flush=True)
    print("============================================================", flush=True)

    t0 = time.time()

    for idx, (image_path, mask_path, sample_name) in enumerate(pairs, 1):
        sample_t0 = time.time()

        print("------------------------------------------------------------", flush=True)
        print(f"[{idx}/{len(pairs)}] Sample: {sample_name}", flush=True)
        print(f"Image: {image_path}", flush=True)
        print(f"Mask : {mask_path}", flush=True)

        scdata = quantify_one_image(
            image_path=image_path,
            mask_path=mask_path,
            channel_names=channel_names,
            threads=args.threads,
        )

        out_csv = output_dir / f"{sample_name}{args.output_suffix}.csv"
        scdata.to_csv(out_csv, index=False)

        print(f"Wrote: {out_csv}", flush=True)
        print(f"Sample finished in {time.time() - sample_t0:.2f} seconds", flush=True)

    print("============================================================", flush=True)
    print(f"All done in {time.time() - t0:.2f} seconds", flush=True)
    print("============================================================", flush=True)


if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)
    main()
