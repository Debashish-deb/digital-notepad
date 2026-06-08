#!/bin/bash
# ============================================================
# pipeline_config.sh
# Centralized configuration for the unified image processing pipeline.
#
# This file is sourced by run_pipeline.sh.
# Do NOT run this file directly.
# ============================================================

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "ERROR: Do not run pipeline_config.sh directly."
    echo "Use:"
    echo "  bash run_pipeline.sh"
    exit 1
fi

# ============================================================
# PROJECT-LOCAL PATH POLICY
# ============================================================
# Expected layout:
#
#   <BASE>/scripts/pipeline_config.sh
#   <BASE>/scripts/run_pipeline.sh
#   <BASE>/data/raw/<sample>/*.rcpnl
#
# By default, BASE is inferred from the location of this config file:
#
#   <BASE>/scripts/pipeline_config.sh  ->  BASE=<BASE>
#
# This prevents accidentally reusing hard-coded paths from another project.
#
# Safe manual override:
#   export PIPELINE_BASE_OVERRIDE=/scratch/project_xxx/image_processing/owner/dataset
#   bash run_pipeline.sh
#
# Legacy BASE override is ignored by default to prevent stale environment leaks.
# To intentionally allow it:
#   export ALLOW_EXTERNAL_BASE_OVERRIDE=1
#   export BASE=/scratch/project_xxx/image_processing/owner/dataset
#
# Derived path overrides such as RAW_DIR, DATA_DIR, LOG_ROOT, etc. are ignored
# by default. To intentionally allow them:
#   export ALLOW_EXTERNAL_PATH_OVERRIDES=1
#
# Safer explicit metadata overrides:
#   export PIPELINE_PROJECT_ID_OVERRIDE=project_xxx
#   export PIPELINE_PROJECT_ROOT_OVERRIDE=/scratch/project_xxx
#   export PIPELINE_DATASET_OWNER_OVERRIDE=owner
#   export PIPELINE_DATASET_NAME_OVERRIDE=dataset
#
# Safer explicit Snakemake env override:
#   export SNAKEMAKE_VENV_OVERRIDE=/scratch/project_xxx/envs/snakemake311/bin/activate
#
# Safer filtering override:
#   export PIPELINE_RUN_FILTERING_OVERRIDE=1
#   export PIPELINE_MARKERS_JSON_OVERRIDE='{"DNA1":0,"Ki67":7}'
# ============================================================

export ALLOW_EXTERNAL_BASE_OVERRIDE="${ALLOW_EXTERNAL_BASE_OVERRIDE:-0}"
export ALLOW_EXTERNAL_PATH_OVERRIDES="${ALLOW_EXTERNAL_PATH_OVERRIDES:-0}"

_PIPELINE_CONFIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
_INFERRED_BASE_FROM_SCRIPT="$(cd "${_PIPELINE_CONFIG_DIR}/.." && pwd -P)"

_infer_project_id_from_base() {
    local p="$1"
    local part
    local -a parts

    IFS='/' read -ra parts <<< "${p}"

    for part in "${parts[@]}"; do
        if [[ "${part}" == project_* ]]; then
            echo "${part}"
            return
        fi
    done

    basename "$(_infer_project_root_from_base "${p}")"
}

_infer_project_root_from_base() {
    local p="$1"
    local part
    local current=""
    local image_processing_parent=""
    local -a parts

    IFS='/' read -ra parts <<< "${p}"

    for part in "${parts[@]}"; do
        [[ -z "${part}" ]] && continue

        current="${current}/${part}"

        if [[ "${part}" == project_* ]]; then
            echo "${current}"
            return
        fi

        if [[ "${part}" == "image_processing" ]]; then
            image_processing_parent="${current%/image_processing}"
        fi
    done

    if [[ -n "${image_processing_parent}" ]]; then
        echo "${image_processing_parent}"
        return
    fi

    echo "${p}"
}

_infer_owner_from_base() {
    local p="$1"
    local i
    local -a parts

    IFS='/' read -ra parts <<< "${p}"

    for ((i=0; i<${#parts[@]}; i++)); do
        if [[ "${parts[$i]}" == "image_processing" && $((i + 1)) -lt ${#parts[@]} ]]; then
            echo "${parts[$((i + 1))]}"
            return
        fi
    done

    basename "$(dirname "${p}")"
}

_infer_dataset_from_base() {
    basename "$1"
}

_set_project_path() {
    local var_name="$1"
    local default_value="$2"
    local existing_value="${!var_name-}"

    if [[ "${ALLOW_EXTERNAL_PATH_OVERRIDES}" == "1" && -n "${existing_value}" ]]; then
        export "${var_name}=${existing_value}"
    else
        export "${var_name}=${default_value}"
    fi
}

_set_default_value() {
    local var_name="$1"
    local default_value="$2"
    local existing_value="${!var_name-}"

    if [[ -n "${existing_value}" ]]; then
        export "${var_name}=${existing_value}"
    else
        export "${var_name}=${default_value}"
    fi
}

_first_existing_path() {
    local p

    for p in "$@"; do
        if [[ -n "${p}" && -e "${p}" ]]; then
            echo "${p}"
            return 0
        fi
    done

    return 1
}

_pipeline_default_sif() {
    local image_name="$1"
    local fallback

    if [[ "${PROJECT_ID}" == project_* ]]; then
        fallback="/projappl/${PROJECT_ID}/envs/${image_name}.sif"
    else
        fallback="${PROJECT_ROOT}/envs/${image_name}.sif"
    fi

    _first_existing_path \
        "${BASE}/envs/${image_name}.sif" \
        "${SCRIPTS_DIR:-${_PIPELINE_CONFIG_DIR}}/envs/${image_name}.sif" \
        "${PROJECT_ROOT}/envs/${image_name}.sif" \
        "/projappl/${PROJECT_ID}/envs/${image_name}.sif" \
        "${fallback}" \
        || echo "${fallback}"
}

_pipeline_default_mesmer_sif() {
    local preferred

    if [[ "${PROJECT_ID}" == project_* ]]; then
        preferred="/projappl/${PROJECT_ID}/envs/mesmer-lumi-rocm63.sif"
    else
        preferred="${PROJECT_ROOT}/envs/mesmer-lumi-rocm63.sif"
    fi

    _first_existing_path \
        "${BASE}/envs/mesmer-lumi-rocm63.sif" \
        "${SCRIPTS_DIR:-${_PIPELINE_CONFIG_DIR}}/envs/mesmer-lumi-rocm63.sif" \
        "${PROJECT_ROOT}/envs/mesmer-lumi-rocm63.sif" \
        "/projappl/${PROJECT_ID}/envs/mesmer-lumi-rocm63.sif" \
        "${preferred}" \
        "$(_pipeline_default_sif mesmer)" \
        || echo "${preferred}"
}

_pipeline_default_snakemake_venv() {
    _first_existing_path \
        "${BASE}/envs/snakemake311/bin/activate" \
        "${PROJECT_ROOT}/envs/snakemake311/bin/activate" \
        "${BASE}/.venv-snakemake/bin/activate" \
        "${BASE}/.venv/bin/activate" \
        || echo "${PROJECT_ROOT}/envs/snakemake311/bin/activate"
}

_pipeline_default_channel_file() {
    _first_existing_path \
        "${DATA_DIR}/channels_quantification.csv" \
        "${DATA_DIR}/channel_quantification.csv" \
        "${DATA_DIR}/channels.csv" \
        "${BASE}/channels_quantification.csv" \
        "${SCRIPTS_DIR:-${_PIPELINE_CONFIG_DIR}}/channels_quantification.csv" \
        || echo "${DATA_DIR}/channels_quantification.csv"
}

# ============================================================
# BASE and project identity
# ============================================================
# BASE is the source of truth.
# PROJECT_ID, DATASET_OWNER, DATASET_NAME are recalculated every time from BASE
# unless explicit PIPELINE_*_OVERRIDE variables are used.

if [[ -n "${PIPELINE_BASE_OVERRIDE:-}" ]]; then
    export BASE="${PIPELINE_BASE_OVERRIDE}"
elif [[ "${ALLOW_EXTERNAL_BASE_OVERRIDE}" == "1" && -n "${BASE:-}" ]]; then
    export BASE="${BASE}"
else
    export BASE="${_INFERRED_BASE_FROM_SCRIPT}"
fi

export PROJECT_ID="${PIPELINE_PROJECT_ID_OVERRIDE:-$(_infer_project_id_from_base "${BASE}")}"
export PROJECT_ROOT="${PIPELINE_PROJECT_ROOT_OVERRIDE:-$(_infer_project_root_from_base "${BASE}")}"
export DATASET_OWNER="${PIPELINE_DATASET_OWNER_OVERRIDE:-$(_infer_owner_from_base "${BASE}")}"
export DATASET_NAME="${PIPELINE_DATASET_NAME_OVERRIDE:-$(_infer_dataset_from_base "${BASE}")}"

# Kept for compatibility/reporting. BASE remains the source of truth.
export IMAGE_PROCESSING_ROOT="$(dirname "$(dirname "${BASE}")")"

# ============================================================
# Project-specific scientific/filtering defaults
# ============================================================
# Filtering is enabled by default, but marker/channel mapping is NOT hard-coded.
#
# Source of truth for every experiment:
#   ${DATA_DIR}/channels_quantification.csv
#
# The config derives:
#   CHANNEL_COUNT        = all rows in channels_quantification.csv
#   FILTER_MARKER_COUNT  = biological filtering markers only
#   MARKERS_JSON         = marker -> zero-based channel index for filtering
#
# Excluded from filtering markers:
#   DAPI_*, *_background, *_failed
#
# Emergency manual override is disabled by default. To intentionally override:
#   export ALLOW_MARKERS_JSON_OVERRIDE=1
#   export PIPELINE_MARKERS_JSON_OVERRIDE='{"Ki-67":15}'
PROJECT_DEFAULT_RUN_FILTERING="1"
PROJECT_DEFAULT_MARKERS_JSON=""
export ALLOW_MARKERS_JSON_OVERRIDE="${ALLOW_MARKERS_JSON_OVERRIDE:-0}"

# ============================================================
# General behavior
# ============================================================

_set_default_value CREATE_PIPELINE_DIRS_ON_SOURCE "1"
_set_default_value RESOLVE_LIVE_PATHS "1"
_set_default_value SHOW_DIRECTORY_REPORT "1"

# ============================================================
# DeepCell token policy
# ============================================================
# IMPORTANT:
# Do not save DeepCell token in this config file.
# Do not export DEEPCELL_ACCESS_TOKEN here.
#
# run_pipeline.sh must always ask the user interactively when Mesmer
# or Both is selected.
unset DEEPCELL_ACCESS_TOKEN 2>/dev/null || true
unset APPTAINERENV_DEEPCELL_ACCESS_TOKEN 2>/dev/null || true
unset SINGULARITYENV_DEEPCELL_ACCESS_TOKEN 2>/dev/null || true

# ============================================================
# Helper functions
# ============================================================

_realpath_safe() {
    local p="$1"

    if [[ "${RESOLVE_LIVE_PATHS}" != "1" ]]; then
        echo "${p}"
        return
    fi

    if command -v readlink >/dev/null 2>&1; then
        readlink -m "${p}" 2>/dev/null || echo "${p}"
    else
        echo "${p}"
    fi
}

_make_dir_safe() {
    local p="$1"

    if [[ -n "${p}" ]]; then
        mkdir -p "${p}"
    fi
}

pipeline_config_print_directories() {
    echo ""
    echo "Directory configuration"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "PROJECT_ID              : ${PROJECT_ID}"
    echo "PROJECT_ROOT            : ${PROJECT_ROOT}"
    echo "DATASET_OWNER           : ${DATASET_OWNER}"
    echo "DATASET_NAME            : ${DATASET_NAME}"
    echo "BASE                    : ${BASE}"
    echo "BASE_LIVE               : ${BASE_LIVE}"
    echo ""
    echo "RAW_DIR                 : ${RAW_DIR}"
    echo "RAW_DIR_LIVE            : ${RAW_DIR_LIVE}"
    echo "ILLUM_DIR               : ${ILLUM_DIR}"
    echo "STITCHED_DIR            : ${STITCHED_DIR}"
    echo "SEGMENTED_DIR           : ${SEGMENTED_DIR}"
    echo "QUANT_DIR               : ${QUANT_DIR}"
    echo "FILTERED_DIR            : ${FILTERED_DIR}"
    echo "FILTERED_TIF_DIR        : ${FILTERED_TIF_DIR}"
    echo "FILTERED_CSV_DIR        : ${FILTERED_CSV_DIR}"
    echo "LOG_ROOT                : ${LOG_ROOT}"
    echo "SNAKEMAKE_SLURM_LOG_DIR : ${SNAKEMAKE_SLURM_LOG_DIR}"
    echo "PIPELINE_TMP_DIR        : ${PIPELINE_TMP_DIR}"
    echo "PIPELINE_CACHE_DIR      : ${PIPELINE_CACHE_DIR}"
    echo "PIPELINE_ENV_MODE       : ${PIPELINE_ENV_MODE}"
    echo "SNAKEMAKE_VENV          : ${SNAKEMAKE_VENV}"
    echo "SLURM_ACCOUNT           : ${SLURM_ACCOUNT}"
    echo "SLURM_PARTITION_CPU     : ${SLURM_PARTITION_CPU}"
    echo "SLURM_PARTITION_GPU     : ${SLURM_PARTITION_GPU}"
    echo "RUN_FILTERING           : ${RUN_FILTERING}"
    echo "CHANNEL_NAMES_FILE      : ${CHANNEL_NAMES_FILE:-}"
    echo "CHANNEL_COUNT           : ${CHANNEL_COUNT:-0}"
    echo "FILTER_MARKER_COUNT     : ${FILTER_MARKER_COUNT:-0}"
    echo "NUCLEAR_CHANNEL         : ${NUCLEAR_CHANNEL:-} (${NUCLEAR_CHANNEL_NAME:-unknown})"
    echo "MEMBRANE_CHANNEL        : ${MEMBRANE_CHANNEL:-} (${MEMBRANE_CHANNEL_NAME:-unknown})"
    echo "MESMER_COMPARTMENT      : ${MESMER_COMPARTMENT:-}"
    echo "MARKERS_JSON            : ${MARKERS_JSON:-}"
    echo ""
    echo "SIF_IMAGE_ILLUMINATION  : ${SIF_IMAGE_ILLUMINATION:-}"
    echo "SIF_IMAGE_STITCHING     : ${SIF_IMAGE_STITCHING:-}"
    echo "SIF_IMAGE_MESMER        : ${SIF_IMAGE_MESMER:-}"
    echo "SIF_IMAGE_STARDIST      : ${SIF_IMAGE_STARDIST:-}"
    echo "SIF_IMAGE_QUANTIFICATION: ${SIF_IMAGE_QUANTIFICATION:-}"
    echo "ALLOW_EXTERNAL_BASE     : ${ALLOW_EXTERNAL_BASE_OVERRIDE}"
    echo "ALLOW_EXTERNAL_PATHS    : ${ALLOW_EXTERNAL_PATH_OVERRIDES}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

# ============================================================
# Pipeline notifications
# ============================================================
_set_default_value PIPELINE_EMAIL ""

# ============================================================
# Project paths
# ============================================================
_set_default_value PIPELINE_TITLE "${DATASET_NAME} Image Processing Pipeline"
_set_default_value SLURM_ACCOUNT "${PROJECT_ID}"

# Resolve the code directory: must contain Snakefile. Prefer the folder that
# holds this config file (works when the folder is named "scripts" OR the
# common typo "scipts"). Fall back to ${BASE}/scripts or ${BASE}/scipts.
_resolve_scripts_dir() {
    local base="$1"
    local config_dir="$2"

    if [[ -f "${config_dir}/Snakefile" ]]; then
        echo "${config_dir}"
        return
    fi

    local candidate
    for candidate in "${base}/scripts" "${base}/scipts"; do
        if [[ -f "${candidate}/Snakefile" ]]; then
            echo "${candidate}"
            return
        fi
    done

    echo "${base}/scripts"
}

_SCRIPTS_DIR_RESOLVED="$(_resolve_scripts_dir "${BASE}" "${_PIPELINE_CONFIG_DIR}")"
if [[ "${_SCRIPTS_DIR_RESOLVED}" == *"/scipts" ]]; then
    echo "NOTE: Using scripts folder '${_SCRIPTS_DIR_RESOLVED}' (spelled 'scipts')." \
         "Consider renaming to 'scripts' when convenient." >&2
fi

_set_project_path STATE_DIR "${BASE}/pipeline_state"
_set_project_path SCRIPTS_DIR "${_SCRIPTS_DIR_RESOLVED}"
_set_project_path DATA_DIR "${BASE}/data"

export BASE_LIVE="$(_realpath_safe "${BASE}")"
export STATE_DIR_LIVE="$(_realpath_safe "${STATE_DIR}")"
export SCRIPTS_DIR_LIVE="$(_realpath_safe "${SCRIPTS_DIR}")"
export DATA_DIR_LIVE="$(_realpath_safe "${DATA_DIR}")"

# ============================================================
# I/O directories
# ============================================================
_set_project_path RAW_DIR "${DATA_DIR}/raw"
_set_project_path ILLUM_DIR "${DATA_DIR}/illumination_correction"
_set_project_path STITCHED_DIR "${DATA_DIR}/stitching"
_set_project_path SEGMENTED_DIR "${DATA_DIR}/segmentation"
_set_project_path QUANT_DIR "${DATA_DIR}/quantification"
_set_project_path FILTERED_DIR "${DATA_DIR}/filter_images"
_set_project_path FILTERED_TIF_DIR "${FILTERED_DIR}/tif"
_set_project_path FILTERED_CSV_DIR "${FILTERED_DIR}/csv"

export RAW_DIR_LIVE="$(_realpath_safe "${RAW_DIR}")"
export ILLUM_DIR_LIVE="$(_realpath_safe "${ILLUM_DIR}")"
export STITCHED_DIR_LIVE="$(_realpath_safe "${STITCHED_DIR}")"
export SEGMENTED_DIR_LIVE="$(_realpath_safe "${SEGMENTED_DIR}")"
export QUANT_DIR_LIVE="$(_realpath_safe "${QUANT_DIR}")"
export FILTERED_DIR_LIVE="$(_realpath_safe "${FILTERED_DIR}")"
export FILTERED_TIF_DIR_LIVE="$(_realpath_safe "${FILTERED_TIF_DIR}")"
export FILTERED_CSV_DIR_LIVE="$(_realpath_safe "${FILTERED_CSV_DIR}")"

# ============================================================
# Log directories
# ============================================================
_set_project_path LOG_ROOT "${BASE}/logs"

_set_project_path LOG_ILLUM_DIR "${LOG_ROOT}/illumination"
_set_project_path LOG_STITCHING_DIR "${LOG_ROOT}/stitching"
_set_project_path LOG_SEGMENTATION_DIR "${LOG_ROOT}/segmentation"
_set_project_path LOG_QUANTIFICATION_DIR "${LOG_ROOT}/quantification"
_set_project_path LOG_FILTERING_DIR "${LOG_ROOT}/filtering"

_set_project_path LOG_MESMER_DIR "${LOG_SEGMENTATION_DIR}/mesmer"
_set_project_path LOG_STARDIST_DIR "${LOG_SEGMENTATION_DIR}/stardist"

_set_project_path SNAKEMAKE_SLURM_LOG_DIR "${LOG_ROOT}/snakemake_slurm"
_set_project_path DONE_DIR "${SCRIPTS_DIR}/.snakemake_done"

export LOG_ROOT_LIVE="$(_realpath_safe "${LOG_ROOT}")"
export SNAKEMAKE_SLURM_LOG_DIR_LIVE="$(_realpath_safe "${SNAKEMAKE_SLURM_LOG_DIR}")"

# ============================================================
# Temporary/cache directories
# ============================================================
_set_project_path PIPELINE_TMP_DIR "${BASE}/tmp"
_set_project_path PIPELINE_CACHE_DIR "${BASE}/cache"
# LUMI-G compute nodes have no local disk and /tmp consumes the job's RAM.
# Keep large workflow scratch on the configured shared filesystem instead.
_set_project_path LOCAL_SCRATCH "${PIPELINE_TMP_DIR}/job_scratch"

_set_project_path TMPDIR "${PIPELINE_TMP_DIR}"
_set_project_path TEMP "${PIPELINE_TMP_DIR}"
_set_project_path TMP "${PIPELINE_TMP_DIR}"

_set_project_path XDG_CACHE_HOME "${PIPELINE_CACHE_DIR}/xdg-cache"
_set_project_path XDG_CONFIG_HOME "${PIPELINE_CACHE_DIR}/xdg-config"
_set_project_path MPLCONFIGDIR "${PIPELINE_CACHE_DIR}/matplotlib"
_set_project_path NUMBA_CACHE_DIR "${PIPELINE_CACHE_DIR}/numba"
_set_project_path PIP_CACHE_DIR "${PIPELINE_CACHE_DIR}/pip"

_set_project_path APPTAINER_CACHEDIR "${PIPELINE_CACHE_DIR}/apptainer"
_set_project_path SINGULARITY_CACHEDIR "${APPTAINER_CACHEDIR}"

_set_project_path KERAS_HOME "${PIPELINE_CACHE_DIR}/keras"
_set_project_path DEEPCELL_CACHE_DIR "${PIPELINE_CACHE_DIR}/deepcell"

_set_project_path MIOPEN_USER_DB_PATH "${PIPELINE_CACHE_DIR}/miopen/user_db"
_set_project_path MIOPEN_CUSTOM_CACHE_DIR "${PIPELINE_CACHE_DIR}/miopen/custom_cache"

_set_default_value CLEAN_TRANSIENT_ON_SUCCESS "1"
_set_default_value CLEAN_DEEPCELL_CACHE_ON_SUCCESS "0"
_set_default_value CLEAN_APPTAINER_CACHE_ON_SUCCESS "0"
_set_default_value CLEAN_WORKFLOW_METADATA_ON_SUCCESS "1"
_set_default_value AUTO_UNLOCK_SNAKEMAKE "1"
_set_default_value SNAKEMAKE_UNLOCK_MODE "direct"  # direct | snakemake
_set_default_value SNAKEMAKE_UNLOCK_TIMEOUT "15"

# ============================================================
# Smart resume / smart resource policy
# ============================================================
_set_default_value PIPELINE_FRIENDLY_LOG "1"
_set_default_value PIPELINE_VERBOSE_LOG "0"

_set_default_value AUTO_SYNC_STATE_FROM_OUTPUTS "1"
_set_default_value CONFIRM_RAW_DATASET_ON_FIRST_RUN "1"
_set_default_value AUTO_APPROVE_PREVIOUS_STAGES_FROM_OUTPUTS "1"

_set_default_value MAX_CPU_JOBS "32"
# GPU segmentation concurrency cap.
#
# Mesmer and StarDist use one LUMI-G GCD per image. LUMI standard-g allocates
# whole nodes, so the default stays on small-g and scales by launching more
# one-GCD image jobs. If you intentionally want full-node standard-g jobs, run:
#   export SLURM_PARTITION_GPU=standard-g
# before launching the pipeline. Keep in mind that standard-g bills/reserves
# the complete node even when a single image job uses only one GCD.
#
# For 150-200 GiB stitched samples, 32 concurrent one-GCD jobs is an aggressive
# but still scheduler-friendly default: about two waves for 58 samples, while
# avoiding the huge waste of submitting one full standard-g node per sample.
_set_default_value MAX_GPU_JOBS "32"

# ============================================================
# Channel names file and automatic marker map
# ============================================================
_set_project_path CHANNEL_NAMES_FILE "$(_pipeline_default_channel_file)"
export CHANNELS_QUANTIFICATION_CSV="${CHANNELS_QUANTIFICATION_CSV:-${CHANNEL_NAMES_FILE}}"

_pipeline_config_python() {
    if command -v python3 >/dev/null 2>&1; then
        command -v python3
        return 0
    fi

    if command -v python >/dev/null 2>&1; then
        command -v python
        return 0
    fi

    return 1
}

_pipeline_derive_channels_from_csv() {
    if [[ ! -f "${CHANNELS_QUANTIFICATION_CSV}" ]]; then
        echo "WARNING: channel names CSV not found yet:" >&2
        echo "  ${CHANNELS_QUANTIFICATION_CSV}" >&2
        export CHANNEL_COUNT="0"
        export FILTER_MARKER_COUNT="0"
        export MARKERS_JSON="{}"
        export PIPELINE_MARKERS_JSON_OVERRIDE="{}"
        export NUCLEAR_CHANNEL_AUTO="0"
        export NUCLEAR_CHANNEL_AUTO_NAME="unknown"
        export MEMBRANE_CHANNEL_AUTO="1"
        export MEMBRANE_CHANNEL_AUTO_NAME="unknown"
        export NUCLEAR_CHANNEL_RESOLVED="${PIPELINE_NUCLEAR_CHANNEL_OVERRIDE:-0}"
        export NUCLEAR_CHANNEL_RESOLVED_NAME="unknown"
        export MEMBRANE_CHANNEL_RESOLVED="${PIPELINE_MEMBRANE_CHANNEL_OVERRIDE:-1}"
        export MEMBRANE_CHANNEL_RESOLVED_NAME="unknown"
        return 0
    fi

    local pybin
    pybin="$(_pipeline_config_python)" || {
        echo "ERROR: python3/python is required to derive MARKERS_JSON from channels_quantification.csv" >&2
        return 1
    }

    eval "$("${pybin}" <<'PY'
from pathlib import Path
import os
import json
import re
import shlex

path = Path(os.environ["CHANNELS_QUANTIFICATION_CSV"])

channels = [
    line.strip()
    for line in path.read_text(encoding="utf-8-sig").splitlines()
    if line.strip()
]

# Tolerate a future accidental header row.
if channels and channels[0].lower() in {
    "channel", "channels", "marker", "markers", "name",
    "channel_name", "marker_name"
}:
    channels = channels[1:]

def exclude_from_filtering(name: str) -> bool:
    lower = name.lower()
    return (
        lower.startswith("dapi")
        or "background" in lower
        or "_failed" in lower
        or lower.endswith("failed")
    )

markers = {
    name: idx
    for idx, name in enumerate(channels)
    if not exclude_from_filtering(name)
}

def normalize_marker(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())

normalized_channels = [normalize_marker(name) for name in channels]

def valid_segmentation_channel(name: str) -> bool:
    lower = name.lower()
    return not any(token in lower for token in ("background", "failed", "blank", "empty"))

nuclear_aliases = (
    "dapi", "hoechst", "dna", "histone", "draq", "ir191", "ir193", "nuclear",
)
nuclear_indices = [
    idx for idx, normalized in enumerate(normalized_channels)
    if valid_segmentation_channel(channels[idx])
    and any(alias in normalized for alias in nuclear_aliases)
]

# The reference mesmer.py uses OME input channel 0 for nuclear segmentation.
# Preserve that exact default whenever channel 0 is a validated nuclear marker.
# If it is not nuclear, use the first validated nuclear marker rather than
# silently selecting a later repeated round.
if 0 in nuclear_indices:
    nuclear_idx = 0
elif nuclear_indices:
    nuclear_idx = nuclear_indices[0]
else:
    nuclear_idx = 0

membrane_priority = [
    ("cellmask", "wga", "panmembrane", "membrane"),
    ("ecadherin", "cdh1"),
    ("panck", "pancytokeratin", "cytokeratin", "keratin"),
    ("cd45", "ptprc"),
    ("ncadherin", "cdh2"),
    ("vimentin",),
    ("asma", "acta2"),
]

membrane_idx = None
for aliases in membrane_priority:
    match = next(
        (
            idx for idx, normalized in enumerate(normalized_channels)
            if valid_segmentation_channel(channels[idx])
            and any(alias in normalized for alias in aliases)
        ),
        None,
    )
    if match is not None:
        membrane_idx = match
        break

if membrane_idx is None:
    membrane_idx = 1 if len(channels) > 1 else 0

nuclear_override = os.environ.get("PIPELINE_NUCLEAR_CHANNEL_OVERRIDE", "").strip()
membrane_override = os.environ.get("PIPELINE_MEMBRANE_CHANNEL_OVERRIDE", "").strip()
nuclear_resolved = int(nuclear_override) if nuclear_override else nuclear_idx
membrane_resolved = int(membrane_override) if membrane_override else membrane_idx

def channel_name(idx: int) -> str:
    if 0 <= idx < len(channels):
        return channels[idx]
    return "unknown"

exports = {
    "CHANNEL_COUNT": str(len(channels)),
    "FILTER_MARKER_COUNT": str(len(markers)),
    "MARKERS_JSON": json.dumps(markers, ensure_ascii=False, separators=(",", ":")),
    "PIPELINE_MARKERS_JSON_OVERRIDE": json.dumps(markers, ensure_ascii=False, separators=(",", ":")),
    "NUCLEAR_CHANNEL_AUTO": str(nuclear_idx),
    "NUCLEAR_CHANNEL_AUTO_NAME": channel_name(nuclear_idx),
    "MEMBRANE_CHANNEL_AUTO": str(membrane_idx),
    "MEMBRANE_CHANNEL_AUTO_NAME": channel_name(membrane_idx),
    "NUCLEAR_CHANNEL_RESOLVED": str(nuclear_resolved),
    "NUCLEAR_CHANNEL_RESOLVED_NAME": channel_name(nuclear_resolved),
    "MEMBRANE_CHANNEL_RESOLVED": str(membrane_resolved),
    "MEMBRANE_CHANNEL_RESOLVED_NAME": channel_name(membrane_resolved),
}

for key, value in exports.items():
    print(f"export {key}={shlex.quote(value)}")
PY
)"
}

_pipeline_derive_channels_from_csv

# ============================================================
# Environment/container mode
# ============================================================
export PIPELINE_ENV_MODE="separate"

_set_default_value CONTAINER_RUNTIME "apptainer"
_set_default_value CONTAINER_BINDS "/users,/scratch,/project,/projappl,/flash,/pfs/lustrep4/scratch"

# ============================================================
# LUMI Snakemake environment
# ============================================================
_set_default_value CRAY_PYTHON_MODULE "cray-python/3.11.7"

# Do not reuse stale SNAKEMAKE_VENV from another project unless explicit override is used.
if [[ -n "${SNAKEMAKE_VENV_OVERRIDE:-}" ]]; then
    export SNAKEMAKE_VENV="${SNAKEMAKE_VENV_OVERRIDE}"
else
    export SNAKEMAKE_VENV="$(_pipeline_default_snakemake_venv)"
fi

# ============================================================
# Common Snakemake settings
# ============================================================
_set_default_value LATENCY_WAIT "60"
_set_default_value RESTART_TIMES "1"
_set_default_value MAX_JOBS_PER_SECOND "5"
_set_default_value LOCAL_CORES "2"

_set_default_value SLURM_PARTITION_CPU "small"
_set_default_value SLURM_PARTITION_GPU "small-g"
_set_default_value MESMER_SUBMISSION_MODE "direct"   # direct | snakemake
_set_default_value MESMER_GPU_GRES "gpu:mi250:1"
_set_default_value MESMER_DIRECT_ARRAY_MEM_MB "auto"
_set_default_value MESMER_DIRECT_RUNTIME_MIN "auto"
_set_default_value SEGMENTATION_STRIPE_COUNT "4"
_set_default_value SEGMENTATION_STRIPE_SIZE "4M"

_set_default_value ILLUMINATION_JOBS "auto"
_set_default_value STITCHING_JOBS "auto"
_set_default_value MESMER_JOBS "32"
_set_default_value STARDIST_JOBS "32"
_set_default_value QUANTIFICATION_JOBS "auto"
_set_default_value FILTER_JOBS "auto"

# ============================================================
# LUMI smart resource policy for uneven huge samples
# ============================================================
# These defaults are conservative for LUMI small/small-g. They avoid launching
# too many heavy jobs when one or two samples are much larger than the rest.
# Override per project with environment variables if needed.
_set_default_value SMART_RESOURCE_POLICY "1"
_set_default_value LUMI_SAFETY_PROFILE "balanced"   # safe | balanced | aggressive
_set_default_value MAX_STITCHING_JOBS_HUGE "1"
_set_default_value MAX_STITCHING_JOBS_LARGE "2"
_set_default_value MAX_STITCHING_JOBS_MEDIUM "4"
_set_default_value MAX_MESMER_JOBS_HUGE "1"
_set_default_value MAX_MESMER_JOBS_LARGE "1"
_set_default_value MAX_MESMER_JOBS_MEDIUM "2"
_set_default_value MAX_MESMER_JOBS_SMALL "4"
_set_default_value HUGE_STITCHED_GIB "60"
_set_default_value LARGE_STITCHED_GIB "35"
_set_default_value MEDIUM_STITCHED_GIB "20"
_set_default_value HUGE_RAW_GIB "70"
_set_default_value LARGE_RAW_GIB "40"
_set_default_value MEDIUM_RAW_GIB "20"
_set_default_value SNAKEMAKE_SUBMISSION_STALL_HINT_SECONDS "900"
_set_default_value AUTO_SCANCEL_ON_SNAKEMAKE_FAILURE "1"
_set_default_value MESMER_CLEAN_MODEL_CACHE_AFTER_SUCCESS "0"

# ============================================================
# Step 0: Illumination correction
# ============================================================
_set_project_path SIF_IMAGE_ILLUMINATION "$(_pipeline_default_sif illumination)"

_set_default_value ILLUMINATION_THREADS "4"
_set_default_value LAMBDA_FLAT "0.1"
_set_default_value LAMBDA_DARK "0.01"
_set_default_value COPY_INPUT_TO_SCRATCH "1"
_set_default_value IMAGEJ_BIN "/opt/fiji/Fiji.app/ImageJ-linux64"
_set_project_path IJ_SCRIPT "${SCRIPTS_DIR}/0-illumination_correction/imagej_basic_ashlar.py"

# ============================================================
# Step 1: Stitching
# ============================================================
_set_project_path SIF_IMAGE_STITCHING "$(_pipeline_default_sif ashlar)"

_set_default_value STITCHING_THREADS "4"
_set_project_path PY_SCRIPT_STITCHING "${SCRIPTS_DIR}/1-stitching/ashlar_workflow.py"

# ============================================================
# Step 2a: Mesmer segmentation
# ============================================================
_set_project_path SIF_IMAGE_MESMER "$(_pipeline_default_mesmer_sif)"
_set_default_value MESMER_PYTHON_BIN "/usr/local/bin/python3.10"

_set_default_value MESMER_THREADS "8"
_set_project_path MESMER_PYTHON_USER_PACKAGES "${BASE}/python_user_packages"
_set_default_value MESMER_ROCM_BIND "/opt/rocm-6.3.4:/opt/rocm"
_set_default_value MESMER_ROCM_BITCODE "/opt/rocm/lib/llvm/lib/clang/18/lib/amdgcn/bitcode"
_set_default_value MESMER_USE_PROJECT_PACKAGES "0"
_set_default_value MESMER_REQUIRE_GPU "1"
# Full-resolution label masks are always written. By default, keep them
# uncompressed so the on-disk file size reflects the uint32 label array and
# avoids any viewer/tool ambiguity from compressed tiled labels. Set to
# "deflate" only if storage pressure becomes a problem; deflate is lossless.
_set_default_value MESMER_MASK_COMPRESSION "none"
# Optional original-style output conversion. The mask labels are unchanged, but
# the flat tiled TIFF is transcoded to pyramidal OME-TIFF using
# bioformats2raw/raw2ometiff. Slower, and requires those tools in the SIF.
_set_default_value MESMER_WRITE_PYRAMID "0"
_set_project_path PY_SCRIPT_MESMER "${SCRIPTS_DIR}/2-segmentation/mesmer/mesmer.py"

_set_default_value MESMER_BATCH_SIZE "4"

_set_default_value IMAGE_MPP "auto"

# Resolve channels from channels_quantification.csv. Explicit PIPELINE_* channel
# overrides remain available, but their resolved names are validated by the
# worker before inference.
export NUCLEAR_CHANNEL="${NUCLEAR_CHANNEL_RESOLVED:-${NUCLEAR_CHANNEL_AUTO:-0}}"
export MEMBRANE_CHANNEL="${MEMBRANE_CHANNEL_RESOLVED:-${MEMBRANE_CHANNEL_AUTO:-1}}"
export NUCLEAR_CHANNEL_NAME="${NUCLEAR_CHANNEL_RESOLVED_NAME:-unknown}"
export MEMBRANE_CHANNEL_NAME="${MEMBRANE_CHANNEL_RESOLVED_NAME:-unknown}"

# Mesmer compartment priority:
#   1. explicit environment override
#   2. saved interactive pipeline choice
#   3. default used only to populate non-interactive configuration
_MESMER_COMPARTMENT_USER_SET=0
if [[ -n "${MESMER_COMPARTMENT:-}" ]]; then
    _REQUESTED_MESMER_COMPARTMENT="$(
        printf '%s' "${MESMER_COMPARTMENT}" \
            | tr '[:upper:]_' '[:lower:]-' \
            | tr -d '[:space:]'
    )"
    [[ "${_REQUESTED_MESMER_COMPARTMENT}" == "wholecell" ]] && \
        _REQUESTED_MESMER_COMPARTMENT="whole-cell"
    case "${_REQUESTED_MESMER_COMPARTMENT}" in
        nuclear|whole-cell|both)
            export MESMER_COMPARTMENT="${_REQUESTED_MESMER_COMPARTMENT}"
            _MESMER_COMPARTMENT_USER_SET=1
            ;;
        *)
            echo "WARNING: invalid MESMER_COMPARTMENT=${MESMER_COMPARTMENT}; interactive selection will be requested." >&2
            export MESMER_COMPARTMENT="both"
            ;;
    esac
    unset _REQUESTED_MESMER_COMPARTMENT
elif [[ -s "${STATE_DIR}/mesmer_compartment.txt" && -f "${STATE_DIR}/mesmer_compartment_choice_v2.flag" ]]; then
    _SAVED_MESMER_COMPARTMENT="$(tr -d '[:space:]' < "${STATE_DIR}/mesmer_compartment.txt")"
    case "${_SAVED_MESMER_COMPARTMENT}" in
        nuclear|whole-cell|both)
            export MESMER_COMPARTMENT="${_SAVED_MESMER_COMPARTMENT}"
            _MESMER_COMPARTMENT_USER_SET=1
            ;;
        *)
            export MESMER_COMPARTMENT="both"
            ;;
    esac
    unset _SAVED_MESMER_COMPARTMENT
else
    export MESMER_COMPARTMENT="both"
fi

_set_default_value TILE_SIZE "1024"
_set_default_value TILE_SIZE_HUGE "1024"
_set_default_value TILE_SIZE_LARGE "1024"
_set_default_value TILE_SIZE_SMALL "1024"
_set_default_value OVERLAP_FRACTION "0.10"
_set_default_value PREPROCESS_GAMMA "1.5"
_set_default_value MESMER_PREPROCESS_MODE "gamma-unsharp"
_set_default_value BACKGROUND_THRESHOLD "600"
_set_default_value MESMER_PAD_MODE "constant"
_set_default_value MESMER_STRICT_CHANNEL_NAMES "1"
_set_default_value WARMUP "1"

# ============================================================
# Step 2b: StarDist segmentation
# ============================================================
_set_project_path SIF_IMAGE_STARDIST "$(_pipeline_default_sif stardist)"
_set_default_value STARDIST_PYTHON_BIN "python3"

_set_default_value STARDIST_THREADS "8"
_set_default_value STARDIST_ROCM_BIND "/opt/rocm-6.3.4:/opt/rocm"
_set_project_path PY_SCRIPT_STARDIST "${SCRIPTS_DIR}/2-segmentation/stardist/run_stardist.py"
# StarDist is a nuclear-only model and must follow the same resolved nuclear
# channel as Mesmer. Use PIPELINE_NUCLEAR_CHANNEL_OVERRIDE for a manual choice.
export STARDIST_CHANNEL="${NUCLEAR_CHANNEL_RESOLVED:-${NUCLEAR_CHANNEL_AUTO:-0}}"
export STARDIST_CHANNEL_NAME="${NUCLEAR_CHANNEL_RESOLVED_NAME:-${NUCLEAR_CHANNEL_AUTO_NAME:-unknown}}"
_set_default_value STARDIST_MODEL "2D_versatile_fluo"
_set_default_value STARDIST_TARGET_TILE_EDGE "4096"
_set_default_value STARDIST_OOM_RETRIES "2"
_set_default_value STARDIST_REQUIRE_GPU "1"
_set_default_value STARDIST_STRICT_CHANNEL_NAMES "1"
_set_default_value STARDIST_MASK_COMPRESSION "none"
# Keep pretrained StarDist thresholds unchanged by default. Set these only for
# explicit QC experiments after visual comparison because higher thresholds can
# reduce false positives but also increase false negatives.
_set_default_value STARDIST_PROB_THRESH ""
_set_default_value STARDIST_NMS_THRESH ""

# ============================================================
# Step 3: Quantification
# ============================================================
_set_project_path SIF_IMAGE_QUANTIFICATION "$(_pipeline_default_sif quantification)"
_set_default_value QUANTIFICATION_PYTHON_BIN "/opt/conda/envs/quantification/bin/python"

_set_default_value QUANTIFICATION_THREADS "4"
_set_project_path PY_SCRIPT_QUANTIFICATION "${SCRIPTS_DIR}/3-quantification/quantification.py"

# ============================================================
# Step 4: Filtering + filtered-image quantification
# ============================================================
# Filtering is REQUIRED in this pipeline. Stale exported RUN_FILTERING=0 is ignored.
#
# TIFF outputs:
#   ${FILTERED_TIF_DIR}/<method>/<marker>/<sample>.ome_<marker>_tophat.tif
# CSV outputs:
#   ${FILTERED_CSV_DIR}/<method>/<sample>_filtered.csv
#
# Important:
#   There is intentionally no data/quantification_filtered directory.
#   Filtered CSVs belong under data/filter_images/csv/<method>/.

export RUN_FILTERING="${PIPELINE_RUN_FILTERING_OVERRIDE:-${PROJECT_DEFAULT_RUN_FILTERING}}"

# MARKERS_JSON is derived from CHANNELS_QUANTIFICATION_CSV above.
# Do not silently reuse stale PROJECT_DEFAULT_MARKERS_JSON from another dataset.
if [[ "${ALLOW_MARKERS_JSON_OVERRIDE}" == "1" && -n "${PIPELINE_MARKERS_JSON_OVERRIDE:-}" ]]; then
    export MARKERS_JSON="${PIPELINE_MARKERS_JSON_OVERRIDE}"
else
    export PIPELINE_MARKERS_JSON_OVERRIDE="${MARKERS_JSON}"
fi

_set_default_value TOPHAT_SIZE "10"
_set_default_value FILTER_CPUS "1"
_set_default_value QUANT_CPUS "4"
_set_default_value FILTER_USE_CONTAINER "1"
_set_project_path FILTER_SIF_IMAGE "$(_pipeline_default_sif quantification)"
_set_default_value FILTER_PYTHON_BIN "/opt/conda/envs/quantification/bin/python"
_set_project_path PY_SCRIPT_FILTER "${SCRIPTS_DIR}/4-filter_images/filter_image.py"

# ============================================================
# Folder creation
# ============================================================
if [[ "${CREATE_PIPELINE_DIRS_ON_SOURCE}" == "1" ]]; then
    _make_dir_safe "${BASE}"
    _make_dir_safe "${STATE_DIR}"
    _make_dir_safe "${SCRIPTS_DIR}"
    _make_dir_safe "${DATA_DIR}"

    # RAW_DIR is not auto-created; missing raw data should be visible.
    _make_dir_safe "${ILLUM_DIR}"
    _make_dir_safe "${STITCHED_DIR}"
    _make_dir_safe "${SEGMENTED_DIR}"
    _make_dir_safe "${QUANT_DIR}"
    _make_dir_safe "${FILTERED_DIR}"
    _make_dir_safe "${FILTERED_TIF_DIR}"
    _make_dir_safe "${FILTERED_CSV_DIR}"

    _make_dir_safe "${LOG_ROOT}"
    _make_dir_safe "${LOG_ILLUM_DIR}"
    _make_dir_safe "${LOG_STITCHING_DIR}"
    _make_dir_safe "${LOG_SEGMENTATION_DIR}"
    _make_dir_safe "${LOG_QUANTIFICATION_DIR}"
    _make_dir_safe "${LOG_FILTERING_DIR}"
    _make_dir_safe "${LOG_MESMER_DIR}"
    _make_dir_safe "${LOG_STARDIST_DIR}"
    _make_dir_safe "${SNAKEMAKE_SLURM_LOG_DIR}"
    _make_dir_safe "${DONE_DIR}"

    _make_dir_safe "${PIPELINE_TMP_DIR}"
    _make_dir_safe "${PIPELINE_CACHE_DIR}"
    _make_dir_safe "${XDG_CACHE_HOME}"
    _make_dir_safe "${XDG_CONFIG_HOME}"
    _make_dir_safe "${MPLCONFIGDIR}"
    _make_dir_safe "${NUMBA_CACHE_DIR}"
    _make_dir_safe "${PIP_CACHE_DIR}"
    _make_dir_safe "${APPTAINER_CACHEDIR}"
    _make_dir_safe "${KERAS_HOME}"
    _make_dir_safe "${DEEPCELL_CACHE_DIR}"
    _make_dir_safe "${MIOPEN_USER_DB_PATH}"
    _make_dir_safe "${MIOPEN_CUSTOM_CACHE_DIR}"
fi
