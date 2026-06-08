#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Mesmer segmentation for large OME-TIFF images on LUMI.

The worker reads explicit nuclear and membrane channels, runs Mesmer on
overlapping DeepTile tiles, and stitches whole-cell and nuclear labels
independently. Mesmer returns whole-cell labels in output channel 0 and
nuclear labels in output channel 1; those indices are named constants below
and validated before the masks are written.
"""

from __future__ import annotations

import os

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("OMP_NUM_THREADS", os.environ.get("OMP_NUM_THREADS", "8"))
os.environ.setdefault(
    "TF_NUM_INTRAOP_THREADS",
    os.environ.get("TF_NUM_INTRAOP_THREADS", "8"),
)
os.environ.setdefault(
    "TF_NUM_INTEROP_THREADS",
    os.environ.get("TF_NUM_INTEROP_THREADS", "1"),
)
os.environ.setdefault("ROCM_PATH", "/opt/rocm")
os.environ.setdefault(
    "HIP_DEVICE_LIB_PATH",
    "/opt/rocm/lib/llvm/lib/clang/18/lib/amdgcn/bitcode",
)
os.environ.setdefault("TF_USE_LEGACY_KERAS", "1")
os.environ.setdefault("TF_XLA_FLAGS", "--tf_xla_auto_jit=-1")
os.environ.setdefault("TF_ENABLE_MLIR_BRIDGE", "0")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

import argparse
import gc
import json
import re
import resource
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import numpy as np
import tensorflow as tf
import tifffile
from deepcell.applications import Mesmer
from deeptile import lift, load
from deeptile.core.data import Tiled
from deeptile.extensions import stitch
from tqdm import tqdm


# These are two different index spaces:
# 1. Mesmer model input is always [nuclear marker, membrane/cytoplasm marker].
# 2. Mesmer output depends on the requested compartment. In "both" mode,
#    DeepCell concatenates [whole-cell labels, nuclear labels]. In a
#    single-compartment call, the requested mask is the sole output channel 0.
MESMER_NUCLEAR_INPUT = 0
MESMER_MEMBRANE_INPUT = 1
MESMER_SINGLE_COMPARTMENT_OUTPUT = 0
MESMER_BOTH_WHOLE_CELL_OUTPUT = 0
MESMER_BOTH_NUCLEAR_OUTPUT = 1
NUCLEAR_NAME_PATTERN = re.compile(
    r"(dapi|hoechst|dna|histone|draq|ir191|ir193|nuclear)",
    re.IGNORECASE,
)
MEMBRANE_NAME_PATTERN = re.compile(
    r"(cell[\W_]*mask|wga|pan[\W_]*membrane|membrane|cytoplasm|"
    r"cd45|ptprc|e[\W_]*cadherin|cdh1|pan[\W_]*(ck|cytokeratin)|"
    r"cytokeratin|keratin|n[\W_]*cadherin|cdh2|vimentin|"
    r"a[\W_]*sma|acta2|beta[\W_]*catenin|epcam|"
    r"na[\W_]*k[\W_]*atpase)",
    re.IGNORECASE,
)
INVALID_CHANNEL_NAME_PATTERN = re.compile(
    r"(background|failed|blank|empty)",
    re.IGNORECASE,
)


def log(message: str) -> None:
    print(message, flush=True)


def peak_rss_gib() -> float:
    """Return peak resident memory in GiB on Linux and macOS."""
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
    require_gpu = os.environ.get("MESMER_REQUIRE_GPU", "1") == "1"
    build_info = tf.sysconfig.get_build_info()
    is_rocm_build = bool(build_info.get("is_rocm_build"))
    gpus = tf.config.experimental.list_physical_devices("GPU")
    log(f"TensorFlow version       : {tf.__version__}")
    log(f"TensorFlow ROCm build    : {is_rocm_build}")
    if gpus:
        log(f"Detected TensorFlow GPU(s): {gpus}")
        for device in gpus:
            try:
                tf.config.experimental.set_memory_growth(device, True)
            except Exception as exc:
                log(f"WARNING: could not set memory growth for {device}: {exc}")
    elif require_gpu:
        raise RuntimeError(
            "TensorFlow did not detect the allocated GPU. Refusing to run "
            "Mesmer on CPU inside a GPU SLURM job."
        )
    else:
        log("WARNING: TensorFlow did not detect a GPU; CPU fallback allowed.")

    if require_gpu and not is_rocm_build:
        raise RuntimeError(
            "Installed TensorFlow is not a ROCm build. Refusing to run a GPU "
            "job with CPU TensorFlow."
        )

    try:
        tf.config.threading.set_intra_op_parallelism_threads(
            int(os.environ.get("TF_NUM_INTRAOP_THREADS", "8"))
        )
        tf.config.threading.set_inter_op_parallelism_threads(
            int(os.environ.get("TF_NUM_INTEROP_THREADS", "1"))
        )
    except Exception as exc:
        log(f"WARNING: could not configure TensorFlow threads: {exc}")


def require_deepcell_token() -> None:
    if not os.environ.get("DEEPCELL_ACCESS_TOKEN", ""):
        raise RuntimeError("DEEPCELL_ACCESS_TOKEN is not set.")


def clean_sample_name(path: Path) -> str:
    name = path.name
    for extension in (".ome.tiff", ".ome.tif", ".tiff", ".tif"):
        if name.lower().endswith(extension):
            return name[: -len(extension)]
    return path.stem


def _full_resolution_array(tif: tifffile.TiffFile):
    """Return the full-resolution Zarr array for the first TIFF series."""
    import zarr

    zarr_data = zarr.open(tif.aszarr(series=0), mode="r")
    if isinstance(zarr_data, zarr.Group):
        if "0" in zarr_data:
            return zarr_data["0"]
        arrays = list(zarr_data.arrays())
        if not arrays:
            raise ValueError("OME-TIFF Zarr group contains no image arrays.")
        return arrays[0][1]
    return zarr_data


def read_single_channel(input_path: Path, channel: int) -> np.ndarray:
    """Read one YX channel using OME axes instead of TIFF page numbers."""
    if channel < 0:
        raise ValueError(f"Channel index must be non-negative, received {channel}.")

    log(f"Reading channel {channel} from: {input_path}")
    with tifffile.TiffFile(str(input_path)) as tif:
        series = tif.series[0]
        zarr_data = _full_resolution_array(tif)
        axes = str(series.axes)
        shape = tuple(zarr_data.shape)

        log(f"TIFF series shape: {series.shape}")
        log(f"TIFF series axes : {axes}")
        log(f"Zarr level shape : {shape}")

        if len(axes) == len(shape) and "C" in axes:
            channel_axis = axes.index("C")
            if channel >= shape[channel_axis]:
                raise ValueError(
                    f"Requested channel {channel}, but OME C axis has "
                    f"{shape[channel_axis]} channels (axes={axes}, shape={shape})."
                )

            slices = [slice(None)] * len(shape)
            slices[channel_axis] = channel
            for index, axis_name in enumerate(axes):
                if index == channel_axis or axis_name in ("Y", "X"):
                    continue
                slices[index] = 0
            image = np.asarray(zarr_data[tuple(slices)])
        elif len(shape) == 2:
            if channel != 0:
                raise ValueError(
                    f"Image has no channel axis, but channel {channel} was requested."
                )
            image = np.asarray(zarr_data[:, :])
        elif len(shape) == 3:
            if channel >= shape[0]:
                raise ValueError(
                    f"Requested channel {channel}, but inferred channel-first "
                    f"array only has {shape[0]} channels."
                )
            image = np.asarray(zarr_data[channel, :, :])
        else:
            raise ValueError(
                f"Cannot resolve a 2D channel from axes={axes}, shape={shape}."
            )

    image = np.squeeze(image)
    if image.ndim != 2:
        raise ValueError(
            f"Expected a 2D channel after indexing, received shape {image.shape}."
        )
    return image


def _micrometre_scale(unit: str) -> float | None:
    normalized = unit.strip().lower().replace("μ", "µ")
    scales = {
        "µm": 1.0,
        "um": 1.0,
        "micrometer": 1.0,
        "micrometre": 1.0,
        "micron": 1.0,
        "nm": 0.001,
        "nanometer": 0.001,
        "nanometre": 0.001,
        "mm": 1000.0,
        "millimeter": 1000.0,
        "millimetre": 1000.0,
    }
    return scales.get(normalized)


def read_ome_mpp(input_path: Path) -> float | None:
    """Read and convert OME PhysicalSizeX/Y to micrometres per pixel."""
    with tifffile.TiffFile(str(input_path)) as tif:
        xml_text = tif.ome_metadata

    if not xml_text:
        return None

    try:
        root = ET.fromstring(xml_text)
        pixels = next(
            element for element in root.iter() if element.tag.endswith("Pixels")
        )
    except (ET.ParseError, StopIteration):
        return None

    unit_x = pixels.attrib.get("PhysicalSizeXUnit", "µm")
    unit_y = pixels.attrib.get("PhysicalSizeYUnit", unit_x)
    scale_x = _micrometre_scale(unit_x)
    scale_y = _micrometre_scale(unit_y)
    if scale_x is None or scale_y is None:
        log(
            "WARNING: unsupported OME physical-size units: "
            f"X={unit_x!r}, Y={unit_y!r}"
        )
        return None

    try:
        raw_x = float(pixels.attrib["PhysicalSizeX"])
        raw_y = pixels.attrib.get("PhysicalSizeY")
        mpp_x = raw_x * scale_x
        mpp_y = float(raw_y) * scale_y if raw_y is not None else mpp_x
    except (KeyError, TypeError, ValueError):
        return None

    if mpp_x <= 0 or mpp_y <= 0:
        return None
    if abs(mpp_x - mpp_y) / max(mpp_x, mpp_y) > 0.02:
        raise ValueError(
            f"Anisotropic OME pixel sizes are unsupported: X={mpp_x}, Y={mpp_y} µm."
        )
    return (mpp_x + mpp_y) / 2.0


def resolve_image_mpp(input_path: Path, requested_mpp: str) -> float:
    metadata_mpp = read_ome_mpp(input_path)
    requested = str(requested_mpp).strip().lower()

    if requested == "auto":
        if metadata_mpp is None:
            raise ValueError(
                "IMAGE_MPP=auto, but PhysicalSizeX/Y could not be read from the "
                "OME-TIFF. Set IMAGE_MPP to the verified microscope resolution."
            )
        log(f"Using OME metadata pixel size: {metadata_mpp:.6g} µm/px")
        return metadata_mpp

    try:
        configured_mpp = float(requested)
    except ValueError as exc:
        raise ValueError(
            f"--mpp must be 'auto' or a positive number, received {requested_mpp!r}."
        ) from exc

    if configured_mpp <= 0:
        raise ValueError(f"--mpp must be positive, received {configured_mpp}.")

    if metadata_mpp is not None:
        relative_error = abs(configured_mpp - metadata_mpp) / metadata_mpp
        if relative_error > 0.05:
            log(
                "WARNING: configured MPP differs from OME metadata by "
                f"{relative_error:.1%}: configured={configured_mpp}, "
                f"metadata={metadata_mpp} µm/px"
            )
    return configured_mpp


def validate_channel_names(
    nuclear_name: str,
    membrane_name: str,
    nuclear_channel: int,
    membrane_channel: int,
    strict: bool,
) -> None:
    nuclear_name = nuclear_name.strip()
    membrane_name = membrane_name.strip()

    if nuclear_channel == membrane_channel:
        raise ValueError(
            "Nuclear and membrane channels resolve to the same index "
            f"({nuclear_channel}). Configure two biologically distinct inputs."
        )

    unknown_names = {
        "",
        "unknown",
    }
    if strict and nuclear_name.lower() in unknown_names:
        raise ValueError(
            "Strict channel validation requires a nuclear channel name. "
            "Provide channels_quantification.csv or disable strict validation "
            "only after manually verifying the channel index."
        )
    if strict and membrane_name.lower() in unknown_names:
        raise ValueError(
            "Strict channel validation requires a membrane/cytoplasm channel "
            "name. Provide channels_quantification.csv or disable strict "
            "validation only after manually verifying the channel index."
        )
    for role, channel, name in (
        ("nuclear", nuclear_channel, nuclear_name),
        ("membrane/cytoplasm", membrane_channel, membrane_name),
    ):
        if name and INVALID_CHANNEL_NAME_PATTERN.search(name):
            raise ValueError(
                f"Channel {channel} is configured as {role}, but its name "
                f"{name!r} marks it as unusable."
            )

    if nuclear_name and nuclear_name.lower() != "unknown":
        if not NUCLEAR_NAME_PATTERN.search(nuclear_name):
            message = (
                f"Channel {nuclear_channel} is configured as nuclear, but its "
                f"name is {nuclear_name!r}, which does not look like a nuclear marker."
            )
            if strict:
                raise ValueError(message)
            log(f"WARNING: {message}")

    if (
        membrane_name
        and membrane_name.lower() != "unknown"
        and NUCLEAR_NAME_PATTERN.search(membrane_name)
    ):
        message = (
            f"Channel {membrane_channel} is configured as membrane, but its "
            f"name is {membrane_name!r}, which looks nuclear."
        )
        if strict:
            raise ValueError(message)
        log(f"WARNING: {message}")
    elif membrane_name and membrane_name.lower() != "unknown":
        if not MEMBRANE_NAME_PATTERN.search(membrane_name):
            message = (
                f"Channel {membrane_channel} is configured as membrane/cytoplasm, "
                f"but its name is {membrane_name!r}, which is not a recognized "
                "Mesmer whole-cell marker."
            )
            if strict:
                raise ValueError(message)
            log(f"WARNING: {message}")


def preprocess_channel(
    image: np.ndarray,
    gamma: float,
    mode: str,
) -> np.ndarray:
    """Prepare a channel while retaining the validated workstation behavior."""
    mode = mode.lower()
    if mode not in {"none", "gamma", "gamma-unsharp"}:
        raise ValueError(f"Unsupported preprocessing mode: {mode}")

    if mode == "none":
        if np.issubdtype(image.dtype, np.integer):
            dtype_max = float(np.iinfo(image.dtype).max)
            if dtype_max <= 0:
                return np.zeros(image.shape, dtype=np.uint16)
            scaled = image.astype(np.float32) / dtype_max
        else:
            scaled = image.astype(np.float32)
            if float(np.nanmax(scaled)) > 1.0:
                scaled = scaled / 65535.0
        return np.clip(scaled * 65535.0, 0, 65535).astype(np.uint16)

    image_float = image.astype(np.float32)
    minimum = float(np.min(image_float))
    maximum = float(np.max(image_float))
    if maximum <= minimum:
        return np.zeros(image.shape, dtype=np.uint16)

    # Keep the original global min/max and gamma transform, but perform the
    # arithmetic in-place to avoid several whole-slide float32 copies.
    np.subtract(image_float, minimum, out=image_float)
    np.divide(image_float, maximum - minimum, out=image_float)
    np.power(image_float, 1.0 / gamma, out=image_float)
    np.multiply(image_float, 65535.0, out=image_float)
    np.clip(image_float, 0, 65535, out=image_float)
    image_u16 = image_float.astype(np.uint16)
    del image_float

    if mode == "gamma":
        return image_u16

    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError(
            "PREPROCESS_MODE=gamma-unsharp requires OpenCV in the Mesmer container."
        ) from exc

    image_float = image_u16.astype(np.float32)
    blurred = cv2.GaussianBlur(image_float, (0, 0), 1.0)
    sharpened = cv2.addWeighted(
        image_float,
        2.5,
        blurred,
        -1.5,
        0,
    )
    del image_float, blurred
    return np.clip(sharpened, 0, 65535).astype(np.uint16)


class DeepTileMesmerProcessor:
    """Run Mesmer on batches of DeepTile tiles and crop padding afterward."""

    def __init__(
        self,
        app: Mesmer,
        total_tiles: int,
        mpp: float,
        background_threshold: float,
        model_tile_size: int,
        compartment: str,
        pad_mode: str,
        batch_size: int,
    ):
        self.app = app
        self.mpp = mpp
        self.background_threshold = float(background_threshold)
        self.model_tile_size = int(model_tile_size)
        self.compartment = compartment
        self.pad_mode = pad_mode
        self.batch_size = int(batch_size)
        self.pbar = tqdm(total=total_tiles, desc="Mesmer tiles")
        self.tile_index = 0

    @staticmethod
    def _pad_to_multiple(length: int, block: int = 256) -> int:
        return int(np.ceil(length / block) * block)

    @staticmethod
    def _split_channels(tile: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        tile = np.squeeze(np.asarray(tile))
        if tile.ndim != 3:
            raise ValueError(f"Expected a two-channel tile, received {tile.shape}.")
        if tile.shape[0] == 2:
            return tile[0], tile[1]
        if tile.shape[-1] == 2:
            return tile[..., 0], tile[..., 1]
        raise ValueError(
            f"Could not locate the two-channel axis in tile shape {tile.shape}."
        )

    def _is_background(
        self,
        nuclear: np.ndarray,
        membrane: np.ndarray,
    ) -> bool:
        nuclear_mean = float(np.mean(nuclear, dtype=np.float64))
        if self.compartment == "nuclear":
            return nuclear_mean < self.background_threshold

        # Mesmer can identify whole cells whose nuclei are outside the tissue
        # section. For whole-cell/both mode, retain a tile whenever either the
        # nuclear or membrane/cytoplasm channel contains biological signal.
        membrane_mean = float(np.mean(membrane, dtype=np.float64))
        return (
            nuclear_mean < self.background_threshold
            and membrane_mean < self.background_threshold
        )

    @staticmethod
    def _tile_list(tile_batch) -> list[np.ndarray]:
        batch = np.asarray(tile_batch)
        if batch.dtype == object:
            return [np.asarray(tile) for tile in batch.flat]
        if batch.ndim < 4:
            return [batch]
        return [batch[index] for index in range(batch.shape[0])]

    def _predict_active_batch(
        self,
        active_inputs: list[np.ndarray],
        active_metadata: list[tuple[int, int, int]],
        results: np.ndarray,
    ) -> None:
        try:
            prediction = self.app.predict(
                np.stack(active_inputs, axis=0),
                image_mpp=self.mpp,
                compartment=self.compartment,
                batch_size=min(self.batch_size, len(active_inputs)),
            )
        except tf.errors.ResourceExhaustedError:
            if len(active_inputs) == 1:
                raise
            midpoint = len(active_inputs) // 2
            log(
                "GPU OOM for an outer Mesmer batch; retrying as "
                f"{midpoint} + {len(active_inputs) - midpoint} tiles"
            )
            self._predict_active_batch(
                active_inputs[:midpoint],
                active_metadata[:midpoint],
                results,
            )
            self._predict_active_batch(
                active_inputs[midpoint:],
                active_metadata[midpoint:],
                results,
            )
            return

        for prediction_index, (output_index, height, width) in enumerate(
            active_metadata
        ):
            if self.compartment == "both":
                if prediction.ndim != 4 or prediction.shape[-1] != 2:
                    raise RuntimeError(
                        "Mesmer compartment='both' must return shape "
                        f"(batch, Y, X, 2), received {prediction.shape}."
                    )
                results[output_index] = prediction[
                    prediction_index,
                    :height,
                    :width,
                    :,
                ].astype(np.uint32)
            else:
                if prediction.ndim != 4 or prediction.shape[-1] != 1:
                    raise RuntimeError(
                        "A single Mesmer compartment must return shape "
                        f"(batch, Y, X, 1), received {prediction.shape}."
                    )
                results[output_index] = prediction[
                    prediction_index,
                    :height,
                    :width,
                    MESMER_SINGLE_COMPARTMENT_OUTPUT,
                ].astype(np.uint32)

    def process_batch(self, tile_batch):
        tile_list = self._tile_list(tile_batch)
        batch_start = self.tile_index + 1
        self.tile_index += len(tile_list)
        results = np.empty(len(tile_list), dtype=object)
        active_inputs = []
        active_metadata = []

        try:
            for output_index, tile in enumerate(tile_list):
                nuclear, membrane = self._split_channels(tile)
                height, width = nuclear.shape

                if self._is_background(nuclear, membrane):
                    output_shape = (
                        (height, width, 2)
                        if self.compartment == "both"
                        else (height, width)
                    )
                    results[output_index] = np.zeros(
                        output_shape,
                        dtype=np.uint32,
                    )
                    continue

                target_size = self._pad_to_multiple(
                    max(height, width, self.model_tile_size, 256)
                )
                padding = ((0, target_size - height), (0, target_size - width))
                if padding[0][1] or padding[1][1]:
                    nuclear = np.pad(nuclear, padding, mode=self.pad_mode)
                    membrane = np.pad(membrane, padding, mode=self.pad_mode)

                model_input = np.empty(
                    (target_size, target_size, 2),
                    dtype=np.float32,
                )
                model_input[..., MESMER_NUCLEAR_INPUT] = nuclear
                model_input[..., MESMER_MEMBRANE_INPUT] = membrane
                model_input /= 65535.0
                active_inputs.append(model_input)
                active_metadata.append((output_index, height, width))

            if active_inputs:
                self._predict_active_batch(
                    active_inputs,
                    active_metadata,
                    results,
                )
        except Exception as exc:
            log(
                "ERROR during Mesmer prediction "
                f"for tiles {batch_start}-{self.tile_index}/{self.pbar.total}: "
                f"batch_size={len(tile_list)}, mpp={self.mpp}, error={exc}"
            )
            raise
        finally:
            self.pbar.update(len(tile_list))

        return results


def _compartment_tiles(masks: Tiled, output_index: int) -> Tiled:
    """Extract one Mesmer output channel while preserving DeepTile metadata."""
    data = np.empty(masks.shape, dtype=object)
    for index in np.ndindex(masks.shape):
        tile = masks[index]
        data[index] = (
            None
            if tile is None
            else np.asarray(tile[..., output_index], dtype=np.uint32)
        )

    metadata = getattr(masks, "metadata", {}) or {}
    return Tiled(
        data,
        job=masks.job,
        mask=getattr(masks, "mask", None),
        isimage=True,
        stackable=False,
        tile_scales=metadata.get("tile_scales"),
    )


def _foreground_fraction(mask: np.ndarray) -> float:
    return float(np.count_nonzero(mask)) / float(mask.size)


def _validate_terminal_bands(
    mask: np.ndarray,
    mask_name: str,
    high_fraction: float,
) -> None:
    """Reject an abrupt full-frame-like corruption in the first/last image fifth."""
    for axis, axis_name in ((0, "Y"), (1, "X")):
        if mask.shape[axis] < 5:
            continue
        boundaries = np.linspace(0, mask.shape[axis], 6, dtype=int)
        fractions = []
        for start, stop in zip(boundaries[:-1], boundaries[1:]):
            slices = [slice(None), slice(None)]
            slices[axis] = slice(start, stop)
            band = mask[tuple(slices)]
            fractions.append(_foreground_fraction(band))

        log(
            f"{mask_name} foreground by {axis_name}-fifth: "
            + ", ".join(f"{value:.3f}" for value in fractions)
        )
        for terminal, adjacent in ((0, 1), (4, 3)):
            if (
                fractions[terminal] >= high_fraction
                and fractions[terminal] - fractions[adjacent] >= 0.20
            ):
                side = "leading" if terminal == 0 else "trailing"
                raise RuntimeError(
                    f"{mask_name} has an abrupt near-solid {side} 20% band "
                    f"along {axis_name} ({fractions[terminal]:.1%} foreground "
                    f"versus {fractions[adjacent]:.1%} next to it). This matches "
                    "the known full-viewport stitching/noise failure."
                )


def validate_masks(
    nuclear_mask: np.ndarray,
    whole_cell_mask: np.ndarray,
    expected_shape: tuple[int, int],
) -> dict[str, float | int | list[int]]:
    """Catch channel reversal and catastrophic full-frame corruption."""
    if nuclear_mask.shape != expected_shape or whole_cell_mask.shape != expected_shape:
        raise ValueError(
            "Stitched mask shape mismatch: "
            f"nuclear={nuclear_mask.shape}, whole-cell={whole_cell_mask.shape}, "
            f"expected={expected_shape}."
        )

    nuclear_fraction = _foreground_fraction(nuclear_mask)
    whole_cell_fraction = _foreground_fraction(whole_cell_mask)
    nuclear_max_label = int(nuclear_mask.max(initial=0))
    whole_cell_max_label = int(whole_cell_mask.max(initial=0))
    log(f"Nuclear foreground fraction   : {nuclear_fraction:.4f}")
    log(f"Whole-cell foreground fraction: {whole_cell_fraction:.4f}")
    log(f"Nuclear max label             : {nuclear_max_label}")
    log(f"Whole-cell max label          : {whole_cell_max_label}")

    if nuclear_max_label < 1:
        raise RuntimeError("Nuclear mask contains no labeled nuclei.")
    if whole_cell_max_label < 1:
        raise RuntimeError("Whole-cell mask contains no labeled cells.")

    if nuclear_fraction > 0.90:
        raise RuntimeError(
            "Nuclear mask covers more than 90% of the image. This strongly "
            "suggests a wrong channel or catastrophic segmentation noise."
        )
    if whole_cell_fraction > 0.995:
        raise RuntimeError(
            "Whole-cell mask covers more than 99.5% of the image. Refusing to "
            "publish a likely corrupted full-frame mask."
        )
    if whole_cell_fraction + 1e-6 < nuclear_fraction:
        log(
            "WARNING: whole-cell foreground is smaller than nuclear foreground. "
            "This can happen on weak membrane samples; channel reversal is checked "
            "by nuclear-in-whole-cell containment below."
        )

    _validate_terminal_bands(
        nuclear_mask,
        mask_name="Nuclear mask",
        high_fraction=0.65,
    )
    _validate_terminal_bands(
        whole_cell_mask,
        mask_name="Whole-cell mask",
        high_fraction=0.98,
    )

    nuclear_pixel_count = 0
    contained_pixel_count = 0
    for row_start in range(0, expected_shape[0], 2048):
        row_stop = min(row_start + 2048, expected_shape[0])
        nuclear_rows = nuclear_mask[row_start:row_stop] > 0
        nuclear_pixel_count += int(np.count_nonzero(nuclear_rows))
        contained_pixel_count += int(
            np.count_nonzero(
                nuclear_rows & (whole_cell_mask[row_start:row_stop] > 0)
            )
        )

    if nuclear_pixel_count:
        containment = contained_pixel_count / nuclear_pixel_count
        log(f"Nuclear pixels inside whole-cell mask: {containment:.4f}")
        if containment < 0.70:
            raise RuntimeError(
                "Fewer than 70% of nuclear pixels lie inside whole-cell masks. "
                "Check channel selection and compartment mapping."
            )
    else:
        containment = 0.0

    return {
        "shape": [int(expected_shape[0]), int(expected_shape[1])],
        "nuclear_foreground_fraction": nuclear_fraction,
        "whole_cell_foreground_fraction": whole_cell_fraction,
        "nuclear_max_label": nuclear_max_label,
        "whole_cell_max_label": whole_cell_max_label,
        "nuclear_pixels_inside_whole_cell_fraction": containment,
    }


def _write_flat_mask(path: Path, mask: np.ndarray, mpp: float, name: str) -> None:
    compression = os.environ.get("MESMER_MASK_COMPRESSION", "none").strip().lower()
    compression_arg = None if compression in {"", "0", "none", "false", "off"} else compression
    metadata = {
        "axes": "YX",
        "PhysicalSizeX": mpp,
        "PhysicalSizeY": mpp,
        "PhysicalSizeXUnit": "µm",
        "PhysicalSizeYUnit": "µm",
        "Channel": {"Name": name, "Color": -16711681},
    }
    tifffile.imwrite(
        str(path),
        mask,
        dtype=np.uint32,
        tile=(512, 512),
        compression=compression_arg,
        metadata=metadata,
    )


def _convert_flat_to_pyramid(flat_path: Path, final_path: Path) -> None:
    """Convert a flat tiled label TIFF to pyramidal OME-TIFF like the original."""
    bioformats2raw = shutil.which("bioformats2raw")
    raw2ometiff = shutil.which("raw2ometiff")
    if not bioformats2raw or not raw2ometiff:
        raise RuntimeError(
            "MESMER_WRITE_PYRAMID=1 requires bioformats2raw and raw2ometiff "
            "inside the Mesmer container."
        )

    temp_zarr = flat_path.with_suffix("").with_name(flat_path.stem + "_zarr_temp")
    if temp_zarr.exists():
        shutil.rmtree(temp_zarr)

    try:
        subprocess.run(
            [
                bioformats2raw,
                "--resolutions",
                "5",
                "--downsample-type",
                "SIMPLE",
                "--compression",
                "zlib",
                "--series",
                "0",
                "--tile_width",
                "512",
                "--tile_height",
                "512",
                "--overwrite",
                str(flat_path),
                str(temp_zarr),
            ],
            check=True,
        )
        tmp_final = final_path.with_suffix(final_path.suffix + ".tmp")
        if tmp_final.exists():
            tmp_final.unlink()
        subprocess.run(
            [
                raw2ometiff,
                "--compression",
                "zlib",
                str(temp_zarr),
                str(tmp_final),
            ],
            check=True,
        )
        tmp_final.replace(final_path)
    finally:
        if temp_zarr.exists():
            shutil.rmtree(temp_zarr)


def write_mask(path: Path, mask: np.ndarray, mpp: float, name: str) -> None:
    if os.environ.get("MESMER_WRITE_PYRAMID", "0") != "1":
        _write_flat_mask(path, mask, mpp, name)
        return

    flat_path = path.with_suffix("").with_name(path.stem + "_flat.tif")
    log(f"Writing temporary flat mask for pyramid conversion: {flat_path}")
    _write_flat_mask(flat_path, mask, mpp, name)
    log(f"Converting flat mask to pyramidal OME-TIFF: {path}")
    try:
        _convert_flat_to_pyramid(flat_path, path)
    finally:
        if path.exists() and flat_path.exists():
            flat_path.unlink()


def write_qc(path: Path, payload: dict) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    tmp_path.replace(path)


def run_mesmer(
    input_path: Path,
    output_dir: Path,
    requested_mpp: str,
    nuclear_channel: int,
    membrane_channel: int,
    nuclear_channel_name: str,
    membrane_channel_name: str,
    strict_channel_names: bool,
    compartment: str,
    tile_size: int,
    batch_size: int,
    overlap_fraction: float,
    preprocess_gamma: float,
    preprocess_mode: str,
    background_threshold: float,
    pad_mode: str,
    warmup: bool,
) -> None:
    start = time.time()
    output_dir.mkdir(parents=True, exist_ok=True)
    sample = clean_sample_name(input_path)
    nuclear_path = output_dir / f"{sample}_mask_nuclear.tif"
    whole_cell_path = output_dir / f"{sample}_mask_whole_cell.tif"
    qc_path = output_dir / f"{sample}_mesmer_qc.json"

    validate_channel_names(
        nuclear_channel_name,
        membrane_channel_name,
        nuclear_channel,
        membrane_channel,
        strict_channel_names,
    )
    image_mpp = resolve_image_mpp(input_path, requested_mpp)

    read_started = time.perf_counter()
    raw_nuclear = read_single_channel(input_path, nuclear_channel)
    raw_membrane = read_single_channel(input_path, membrane_channel)
    if raw_nuclear.shape != raw_membrane.shape:
        raise ValueError(
            f"Nuclear shape {raw_nuclear.shape} and membrane shape "
            f"{raw_membrane.shape} do not match."
        )
    log_timing("read two input channels", read_started)

    preprocess_started = time.perf_counter()
    nuclear = preprocess_channel(
        raw_nuclear,
        gamma=preprocess_gamma,
        mode=preprocess_mode,
    )
    del raw_nuclear
    gc.collect()
    membrane = preprocess_channel(
        raw_membrane,
        gamma=preprocess_gamma,
        mode=preprocess_mode,
    )
    del raw_membrane
    log_timing("preprocess two input channels", preprocess_started)

    height, width = nuclear.shape
    image = np.stack([nuclear, membrane], axis=0)
    del nuclear, membrane
    gc.collect()

    log("======================================")
    log("Mesmer segmentation")
    log("======================================")
    log(f"Input image          : {input_path}")
    log(f"Image shape          : {height} x {width}")
    log(
        f"Nuclear channel      : {nuclear_channel} "
        f"({nuclear_channel_name or 'unknown'})"
    )
    log(
        f"Membrane channel     : {membrane_channel} "
        f"({membrane_channel_name or 'unknown'})"
    )
    log(f"Compartment          : {compartment}")
    log(f"Image MPP            : {image_mpp}")
    log(f"Tile size            : {tile_size}")
    log(f"Outer tile batch     : {batch_size}")
    log(f"Overlap fraction     : {overlap_fraction}")
    log(f"Preprocessing        : {preprocess_mode}, gamma={preprocess_gamma}")
    log(f"Background threshold : {background_threshold}")
    log(f"Model padding        : {pad_mode}")
    log(
        "Input mapping        : Mesmer input[0] <- nuclear marker, "
        "input[1] <- membrane/cytoplasm marker"
    )
    if compartment == "both":
        log(
            "Output mapping       : Mesmer[0] -> whole-cell, "
            "Mesmer[1] -> nuclear"
        )
    else:
        log(f"Output mapping       : Mesmer[0] -> {compartment}")
    log("======================================")

    model_started = time.perf_counter()
    configure_tensorflow()
    app = Mesmer()
    try:
        deepcell_version = version("deepcell")
    except PackageNotFoundError:
        deepcell_version = "unknown"
    model_mpp = getattr(app, "model_mpp", None)
    log(f"DeepCell package      : {deepcell_version}")
    log(f"Mesmer training MPP  : {model_mpp}")
    log(
        "Mesmer internals     : official percentile/histogram preprocessing "
        "and default compartment-specific watershed"
    )

    if warmup:
        warmup_size = int(np.ceil(max(tile_size, 256) / 256) * 256)
        dummy = np.zeros((1, warmup_size, warmup_size, 2), dtype=np.float32)
        app.predict(
            dummy,
            image_mpp=image_mpp,
            compartment=compartment,
            batch_size=1,
        )
        log(f"Warm-up complete: {dummy.shape}, compartment={compartment}")
    log_timing("initialize and warm Mesmer", model_started)

    inference_started = time.perf_counter()
    tiles = load(image).get_tiles(
        tile_size=(tile_size, tile_size),
        overlap=(overlap_fraction, overlap_fraction),
    )
    processor = DeepTileMesmerProcessor(
        app=app,
        total_tiles=len(tiles.flat),
        mpp=image_mpp,
        background_threshold=background_threshold,
        model_tile_size=tile_size,
        compartment=compartment,
        pad_mode=pad_mode,
        batch_size=batch_size,
    )

    def predict_tile_batch(tile_batch):
        return processor.process_batch(tile_batch)

    predict_tile_batch = lift(
        predict_tile_batch,
        vectorized=True,
        batch_size=batch_size,
    )
    predicted_tiles = predict_tile_batch(tiles)
    processor.pbar.close()
    log_timing("Mesmer tile inference", inference_started)

    stitch_started = time.perf_counter()
    if compartment == "both":
        whole_cell_tiles = _compartment_tiles(
            predicted_tiles,
            MESMER_BOTH_WHOLE_CELL_OUTPUT,
        )
        whole_cell_mask = np.asarray(
            stitch.stitch_masks(whole_cell_tiles),
            dtype=np.uint32,
        )
        del whole_cell_tiles
        gc.collect()
        log_timing("stitch whole-cell mask", stitch_started)

        nuclear_stitch_started = time.perf_counter()
        nuclear_tiles = _compartment_tiles(
            predicted_tiles,
            MESMER_BOTH_NUCLEAR_OUTPUT,
        )
        nuclear_mask = np.asarray(
            stitch.stitch_masks(nuclear_tiles),
            dtype=np.uint32,
        )
        del nuclear_tiles
        gc.collect()
        log_timing("stitch nuclear mask", nuclear_stitch_started)

        validation_started = time.perf_counter()
        qc = validate_masks(nuclear_mask, whole_cell_mask, (height, width))
        write_mask(nuclear_path, nuclear_mask, image_mpp, "Nuclei Labels")
        write_mask(
            whole_cell_path,
            whole_cell_mask,
            image_mpp,
            "Whole-cell Labels",
        )
        qc.update(
            {
                "sample": sample,
                "input_image": str(input_path),
                "image_mpp": image_mpp,
                "compartment": compartment,
                "nuclear_channel": nuclear_channel,
                "nuclear_channel_name": nuclear_channel_name,
                "membrane_channel": membrane_channel,
                "membrane_channel_name": membrane_channel_name,
                "mesmer_input_mapping": {
                    "0": "nuclear marker",
                    "1": "membrane/cytoplasm marker",
                },
                "mesmer_output_mapping": {
                    "0": "whole-cell labels",
                    "1": "nuclear labels",
                },
                "nuclear_mask": str(nuclear_path),
                "whole_cell_mask": str(whole_cell_path),
                "mask_dtype": "uint32",
                "mask_compression": os.environ.get(
                    "MESMER_MASK_COMPRESSION",
                    "none",
                ),
                "pyramid_output": os.environ.get("MESMER_WRITE_PYRAMID", "0") == "1",
                "preprocessing": preprocess_mode,
                "preprocess_gamma": preprocess_gamma,
            }
        )
        write_qc(qc_path, qc)
        log_timing("validate and write masks", validation_started)
        log(f"SUCCESS: wrote {nuclear_path} and {whole_cell_path}")
        log(f"QC summary: {qc_path}")
        del nuclear_mask, whole_cell_mask
    else:
        mask = np.asarray(stitch.stitch_masks(predicted_tiles), dtype=np.uint32)
        if mask.shape != (height, width):
            raise ValueError(
                f"Stitched mask shape {mask.shape} does not match {(height, width)}."
            )
        foreground_fraction = _foreground_fraction(mask)
        max_label = int(mask.max(initial=0))
        if max_label < 1:
            raise RuntimeError(f"{compartment} mask contains no labels.")
        if compartment == "nuclear":
            if foreground_fraction > 0.90:
                raise RuntimeError("Nuclear mask is likely corrupted.")
            write_mask(nuclear_path, mask, image_mpp, "Nuclei Labels")
            log(f"SUCCESS: wrote {nuclear_path}")
        else:
            if foreground_fraction > 0.995:
                raise RuntimeError("Whole-cell mask is likely corrupted.")
            write_mask(whole_cell_path, mask, image_mpp, "Whole-cell Labels")
            log(f"SUCCESS: wrote {whole_cell_path}")
        write_qc(
            qc_path,
            {
                "sample": sample,
                "input_image": str(input_path),
                "shape": [int(height), int(width)],
                "image_mpp": image_mpp,
                "compartment": compartment,
                "nuclear_channel": nuclear_channel,
                "nuclear_channel_name": nuclear_channel_name,
                "membrane_channel": membrane_channel,
                "membrane_channel_name": membrane_channel_name,
                "foreground_fraction": foreground_fraction,
                "max_label": max_label,
                "mask_dtype": "uint32",
                "mask_compression": os.environ.get("MESMER_MASK_COMPRESSION", "none"),
                "pyramid_output": os.environ.get("MESMER_WRITE_PYRAMID", "0") == "1",
                "preprocessing": preprocess_mode,
                "preprocess_gamma": preprocess_gamma,
            },
        )
        log(f"QC summary: {qc_path}")
        del mask

    log(f"Elapsed seconds: {time.time() - start:.1f}")
    log(f"Peak RSS GiB   : {peak_rss_gib():.2f}")
    del image, predicted_tiles, tiles
    gc.collect()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Robust nuclear and whole-cell Mesmer segmentation"
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--mpp",
        default="auto",
        help="'auto' to use OME PhysicalSizeX/Y, or verified microns per pixel.",
    )
    parser.add_argument("--channel", type=int, required=True)
    parser.add_argument("--membrane-channel", type=int, required=True)
    parser.add_argument("--nuclear-channel-name", default="unknown")
    parser.add_argument("--membrane-channel-name", default="unknown")
    parser.add_argument("--strict-channel-names", action="store_true")
    parser.add_argument(
        "--compartment",
        default="both",
        choices=("nuclear", "whole-cell", "both"),
    )
    parser.add_argument("--tile-size", type=int, default=1024)
    parser.add_argument("--overlap-fraction", type=float, default=0.10)
    parser.add_argument("--preprocess-gamma", type=float, default=1.5)
    parser.add_argument(
        "--preprocess-mode",
        default="gamma-unsharp",
        choices=("none", "gamma", "gamma-unsharp"),
    )
    parser.add_argument("--background-threshold", type=float, default=600.0)
    parser.add_argument(
        "--pad-mode",
        choices=("constant", "edge", "reflect"),
        default="constant",
    )
    parser.add_argument("--warmup", action="store_true")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=4,
        help="Number of outer DeepTile tiles submitted to Mesmer together.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    if not input_path.is_file():
        raise FileNotFoundError(f"Input image does not exist: {input_path}")
    if args.tile_size < 256:
        raise ValueError("--tile-size must be at least 256.")
    if not 0 <= args.overlap_fraction < 1:
        raise ValueError("--overlap-fraction must be in [0, 1).")
    if args.preprocess_gamma <= 0:
        raise ValueError("--preprocess-gamma must be positive.")
    if args.batch_size < 1:
        raise ValueError("--batch-size must be at least 1.")

    require_deepcell_token()
    run_mesmer(
        input_path=input_path,
        output_dir=Path(args.output_dir),
        requested_mpp=args.mpp,
        nuclear_channel=args.channel,
        membrane_channel=args.membrane_channel,
        nuclear_channel_name=args.nuclear_channel_name,
        membrane_channel_name=args.membrane_channel_name,
        strict_channel_names=args.strict_channel_names,
        compartment=args.compartment,
        tile_size=args.tile_size,
        batch_size=args.batch_size,
        overlap_fraction=args.overlap_fraction,
        preprocess_gamma=args.preprocess_gamma,
        preprocess_mode=args.preprocess_mode,
        background_threshold=args.background_threshold,
        pad_mode=args.pad_mode,
        warmup=args.warmup,
    )

    try:
        tf.keras.backend.clear_session()
    except Exception:
        pass


if __name__ == "__main__":
    main()
