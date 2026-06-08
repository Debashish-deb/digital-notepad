#!/usr/bin/env python3
"""Turn technical pipeline log lines into plain-language messages for biologists."""

from __future__ import annotations

import os
import re
from pathlib import Path

FRIENDLY_RULES: dict[str, tuple[str, str]] = {
    "illumination_basic": (
        "Lighting correction",
        "Fixing uneven illumination before stitching",
    ),
    "stitching": (
        "Tile stitching",
        "Combining microscope tiles into one image",
    ),
    "mesmer_segmentation": (
        "Cell segmentation (Mesmer)",
        "Finding cells with Mesmer deep learning",
    ),
    "mesmer": (
        "Cell segmentation (Mesmer)",
        "Finding whole-cell and nuclear masks with Mesmer",
    ),
    "stardist_segmentation": (
        "Cell segmentation (StarDist)",
        "Finding nuclei with StarDist",
    ),
    "quantify_nuclear_mesmer": (
        "Marker quantification",
        "Measuring marker levels per nucleus (Mesmer masks)",
    ),
    "quantify_whole_cell_mesmer": (
        "Marker quantification",
        "Measuring marker levels per whole cell (Mesmer masks)",
    ),
    "quantify_nuclear_stardist": (
        "Marker quantification",
        "Measuring marker levels per nucleus (StarDist masks)",
    ),
    "filter_one_marker_mesmer": (
        "Marker enhancement",
        "Applying white-top-hat filter to highlight one marker",
    ),
    "filter_one_marker_stardist": (
        "Marker enhancement",
        "Applying white-top-hat filter to highlight one marker",
    ),
    "quantify_filtered_mesmer": (
        "Filtered marker quantification",
        "Measuring intensities on enhanced marker images",
    ),
    "quantify_filtered_whole_cell_mesmer": (
        "Filtered marker quantification",
        "Measuring intensities on enhanced marker images (whole cell)",
    ),
    "quantify_filtered_stardist": (
        "Filtered marker quantification",
        "Measuring intensities on enhanced marker images",
    ),
}

# (regex, replacement) — applied in order; replacement can be str or callable(match)
_LINE_REWRITES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^=+$"), ""),
    (re.compile(r"^-+$"), ""),
    (re.compile(r"Illumination job started", re.I), "Starting lighting correction"),
    (re.compile(r"Ashlar stitching job started", re.I), "Starting tile stitching"),
    (re.compile(r"Mesmer segmentation job started", re.I), "Starting Mesmer cell segmentation"),
    (re.compile(r"StarDist segmentation job started", re.I), "Starting StarDist nucleus segmentation"),
    (re.compile(r"Nuclear quantification job started", re.I), "Starting marker quantification (nuclei)"),
    (re.compile(r"Whole-cell quantification job started", re.I), "Starting marker quantification (whole cells)"),
    (re.compile(r"White-tophat filtering job started", re.I), "Enhancing one marker image"),
    (re.compile(r"Filtered-image quantification job started", re.I), "Quantifying enhanced marker images"),
    (re.compile(r"Filter one marker", re.I), "Enhancing marker channel"),
    (re.compile(r"Quantify filtered marker images", re.I), "Quantifying filtered markers"),
    (re.compile(r"Running Ashlar inside Singularity", re.I), "Stitching tiles together (please wait)"),
    (re.compile(r"Running Mesmer inside Singularity", re.I), "Running Mesmer AI segmentation"),
    (re.compile(r"Running StarDist inside Singularity", re.I), "Running StarDist segmentation"),
    (re.compile(r"Running quantification inside Singularity", re.I), "Measuring marker intensities in cells"),
    (re.compile(r"Running headless ImageJ", re.I), "Estimating lighting profiles with ImageJ"),
    (re.compile(r"Copying raw files to local scratch", re.I), "Copying raw tiles to fast workspace storage"),
    (re.compile(r"Copying input to local scratch", re.I), "Copying input to fast workspace storage"),
    (re.compile(r"Copying stitched OME-TIFF", re.I), "Saving stitched whole-slide image"),
    (re.compile(r"Promoting staged masks", re.I), "Saving segmentation masks"),
    (re.compile(r"Job finished successfully", re.I), "Finished successfully"),
    (re.compile(r"Output already exists\. Job complete\.", re.I), "Already done — skipping"),
    (re.compile(r"Output masks already exist", re.I), "Segmentation masks already exist — skipping"),
    (re.compile(r"Total tiles", re.I), "Image split into tiles for AI processing"),
    (re.compile(r"Stitching masks using", re.I), "Assembling tile results into full image"),
    (re.compile(r"SUCCESS: wrote", re.I), "Saved output"),
    (re.compile(r"Wrote:", re.I), "Saved"),
    (re.compile(r"Matched pairs", re.I), "Samples ready for quantification"),
    (re.compile(r"Markers loaded", re.I), "Marker list loaded"),
    (re.compile(r"Reading channel \d+ from", re.I), "Reading marker channel from image"),
    (re.compile(r"Applying white-tophat", re.I), "Enhancing marker signal (white top-hat)"),
    (re.compile(r"Preparing Mesmer Python", re.I), "Preparing Mesmer software environment"),
    (re.compile(r"Warming StarDist model", re.I), "Loading StarDist AI model (first time may take a minute)"),
    (re.compile(r"DeepCell/Mesmer model cache", re.I), "Checking Mesmer model download"),
    (re.compile(r"Container GPU selected", re.I), "Using GPU for faster processing"),
    (re.compile(r"WARNING: /dev/kfd", re.I), "Note: GPU device check — job may still run on CPU"),
    (re.compile(r"WARNING:", re.I), "Note:"),
    (re.compile(r"ERROR:", re.I), "Problem:"),
]

_NOISE_SUBSTRINGS = (
    "singularity exec",
    "PYTHONPATH=",
    "LD_LIBRARY_PATH",
    "TF_CPP_MIN_LOG_LEVEL",
    "OMP_NUM_THREADS",
    "HIP_VISIBLE",
    "ROCR_VISIBLE",
    "CUDA_VISIBLE",
    "MIOPEN_",
    "JAVA_OPTS",
    "_JAVA_OPTIONS",
    "device_lib",
    "cuDNN",
    "MIOpen",
    "Keras",
    "tensorflow",
    "Monkey-patched",
    "Removed SLURM_NTASKS",
    "realpath --relative",
    "mkdir -p",
    "trap cleanup",
    "flock -w",
    "chmod -R",
    "unset LD_PRELOAD",
    "Submitted batch job",
    "SLURM jobid",
    "--bind ",
    "--env ",
    "--rocm",
    "printf '[",
    "set -euo",
)


def friendly_log_enabled() -> bool:
    return os.environ.get("PIPELINE_FRIENDLY_LOG", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def parse_wildcards(wildcards: str) -> str:
    if not wildcards or wildcards == "unknown":
        return ""

    parts: list[str] = []
    for token in wildcards.replace(",", " ").split():
        if token.startswith("sample_"):
            parts.append(f"Sample {token[7:]}")
        elif token.startswith("exp_"):
            parts.append(f"cycle {token[4:]}")
        elif token.startswith("marker_"):
            parts.append(f"marker {token[7:]}")
        elif token.startswith("method_"):
            parts.append(token[7:])
        else:
            parts.append(token.replace("_", " "))

    return " · ".join(parts)


def rule_label(rule: str) -> tuple[str, str]:
    title, subtitle = FRIENDLY_RULES.get(
        rule,
        (rule.replace("_", " ").title(), "Processing"),
    )
    return title, subtitle


def format_live_prefix(rule: str, wildcards: str) -> str:
    title, _ = rule_label(rule)
    wc = parse_wildcards(wildcards)
    if wc:
        return f"{title} — {wc}"
    return title


def format_submit_line(rule: str, wildcards: str, resources: str) -> str:
    title, subtitle = rule_label(rule)
    wc = parse_wildcards(wildcards)
    if wc:
        head = f"Starting: {title} ({wc})"
    else:
        head = f"Starting: {title}"
    return f"  ▶ QUEUE  {head}  [{resources}]  — {subtitle}"


def _shorten_paths(text: str) -> str:
    def repl(m: re.Match[str]) -> str:
        p = m.group(0)
        try:
            name = Path(p).name
            if len(name) < len(p):
                return name
        except Exception:
            pass
        return p

    return re.sub(r"(?:/[\w.\-]+){2,}", repl, text)


def humanize_line(line: str) -> str | None:
    """Return a friendly line, or None if the line should be hidden in live view."""
    if not line or not line.strip():
        return None

    s = line.strip()
    s = s.split("\r")[-1].strip()

    if not friendly_log_enabled():
        return s

    for noise in _NOISE_SUBSTRINGS:
        if noise.lower() in s.lower():
            return None

    if is_bash_noise(s):
        return None

    for pattern, repl in _LINE_REWRITES:
        if pattern.search(s):
            s = pattern.sub(repl, s).strip()
            break

    s = _shorten_paths(s)

    # Drop lines that are still mostly shell paths or flags
    if s.startswith("-") or s.startswith("[[") or "=" in s and "/" in s and len(s) > 120:
        return None

    if not s:
        return None

    return s


def is_bash_noise(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    if s in ("(", ")", "{", "}", "fi", "else", "then", "do", "done", "elif"):
        return True
    if s.endswith("\\"):
        return True
    first = s.split()[0] if s.split() else ""
    if first in (
        "if",
        "for",
        "while",
        "elif",
        "case",
        "esac",
        "flock",
        "mkdir",
        "rm",
        "cp",
        "mv",
        "chmod",
        "singularity",
        "unset",
        "exit",
        "return",
        "trap",
        "local",
        "printf",
        "echo",
        "export",
        "set",
        "test_container_imports",
        "install_project_python_packages",
        "test_mesmer_model_cache",
        "clean_deepcell_model_cache",
        "cleanup",
        "select_first_gpu",
    ):
        return True
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", s):
        return True
    return False


def is_progress_bar(line: str) -> bool:
    if "it/s" in line or "s/it" in line:
        return True
    if any(ch in line for ch in "█▋░▒▓"):
        return True
    if re.search(r"\[\d{2}:\d{2}<\d{2}:\d{2}", line):
        return True
    return False


def progress_percent(line: str) -> int | None:
    m = re.search(r"(\d+)%\s*\|", line)
    if m:
        return int(m.group(1))
    return None
