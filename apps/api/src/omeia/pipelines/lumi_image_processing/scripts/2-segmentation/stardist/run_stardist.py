#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LUMI-compatible StarDist nuclear segmentation worker.

Scientific behavior preserved from the local workstation script:
  - model: 2D_versatile_fluo by default
  - image normalization: csbdeep.utils.normalize
  - model.predict_instances(..., n_tiles=(tiles_y, tiles_x))
  - output labels as int32

The LUMI worker uses larger rectangular GPU tiles to reduce model-call
overhead, with automatic retries using smaller tiles after a GPU OOM.
"""

import argparse
import gc
import json
import math
import os
import re
import resource
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import tensorflow as tf
import tifffile
from csbdeep.utils import normalize
from stardist.models import StarDist2D

NUCLEAR_NAME_PATTERN = re.compile(
    r"(dapi|hoechst|dna|histone|draq|ir191|ir193|nuclear)",
    re.IGNORECASE,
)
INVALID_CHANNEL_NAME_PATTERN = re.compile(
    r"(background|failed|blank|empty)",
    re.IGNORECASE,
)


def log(msg: str) -> None:
    print(msg, flush=True)


def peak_rss_gib() -> float:
    rss = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    if sys.platform == "darwin":
        return rss / (1024**3)
    return rss / (1024**2)


def log_timing(label: str, started_at: float) -> None:
    log(
        f"TIMING {label}: {time.perf_counter() - started_at:.1f}s "
        f"(peak RSS {peak_rss_gib():.2f} GiB)"
    )


def configure_tensorflow() -> None:
    gpus = tf.config.list_physical_devices("GPU")
    require_gpu = os.environ.get("STARDIST_REQUIRE_GPU", "1") == "1"
    is_rocm_build = getattr(tf.test, "is_built_with_rocm", lambda: False)()
    log(f"TensorFlow version       : {tf.__version__}")
    log(f"TensorFlow ROCm build    : {is_rocm_build}")
    log(f"Detected TensorFlow GPU(s): {gpus}")
    if require_gpu and not gpus:
        raise RuntimeError("STARDIST_REQUIRE_GPU=1 but TensorFlow cannot see a GPU.")
    for gpu in gpus:
        try:
            tf.config.experimental.set_memory_growth(gpu, True)
        except Exception:
            pass


def validate_channel_name(channel: int, channel_name: str, strict: bool) -> None:
    channel_name = (channel_name or "unknown").strip()
    if channel_name and INVALID_CHANNEL_NAME_PATTERN.search(channel_name):
        raise ValueError(
            f"Channel {channel} is configured for StarDist nuclear segmentation, "
            f"but its name {channel_name!r} marks it as unusable."
        )
    if channel_name.lower() in {"", "unknown", "none", "na", "n/a"}:
        message = "StarDist nuclear channel name is unknown."
    elif not NUCLEAR_NAME_PATTERN.search(channel_name):
        message = (
            f"Channel {channel} is configured for StarDist nuclear segmentation, "
            f"but its name {channel_name!r} does not look like a nuclear marker."
        )
    else:
        return

    if strict:
        raise ValueError(message)
    log(f"WARNING: {message}")


def _first_float_attr(xml_text, attribute):
    if not xml_text:
        return None
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None
    for elem in root.iter():
        value = elem.attrib.get(attribute)
        if value:
            try:
                return float(value)
            except ValueError:
                return None
    return None


def resolve_image_mpp(image_path):
    try:
        with tifffile.TiffFile(str(image_path)) as tif:
            x = _first_float_attr(tif.ome_metadata, "PhysicalSizeX")
            y = _first_float_attr(tif.ome_metadata, "PhysicalSizeY")
            if x and y:
                return float((x + y) / 2.0)
            return x or y
    except Exception as exc:
        log(f"WARNING: could not read image MPP metadata: {exc}")
        return None


def read_single_channel(image_path: Path, channel: int) -> np.ndarray:
    """
    Read one 2D channel from a TIFF/OME-TIFF.

    Uses the series-level zarr view so we can index by the real series axes
    (CYX, ZCYX, CZYX, TCYX, ...). For the standard Ashlar OME-TIFF case
    (axes='CYX', one IFD per channel) this returns exactly the same pixels
    as the original `tifffile.imread(path, key=channel)` call.
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Input image not found: {image_path}")

    with tifffile.TiffFile(str(image_path)) as tif:
        series = tif.series[0]

        log(f"TIFF series shape: {series.shape}")
        log(f"TIFF series axes : {series.axes}")
        log(f"TIFF pages       : {len(series.pages)}")

        try:
            import zarr

            store = tif.aszarr(series=0)
            z = zarr.open(store, mode="r")

            # Pyramidal OME-TIFF: pick full-resolution level 0.
            if isinstance(z, zarr.Group):
                if "0" in z:
                    z = z["0"]
                else:
                    z = list(z.arrays())[0][1]

            axes = series.axes
            shape = z.shape

            if len(axes) != len(shape):
                # Fallback when series axes do not align with the zarr shape.
                if len(shape) == 2:
                    arr = np.asarray(z[:, :])
                elif len(shape) >= 3:
                    arr = np.asarray(z[(channel,) + (slice(None),) * (len(shape) - 1)])
                else:
                    raise ValueError(f"Unsupported zarr shape {shape}")
            elif "C" in axes:
                c_axis = axes.index("C")

                if shape[c_axis] <= channel:
                    raise ValueError(
                        f"Requested channel {channel} but C dim only has "
                        f"{shape[c_axis]} channels (axes={axes}, shape={shape})."
                    )

                slicer = [slice(None)] * len(shape)
                slicer[c_axis] = channel
                # Collapse non-spatial singleton-style axes (T, Z, S) to index 0
                # to obtain a 2D YX plane.
                for i, ax in enumerate(axes):
                    if i == c_axis or ax in ("Y", "X"):
                        continue
                    slicer[i] = 0
                arr = np.asarray(z[tuple(slicer)])
            elif len(shape) == 2:
                if channel != 0:
                    raise ValueError(
                        f"Image appears 2D but requested channel={channel}"
                    )
                arr = np.asarray(z[:, :])
            elif len(shape) == 3:
                # No C axis but 3D: assume first dim is channel-like.
                if channel >= shape[0]:
                    raise IndexError(
                        f"Requested channel {channel}, but first axis has size {shape[0]}"
                    )
                arr = np.asarray(z[channel, :, :])
            else:
                raise ValueError(f"Cannot infer channel axis from zarr shape {shape}")

            arr = np.squeeze(arr)

            if arr.ndim != 2:
                raise ValueError(f"Expected 2D channel image, got shape {arr.shape}")

            return arr

        except Exception as e:
            raise RuntimeError(
                f"Could not read channel {channel} from {image_path}. "
                f"Series shape={series.shape}, axes={series.axes}. "
                f"Underlying error: {e}"
            )


def calculate_tiles(shape, target_tile_edge):
    """Choose rectangular tile counts for the requested approximate edge."""
    if target_tile_edge < 256:
        raise ValueError("StarDist target tile edge must be at least 256.")
    return tuple(
        max(1, math.ceil(int(length) / target_tile_edge))
        for length in shape
    )


def _foreground_fraction(mask: np.ndarray) -> float:
    return float(np.count_nonzero(mask)) / float(mask.size)


def _validate_terminal_bands(mask, high_fraction):
    if mask.shape[0] < 5:
        return []
    boundaries = np.linspace(0, mask.shape[0], 6, dtype=int)
    fractions = []
    for start, stop in zip(boundaries[:-1], boundaries[1:]):
        fractions.append(_foreground_fraction(mask[start:stop, :]))
    log(
        "StarDist nuclear foreground by Y-fifth: "
        + ", ".join(f"{value:.3f}" for value in fractions)
    )
    for terminal, adjacent in ((0, 1), (4, 3)):
        if (
            fractions[terminal] >= high_fraction
            and fractions[terminal] - fractions[adjacent] >= 0.20
        ):
            side = "leading" if terminal == 0 else "trailing"
            raise RuntimeError(
                f"StarDist nuclear mask has an abrupt near-solid {side} 20% "
                f"band ({fractions[terminal]:.1%} foreground versus "
                f"{fractions[adjacent]:.1%} next to it)."
            )
    return fractions


def validate_mask(labels, expected_shape):
    if labels.shape != expected_shape:
        raise ValueError(
            f"StarDist mask shape {labels.shape} does not match input "
            f"shape {expected_shape}."
        )

    max_label = int(labels.max()) if labels.size else 0
    foreground_fraction = _foreground_fraction(labels)
    log(f"StarDist foreground fraction: {foreground_fraction:.4f}")
    log(f"StarDist max label          : {max_label}")

    if max_label < 1:
        raise RuntimeError("StarDist nuclear mask contains no labeled nuclei.")
    if foreground_fraction > 0.90:
        raise RuntimeError(
            "StarDist nuclear mask covers more than 90% of the image; refusing "
            "to publish a likely corrupted or wrong-channel mask."
        )
    terminal_fractions = _validate_terminal_bands(labels, high_fraction=0.65)
    return {
        "shape": [int(expected_shape[0]), int(expected_shape[1])],
        "foreground_fraction": foreground_fraction,
        "max_label": max_label,
        "foreground_by_y_fifth": terminal_fractions,
    }


def _compression_arg():
    value = os.environ.get("STARDIST_MASK_COMPRESSION", "none").strip().lower()
    return None if value in {"", "0", "none", "false", "off"} else value


def write_mask(output_path, labels, image_mpp):
    metadata = {
        "axes": "YX",
        "Channel": {"Name": "Nuclei Labels", "Color": -16711681},
    }
    if image_mpp:
        metadata.update(
            {
                "PhysicalSizeX": image_mpp,
                "PhysicalSizeY": image_mpp,
                "PhysicalSizeXUnit": "µm",
                "PhysicalSizeYUnit": "µm",
            }
        )
    tifffile.imwrite(
        str(output_path),
        labels,
        dtype=np.int32,
        photometric="minisblack",
        compression=_compression_arg(),
        tile=(512, 512),
        metadata=metadata,
        description="axes=YX;labels=Nuclear;method=StarDist",
    )


def write_qc(path: Path, payload: dict) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    tmp_path.replace(path)


def optional_float(raw):
    if raw is None:
        return None
    raw = raw.strip()
    if not raw or raw.lower() in {"none", "default", "auto"}:
        return None
    return float(raw)


def run_stardist(
    input_path: Path,
    output_path: Path,
    qc_output_path,
    channel: int,
    channel_name: str,
    strict_channel_names: bool,
    model_name: str,
    target_tile_edge: int,
    oom_retries: int,
    prob_thresh,
    nms_thresh,
) -> None:
    start = time.time()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists() and output_path.stat().st_size > 0:
        log(f"ALREADY DONE: {output_path}")
        return

    log("============================================================")
    log("StarDist nuclear segmentation")
    log(f"Input file : {input_path}")
    log(f"Output file: {output_path}")
    log(f"Channel    : {channel} ({channel_name or 'unknown'})")
    log(f"Model      : {model_name}")
    log(f"Prob thresh: {prob_thresh if prob_thresh is not None else 'model default'}")
    log(f"NMS thresh : {nms_thresh if nms_thresh is not None else 'model default'}")
    log("============================================================")

    validate_channel_name(channel, channel_name, strict_channel_names)
    configure_tensorflow()
    image_mpp = resolve_image_mpp(input_path)
    log(f"Image MPP  : {image_mpp if image_mpp is not None else 'unknown'}")

    read_started = time.perf_counter()
    img = read_single_channel(input_path, channel)
    log(f"Image shape: {img.shape}")
    log(f"Image dtype: {img.dtype}")
    log_timing("read nuclear channel", read_started)

    tiles = calculate_tiles(img.shape, target_tile_edge)
    log(f"Target tile edge: {target_tile_edge}")
    log(f"Calculated n_tiles: {tiles}")

    model_started = time.perf_counter()
    model = StarDist2D.from_pretrained(model_name)
    normalized = normalize(img)
    log_timing("initialize model and normalize image", model_started)

    prediction_started = time.perf_counter()
    predict_kwargs = {"n_tiles": tiles}
    if prob_thresh is not None:
        predict_kwargs["prob_thresh"] = prob_thresh
    if nms_thresh is not None:
        predict_kwargs["nms_thresh"] = nms_thresh
    for attempt in range(oom_retries + 1):
        try:
            labels, _ = model.predict_instances(
                normalized,
                **predict_kwargs,
            )
            break
        except tf.errors.ResourceExhaustedError:
            if attempt >= oom_retries:
                raise
            tiles = tuple(value * 2 for value in tiles)
            log(
                "GPU OOM during StarDist prediction; retrying with smaller "
                f"tiles using n_tiles={tiles}"
            )
            predict_kwargs["n_tiles"] = tiles
            gc.collect()
    log_timing("StarDist prediction and NMS", prediction_started)
    labels = labels.astype(np.int32, copy=False)
    qc = validate_mask(labels, img.shape)

    write_started = time.perf_counter()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_mask(output_path, labels, image_mpp)
    if qc_output_path:
        qc.update(
            {
                "input_image": str(input_path),
                "output_mask": str(output_path),
                "channel": channel,
                "channel_name": channel_name,
                "model": model_name,
                "image_mpp": image_mpp,
                "mask_dtype": "int32",
                "mask_compression": os.environ.get("STARDIST_MASK_COMPRESSION", "none"),
                "normalization": "csbdeep.utils.normalize(image)",
                "prob_thresh": prob_thresh,
                "nms_thresh": nms_thresh,
                "n_tiles": [int(tiles[0]), int(tiles[1])],
            }
        )
        write_qc(Path(qc_output_path), qc)
    log_timing("write nuclear mask", write_started)

    log(f"SUCCESS: wrote {output_path}")
    if qc_output_path:
        log(f"QC summary: {qc_output_path}")
    log(f"Max label: {int(labels.max())}")
    log(f"Elapsed seconds: {time.time() - start:.1f}")
    log(f"Peak RSS GiB   : {peak_rss_gib():.2f}")


def parse_args():
    p = argparse.ArgumentParser(description="Run StarDist segmentation for one stitched OME-TIFF.")
    p.add_argument("--input", required=True, help="Input TIFF/OME-TIFF image")
    p.add_argument("--output", required=True, help="Output mask TIFF")
    p.add_argument("--qc-output", default="", help="Optional JSON QC sidecar path")
    p.add_argument("--channel", type=int, default=0, help="Channel/page index; default matches local script key=0")
    p.add_argument("--channel-name", default="unknown", help="Resolved channel name for QC and validation")
    p.add_argument("--strict-channel-names", action="store_true", help="Fail if the selected channel does not look nuclear")
    p.add_argument("--model", default="2D_versatile_fluo", help="StarDist pretrained model name")
    p.add_argument(
        "--target-tile-edge",
        type=int,
        default=4096,
        help="Approximate GPU inference tile edge; automatically reduced on OOM.",
    )
    p.add_argument(
        "--oom-retries",
        type=int,
        default=2,
        help="Number of automatic retries with half-size GPU tiles.",
    )
    p.add_argument("--prob-thresh", default="", help="Optional StarDist prob_thresh; blank keeps model default")
    p.add_argument("--nms-thresh", default="", help="Optional StarDist nms_thresh; blank keeps model default")
    return p.parse_args()


def main():
    args = parse_args()
    if args.oom_retries < 0:
        raise ValueError("--oom-retries must be non-negative.")
    run_stardist(
        Path(args.input),
        Path(args.output),
        Path(args.qc_output) if args.qc_output else None,
        args.channel,
        args.channel_name,
        args.strict_channel_names,
        args.model,
        args.target_tile_edge,
        args.oom_retries,
        optional_float(args.prob_thresh),
        optional_float(args.nms_thresh),
    )


if __name__ == "__main__":
    main()
