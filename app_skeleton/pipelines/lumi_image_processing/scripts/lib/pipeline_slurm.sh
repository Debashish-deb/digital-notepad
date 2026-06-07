#!/bin/bash
# ============================================================
# lib/pipeline_slurm.sh
#
# Validation, token handling, Snakemake/SLURM execution,
# doctor checks, and notification helpers.
#
# This file is sourced by run_pipeline.sh.
# Do NOT run this file directly.
# ============================================================

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "ERROR: Do not run lib/pipeline_slurm.sh directly."
    echo "Use: bash run_pipeline.sh"
    exit 1
fi

send_email() {
    local subject="$1"
    local body="$2"

    if [[ -n "${PIPELINE_EMAIL:-}" ]]; then
        echo -e "${body}" | mail -s "[Pipeline] ${subject}" "${PIPELINE_EMAIL}" || true
    fi
}

prompt_deepcell_token_always() {
    echo ""
    echo "Mesmer selected: DeepCell access token is required."
    echo "The token will be used only for this running pipeline session."
    echo "It will not be saved in pipeline_config.sh or printed to the log."
    echo ""

    unset DEEPCELL_ACCESS_TOKEN || true
    unset APPTAINERENV_DEEPCELL_ACCESS_TOKEN || true
    unset SINGULARITYENV_DEEPCELL_ACCESS_TOKEN || true

    if [[ ! -r /dev/tty ]]; then
        echo "ERROR: Cannot read DeepCell token interactively because /dev/tty is not available."
        echo "Please run this launcher in an interactive terminal:"
        echo "  bash run_pipeline.sh"
        exit 1
    fi

    local token=""

    while [[ -z "${token}" ]]; do
        printf "DeepCell access token: " > /dev/tty
        IFS= read -r -s token < /dev/tty
        printf "\n" > /dev/tty

        if [[ -z "${token}" ]]; then
            echo "Token cannot be empty. Please paste/type the token again." > /dev/tty
        elif [[ "${token}" == /* || "${token}" == *".log" || -f "${token}" ]]; then
            echo "ERROR: Entered token looks like a file path or log file: ${token}" > /dev/tty
            echo "Please copy and paste the correct DeepCell access token from https://users.deepcell.org." > /dev/tty
            token=""
        fi
    done

    export DEEPCELL_ACCESS_TOKEN="${token}"
    export APPTAINERENV_DEEPCELL_ACCESS_TOKEN="${token}"
    export SINGULARITYENV_DEEPCELL_ACCESS_TOKEN="${token}"

    echo "  └─ ✓ DeepCell token received for this run only."
    echo ""
}

load_snakemake_env() {
    if command -v module >/dev/null 2>&1; then
        module load "${CRAY_PYTHON_MODULE}"
    else
        echo "WARNING: module command not found; assuming ${CRAY_PYTHON_MODULE} is already available."
    fi

    if [[ ! -f "${SNAKEMAKE_VENV}" ]]; then
        echo "ERROR: Snakemake venv not found: ${SNAKEMAKE_VENV}"
        exit 1
    fi

    source "${SNAKEMAKE_VENV}"
}

validate_core_inputs() {
    local errors=0

    echo "Input/config check:"

    local n_raw=0
    if [[ ! -d "${RAW_DIR}" ]]; then
        echo "  - NOTE: RAW_DIR not found: ${RAW_DIR}"
    else
        n_raw=$(find "${RAW_DIR}" -mindepth 2 -maxdepth 2 -type f -iname "*.rcpnl" | wc -l)
    fi

    if [[ "${n_raw}" -lt 1 ]]; then
        # If the user explicitly disabled the stitching stage (via --only /
        # --from / --until), missing raw files is expected — don't prompt or
        # error, just continue. Downstream stages run from stitched outputs.
        if [[ "${RUN_STAGE_STITCHING:-1}" != "1" ]]; then
            local n_stitched_downstream=0
            if declare -F _count_stitched_present >/dev/null 2>&1; then
                n_stitched_downstream=$(_count_stitched_present 2>/dev/null || echo 0)
            fi
            if [[ "${n_stitched_downstream}" -gt 0 ]]; then
                echo "  - NOTE: No .rcpnl files under ${RAW_DIR}/<sample>/ — stitching stage disabled."
                echo "  - Detected ${n_stitched_downstream} stitched sample(s); continuing downstream."
                mkdir -p "${STATE_DIR}"
                touch "${STATE_DIR}/stitching_complete.flag" "${STATE_DIR}/stitching_approved.flag"
                echo ""
                return 0
            fi
            echo "  - ERROR: stitching stage disabled but no runnable stitched samples found."
            echo "    Expected: ${STITCHED_DIR}/<sample>/<sample>.ome.tif"
            errors=1
        fi

        # No raw inputs: see if stitched outputs already exist. If they do,
        # the user has likely already done illumination + stitching and just
        # wants to continue from there — ask to confirm instead of failing.
        local n_stitched=0
        if declare -F _count_stitched_present >/dev/null 2>&1; then
            n_stitched=$(_count_stitched_present 2>/dev/null || echo 0)
        fi

        if [[ "${n_stitched}" -gt 0 ]]; then
            echo "  - NOTE: No .rcpnl files under ${RAW_DIR}/<sample>/"
            echo "  - Detected ${n_stitched} existing stitched sample(s) in: ${STITCHED_DIR}"
            echo "    Illumination + stitching look already done."

            local skip_stitch="${SKIP_STITCHING_IF_NO_RAW:-}"
            if [[ -z "${skip_stitch}" ]]; then
                if [[ -t 0 ]]; then
                    read -p "    Skip illumination + stitching and continue from there? [Y/n] " -r
                    if [[ -z "${REPLY}" || "${REPLY}" =~ ^[Yy]$ ]]; then
                        skip_stitch=1
                    else
                        skip_stitch=0
                    fi
                else
                    # Non-interactive: default to skip (safe — outputs exist).
                    skip_stitch=1
                fi
            fi

            if [[ "${skip_stitch}" == "1" ]]; then
                mkdir -p "${STATE_DIR}"
                touch "${STATE_DIR}/stitching_complete.flag"
                touch "${STATE_DIR}/stitching_approved.flag"
                echo "  - Marked stitching as complete + approved from existing outputs."
            else
                echo "  - ERROR: No .rcpnl files found under ${RAW_DIR}/<sample>/ and user declined to skip."
                errors=1
            fi
        else
            echo "  - ERROR: No .rcpnl files found under ${RAW_DIR}/<sample>/"
            echo "    (no stitched outputs detected either — nothing to do)"
            errors=1
        fi
    else
        echo "  - Raw input OK: ${n_raw} .rcpnl files"
    fi

    [[ -f "${SCRIPTS_DIR}/Snakefile" ]] || {
        echo "  - ERROR: Snakefile not found: ${SCRIPTS_DIR}/Snakefile"
        errors=1
    }

    for f in \
        "${IJ_SCRIPT}" \
        "${PY_SCRIPT_STITCHING}" \
        "${PY_SCRIPT_MESMER}" \
        "${PY_SCRIPT_STARDIST}" \
        "${PY_SCRIPT_QUANTIFICATION}"
    do
        if [[ ! -f "${f}" ]]; then
            echo "  - WARNING: Script not found now: ${f}"
            echo "    This is only fatal if that stage/method is selected."
        fi
    done

    if [[ ! -f "${PY_SCRIPT_FILTER}" ]]; then
        echo "  - WARNING: Filter script not found now: ${PY_SCRIPT_FILTER}"
        echo "    This is fatal because filtering is required."
    fi

    if [[ "${errors}" -ne 0 ]]; then
        echo "Input/config check failed. Fix the errors above or edit pipeline_config.sh."
        exit 1
    fi

    echo ""
}

validate_method_inputs() {
    local method="$1"

    if [[ "${method}" == "mesmer" || "${method}" == "both" ]]; then
        [[ -n "${DEEPCELL_ACCESS_TOKEN:-}" ]] || {
            echo "ERROR: DeepCell token was not provided."
            exit 1
        }

        if [[ "${DEEPCELL_ACCESS_TOKEN}" == /* || "${DEEPCELL_ACCESS_TOKEN}" == *".log" || -f "${DEEPCELL_ACCESS_TOKEN}" ]]; then
            echo "ERROR: DeepCell token looks like a file path or log file: ${DEEPCELL_ACCESS_TOKEN}"
            echo "Please run the launcher again and paste the correct DeepCell access token from https://users.deepcell.org."
            exit 1
        fi

        [[ -f "${PY_SCRIPT_MESMER}" ]] || {
            echo "ERROR: Mesmer script not found: ${PY_SCRIPT_MESMER}"
            echo "  SCRIPTS_DIR=${SCRIPTS_DIR:-unset}"
            exit 1
        }

        [[ -f "${SIF_IMAGE_MESMER}" ]] || {
            echo "ERROR: Mesmer container not found: ${SIF_IMAGE_MESMER}"
            exit 1
        }
    fi

    if [[ "${method}" == "stardist" || "${method}" == "both" ]]; then
        [[ -f "${PY_SCRIPT_STARDIST}" ]] || {
            echo "ERROR: StarDist script not found: ${PY_SCRIPT_STARDIST}"
            exit 1
        }

        [[ -f "${SIF_IMAGE_STARDIST}" ]] || {
            echo "ERROR: StarDist container not found: ${SIF_IMAGE_STARDIST}"
            exit 1
        }
    fi
}

validate_quant_filter_inputs() {
    [[ -f "${CHANNEL_NAMES_FILE}" ]] || {
        echo "ERROR: Channel names file not found: ${CHANNEL_NAMES_FILE}"
        exit 1
    }

    [[ -f "${PY_SCRIPT_QUANTIFICATION}" ]] || {
        echo "ERROR: Quantification script not found: ${PY_SCRIPT_QUANTIFICATION}"
        exit 1
    }

    [[ -f "${SIF_IMAGE_QUANTIFICATION}" ]] || {
        echo "ERROR: Quantification container not found: ${SIF_IMAGE_QUANTIFICATION}"
        exit 1
    }

    # Filtering is optional.
    # Only validate filter script/container/MARKERS_JSON when RUN_FILTERING=1.
    if [[ "${RUN_FILTERING:-0}" == "1" ]]; then
        [[ -f "${PY_SCRIPT_FILTER}" ]] || {
            echo "ERROR: Filter script not found: ${PY_SCRIPT_FILTER}"
            exit 1
        }

        if [[ "${FILTER_USE_CONTAINER}" == "1" ]]; then
            [[ -f "${FILTER_SIF_IMAGE}" ]] || {
                echo "ERROR: Filter container not found: ${FILTER_SIF_IMAGE}"
                exit 1
            }
        fi

        python3 - <<'PY_MARKERS_JSON'
import json
import os
import sys

raw = os.environ.get("MARKERS_JSON", "").strip()

if not raw:
    print("ERROR: RUN_FILTERING=1 but MARKERS_JSON is empty.", file=sys.stderr)
    print("Example:", file=sys.stderr)
    print("  export MARKERS_JSON='{\"Ki67\":7,\"DNA1\":1,\"CD3\":4}'", file=sys.stderr)
    sys.exit(1)

try:
    markers = json.loads(raw)

    if not isinstance(markers, dict) or not markers:
        raise ValueError("MARKERS_JSON must be a non-empty JSON object")

    for key, value in markers.items():
        int(value)

except Exception as e:
    print(f"ERROR: Invalid MARKERS_JSON: {e}", file=sys.stderr)
    sys.exit(1)
PY_MARKERS_JSON
    fi
}

unlock_snakemake_workdir() {
    [[ "${AUTO_UNLOCK_SNAKEMAKE:-1}" == "1" ]] || return 0
    [[ -n "${SCRIPTS_DIR:-}" && -f "${SCRIPTS_DIR}/Snakefile" ]] || return 0
    echo "  ├─ Unlocking Snakemake workdir if needed..."

    # Keep Snakemake metadata in the same directory that the cleanup code
    # manages, regardless of where the user launched run_pipeline.sh from.
    local -a smk_workdir_args=(--directory "${SCRIPTS_DIR}" --snakefile "${SCRIPTS_DIR}/Snakefile")
    local lock_dir="${SCRIPTS_DIR}/.snakemake/locks"
    local lock_count=0
    local unlock_mode="${SNAKEMAKE_UNLOCK_MODE:-direct}"
    if [[ -d "${lock_dir}" ]]; then
        lock_count="$(find "${lock_dir}" -type f 2>/dev/null | wc -l | awk '{print $1}')"
    fi

    if [[ "${lock_count}" -eq 0 ]]; then
        rm -rf "${lock_dir}" 2>/dev/null || true
        return 0
    fi

    # Default to direct cleanup. Calling "snakemake --unlock" can hang during
    # Snakemake startup/plugin loading on LUMI, which blocks job submission
    # before any sbatch call is made. The launcher already cleans stale locks
    # only at run startup/exit/interrupt, and no SLURM jobs are cancelled here.
    if [[ "${unlock_mode}" == "direct" ]]; then
        echo "  │  Removing ${lock_count} stale Snakemake lock file(s) directly."
        rm -rf "${lock_dir}" 2>/dev/null || true
        return 0
    fi

    if [[ -n "${SNAKEMAKE_VENV:-}" && -f "${SNAKEMAKE_VENV}" ]]; then
        load_snakemake_env || return 0
    elif ! command -v snakemake >/dev/null 2>&1; then
        load_snakemake_env || return 0
    fi

    local unlock_timeout="${SNAKEMAKE_UNLOCK_TIMEOUT:-60}"
    local -a timeout_prefix=()
    if command -v timeout >/dev/null 2>&1; then
        timeout_prefix=(timeout "${unlock_timeout}s")
    else
        echo "  │  timeout command not found; removing stale Snakemake locks directly."
        rm -rf "${lock_dir}" 2>/dev/null || true
        return 0
    fi

    # Try unlocking via the humanizing/debug launcher first, falling back to direct snakemake.
    # The timeout prevents a stale Snakemake startup/query from blocking SLURM submission.
    if [[ -f "${SCRIPTS_DIR}/lib/snakemake_debug.py" ]]; then
        "${timeout_prefix[@]}" python3 "${SCRIPTS_DIR}/lib/snakemake_debug.py" "${smk_workdir_args[@]}" --unlock --quiet >/dev/null 2>&1 || \
        "${timeout_prefix[@]}" snakemake "${smk_workdir_args[@]}" --unlock --quiet >/dev/null 2>&1 || true
    else
        "${timeout_prefix[@]}" snakemake "${smk_workdir_args[@]}" --unlock --quiet >/dev/null 2>&1 || true
    fi

    # Robust fallback: remove the Snakemake locks directory directly if it still exists
    if [[ -d "${lock_dir}" ]]; then
        rm -rf "${lock_dir}"
    fi
}

print_live_rule_log_hint() {
    local target="$1"
    local hint

    if declare -F ui_live_hint_for_target >/dev/null 2>&1; then
        hint="$(ui_live_hint_for_target "${target}")"
    else
        hint="Detailed per-sample logs are under ${LOG_ROOT}"
    fi

    if declare -F ui_note >/dev/null 2>&1 && ui_enabled; then
        ui_note "${hint}"
    else
        echo "  │  ${hint}"
    fi
}

cancel_snakemake_slurm_jobs() {
    local smk_log="$1"
    local target="$2"

    [[ "${AUTO_SCANCEL_ON_SNAKEMAKE_FAILURE:-1}" == "1" ]] || return 0
    [[ -f "${smk_log}" ]] || return 0

    if ! command -v scancel >/dev/null 2>&1; then
        echo "  │  scancel not found; cannot cancel submitted SLURM jobs automatically."
        return 0
    fi

    local ids
    ids="$(
        { grep -Eo 'SLURM jobid [0-9]+|Submitted batch job [0-9]+' "${smk_log}" 2>/dev/null || true; } \
            | awk '{print $NF}' \
            | sort -u
    )"

    if [[ -z "${ids}" ]]; then
        echo "  │  No submitted SLURM job IDs found for ${target}; nothing to cancel."
        return 0
    fi

    echo "  │  Cancelling submitted SLURM job(s) for ${target}: $(echo "${ids}" | tr '\n' ' ')"
    # shellcheck disable=SC2086
    scancel ${ids} || true
}

_mesmer_direct_resource_plan() {
    local pending_file="$1"
    local override_mem="${MESMER_DIRECT_ARRAY_MEM_MB:-auto}"
    local override_runtime="${MESMER_DIRECT_RUNTIME_MIN:-auto}"

    awk \
        -v stitched_dir="${STITCHED_DIR}" \
        -v channel_count="${CHANNEL_COUNT:-0}" \
        -v override_mem="${override_mem}" \
        -v override_runtime="${override_runtime}" '
        function ceil(x) { return int(x) == x ? int(x) : int(x) + 1 }
        function round_mem_mb(value) { return ceil(value / 8000) * 8000 }
        BEGIN {
            max_mem = 64000
            max_runtime = 360
        }
        NF {
            sample = $0
            path = stitched_dir "/" sample "/" sample ".ome.tif"
            cmd = "stat -c %s \"" path "\" 2>/dev/null"
            cmd | getline bytes
            close(cmd)
            gib = (bytes + 0) / (1024 * 1024 * 1024)
            plane_gib = gib
            if ((channel_count + 0) > 0) {
                plane_gib = gib / (channel_count + 0)
            }

            mem = round_mem_mb(40000 + plane_gib * 12000)
            if (mem < 64000) mem = 64000
            if (mem > 240000) mem = 240000
            if (mem > max_mem) max_mem = mem

            runtime = int(240 + gib * 2.4)
            if (runtime < 360) runtime = 360
            if (runtime > 1440) runtime = 1440
            if (runtime > max_runtime) max_runtime = runtime
        }
        END {
            if (override_mem != "" && override_mem != "auto") {
                max_mem = override_mem + 0
            }
            if (override_runtime != "" && override_runtime != "auto") {
                max_runtime = override_runtime + 0
            }
            printf "%d %d\n", max_mem, max_runtime
        }
    ' "${pending_file}"
}

_minutes_to_slurm_time() {
    local minutes="$1"
    local hours=$((minutes / 60))
    local mins=$((minutes % 60))
    printf "%02d:%02d:00" "${hours}" "${mins}"
}

run_mesmer_direct_slurm() {
    local stage_name="$1"
    local target="$2"
    local jobs="$3"

    local friendly_line friendly_title friendly_blurb
    friendly_line="$(ui_friendly_stage_for_target "${target}" 2>/dev/null || echo "${stage_name}|")"
    friendly_title="${friendly_line%%|*}"
    friendly_blurb="${friendly_line#*|}"

    if declare -F ui_section >/dev/null 2>&1 && ui_enabled; then
        ui_section "Now running" "${friendly_title}"
        [[ -n "${friendly_blurb}" ]] && ui_note "${friendly_blurb}"
    else
        echo "  ├─ Running ${stage_name}..."
    fi

    local start_time
    start_time=$(date +%s)

    mkdir -p "${LOG_ROOT}" "${SNAKEMAKE_SLURM_LOG_DIR}" "${LOG_MESMER_DIR}" "${STATE_DIR}"

    local run_stamp pending_file array_log_dir array_script
    run_stamp="$(date +%Y%m%d_%H%M%S)"
    pending_file="${STATE_DIR}/mesmer_direct_samples_${run_stamp}.txt"
    array_log_dir="${LOG_ROOT}/slurm_mesmer_direct_${run_stamp}"
    array_script="${STATE_DIR}/mesmer_direct_array_${run_stamp}.sh"
    mkdir -p "${array_log_dir}"

    local sample n_pending=0
    while IFS= read -r sample; do
        [[ -n "${sample}" ]] || continue
        if ! mesmer_sample_complete "${sample}"; then
            printf '%s\n' "${sample}" >> "${pending_file}"
            n_pending=$((n_pending + 1))
        fi
    done < <(sample_list)

    if [[ "${n_pending}" -eq 0 ]]; then
        ui_stage_done "${friendly_title:-${stage_name}}" "0h 0m"
        ui_path "All requested Mesmer masks already exist: ${SEGMENTED_DIR}/mesmer"
        return 0
    fi

    if [[ "${jobs}" == "auto" || -z "${jobs}" || "${jobs}" -lt 1 ]]; then
        jobs="${MESMER_JOBS:-1}"
    fi

    local threads="${MESMER_THREADS:-8}"
    local partition="${SLURM_PARTITION_GPU:-small-g}"
    local gpu_gres="${MESMER_GPU_GRES:-gpu:mi250:1}"
    local mem_mb runtime_min slurm_time
    read -r mem_mb runtime_min < <(_mesmer_direct_resource_plan "${pending_file}")
    slurm_time="$(_minutes_to_slurm_time "${runtime_min}")"

    echo "  ├─ Direct Mesmer SLURM array: ${n_pending} sample(s), up to ${jobs} running at once."
    echo "  ├─ Resources per sample: ${threads} CPU, ${mem_mb} MB, ${gpu_gres}, ${slurm_time} on ${partition}."
    echo "  ├─ Array logs: ${array_log_dir}/<array_job>_<task>.out"

    cat > "${array_script}" <<EOF
#!/usr/bin/env bash
#SBATCH --account=${SLURM_ACCOUNT}
#SBATCH --partition=${partition}
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=${threads}
#SBATCH --mem=${mem_mb}M
#SBATCH --time=${slurm_time}
#SBATCH --gres=${gpu_gres}
#SBATCH --job-name=mesmer_direct
#SBATCH --output=${array_log_dir}/%A_%a.out
#SBATCH --error=${array_log_dir}/%A_%a.out

set -euo pipefail

cd "${SCRIPTS_DIR}"

DEEPCELL_TOKEN_FOR_JOB="\${DEEPCELL_ACCESS_TOKEN:-}"
APPTAINER_DEEPCELL_TOKEN_FOR_JOB="\${APPTAINERENV_DEEPCELL_ACCESS_TOKEN:-}"
SINGULARITY_DEEPCELL_TOKEN_FOR_JOB="\${SINGULARITYENV_DEEPCELL_ACCESS_TOKEN:-}"

source "${SCRIPTS_DIR}/pipeline_config.sh"
source "${SCRIPTS_DIR}/lib/pipeline_state.sh"
source "${SCRIPTS_DIR}/lib/pipeline_slurm.sh"

if [[ -n "\${DEEPCELL_TOKEN_FOR_JOB}" ]]; then
    export DEEPCELL_ACCESS_TOKEN="\${DEEPCELL_TOKEN_FOR_JOB}"
    export APPTAINERENV_DEEPCELL_ACCESS_TOKEN="\${APPTAINER_DEEPCELL_TOKEN_FOR_JOB:-\${DEEPCELL_TOKEN_FOR_JOB}}"
    export SINGULARITYENV_DEEPCELL_ACCESS_TOKEN="\${SINGULARITY_DEEPCELL_TOKEN_FOR_JOB:-\${DEEPCELL_TOKEN_FOR_JOB}}"
fi

sample="\$(sed -n "\$((SLURM_ARRAY_TASK_ID + 1))p" "${pending_file}")"
if [[ -z "\${sample}" ]]; then
    echo "No sample found for SLURM_ARRAY_TASK_ID=\${SLURM_ARRAY_TASK_ID}" >&2
    exit 2
fi

echo "[\$(date '+%Y-%m-%d %H:%M:%S')] Mesmer direct task starting: \${sample}"
echo "Node: \$(hostname)"
echo "Workdir: \$(pwd)"

echo "[\$(date '+%Y-%m-%d %H:%M:%S')] Loading Snakemake environment"
load_snakemake_env
echo "[\$(date '+%Y-%m-%d %H:%M:%S')] Snakemake executable: \$(command -v snakemake)"

echo "[\$(date '+%Y-%m-%d %H:%M:%S')] Resolving Mesmer output targets"
mapfile -t targets < <(mesmer_required_mask_paths_for_sample "\${sample}")
if [[ "\${#targets[@]}" -lt 1 ]]; then
    echo "No Mesmer targets resolved for \${sample}" >&2
    exit 2
fi

for target_path in "\${targets[@]}"; do
    printf '[%s] Target: %s\n' "\$(date '+%Y-%m-%d %H:%M:%S')" "\${target_path}"
done
echo "[\$(date '+%Y-%m-%d %H:%M:%S')] Running local Snakemake Mesmer rule"

TASK_SNAKEMAKE_DIR="${PIPELINE_TMP_DIR}/snakemake_mesmer_\${SLURM_JOB_ID:-manual}_\${SLURM_ARRAY_TASK_ID:-0}"
rm -rf "\${TASK_SNAKEMAKE_DIR}"
mkdir -p "\${TASK_SNAKEMAKE_DIR}"
echo "[\$(date '+%Y-%m-%d %H:%M:%S')] Snakemake metadata dir: \${TASK_SNAKEMAKE_DIR}"

PYTHONUNBUFFERED=1 snakemake \
    --directory "\${TASK_SNAKEMAKE_DIR}" \
    --snakefile "${SCRIPTS_DIR}/Snakefile" \
    --cores "${threads}" \
    --local-cores "${threads}" \
    --jobs 1 \
    --nolock \
    --latency-wait "${LATENCY_WAIT}" \
    --rerun-incomplete \
    --printshellcmds \
    --show-failed-logs \
    "\${targets[@]}"

echo "[\$(date '+%Y-%m-%d %H:%M:%S')] Mesmer direct task finished: \${sample}"
EOF
    chmod +x "${array_script}"

    local array_max=$((n_pending - 1))
    local submit_out array_job
    submit_out="$(sbatch --parsable --array="0-${array_max}%${jobs}" --export=ALL,DEEPCELL_ACCESS_TOKEN,APPTAINERENV_DEEPCELL_ACCESS_TOKEN,SINGULARITYENV_DEEPCELL_ACCESS_TOKEN "${array_script}")"
    array_job="${submit_out%%;*}"

    echo "  ├─ Submitted Mesmer array job: ${array_job}"
    echo "  ├─ Watch queue: squeue -r -j ${array_job}"
    echo ""

    while squeue -h -j "${array_job}" >/dev/null 2>&1 && [[ -n "$(squeue -h -j "${array_job}" 2>/dev/null)" ]]; do
        local running pending completing completed failed
        running="$(squeue -h -r -j "${array_job}" -t R 2>/dev/null | wc -l | tr -d ' ')"
        pending="$(squeue -h -r -j "${array_job}" -t PD 2>/dev/null | wc -l | tr -d ' ')"
        completing="$(squeue -h -r -j "${array_job}" -t CG 2>/dev/null | wc -l | tr -d ' ')"
        read -r completed failed < <(
            sacct -X -n -P -j "${array_job}" --format=JobIDRaw,State 2>/dev/null \
                | awk -F'|' -v parent="${array_job}" '
                    $1 != parent && $2 ~ /^COMPLETED/ { completed++ }
                    $1 != parent && $2 ~ /^(FAILED|CANCELLED|TIMEOUT|OUT_OF_MEMORY|NODE_FAIL)/ { failed++ }
                    END { printf "%d %d\n", completed + 0, failed + 0 }
                '
        )
        echo "  ├─ Mesmer array ${array_job}: ${running} running, ${pending} pending, ${completing} completing, ${completed} completed, ${failed} failed"
        sleep 30
    done

    local failed=0
    while IFS= read -r sample; do
        [[ -n "${sample}" ]] || continue
        if ! mesmer_sample_complete "${sample}"; then
            echo "  ├─ ✗ Missing Mesmer output after array finished: ${sample}"
            failed=1
        fi
    done < "${pending_file}"

    echo "  ├─ SLURM accounting summary:"
    sacct -j "${array_job}" --format=JobID,State,ExitCode,Elapsed,NodeList%24 -P 2>/dev/null | sed 's/^/  │  /' || true

    local end_time duration hours mins
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    hours=$((duration / 3600))
    mins=$(((duration % 3600) / 60))

    if [[ "${failed}" -ne 0 ]]; then
        ui_stage_fail "${friendly_title:-${stage_name}}" "after ${hours}h ${mins}m — see ${array_log_dir}"
        ui_path "${array_log_dir}"
        exit 1
    fi

    touch "${STATE_DIR}/segmentation_mesmer_complete.flag"
    ui_stage_done "${friendly_title:-${stage_name}}" "${hours}h ${mins}m"
    ui_path "Array logs: ${array_log_dir}"
}

run_snakemake() {
    local stage_name="$1"
    local target="$2"
    local jobs="$3"
    local stage_kind="$4"

    if [[ "${target}" == "stage_segmentation_mesmer" && "${MESMER_SUBMISSION_MODE:-direct}" == "direct" ]]; then
        run_mesmer_direct_slurm "${stage_name}" "${target}" "${jobs}"
        return 0
    fi

    local partition="${SLURM_PARTITION_CPU:-small}"

    if [[ "${stage_kind}" == "gpu" ]]; then
        partition="${SLURM_PARTITION_GPU:-small-g}"
    fi

    local friendly_line friendly_title friendly_blurb
    friendly_line="$(ui_friendly_stage_for_target "${target}" 2>/dev/null || echo "${stage_name}|")"
    friendly_title="${friendly_line%%|*}"
    friendly_blurb="${friendly_line#*|}"

    if declare -F ui_section >/dev/null 2>&1 && ui_enabled; then
        ui_section "Now running" "${friendly_title}"
        [[ -n "${friendly_blurb}" ]] && ui_note "${friendly_blurb}"
    else
        echo "  ├─ Running ${stage_name}..."
    fi

    local start_time
    start_time=$(date +%s)

    mkdir -p "${LOG_ROOT}" "${SNAKEMAKE_SLURM_LOG_DIR}"

    local smk_log="${LOG_ROOT}/snakemake_${target}_$(date +%Y%m%d_%H%M%S).log"

    print_live_rule_log_hint "${target}"
    ui_snakemake_intro "${friendly_title}" "${jobs}" "${smk_log}" \
        "Watch below for plain-language progress per sample."

    echo "  ├─ Loading workflow engine..."

    load_snakemake_env

    if ui_verbose; then
        echo "  ├─ Python      : $(which python)"
        echo "  ├─ Snakemake   : $(which snakemake)"
        echo "  ├─ Version     : $(timeout 20s snakemake --version 2>/dev/null || echo unavailable)"
        echo "  ├─ Snakefile   : ${SCRIPTS_DIR}/Snakefile"
        echo "  ├─ Target      : ${target}"
        echo "  ├─ Partition   : ${partition}"
        echo "  ├─ Jobs        : ${jobs}"
    fi

    ui_blank

    send_email "Started: ${stage_name}" "Target: ${target}\nJobs: ${jobs}\nPartition: ${partition}\nLog: ${smk_log}\nTime: $(date)"

    local -a slurm_log_args=()
    if timeout 20s snakemake --help 2>&1 | grep -q -- "--slurm-logdir"; then
        slurm_log_args=(--slurm-logdir "${SNAKEMAKE_SLURM_LOG_DIR}")
    else
        echo "  ├─ WARNING: This Snakemake/SLURM plugin does not expose --slurm-logdir."
        echo "  │  Executor logs may appear later under ${SCRIPTS_DIR}/.snakemake/slurm_logs."
        echo "  │  For live progress, tail the per-sample/per-job logs shown above."
    fi

    local -a envvar_args=()
    if [[ "${target}" == "stage_segmentation_mesmer" ]]; then
        envvar_args=(
            --envvars
            DEEPCELL_ACCESS_TOKEN
            APPTAINERENV_DEEPCELL_ACCESS_TOKEN
            SINGULARITYENV_DEEPCELL_ACCESS_TOKEN
            MESMER_COMPARTMENT
            NUCLEAR_CHANNEL
            MEMBRANE_CHANNEL
            SEGMENTATION_METHOD
            PIPELINE_SEGMENTATION_METHOD
        )
    fi

    # ── Stale-metadata cleanup ──────────────────────────────────
    # After a failed SLURM run, .snakemake/incomplete/ and the SLURM
    # executor's job-tracking state can cause the executor to silently
    # hang when it tries to re-submit. Cleaning these stale markers
    # lets --rerun-incomplete rediscover incomplete outputs from the
    # actual filesystem instead of relying on (potentially corrupt)
    # cached state.
    local smk_meta_dir="${SCRIPTS_DIR}/.snakemake"
    if [[ -d "${smk_meta_dir}/incomplete" ]]; then
        local n_stale
        n_stale="$(find "${smk_meta_dir}/incomplete" -type f 2>/dev/null | wc -l)"
        if [[ "${n_stale}" -gt 0 ]]; then
            echo "  ├─ Cleaning ${n_stale} stale incomplete-output marker(s) from .snakemake/"
            rm -rf "${smk_meta_dir}/incomplete"
        fi
    fi

    # Also remove stale SLURM executor job state from previous failed runs
    # so the executor doesn't hang trying to query dead job IDs via squeue/sacct.
    if [[ -d "${smk_meta_dir}/slurm_jobs" ]]; then
        echo "  ├─ Cleaning stale SLURM job tracking state from .snakemake/"
        rm -rf "${smk_meta_dir}/slurm_jobs"
    fi

    # Unconditionally unlock the Snakemake working directory before starting
    # to clean up any stale locks left by previously aborted or crashed runs.
    unlock_snakemake_workdir
    # ────────────────────────────────────────────────────────────

    set +e

    trap 'echo "  ├─ Interrupted; cancelling submitted SLURM jobs for current Snakemake run..."; cancel_snakemake_slurm_jobs "${smk_log}" "${target}"; unlock_snakemake_workdir; exit 130' INT TERM

    # IMPORTANT:
    # Put the Snakemake target before --envvars.
    # Otherwise --envvars can accidentally consume the target name as an env var.
    export PIPELINE_FRIENDLY_LOG="${PIPELINE_FRIENDLY_LOG:-1}"
    export PIPELINE_VERBOSE_LOG="${PIPELINE_VERBOSE_LOG:-0}"

    # Friendly mode: technical Snakemake output → log file only; live panel → terminal.
    if ui_verbose; then
        PYTHONUNBUFFERED=1 python3 "${SCRIPTS_DIR}/lib/snakemake_debug.py" \
            --directory "${SCRIPTS_DIR}" \
            --snakefile "${SCRIPTS_DIR}/Snakefile" \
            --executor slurm \
            --scheduler greedy \
            --jobs "${jobs}" \
            --local-cores "${LOCAL_CORES:-2}" \
            --default-resources slurm_account="${SLURM_ACCOUNT}" slurm_partition="${partition}" \
            --latency-wait "${LATENCY_WAIT}" \
            --restart-times "${RESTART_TIMES}" \
            --max-jobs-per-second "${MAX_JOBS_PER_SECOND}" \
            --keep-going \
            --rerun-incomplete \
            --printshellcmds \
            --show-failed-logs \
            "${slurm_log_args[@]}" \
            "${target}" \
            "${envvar_args[@]}" \
            2>&1 | tee "${smk_log}"
    else
        PYTHONUNBUFFERED=1 python3 "${SCRIPTS_DIR}/lib/snakemake_debug.py" \
            --directory "${SCRIPTS_DIR}" \
            --snakefile "${SCRIPTS_DIR}/Snakefile" \
            --executor slurm \
            --scheduler greedy \
            --jobs "${jobs}" \
            --local-cores "${LOCAL_CORES:-2}" \
            --default-resources slurm_account="${SLURM_ACCOUNT}" slurm_partition="${partition}" \
            --latency-wait "${LATENCY_WAIT}" \
            --restart-times "${RESTART_TIMES}" \
            --max-jobs-per-second "${MAX_JOBS_PER_SECOND}" \
            --keep-going \
            --rerun-incomplete \
            "${slurm_log_args[@]}" \
            "${target}" \
            "${envvar_args[@]}" \
            >>"${smk_log}" \
            2> >(tee -a "${smk_log}" >&2)
    fi

    local smk_exit=${PIPESTATUS[0]}

    trap - INT TERM

    set -e

    unlock_snakemake_workdir

    local end_time
    end_time=$(date +%s)

    local duration=$((end_time - start_time))
    local hours=$((duration / 3600))
    local mins=$(((duration % 3600) / 60))

    if [[ ${smk_exit} -ne 0 ]]; then
        ui_stage_fail "${friendly_title:-${stage_name}}" "after ${hours}h ${mins}m — see log for details"
        ui_path "${smk_log}"
        cancel_snakemake_slurm_jobs "${smk_log}" "${target}"
        send_email "FAILED: ${stage_name}" "Target: ${target} failed.\nLog: ${smk_log}"
        exit 1
    fi

    ui_stage_done "${friendly_title:-${stage_name}}" "${hours}h ${mins}m"
    ui_path "Full log: ${smk_log}"
    send_email "Completed: ${stage_name}" "Target: ${target} finished successfully in ${hours}h ${mins}m.\nLog: ${smk_log}"
}

doctor() {
    ensure_pipeline_dirs
    print_summary

    echo "Pipeline doctor"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    local errors=0

    for cmd in find awk sed grep tee date python3; do
        if command -v "${cmd}" >/dev/null 2>&1; then
            echo "  ✓ command: ${cmd}"
        else
            echo "  ✗ missing command: ${cmd}"
            errors=1
        fi
    done

    [[ -f "${SCRIPTS_DIR}/Snakefile" ]] \
        && echo "  ✓ Snakefile found" \
        || { echo "  ✗ Snakefile missing: ${SCRIPTS_DIR}/Snakefile"; errors=1; }

    [[ -f "${SNAKEMAKE_VENV}" ]] \
        && echo "  ✓ Snakemake venv found" \
        || { echo "  ✗ Snakemake venv missing: ${SNAKEMAKE_VENV}"; errors=1; }

    for d in "${RAW_DIR}" "${LOG_ROOT}" "${PIPELINE_TMP_DIR}" "${PIPELINE_CACHE_DIR}"; do
        if [[ -d "${d}" && -w "${d}" ]]; then
            echo "  ✓ writable: ${d}"
        else
            echo "  ✗ not writable/missing: ${d}"
            errors=1
        fi
    done

    if [[ "${DATASET_RAW_FILES:-0}" -lt 1 ]]; then
        echo "  ✗ no .rcpnl files found"
        errors=1
    else
        echo "  ✓ raw files found: ${DATASET_RAW_FILES}"
    fi

    for f in \
        "${SIF_IMAGE_ILLUMINATION}" \
        "${SIF_IMAGE_STITCHING}" \
        "${SIF_IMAGE_MESMER}" \
        "${SIF_IMAGE_STARDIST}" \
        "${SIF_IMAGE_QUANTIFICATION}"
    do
        [[ -f "${f}" ]] \
            && echo "  ✓ container: ${f}" \
            || echo "  ⚠ container not found now: ${f}"
    done

    if [[ "${RUN_FILTERING:-0}" == "1" ]]; then
        [[ -f "${FILTER_SIF_IMAGE}" ]] \
            && echo "  ✓ filter container: ${FILTER_SIF_IMAGE}" \
            || echo "  ⚠ filter container not found now: ${FILTER_SIF_IMAGE}"

        [[ -n "${MARKERS_JSON:-}" ]] \
            && echo "  ✓ MARKERS_JSON configured" \
            || { echo "  ✗ RUN_FILTERING=1 but MARKERS_JSON is empty"; errors=1; }
    else
        echo "  ✓ filtering disabled: RUN_FILTERING=${RUN_FILTERING:-0}"
    fi

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if [[ "${errors}" -ne 0 ]]; then
        echo "Doctor found problems. Fix them before running."
        exit 1
    fi

    echo "Doctor check passed."
}

# ============================================================
# Stage-aware validation overrides
# These make single-stage and partial runs possible without requiring inputs
# from stages that are not selected.
# ============================================================

validate_selected_stage_inputs() {
    local errors=0

    echo "Selected-stage input check:"
    echo "  - Selected stages : $(selected_stage_label 2>/dev/null || echo unknown)"

    if declare -F normalize_stitched_layout >/dev/null 2>&1; then
        normalize_stitched_layout || true
    fi

    local n_raw=0 n_stitched=0 n_samples=0
    n_raw=$(raw_file_total_count 2>/dev/null || echo 0)
    n_stitched=$(stitched_sample_count 2>/dev/null || echo 0)
    n_samples=$(count_samples 2>/dev/null || echo 0)

    echo "  - Runnable samples : ${n_samples}"
    echo "  - Raw .rcpnl files : ${n_raw}"
    echo "  - Stitched images  : ${n_stitched}"

    # ------------------------------------------------------------
    # Stage 1 validation
    # ------------------------------------------------------------
    # Stage 1 genuinely needs raw .rcpnl files unless stitching is already
    # complete from existing stitched outputs. This allows the default/full
    # launcher to resume from stitched data when RAW_DIR is intentionally empty.
    if [[ "${RUN_STAGE_STITCHING:-1}" == "1" ]]; then
        if [[ ! -f "${STATE_DIR}/stitching_complete.flag" && "${n_raw}" -lt 1 ]]; then
            if [[ "${n_stitched}" -gt 0 ]]; then
                echo "  - NOTE: Stage 1 selected, but stitched outputs already exist."
                echo "    Marking stitching complete/approved from existing OME-TIFFs."
                mkdir -p "${STATE_DIR}"
                touch "${STATE_DIR}/stitching_complete.flag" "${STATE_DIR}/stitching_approved.flag"
            else
                echo "  - ERROR: Stage 1 selected but no raw .rcpnl files were found."
                echo "    Expected: ${RAW_DIR}/<sample>/*.rcpnl"
                errors=1
            fi
        fi
    fi

    # ------------------------------------------------------------
    # Stage 2 validation
    # ------------------------------------------------------------
    # Segmentation needs stitched OME-TIFFs only. It must not require raw data.
    if [[ "${RUN_STAGE_SEGMENTATION:-0}" == "1" ]]; then
        if [[ "${RUN_STAGE_STITCHING:-1}" == "0" && "${n_stitched}" -lt 1 ]]; then
            echo "  - ERROR: Segmentation selected but no stitched OME-TIFFs were found."
            echo "    Expected: ${STITCHED_DIR}/<sample>/<sample>.ome.tif"
            errors=1
        fi

        # Important fix:
        # If segmentation is selected but segmentation_method.txt is missing,
        # do NOT fail here. Stage 2 is the place where the method is configured.
        # Also clear stale segmentation flags if they exist without a method,
        # otherwise run_stage_2_segmentation() may return early and stage 3
        # will later fail trying to read segmentation_method.txt.
        if [[ ! -f "${STATE_DIR}/segmentation_method.txt" ]]; then
            local inferred_method=""
            if declare -F infer_method_from_outputs >/dev/null 2>&1; then
                inferred_method="$(infer_method_from_outputs || true)"
            fi

            if [[ -n "${inferred_method}" ]]; then
                echo "${inferred_method}" > "${STATE_DIR}/segmentation_method.txt"
                echo "  - Inferred segmentation method from existing masks: ${inferred_method}"
            else
                if [[ -f "${STATE_DIR}/segmentation_complete.flag" || -f "${STATE_DIR}/segmentation_approved.flag" ]]; then
                    echo "  - NOTE: segmentation flags existed, but segmentation_method.txt was missing."
                    echo "    Clearing stale segmentation flags so Stage 2 can ask for method again."
                    rm -f "${STATE_DIR}/segmentation_complete.flag" "${STATE_DIR}/segmentation_approved.flag"
                fi
                echo "  - NOTE: Segmentation method is not configured yet."
                echo "    Stage 2 will ask Mesmer / StarDist / Both when it starts."
            fi
        fi
    fi

    # ------------------------------------------------------------
    # Stage 3 validation
    # ------------------------------------------------------------
    # Stage 3 only needs method/mask validation when Stage 3 is the first
    # reachable downstream stage in this invocation. If segmentation is selected
    # in the same run, we must defer method/mask validation because Stage 2 may
    # configure or regenerate segmentation before Stage 3 is reached.
    if [[ "${RUN_STAGE_QUANT_FILTER:-0}" == "1" ]]; then
        if [[ "${RUN_STAGE_STITCHING:-1}" == "0" && "${n_stitched}" -lt 1 ]]; then
            echo "  - ERROR: Quantification/filtering selected but no stitched OME-TIFFs were found."
            echo "    Expected: ${STITCHED_DIR}/<sample>/<sample>.ome.tif"
            errors=1
        fi

        if [[ "${RUN_STAGE_SEGMENTATION:-0}" == "1" ]]; then
            echo "  - NOTE: Stage 3 selected, but segmentation is also selected."
            echo "    Deferring segmentation-method and mask validation until Stage 3 is actually reached."
        else
            # Direct stage-3 run: --only quantification, --only filtering,
            # --from quantification, or --from filtering. Here method and masks
            # must already exist because segmentation will not run.
            if [[ ! -f "${STATE_DIR}/segmentation_method.txt" ]]; then
                local inferred_method=""
                if declare -F infer_method_from_outputs >/dev/null 2>&1; then
                    inferred_method="$(infer_method_from_outputs || true)"
                fi
                if [[ -n "${inferred_method}" ]]; then
                    echo "${inferred_method}" > "${STATE_DIR}/segmentation_method.txt"
                    echo "  - Inferred segmentation method from existing masks: ${inferred_method}"
                fi
            fi

            if [[ ! -f "${STATE_DIR}/segmentation_method.txt" ]]; then
                echo "  - ERROR: Stage 3 selected directly, but segmentation method is unknown."
                echo "    Create one of these before running Stage 3 directly:"
                echo "      echo mesmer   > ${STATE_DIR}/segmentation_method.txt"
                echo "      echo stardist > ${STATE_DIR}/segmentation_method.txt"
                echo "      echo both     > ${STATE_DIR}/segmentation_method.txt"
                errors=1
            else
                local method
                method="$(cat "${STATE_DIR}/segmentation_method.txt" | tr '[:upper:]' '[:lower:]' | xargs)"
                case "${method}" in
                    mesmer|stardist|both)
                        echo "${method}" > "${STATE_DIR}/segmentation_method.txt"
                        if ! method_segmentation_complete "${method}"; then
                            echo "  - ERROR: Stage 3 selected directly, but segmentation masks are incomplete for method: ${method}"
                            echo "    Expected under: ${SEGMENTED_DIR}/<method>/"
                            errors=1
                        fi
                        ;;
                    *)
                        echo "  - ERROR: Invalid segmentation method: ${method}"
                        errors=1
                        ;;
                esac
            fi
        fi
    fi

    if [[ "${errors}" -ne 0 ]]; then
        echo ""
        echo "Selected-stage input check failed. No SLURM jobs were submitted."
        echo "Run: bash run_pipeline.sh --status"
        exit 1
    fi

    echo "  └─ ✓ Selected-stage inputs OK"
    echo ""
}

validate_quant_filter_inputs() {
    # Quantification inputs are required only when quantification is selected.
    if [[ "${RUN_SUBSTAGE_QUANT:-1}" == "1" ]]; then
        [[ -f "${CHANNEL_NAMES_FILE}" ]] || {
            echo "ERROR: Channel names file not found: ${CHANNEL_NAMES_FILE}"
            exit 1
        }

        [[ -f "${PY_SCRIPT_QUANTIFICATION}" ]] || {
            echo "ERROR: Quantification script not found: ${PY_SCRIPT_QUANTIFICATION}"
            exit 1
        }

        [[ -f "${SIF_IMAGE_QUANTIFICATION}" ]] || {
            echo "ERROR: Quantification container not found: ${SIF_IMAGE_QUANTIFICATION}"
            exit 1
        }
    else
        echo "  ├─ Quantification input validation skipped — quantification not selected."
    fi

    # Filtering validation is required only when filtering is selected.
    if [[ "${RUN_SUBSTAGE_FILTER:-1}" == "1" ]]; then
        [[ -f "${PY_SCRIPT_FILTER}" ]] || {
            echo "ERROR: Filter script not found: ${PY_SCRIPT_FILTER}"
            exit 1
        }

        if [[ "${FILTER_USE_CONTAINER}" == "1" ]]; then
            [[ -f "${FILTER_SIF_IMAGE}" ]] || {
                echo "ERROR: Filter container not found: ${FILTER_SIF_IMAGE}"
                exit 1
            }
        fi

        python3 - <<'PY_MARKERS_JSON'
import json
import os
import sys

raw = os.environ.get("MARKERS_JSON", "").strip()
if not raw:
    print("ERROR: filtering selected but MARKERS_JSON is empty.", file=sys.stderr)
    print("Example:", file=sys.stderr)
    print("  export MARKERS_JSON='{\"Ki67\":7,\"DNA1\":1,\"CD3\":4}'", file=sys.stderr)
    sys.exit(1)
try:
    markers = json.loads(raw)
    if not isinstance(markers, dict) or not markers:
        raise ValueError("MARKERS_JSON must be a non-empty JSON object")
    for _, value in markers.items():
        int(value)
except Exception as e:
    print(f"ERROR: Invalid MARKERS_JSON: {e}", file=sys.stderr)
    sys.exit(1)
PY_MARKERS_JSON
    else
        echo "  ├─ Filtering input validation skipped — filtering not selected."
    fi
}
