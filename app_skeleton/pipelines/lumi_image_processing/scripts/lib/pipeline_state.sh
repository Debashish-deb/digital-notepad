#!/bin/bash
# ============================================================
# lib/pipeline_state.sh
#
# State, filesystem, sample discovery, output detection,
# planning, cleanup, and summary helpers.
#
# This file is sourced by run_pipeline.sh.
# Do NOT run this file directly.
# ============================================================

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "ERROR: Do not run lib/pipeline_state.sh directly."
    echo "Use: bash run_pipeline.sh"
    exit 1
fi

_is_truthy() {
    case "${1:-0}" in
        1|true|TRUE|yes|YES|y|Y|on|ON)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

filtering_enabled() {
    _is_truthy "${RUN_FILTERING:-0}"
}

log_header() {
    clear || true
    if declare -F ui_title >/dev/null 2>&1 && ui_enabled; then
        ui_title "${PIPELINE_TITLE:-Microscopy image processing pipeline}"
        ui_note "Started: $(date '+%Y-%m-%d %H:%M:%S')"
    else
        echo "  ${PIPELINE_TITLE}"
        echo "  Started: $(date '+%Y-%m-%d %H:%M:%S')"
    fi
}

ensure_pipeline_dirs() {
    echo "Ensuring required folders exist..."

    mkdir -p \
        "${STATE_DIR}" \
        "${LOG_ROOT}" \
        "${SNAKEMAKE_SLURM_LOG_DIR}" \
        "${DONE_DIR}" \
        "${DATA_DIR}" \
        "${RAW_DIR}" \
        "${ILLUM_DIR}" \
        "${STITCHED_DIR}" \
        "${SEGMENTED_DIR}" \
        "${QUANT_DIR}" \
        "${FILTERED_DIR}" \
        "${FILTERED_CSV_DIR}" \
        "${PIPELINE_TMP_DIR}" \
        "${PIPELINE_CACHE_DIR}" \
        "${XDG_CACHE_HOME}" \
        "${XDG_CONFIG_HOME}" \
        "${MPLCONFIGDIR}" \
        "${NUMBA_CACHE_DIR}" \
        "${PIP_CACHE_DIR}" \
        "${APPTAINER_CACHEDIR}" \
        "${KERAS_HOME}" \
        "${DEEPCELL_CACHE_DIR}" \
        "${MIOPEN_USER_DB_PATH}" \
        "${MIOPEN_CUSTOM_CACHE_DIR}" \
        "${LOG_ROOT}/illumination" \
        "${LOG_ROOT}/stitching" \
        "${LOG_ROOT}/segmentation/mesmer" \
        "${LOG_ROOT}/segmentation/stardist" \
        "${LOG_ROOT}/quantification/mesmer" \
        "${LOG_ROOT}/quantification/stardist" \
        "${LOG_ROOT}/filtering/mesmer" \
        "${LOG_ROOT}/filtering/stardist" \
        "${LOG_ROOT}/benchmarks/illumination" \
        "${LOG_ROOT}/benchmarks/stitching" \
        "${LOG_ROOT}/benchmarks/mesmer" \
        "${LOG_ROOT}/benchmarks/stardist" \
        "${LOG_ROOT}/benchmarks/quantification" \
        "${LOG_ROOT}/benchmarks/filtering" \
        "${SEGMENTED_DIR}/mesmer" \
        "${SEGMENTED_DIR}/stardist" \
        "${QUANT_DIR}/mesmer" \
        "${QUANT_DIR}/stardist" \
        "${FILTERED_TIF_DIR}/mesmer" \
        "${FILTERED_TIF_DIR}/stardist" \
        "${FILTERED_CSV_DIR}/mesmer" \
        "${FILTERED_CSV_DIR}/stardist"

    echo "  └─ ✓ Folder check complete"
    echo ""
}

sample_list() {
    # Important:
    # Sample names are taken from folder names under RAW_DIR, not parsed from
    # .rcpnl filenames. This supports names like:
    #   S005_iOme
    #   S027_iOme_b1
    #   S026_iOme1
    #   S333_iOvaR
    #
    # Non-sample folders and hidden folders are ignored.
    local found_any=0
    if [[ -d "${RAW_DIR}" ]]; then
        local tmpfile
        tmpfile="$(mktemp 2>/dev/null || echo "/tmp/sample_list.$$")"
        while IFS= read -r -d '' d; do
            if find "${d}" -maxdepth 1 -type f -iname "*.rcpnl" -print -quit 2>/dev/null | grep -q .; then
                basename "${d}" >> "${tmpfile}"
                found_any=1
            fi
        done < <(
            find "${RAW_DIR}" \
                -mindepth 1 \
                -maxdepth 1 \
                -type d \
                ! -name "tmp" \
                ! -name ".*" \
                -print0
        )
        if [[ "${found_any}" -eq 1 ]]; then
            sort -u "${tmpfile}"
        fi
        rm -f "${tmpfile}" 2>/dev/null || true
    fi

    # Fallback: when no raw inputs exist, derive sample names from existing
    # stitched outputs so downstream listings and counts still work.
    if [[ "${found_any}" -eq 0 && -d "${STITCHED_DIR}" ]]; then
        while IFS= read -r -d '' d; do
            local name
            name="$(basename "${d}")"
            if [[ -f "${d}/${name}.ome.tif" ]]; then
                echo "${name}"
            fi
        done < <(
            find "${STITCHED_DIR}" \
                -mindepth 1 \
                -maxdepth 1 \
                -type d \
                ! -name "tmp" \
                ! -name ".*" \
                -print0
        ) | sort -u
    fi
}

sample_has_raw() {
    local sample="$1"
    find "${RAW_DIR}/${sample}" -maxdepth 1 -type f -iname "*.rcpnl" 2>/dev/null | grep -q .
}

raw_file_count_for_sample() {
    local sample="$1"

    find "${RAW_DIR}/${sample}" \
        -maxdepth 1 \
        -type f \
        -iname "*.rcpnl" \
        2>/dev/null | wc -l | awk '{print $1}'
}

raw_size_gib_for_sample() {
    local sample="$1"
    local size_b

    size_b=$(
        find "${RAW_DIR}/${sample}" \
            -maxdepth 1 \
            -type f \
            -iname "*.rcpnl" \
            -print0 2>/dev/null \
        | du --files0-from=- -bc 2>/dev/null \
        | tail -1 \
        | cut -f1
    )

    size_b=${size_b:-0}

    awk -v b="${size_b}" 'BEGIN { printf "%.2f", b / 1073741824 }'
}

raw_dataset_fingerprint() {
    # Fingerprint is based on sample folder names, raw .rcpnl filenames, and file sizes.
    # This detects newly added/removed raw files without relying on permanent user settings.
    if command -v sha256sum >/dev/null 2>&1; then
        {
            echo "RAW_DIR=${RAW_DIR}"

            local s
            while IFS= read -r s; do
                [[ -z "${s}" ]] && continue
                echo "SAMPLE=${s}"

                find "${RAW_DIR}/${s}" \
                    -maxdepth 1 \
                    -type f \
                    -iname "*.rcpnl" \
                    -printf "%f\t%s\n" 2>/dev/null | sort
            done < <(sample_list)
        } | sha256sum | awk '{print $1}'
    else
        {
            echo "RAW_DIR=${RAW_DIR}"

            local s
            while IFS= read -r s; do
                [[ -z "${s}" ]] && continue
                echo "SAMPLE=${s}"

                find "${RAW_DIR}/${s}" \
                    -maxdepth 1 \
                    -type f \
                    -iname "*.rcpnl" \
                    -printf "%f\t%s\n" 2>/dev/null | sort
            done < <(sample_list)
        } | cksum | awk '{print $1}'
    fi
}

raw_dataset_confirmation_needed() {
    [[ "${CONFIRM_RAW_DATASET_ON_FIRST_RUN:-1}" == "1" ]] || return 1

    local current
    local saved

    current="$(raw_dataset_fingerprint)"
    saved="$(cat "${STATE_DIR}/raw_dataset_fingerprint.txt" 2>/dev/null || true)"

    if [[ ! -f "${STATE_DIR}/raw_dataset_confirmed.flag" ]]; then
        return 0
    fi

    if [[ -z "${saved}" || "${saved}" != "${current}" ]]; then
        return 0
    fi

    return 1
}

raw_dataset_changed_since_confirmation() {
    local current
    local saved

    saved="$(cat "${STATE_DIR}/raw_dataset_fingerprint.txt" 2>/dev/null || true)"

    # No previous confirmation yet: not a "change"; it just needs confirmation.
    [[ -n "${saved}" ]] || return 1

    current="$(raw_dataset_fingerprint)"
    [[ "${saved}" != "${current}" ]]
}

invalidate_state_for_raw_change() {
    if raw_dataset_changed_since_confirmation; then
        echo "  - Raw input set changed since last confirmation."
        echo "  - Clearing pipeline state flags only; output data is NOT deleted."
        echo "  - Snakemake will rebuild only missing/stale outputs after confirmation."

        rm -f \
            "${STATE_DIR}/stitching_complete.flag" \
            "${STATE_DIR}/stitching_approved.flag" \
            "${STATE_DIR}/segmentation_complete.flag" \
            "${STATE_DIR}/segmentation_approved.flag" \
            "${STATE_DIR}/pipeline_complete.flag" \
            "${STATE_DIR}/raw_dataset_confirmed.flag"

        return 0
    fi

    return 1
}

write_raw_sample_manifest() {
    mkdir -p "${STATE_DIR}"

    local out="${STATE_DIR}/raw_sample_manifest.tsv"
    local s

    {
        printf "sample\trcpnl_files\tsize_GiB\n"

        while IFS= read -r s; do
            [[ -z "${s}" ]] && continue
            printf "%s\t%s\t%s\n" \
                "${s}" \
                "$(raw_file_count_for_sample "${s}")" \
                "$(raw_size_gib_for_sample "${s}")"
        done < <(sample_list)
    } > "${out}"

    echo "${out}"
}

print_raw_sample_preview() {
    local limit="${1:-30}"
    local total=0
    local shown=0
    local s

    printf "  %-32s %10s %12s\n" "Sample" ".rcpnl" "GiB"
    printf "  %-32s %10s %12s\n" "------" "------" "---"

    while IFS= read -r s; do
        [[ -z "${s}" ]] && continue

        total=$((total + 1))

        if [[ "${shown}" -lt "${limit}" ]]; then
            printf "  %-32s %10s %12s\n" \
                "${s}" \
                "$(raw_file_count_for_sample "${s}")" \
                "$(raw_size_gib_for_sample "${s}")"

            shown=$((shown + 1))
        fi
    done < <(sample_list)

    if [[ "${total}" -gt "${limit}" ]]; then
        echo "  ... $((total - limit)) more samples not shown here."
    fi
}

confirm_raw_dataset_if_needed() {
    [[ "${CONFIRM_RAW_DATASET_ON_FIRST_RUN:-1}" == "1" ]] || return 0

    # When the user disabled the stitching stage (--only/--from/--until past
    # stitching), raw .rcpnl files are not required at all — skip confirmation.
    if [[ "${RUN_STAGE_STITCHING:-1}" != "1" ]]; then
        return 0
    fi

    if ! raw_dataset_confirmation_needed; then
        return 0
    fi

    compute_raw_stats

    local manifest
    manifest="$(write_raw_sample_manifest)"

    if declare -F ui_section >/dev/null 2>&1 && ui_enabled; then
        ui_section "Confirm your raw data" "Please check this matches what you expect before any jobs run"
        ui_path "Raw data folder: ${RAW_DIR}"
        ui_step "Samples: ${DATASET_SAMPLES}"
        ui_step "Microscope files (.rcpnl): ${DATASET_RAW_FILES}"
        ui_step "Total size: ${DATASET_SIZE_GIB} GiB (about ${DATASET_AVG_GIB} GiB per sample)"
        ui_note "Sample list saved to: ${manifest}"
        ui_blank
        print_raw_sample_preview 30
        ui_blank
    else
        echo ""
        echo "Raw dataset confirmation"
        echo "RAW_DIR         : ${RAW_DIR}"
        echo "Detected samples: ${DATASET_SAMPLES}"
        echo "Detected files  : ${DATASET_RAW_FILES} (.rcpnl)"
        echo "Total raw size  : ${DATASET_SIZE_GIB} GiB"
        echo "Manifest        : ${manifest}"
        echo ""
        print_raw_sample_preview 30
        echo ""
    fi

    if [[ "${DATASET_SAMPLES:-0}" -lt 1 || "${DATASET_RAW_FILES:-0}" -lt 1 ]]; then
        echo "ERROR: No valid samples/raw .rcpnl files detected."
        echo "Expected layout:"
        echo "  ${RAW_DIR}/<sample>/*.rcpnl"
        exit 1
    fi

    if [[ ! -r /dev/tty ]]; then
        echo "ERROR: Raw dataset needs confirmation, but no interactive terminal is available."
        echo "Run this in an interactive shell:"
        echo "  bash run_pipeline.sh"
        exit 1
    fi

    local answer=""
    if declare -F ui_note >/dev/null 2>&1 && ui_enabled; then
        printf "  Continue with these %s samples? [y/N] " "${DATASET_SAMPLES}" > /dev/tty
    else
        printf "Continue with these ${DATASET_SAMPLES} samples and ${DATASET_RAW_FILES} .rcpnl files? [y/N] " > /dev/tty
    fi
    IFS= read -r answer < /dev/tty

    case "${answer}" in
        y|Y|yes|YES)
            raw_dataset_fingerprint > "${STATE_DIR}/raw_dataset_fingerprint.txt"
            touch "${STATE_DIR}/raw_dataset_confirmed.flag"
            if declare -F ui_ok >/dev/null 2>&1 && ui_enabled; then
                ui_ok "Raw dataset confirmed — processing can start."
                ui_blank
            else
                echo "  └─ ✓ Raw dataset confirmed for this project."
                echo ""
            fi
            ;;
        *)
            echo "Stopping. No cluster jobs were submitted."
            exit 0
            ;;
    esac
}


valid_file() {
    local f="$1"
    [[ -f "${f}" && -s "${f}" && -r "${f}" ]]
}

count_samples() {
    local n=0
    local s
    local raw_dir_has_data=0

    if [[ -d "${RAW_DIR}" ]] && find "${RAW_DIR}" -mindepth 2 -maxdepth 2 -type f -iname "*.rcpnl" -print -quit 2>/dev/null | grep -q .; then
        raw_dir_has_data=1
    fi

    while IFS= read -r s; do
        [[ -z "${s}" ]] && continue
        if [[ "${raw_dir_has_data}" -eq 1 ]]; then
            # Strict mode: only count samples that actually have raw files.
            if sample_has_raw "${s}"; then
                n=$((n + 1))
            fi
        else
            # Fallback mode: raw is empty — sample_list returned stitched-derived names.
            n=$((n + 1))
        fi
    done < <(sample_list)

    echo "${n}"
}

compute_raw_stats() {
    # DATASET_SAMPLES must mean runnable samples for the current stage.
    # In segmentation-only / downstream mode there may be no raw .rcpnl files,
    # but stitched outputs are valid inputs:
    #   STITCHED_DIR/<sample>/<sample>.ome.tif
    # The previous raw-only counter made downstream runs report Samples=0.
    local samples=0
    local raw_samples=0
    local files=0
    local size_b=0
    local stitched_size_b=0
    local s f sz

    samples="$(count_samples)"

    while IFS= read -r s; do
        [[ -z "${s}" ]] && continue
        if sample_has_raw "${s}"; then
            raw_samples=$((raw_samples + 1))
        fi
        f="${STITCHED_DIR}/${s}/${s}.ome.tif"
        if [[ -f "${f}" ]]; then
            sz="$(stat -c '%s' "${f}" 2>/dev/null || echo 0)"
            stitched_size_b=$((stitched_size_b + sz))
        fi
    done < <(sample_list)

    if [[ -d "${RAW_DIR}" ]]; then
        files=$(find "${RAW_DIR}" -mindepth 2 -maxdepth 2 -type f -iname "*.rcpnl" | wc -l)
        size_b=$(find "${RAW_DIR}" -mindepth 2 -maxdepth 2 -type f -iname "*.rcpnl" -print0 | du --files0-from=- -bc 2>/dev/null | tail -1 | cut -f1)
        size_b=${size_b:-0}
    fi

    local size_gib avg_gib stitched_size_gib stitched_avg_gib
    size_gib=$(awk -v b="${size_b}" 'BEGIN { printf "%.1f", b / 1073741824 }')
    stitched_size_gib=$(awk -v b="${stitched_size_b}" 'BEGIN { printf "%.1f", b / 1073741824 }')

    if [[ "${raw_samples}" -gt 0 ]]; then
        avg_gib=$(awk -v s="${size_gib}" -v n="${raw_samples}" 'BEGIN { printf "%.1f", s / n }')
    else
        avg_gib="0.0"
    fi

    if [[ "${samples}" -gt 0 ]]; then
        stitched_avg_gib=$(awk -v s="${stitched_size_gib}" -v n="${samples}" 'BEGIN { printf "%.1f", s / n }')
    else
        stitched_avg_gib="0.0"
    fi

    export DATASET_SAMPLES="${samples}"
    export DATASET_RAW_SAMPLES="${raw_samples}"
    export DATASET_RAW_FILES="${files}"
    export DATASET_SIZE_GIB="${size_gib}"
    export DATASET_AVG_GIB="${avg_gib}"
    export DATASET_STITCHED_SIZE_GIB="${stitched_size_gib}"
    export DATASET_STITCHED_AVG_GIB="${stitched_avg_gib}"
}

print_summary() {
    compute_raw_stats

    echo "Dataset Summary"
    echo "   Runnable samples : ${DATASET_SAMPLES}"
    echo "   Raw samples      : ${DATASET_RAW_SAMPLES:-0}"
    echo "   Raw files        : ${DATASET_RAW_FILES} (.rcpnl)"
    echo "   Total raw size   : ${DATASET_SIZE_GIB} GiB"
    echo "   Avg raw/sample   : ${DATASET_AVG_GIB} GiB"
    echo "   Stitched total   : ${DATASET_STITCHED_SIZE_GIB:-0.0} GiB"
    echo "   Filtering      : ${RUN_FILTERING:-0}"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

float_lt() {
    awk -v a="$1" -v b="$2" 'BEGIN { exit !(a < b) }'
}

min_int() {
    local a="$1"
    local b="$2"

    if [[ "${a}" -lt "${b}" ]]; then
        echo "${a}"
    else
        echo "${b}"
    fi
}

smart_jobs() {
    local stage="$1"
    local requested="$2"

    compute_raw_stats

    local samples="${DATASET_SAMPLES:-0}"
    local avg="${DATASET_AVG_GIB:-0}"
    local max_cpu="${MAX_CPU_JOBS:-32}"
    local max_gpu="${MAX_GPU_JOBS:-8}"
    local jobs=1

    if [[ "${requested}" != "auto" ]]; then
        echo "${requested}"
        return
    fi

    if [[ "${samples}" -lt 1 ]]; then
        echo 1
        return
    fi

    case "${stage}" in
        illumination)
            if float_lt "${avg}" "10"; then
                jobs=$(min_int "${samples}" "${max_cpu}")
            elif float_lt "${avg}" "25"; then
                jobs=$(min_int "${samples}" 20)
            elif float_lt "${avg}" "50"; then
                jobs=$(min_int "${samples}" 12)
            else
                jobs=$(min_int "${samples}" 8)
            fi
            ;;

        stitching)
            if float_lt "${avg}" "15"; then
                jobs=$(min_int "${samples}" 16)
            elif float_lt "${avg}" "40"; then
                jobs=$(min_int "${samples}" 10)
            else
                jobs=$(min_int "${samples}" 6)
            fi
            jobs=$(min_int "${jobs}" "${max_cpu}")
            ;;

        mesmer|stardist)
            if float_lt "${avg}" "10"; then
                jobs=$(min_int "${samples}" "${max_gpu}")
            elif float_lt "${avg}" "25"; then
                jobs=$(min_int "${samples}" "${max_gpu}")
            elif float_lt "${avg}" "50"; then
                jobs=$(min_int "${samples}" 6)
            elif float_lt "${avg}" "80"; then
                jobs=$(min_int "${samples}" 4)
            else
                jobs=$(min_int "${samples}" 2)
            fi
            jobs=$(min_int "${jobs}" "${max_gpu}")
            ;;

        quantification)
            if float_lt "${avg}" "10"; then
                jobs=$(min_int "${samples}" "${max_cpu}")
            elif float_lt "${avg}" "30"; then
                jobs=$(min_int "${samples}" 24)
            else
                jobs=$(min_int "${samples}" 12)
            fi
            jobs=$(min_int "${jobs}" "${max_cpu}")
            ;;

        filtering)
            if float_lt "${avg}" "10"; then
                jobs=$(min_int "${samples}" 24)
            elif float_lt "${avg}" "30"; then
                jobs=$(min_int "${samples}" 16)
            else
                jobs=$(min_int "${samples}" 8)
            fi
            jobs=$(min_int "${jobs}" "${max_cpu}")
            ;;

        *)
            jobs=$(min_int "${samples}" 8)
            ;;
    esac

    [[ "${jobs}" -lt 1 ]] && jobs=1
    echo "${jobs}"
}

all_stitched_complete() {
    local total=0
    local missing=0
    local s
    local f

    while IFS= read -r s; do
        [[ -z "${s}" ]] && continue
        _sample_passes_raw_gate "${s}" || continue

        total=$((total + 1))
        f="${STITCHED_DIR}/${s}/${s}.ome.tif"
        valid_file "${f}" || missing=$((missing + 1))
    done < <(sample_list)

    [[ "${total}" -gt 0 && "${missing}" -eq 0 ]]
}

infer_mesmer_compartment() {
    local samples=0
    local nuc_complete=0
    local wc_complete=0
    local both_complete=0
    local s nuc wc

    while IFS= read -r s; do
        [[ -z "${s}" ]] && continue
        _sample_passes_raw_gate "${s}" || continue
        samples=$((samples + 1))

        nuc="${SEGMENTED_DIR}/mesmer/${s}_mask_nuclear.tif"
        wc="${SEGMENTED_DIR}/mesmer/${s}_mask_whole_cell.tif"

        if valid_file "${nuc}"; then
            nuc_complete=$((nuc_complete + 1))
        fi
        if valid_file "${wc}"; then
            wc_complete=$((wc_complete + 1))
        fi
        if valid_file "${nuc}" && valid_file "${wc}"; then
            both_complete=$((both_complete + 1))
        fi
    done < <(sample_list)

    if [[ "${samples}" -eq 0 ]]; then
        echo ""
    elif [[ "${both_complete}" -eq "${samples}" ]]; then
        echo "both"
    elif [[ "${nuc_complete}" -eq "${samples}" && "${wc_complete}" -eq 0 ]]; then
        echo "nuclear"
    elif [[ "${wc_complete}" -eq "${samples}" && "${nuc_complete}" -eq 0 ]]; then
        echo "whole-cell"
    else
        # Partial/mixed outputs are ambiguous. Do not infer a compartment from them.
        echo ""
    fi
}

infer_method_from_outputs() {
    local mesmer_done=0
    local stardist_done=0

    all_mesmer_complete && mesmer_done=1 || true
    all_stardist_complete && stardist_done=1 || true

    if [[ "${mesmer_done}" == "1" && "${stardist_done}" == "1" ]]; then
        echo "both"
    elif [[ "${mesmer_done}" == "1" ]]; then
        echo "mesmer"
    elif [[ "${stardist_done}" == "1" ]]; then
        echo "stardist"
    else
        echo ""
    fi
}

method_final_complete() {
    local method="$1"

    if filtering_enabled; then
        case "${method}" in
            mesmer)
                all_filtered_complete_for_method "mesmer"
                ;;
            stardist)
                all_filtered_complete_for_method "stardist"
                ;;
            both)
                all_filtered_complete_for_method "mesmer" && all_filtered_complete_for_method "stardist"
                ;;
            *)
                return 1
                ;;
        esac
    else
        case "${method}" in
            mesmer)
                all_quant_complete_for_method "mesmer"
                ;;
            stardist)
                all_quant_complete_for_method "stardist"
                ;;
            both)
                all_quant_complete_for_method "mesmer" && all_quant_complete_for_method "stardist"
                ;;
            *)
                return 1
                ;;
        esac
    fi
}

method_segmentation_complete() {
    local method="$1"

    case "${method}" in
        mesmer)
            all_mesmer_complete
            ;;
        stardist)
            all_stardist_complete
            ;;
        both)
            all_mesmer_complete && all_stardist_complete
            ;;
        *)
            return 1
            ;;
    esac
}

sync_state_from_outputs() {
    [[ "${AUTO_SYNC_STATE_FROM_OUTPUTS:-1}" == "1" ]] || return 0

    echo "Smart state sync from existing outputs..."

    mkdir -p "${STATE_DIR}"

    if invalidate_state_for_raw_change; then
        echo "  └─ Raw dataset must be confirmed before output-based state sync continues"
        echo ""
        return 0
    fi

    local stitched_ok=0
    local segmentation_ok=0
    local final_ok=0
    local method=""
    local inferred_method=""

    all_stitched_complete && stitched_ok=1 || true

    if [[ "${stitched_ok}" == "1" ]]; then
        if [[ ! -f "${STATE_DIR}/stitching_complete.flag" ]]; then
            touch "${STATE_DIR}/stitching_complete.flag"
            echo "  - Detected complete stitching outputs → created stitching_complete.flag"
        fi
    else
        if [[ -f "${STATE_DIR}/stitching_complete.flag" ]]; then
            rm -f "${STATE_DIR}/stitching_complete.flag"
            echo "  - Removed stale stitching_complete.flag because stitched outputs are incomplete"
        fi

        if [[ -f "${STATE_DIR}/stitching_approved.flag" ]]; then
            rm -f "${STATE_DIR}/stitching_approved.flag"
            echo "  - Removed stale stitching_approved.flag because stitched outputs are incomplete"
        fi
    fi

    if [[ ! -f "${STATE_DIR}/segmentation_method.txt" ]]; then
        inferred_method="$(infer_method_from_outputs)"

        if [[ -n "${inferred_method}" ]]; then
            echo "${inferred_method}" > "${STATE_DIR}/segmentation_method.txt"
            echo "  - Inferred segmentation method from outputs: ${inferred_method}"
        fi
    fi

    if [[ -f "${STATE_DIR}/segmentation_method.txt" ]]; then
        method="$(cat "${STATE_DIR}/segmentation_method.txt")"

        case "${method}" in
            mesmer|stardist|both)
                ;;
            *)
                echo "  - WARNING: invalid segmentation_method.txt value: ${method}"
                rm -f "${STATE_DIR}/segmentation_method.txt"
                method=""
                ;;
        esac
    fi

    if [[ -n "${method}" ]]; then
        method_segmentation_complete "${method}" && segmentation_ok=1 || true
        method_final_complete "${method}" && final_ok=1 || true

        if [[ "${stitched_ok}" == "1" && "${segmentation_ok}" == "1" ]]; then
            if [[ "${AUTO_APPROVE_PREVIOUS_STAGES_FROM_OUTPUTS:-1}" == "1" ]]; then
                touch "${STATE_DIR}/stitching_approved.flag"
            fi

            if [[ ! -f "${STATE_DIR}/segmentation_complete.flag" ]]; then
                touch "${STATE_DIR}/segmentation_complete.flag"
                echo "  - Detected complete segmentation outputs → created segmentation_complete.flag"
            fi
        else
            if [[ -f "${STATE_DIR}/segmentation_complete.flag" ]]; then
                rm -f "${STATE_DIR}/segmentation_complete.flag"
                echo "  - Removed stale segmentation_complete.flag because segmentation outputs are incomplete for method: ${method}"
            fi

            if [[ -f "${STATE_DIR}/segmentation_approved.flag" ]]; then
                rm -f "${STATE_DIR}/segmentation_approved.flag"
                echo "  - Removed stale segmentation_approved.flag because segmentation outputs are incomplete for method: ${method}"
            fi
        fi

        if [[ "${stitched_ok}" == "1" && "${segmentation_ok}" == "1" && "${final_ok}" == "1" ]]; then
            if [[ "${AUTO_APPROVE_PREVIOUS_STAGES_FROM_OUTPUTS:-1}" == "1" ]]; then
                touch "${STATE_DIR}/stitching_approved.flag"
                touch "${STATE_DIR}/segmentation_approved.flag"
            fi

            if [[ ! -f "${STATE_DIR}/pipeline_complete.flag" ]]; then
                touch "${STATE_DIR}/pipeline_complete.flag"

                if filtering_enabled; then
                    echo "  - Detected final filtered quantification outputs → created pipeline_complete.flag"
                else
                    echo "  - Detected final quantification outputs → created pipeline_complete.flag"
                fi
            fi
        else
            if [[ -f "${STATE_DIR}/pipeline_complete.flag" ]]; then
                rm -f "${STATE_DIR}/pipeline_complete.flag"
                echo "  - Removed stale pipeline_complete.flag because final outputs are incomplete for method: ${method}"
            fi
        fi
    else
        rm -f \
            "${STATE_DIR}/segmentation_complete.flag" \
            "${STATE_DIR}/segmentation_approved.flag" \
            "${STATE_DIR}/pipeline_complete.flag"
    fi

    echo "  └─ ✓ Smart state sync complete"
    echo ""
}

print_status() {
    echo "Pipeline State:"
    ls -1 "${STATE_DIR}"/*.flag 2>/dev/null | xargs -r -n1 basename || true

    if [[ -f "${STATE_DIR}/segmentation_method.txt" ]]; then
        echo "Segmentation method: $(cat "${STATE_DIR}/segmentation_method.txt")"
    fi

    echo "Filtering enabled: ${RUN_FILTERING:-0}"

    if raw_dataset_confirmation_needed; then
        echo "Raw dataset    : needs confirmation"
    else
        echo "Raw dataset    : confirmed/current"
    fi

    echo ""
    echo "Output detection:"
    all_stitched_complete && echo "  Stitching       : complete" || echo "  Stitching       : incomplete"
    all_mesmer_complete && echo "  Mesmer masks    : complete" || echo "  Mesmer masks    : incomplete"
    all_stardist_complete && echo "  StarDist masks  : complete" || echo "  StarDist masks  : incomplete"

    all_quant_complete_for_method "mesmer" \
        && echo "  Mesmer quant    : complete" \
        || echo "  Mesmer quant    : incomplete"

    all_quant_complete_for_method "stardist" \
        && echo "  StarDist quant  : complete" \
        || echo "  StarDist quant  : incomplete"

    if filtering_enabled; then
        all_filtered_complete_for_method "mesmer" \
            && echo "  Mesmer filtered : complete" \
            || echo "  Mesmer filtered : incomplete"

        all_filtered_complete_for_method "stardist" \
            && echo "  StarDist filtered: complete" \
            || echo "  StarDist filtered: incomplete"
    fi

    if [[ -f "${STATE_DIR}/segmentation_method.txt" ]]; then
        local method
        method="$(cat "${STATE_DIR}/segmentation_method.txt")"

        method_segmentation_complete "${method}" \
            && echo "  Segmentation    : complete for ${method}" \
            || echo "  Segmentation    : incomplete for ${method}"

        method_final_complete "${method}" \
            && echo "  Final outputs   : complete for ${method}" \
            || echo "  Final outputs   : incomplete for ${method}"
    fi
}


ensure_runnable_samples_available() {
    local context="${1:-pipeline stage}"
    local n
    n="$(count_samples)"
    if [[ "${n}" -lt 1 ]]; then
        echo "ERROR: No runnable samples detected for ${context}."
        echo "Expected at least one of:"
        echo "  1) raw input:      ${RAW_DIR}/<sample>/*.rcpnl"
        echo "  2) stitched input: ${STITCHED_DIR}/<sample>/<sample>.ome.tif"
        echo "Quick check commands:"
        echo "  find ${STITCHED_DIR} -mindepth 2 -maxdepth 2 -name '*.ome.tif' | head"
        echo "  find ${RAW_DIR} -mindepth 2 -maxdepth 2 -name '*.rcpnl' | head"
        return 1
    fi
    return 0
}

print_plan() {
    ensure_pipeline_dirs
    print_summary
    sync_state_from_outputs

    if raw_dataset_confirmation_needed; then
        compute_raw_stats
        write_raw_sample_manifest >/dev/null

        echo "Execution plan"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "Next action: confirm raw dataset"
        echo "Detected samples : ${DATASET_SAMPLES}"
        echo "Detected .rcpnl  : ${DATASET_RAW_FILES}"
        echo "Manifest         : ${STATE_DIR}/raw_sample_manifest.tsv"
        return
    fi

    echo "Execution plan"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if [[ ! -f "${STATE_DIR}/stitching_complete.flag" ]]; then
        echo "Next action: run illumination correction + stitching"
        echo "CPU jobs:"
        echo "  Illumination : $(smart_jobs illumination "${ILLUMINATION_JOBS}")"
        echo "  Stitching    : $(smart_jobs stitching "${STITCHING_JOBS}")"
        return
    fi

    if [[ ! -f "${STATE_DIR}/stitching_approved.flag" ]]; then
        echo "Next action: ask user to approve stitched images"
        echo "Stitched images: ${STITCHED_DIR}"
        return
    fi

    if [[ ! -f "${STATE_DIR}/segmentation_complete.flag" ]]; then
        echo "Next action: choose/run segmentation"
        echo "GPU partition: ${SLURM_PARTITION_GPU}"
        echo "GPU jobs:"
        echo "  Mesmer   : $(smart_jobs mesmer "${MESMER_JOBS}")"
        echo "  StarDist : $(smart_jobs stardist "${STARDIST_JOBS}")"
        return
    fi

    if [[ ! -f "${STATE_DIR}/segmentation_approved.flag" ]]; then
        echo "Next action: ask user to approve segmentation masks"
        echo "Segmentation masks: ${SEGMENTED_DIR}"
        return
    fi

    if [[ ! -f "${STATE_DIR}/pipeline_complete.flag" ]]; then
        if filtering_enabled; then
            echo "Next action: run quantification + filtering"
        else
            echo "Next action: run quantification"
        fi

        echo "CPU jobs:"
        echo "  Quantification : $(smart_jobs quantification "${QUANTIFICATION_JOBS}")"

        if filtering_enabled; then
            echo "  Filtering      : $(smart_jobs filtering "${FILTER_JOBS}")"
        else
            echo "  Filtering      : disabled"
        fi

        return
    fi

    echo "Next action: pipeline already complete"
}

print_method_paths() {
    local method="$1"

    echo "Routing for selected segmentation method: ${method}"
    echo "  Common raw input            : ${RAW_DIR}/<sample>/*.rcpnl"
    echo "  Stitching output/input      : ${STITCHED_DIR}/<sample>/<sample>.ome.tif"

    if [[ "${method}" == "mesmer" || "${method}" == "both" ]]; then
        echo "  Mesmer masks                : ${SEGMENTED_DIR}/mesmer/<sample>_mask_nuclear.tif"
        echo "  Mesmer quantification       : ${QUANT_DIR}/mesmer/<sample>_nuclear.csv"

        if filtering_enabled; then
            echo "  Mesmer filtered images      : ${FILTERED_TIF_DIR}/mesmer/<marker>/<sample>.ome_<marker>_tophat.tif"
            echo "  Mesmer filtered quant CSV   : ${FILTERED_CSV_DIR}/mesmer/<sample>_filtered.csv"
        fi
    fi

    if [[ "${method}" == "stardist" || "${method}" == "both" ]]; then
        echo "  StarDist masks              : ${SEGMENTED_DIR}/stardist/<sample>_mask_nuclear.tif"
        echo "  StarDist quantification     : ${QUANT_DIR}/stardist/<sample>_nuclear.csv"

        if filtering_enabled; then
            echo "  StarDist filtered images    : ${FILTERED_TIF_DIR}/stardist/<marker>/<sample>.ome_<marker>_tophat.tif"
            echo "  StarDist filtered quant CSV : ${FILTERED_CSV_DIR}/stardist/<sample>_filtered.csv"
        fi
    fi

    echo ""
}

write_final_summary() {
    local summary_file="${LOG_ROOT}/pipeline_summary_$(date +%Y%m%d_%H%M%S).txt"
    local method="unknown"

    [[ -f "${STATE_DIR}/segmentation_method.txt" ]] && method="$(cat "${STATE_DIR}/segmentation_method.txt")"

    {
        echo "Pipeline summary"
        echo "================"
        echo "Date                     : $(date)"
        echo "BASE                     : ${BASE}"
        echo "Samples                  : ${DATASET_SAMPLES:-unknown}"
        echo "Raw files                : ${DATASET_RAW_FILES:-unknown}"
        echo "Raw size GiB             : ${DATASET_SIZE_GIB:-unknown}"
        echo "Segmentation method      : ${method}"
        echo "RUN_FILTERING            : ${RUN_FILTERING:-0}"
        echo "Stitching complete       : $(all_stitched_complete && echo yes || echo no)"
        echo "Mesmer masks complete    : $(all_mesmer_complete && echo yes || echo no)"
        echo "StarDist masks complete  : $(all_stardist_complete && echo yes || echo no)"
        echo "Mesmer quant complete    : $(all_quant_complete_for_method mesmer && echo yes || echo no)"
        echo "StarDist quant complete  : $(all_quant_complete_for_method stardist && echo yes || echo no)"

        if filtering_enabled; then
            echo "Mesmer filtered complete : $(all_filtered_complete_for_method mesmer && echo yes || echo no)"
            echo "StarDist filtered complete: $(all_filtered_complete_for_method stardist && echo yes || echo no)"
        fi

        echo "Final complete           : $(method_final_complete "${method}" && echo yes || echo no)"
        echo "Logs                     : ${LOG_ROOT}"
    } > "${summary_file}"

    echo "Final summary written: ${summary_file}"
}


# ============================================================
# Layout v3 overrides: strict method-specific layout
# ============================================================
# Final contract:
#   Normal quantification:
#     ${QUANT_DIR}/mesmer/<sample>_nuclear.csv
#     ${QUANT_DIR}/stardist/<sample>_nuclear.csv
#   Filtered TIFFs:
#     ${FILTERED_TIF_DIR}/mesmer/<marker>/<sample>.ome_<marker>_tophat.tif
#     ${FILTERED_TIF_DIR}/stardist/<marker>/<sample>.ome_<marker>_tophat.tif
#   Filtered CSVs:
#     ${FILTERED_CSV_DIR}/mesmer/<sample>_filtered.csv
#     ${FILTERED_CSV_DIR}/stardist/<sample>_filtered.csv
#
# There is intentionally no quantification_filtered final directory.
# Filtering is required for this pipeline.
# ============================================================

filtering_enabled() { return 0; }

current_segmentation_method() {
    [[ -f "${STATE_DIR}/segmentation_method.txt" ]] && cat "${STATE_DIR}/segmentation_method.txt" || echo ""
}

_methods_from_state_or_all() {
    case "$(current_segmentation_method)" in
        mesmer) echo "mesmer" ;;
        stardist) echo "stardist" ;;
        both) echo "mesmer stardist" ;;
        *) echo "mesmer stardist" ;;
    esac
}

mesmer_compartment_current() {
    local comp=""

    if [[ -s "${STATE_DIR}/mesmer_compartment.txt" ]]; then
        comp="$(tr -d '[:space:]' < "${STATE_DIR}/mesmer_compartment.txt")"
    fi

    [[ -z "${comp}" ]] && comp="${MESMER_COMPARTMENT:-}"

    # If not explicitly set, try to infer from existing outputs.
    if [[ -z "${comp}" ]]; then
        comp="$(infer_mesmer_compartment 2>/dev/null || true)"
    fi

    # Fall back to nuclear (the safe default).
    [[ -z "${comp}" ]] && comp="nuclear"

    case "${comp}" in
        nuclear|whole-cell|both)
            echo "${comp}"
            ;;
        *)
            echo "nuclear"
            ;;
    esac
}

segmentation_mask_path() {
    local m="$1" s="$2"

    if [[ "${m}" == "mesmer" ]]; then
        case "$(mesmer_compartment_current)" in
            nuclear)
                echo "${SEGMENTED_DIR}/${m}/${s}_mask_nuclear.tif"
                ;;
            whole-cell)
                echo "${SEGMENTED_DIR}/${m}/${s}_mask_whole_cell.tif"
                ;;
            both)
                echo "nuclear=${SEGMENTED_DIR}/${m}/${s}_mask_nuclear.tif ; whole-cell=${SEGMENTED_DIR}/${m}/${s}_mask_whole_cell.tif"
                ;;
        esac
    else
        echo "${SEGMENTED_DIR}/${m}/${s}_mask_nuclear.tif"
    fi
}

mesmer_required_mask_paths_for_sample() {
    local s="$1"

    case "$(mesmer_compartment_current)" in
        nuclear)
            echo "${SEGMENTED_DIR}/mesmer/${s}_mask_nuclear.tif"
            ;;
        whole-cell)
            echo "${SEGMENTED_DIR}/mesmer/${s}_mask_whole_cell.tif"
            ;;
        both)
            echo "${SEGMENTED_DIR}/mesmer/${s}_mask_nuclear.tif"
            echo "${SEGMENTED_DIR}/mesmer/${s}_mask_whole_cell.tif"
            ;;
    esac
}

mesmer_sample_complete() {
    local s="$1"
    local f=""

    while IFS= read -r f; do
        [[ -n "${f}" ]] || continue
        valid_file "${f}" || return 1
    done < <(mesmer_required_mask_paths_for_sample "${s}")

    return 0
}

_count_mesmer_required_present() {
    local n=0 s

    while IFS= read -r s; do
        [[ -z "${s}" ]] && continue
        _sample_passes_raw_gate "${s}" || continue
        if mesmer_sample_complete "${s}"; then
            n=$((n + 1))
        fi
    done < <(sample_list)

    echo "${n}"
}

quant_csv_path() {
    local m="$1" s="$2"
    echo "${QUANT_DIR}/${m}/${s}_nuclear.csv"
}

filtered_tif_path_shell() {
    local m="$1" s="$2" marker="$3"
    echo "${FILTERED_TIF_DIR}/${m}/${marker}/${s}.ome_${marker}_tophat.tif"
}

filtered_csv_path_shell() {
    local m="$1" s="$2"
    echo "${FILTERED_CSV_DIR}/${m}/${s}_filtered.csv"
}

# Compartment-aware required CSVs. Mesmer can emit nuclear and/or whole-cell
# outputs depending on MESMER_COMPARTMENT, so completeness must check exactly
# the compartment(s) the run actually produces. StarDist is always nuclear.
mesmer_required_quant_csv_paths_for_sample() {
    local s="$1"
    case "$(mesmer_compartment_current)" in
        whole-cell)
            echo "${QUANT_DIR}/mesmer/${s}_whole_cell.csv"
            ;;
        both)
            echo "${QUANT_DIR}/mesmer/${s}_nuclear.csv"
            echo "${QUANT_DIR}/mesmer/${s}_whole_cell.csv"
            ;;
        *)
            echo "${QUANT_DIR}/mesmer/${s}_nuclear.csv"
            ;;
    esac
}

mesmer_required_filtered_csv_paths_for_sample() {
    local s="$1"
    case "$(mesmer_compartment_current)" in
        whole-cell)
            echo "${FILTERED_CSV_DIR}/mesmer/${s}_whole_cell_filtered.csv"
            ;;
        both)
            echo "${FILTERED_CSV_DIR}/mesmer/${s}_filtered.csv"
            echo "${FILTERED_CSV_DIR}/mesmer/${s}_whole_cell_filtered.csv"
            ;;
        *)
            echo "${FILTERED_CSV_DIR}/mesmer/${s}_filtered.csv"
            ;;
    esac
}

_mesmer_sample_quant_complete() {
    local s="$1" f
    while IFS= read -r f; do
        [[ -n "${f}" ]] || continue
        valid_file "${f}" || return 1
    done < <(mesmer_required_quant_csv_paths_for_sample "${s}")
    return 0
}

_mesmer_sample_filtered_complete() {
    local s="$1" f
    while IFS= read -r f; do
        [[ -n "${f}" ]] || continue
        valid_file "${f}" || return 1
    done < <(mesmer_required_filtered_csv_paths_for_sample "${s}")
    return 0
}

marker_list() {
    python3 - <<'PY_MARKERS'
import json, os, sys
raw = os.environ.get("MARKERS_JSON", "").strip()
if raw.startswith("'") and raw.endswith("'"):
    raw = raw[1:-1].strip()
if raw.startswith('"') and raw.endswith('"'):
    raw = raw[1:-1].strip()
raw = raw.replace('\\"', '"')
if not raw:
    sys.exit(0)
try:
    markers = json.loads(raw)
except Exception:
    sys.exit(0)
if isinstance(markers, dict):
    for k in sorted(markers):
        print(k)
PY_MARKERS
}

marker_count() { marker_list | wc -l | awk '{print $1}'; }

# Derive the canonical sample name from a filename. Strips common pipeline
# suffixes / prefixes and known extensions so users can drop files with names
# like "S073_iOme.ome.tif", "stitched_S073_iOme.tif", "S073_iOme_stitched.ome.tif",
# "S073_iOme.ashlar.ome.tif" etc. and they all collapse to "S073_iOme".
canonical_sample_name() {
    local name="$1"

    # Strip directory part.
    name="$(basename -- "${name}")"

    # Strip extensions: ".ome.tif", ".ome.tiff", ".tif", ".tiff".
    name="${name%.ome.tif}"
    name="${name%.ome.tiff}"
    name="${name%.tif}"
    name="${name%.tiff}"

    # Strip secondary qualifiers like ".ome", ".ashlar", ".stitched".
    name="${name%.ome}"
    name="${name%.ashlar}"
    name="${name%.stitched}"
    name="${name%.stitching}"

    # Strip well-known suffixes / prefixes using case-insensitive matching on
    # a lowercase shadow copy so we can preserve the original casing of the
    # surviving sample name.
    local prev lower
    while :; do
        prev="${name}"
        lower="$(printf '%s' "${name}" | tr '[:upper:]' '[:lower:]')"

        # Suffixes
        case "${lower}" in
            *_stitched)  name="${name:0:${#name}-9}" ;;
            *-stitched)  name="${name:0:${#name}-9}" ;;
            *_stitching) name="${name:0:${#name}-10}" ;;
            *-stitching) name="${name:0:${#name}-10}" ;;
            *_ashlar)    name="${name:0:${#name}-7}" ;;
            *-ashlar)    name="${name:0:${#name}-7}" ;;
        esac

        lower="$(printf '%s' "${name}" | tr '[:upper:]' '[:lower:]')"

        # Prefixes
        case "${lower}" in
            stitched_*)  name="${name:9}" ;;
            stitched-*)  name="${name:9}" ;;
            stitching_*) name="${name:10}" ;;
            stitching-*) name="${name:10}" ;;
            ashlar_*)    name="${name:7}" ;;
            ashlar-*)    name="${name:7}" ;;
        esac

        [[ "${name}" == "${prev}" ]] && break
    done

    printf '%s' "${name}"
}

# Normalize stitched layout: the pipeline expects
#   STITCHED_DIR/<sample>/<sample>.ome.tif
# Users may have dropped in a flat layout or used non-standard names. This
# function detects them, derives the canonical sample name, and creates the
# expected per-sample subdirectory with a symlink. Originals are never moved
# or modified. Idempotent — safe to run on every invocation.
normalize_stitched_layout() {
    [[ -d "${STITCHED_DIR}" ]] || return 0

    local changed=0 src dest_dir dest sample

    # (1) Flat-layout files at top of STITCHED_DIR.
    while IFS= read -r -d '' src; do
        sample="$(canonical_sample_name "${src}")"
        [[ -z "${sample}" ]] && continue
        dest_dir="${STITCHED_DIR}/${sample}"
        dest="${dest_dir}/${sample}.ome.tif"
        [[ -e "${dest}" || -L "${dest}" ]] && continue
        mkdir -p "${dest_dir}"
        ln -s -- "${src}" "${dest}" 2>/dev/null && {
            echo "  - Normalized stitched: $(basename -- "${src}") -> ${sample}/${sample}.ome.tif"
            changed=1
        }
    done < <(find "${STITCHED_DIR}" -mindepth 1 -maxdepth 1 -type f \
                \( -iname "*.ome.tif" -o -iname "*.ome.tiff" -o -iname "*.tif" -o -iname "*.tiff" \) \
                -print0 2>/dev/null)

    # (2) Subdirectories whose inner file has a non-canonical name.
    while IFS= read -r -d '' src; do
        local parent
        parent="$(dirname -- "${src}")"
        sample="$(basename -- "${parent}")"
        dest="${parent}/${sample}.ome.tif"
        [[ "${src}" == "${dest}" ]] && continue
        [[ -e "${dest}" || -L "${dest}" ]] && continue
        ln -s -- "$(basename -- "${src}")" "${dest}" 2>/dev/null && {
            echo "  - Normalized stitched inner: ${sample}/$(basename -- "${src}") -> ${sample}/${sample}.ome.tif"
            changed=1
        }
    done < <(find "${STITCHED_DIR}" -mindepth 2 -maxdepth 2 -type f \
                \( -iname "*.ome.tif" -o -iname "*.ome.tiff" \) \
                -print0 2>/dev/null)

    return 0
}

ensure_pipeline_dirs() {
    echo "Ensuring required folders exist..."
    mkdir -p \
        "${STATE_DIR}" "${LOG_ROOT}" "${SNAKEMAKE_SLURM_LOG_DIR}" "${DONE_DIR}" \
        "${DATA_DIR}" "${ILLUM_DIR}" "${STITCHED_DIR}" \
        "${SEGMENTED_DIR}/mesmer" "${SEGMENTED_DIR}/stardist" \
        "${QUANT_DIR}/mesmer" "${QUANT_DIR}/stardist" \
        "${FILTERED_DIR}" \
        "${FILTERED_TIF_DIR}/mesmer" "${FILTERED_TIF_DIR}/stardist" \
        "${FILTERED_CSV_DIR}/mesmer" "${FILTERED_CSV_DIR}/stardist" \
        "${PIPELINE_TMP_DIR}" "${PIPELINE_CACHE_DIR}" "${XDG_CACHE_HOME}" "${XDG_CONFIG_HOME}" \
        "${MPLCONFIGDIR}" "${NUMBA_CACHE_DIR}" "${PIP_CACHE_DIR}" "${APPTAINER_CACHEDIR}" \
        "${KERAS_HOME}" "${DEEPCELL_CACHE_DIR}" "${MIOPEN_USER_DB_PATH}" "${MIOPEN_CUSTOM_CACHE_DIR}" \
        "${LOG_ROOT}/illumination" "${LOG_ROOT}/stitching" "${LOG_ROOT}/segmentation" \
        "${LOG_ROOT}/segmentation/mesmer" "${LOG_ROOT}/segmentation/stardist" \
        "${LOG_ROOT}/quantification" "${LOG_ROOT}/quantification/mesmer" "${LOG_ROOT}/quantification/stardist" \
        "${LOG_ROOT}/filtering" "${LOG_ROOT}/filtering/mesmer" "${LOG_ROOT}/filtering/stardist" \
        "${LOG_ROOT}/benchmarks/illumination" "${LOG_ROOT}/benchmarks/stitching" "${LOG_ROOT}/benchmarks/mesmer" \
        "${LOG_ROOT}/benchmarks/stardist" "${LOG_ROOT}/benchmarks/quantification" "${LOG_ROOT}/benchmarks/filtering"

    normalize_stitched_layout

    echo "  └─ ✓ Folder check complete"
    echo ""
}

# Returns 0 if the sample passes the raw-presence gate OR if raw is entirely
# absent (single-stage mode running from stitched outputs).
_sample_passes_raw_gate() {
    local s="$1"
    sample_has_raw "${s}" && return 0
    [[ -d "${RAW_DIR}" ]] && find "${RAW_DIR}" -mindepth 2 -maxdepth 2 -type f -iname "*.rcpnl" -print -quit 2>/dev/null | grep -q . && return 1
    return 0
}

_count_stitched_present() {
    local n=0 s f
    while IFS= read -r s; do
        [[ -z "${s}" ]] && continue
        _sample_passes_raw_gate "${s}" || continue
        f="${STITCHED_DIR}/${s}/${s}.ome.tif"
        valid_file "${f}" && n=$((n + 1))
    done < <(sample_list)
    echo "${n}"
}

_count_seg_present() {
    local m="$1" n=0 s f

    if [[ "${m}" == "mesmer" ]]; then
        _count_mesmer_required_present
        return
    fi

    while IFS= read -r s; do
        [[ -z "${s}" ]] && continue
        _sample_passes_raw_gate "${s}" || continue
        f="$(segmentation_mask_path "${m}" "${s}")"
        valid_file "${f}" && n=$((n + 1))
    done < <(sample_list)
    echo "${n}"
}

_count_quant_present() {
    local m="$1" n=0 s f
    while IFS= read -r s; do
        [[ -z "${s}" ]] && continue
        _sample_passes_raw_gate "${s}" || continue
        if [[ "${m}" == "mesmer" ]]; then
            _mesmer_sample_quant_complete "${s}" && n=$((n + 1))
        else
            f="$(quant_csv_path "${m}" "${s}")"
            valid_file "${f}" && n=$((n + 1))
        fi
    done < <(sample_list)
    echo "${n}"
}

_count_filtered_csv_present() {
    local m="$1" n=0 s f
    while IFS= read -r s; do
        [[ -z "${s}" ]] && continue
        _sample_passes_raw_gate "${s}" || continue
        if [[ "${m}" == "mesmer" ]]; then
            _mesmer_sample_filtered_complete "${s}" && n=$((n + 1))
        else
            f="$(filtered_csv_path_shell "${m}" "${s}")"
            valid_file "${f}" && n=$((n + 1))
        fi
    done < <(sample_list)
    echo "${n}"
}

_count_filtered_tif_present() {
    local m="$1" n=0 s marker f
    while IFS= read -r s; do
        [[ -z "${s}" ]] && continue
        _sample_passes_raw_gate "${s}" || continue
        while IFS= read -r marker; do
            [[ -z "${marker}" ]] && continue
            f="$(filtered_tif_path_shell "${m}" "${s}" "${marker}")"
            valid_file "${f}" && n=$((n + 1))
        done < <(marker_list)
    done < <(sample_list)
    echo "${n}"
}

_status_word() {
    local have="$1" want="$2"
    if [[ "${want}" -gt 0 && "${have}" -eq "${want}" ]]; then
        echo complete
    else
        echo incomplete
    fi
}

_print_step_count() {
    printf "  %-24s : %s/%s %s\n" "$1" "$2" "$3" "$(_status_word "$2" "$3")"
}

all_stitched_complete() {
    local w h
    w=$(count_samples)
    h=$(_count_stitched_present)
    [[ "${w}" -gt 0 && "${h}" -eq "${w}" ]]
}

all_mesmer_complete() {
    local w h
    w=$(count_samples)
    h=$(_count_mesmer_required_present)
    [[ "${w}" -gt 0 && "${h}" -eq "${w}" ]]
}

all_stardist_complete() {
    local w h
    w=$(count_samples)
    h=$(_count_seg_present stardist)
    [[ "${w}" -gt 0 && "${h}" -eq "${w}" ]]
}

all_quant_complete_for_method() {
    local m="$1" w h
    w=$(count_samples)
    h=$(_count_quant_present "${m}")
    [[ "${w}" -gt 0 && "${h}" -eq "${w}" ]]
}

all_filtered_complete_for_method() {
    local m="$1" samples markers want_tif have_tif want_csv have_csv
    samples=$(count_samples)
    markers=$(marker_count)
    [[ "${samples}" -gt 0 && "${markers}" -gt 0 ]] || return 1
    want_tif=$((samples * markers))
    want_csv=${samples}
    have_tif=$(_count_filtered_tif_present "${m}")
    have_csv=$(_count_filtered_csv_present "${m}")
    [[ "${have_tif}" -eq "${want_tif}" && "${have_csv}" -eq "${want_csv}" ]]
}

method_final_complete_for_one_method() {
    local m="$1"
    # Final success requires normal quantification plus filtered TIFFs and filtered CSVs.
    all_quant_complete_for_method "${m}" && all_filtered_complete_for_method "${m}"
}

method_final_complete() {
    case "$1" in
        mesmer) method_final_complete_for_one_method mesmer ;;
        stardist) method_final_complete_for_one_method stardist ;;
        both) method_final_complete_for_one_method mesmer && method_final_complete_for_one_method stardist ;;
        *) return 1 ;;
    esac
}

method_segmentation_complete() {
    case "$1" in
        mesmer) all_mesmer_complete ;;
        stardist) all_stardist_complete ;;
        both) all_mesmer_complete && all_stardist_complete ;;
        *) return 1 ;;
    esac
}

print_summary() {
    compute_raw_stats

    if declare -F ui_section >/dev/null 2>&1 && ui_enabled; then
        ui_section "Your dataset" "Overview before processing starts"
        ui_step "Samples to process: ${DATASET_SAMPLES}"
        ui_step "Microscope tile files (.rcpnl): ${DATASET_RAW_FILES}"
        ui_step "Total raw data size: ${DATASET_SIZE_GIB} GiB (about ${DATASET_AVG_GIB} GiB per sample)"
        ui_step "Biological markers for filtering: $(marker_count)"
        ui_note "Marker filtering is enabled for this project."
        ui_blank
    else
        echo "Dataset Summary"
        echo "   Samples        : ${DATASET_SAMPLES}"
        echo "   Raw files      : ${DATASET_RAW_FILES} (.rcpnl)"
        echo "   Total raw size : ${DATASET_SIZE_GIB} GiB"
        echo "   Avg per sample : ${DATASET_AVG_GIB} GiB"
        echo "   Filtering      : required/on"
        echo "   Markers        : $(marker_count)"
        echo ""
    fi
}

sync_state_from_outputs() {
    [[ "${AUTO_SYNC_STATE_FROM_OUTPUTS:-1}" == "1" ]] || return 0

    echo "Smart state sync from existing outputs..."
    mkdir -p "${STATE_DIR}"

    if invalidate_state_for_raw_change; then
        echo "  └─ Raw dataset must be confirmed before output-based state sync continues"
        echo ""
        return 0
    fi

    local stitched_ok=0 segmentation_ok=0 final_ok=0 method="" inferred_method=""
    all_stitched_complete && stitched_ok=1 || true

    if [[ "${stitched_ok}" == "1" ]]; then
        if [[ ! -f "${STATE_DIR}/stitching_complete.flag" ]]; then
            touch "${STATE_DIR}/stitching_complete.flag"
            echo "  - Detected complete stitching outputs → created stitching_complete.flag"
        fi
    else
        rm -f "${STATE_DIR}/stitching_complete.flag" "${STATE_DIR}/stitching_approved.flag"
    fi

    if [[ ! -f "${STATE_DIR}/segmentation_method.txt" ]]; then
        inferred_method="$(infer_method_from_outputs)"
        if [[ -n "${inferred_method}" ]]; then
            echo "${inferred_method}" > "${STATE_DIR}/segmentation_method.txt"
            echo "  - Inferred segmentation method from outputs: ${inferred_method}"
        fi
    fi

    # Also infer Mesmer compartment if needed
    if [[ -f "${STATE_DIR}/segmentation_method.txt" ]]; then
        local method
        method="$(cat "${STATE_DIR}/segmentation_method.txt")"
        if [[ "${method}" == "mesmer" || "${method}" == "both" ]]; then
            if [[ -z "${MESMER_COMPARTMENT:-}" ]]; then
                local inferred_comp
                inferred_comp="$(infer_mesmer_compartment)"
                if [[ -n "${inferred_comp}" ]]; then
                    export MESMER_COMPARTMENT="${inferred_comp}"
                    _MESMER_COMPARTMENT_USER_SET=1
                    echo "  - Inferred Mesmer compartment from outputs: ${inferred_comp}"
                fi
            fi
        fi
    fi

    if [[ -f "${STATE_DIR}/segmentation_method.txt" ]]; then
        method="$(cat "${STATE_DIR}/segmentation_method.txt")"
        case "${method}" in
            mesmer|stardist|both) ;;
            *)
                echo "  - WARNING: invalid segmentation_method.txt value: ${method}"
                rm -f "${STATE_DIR}/segmentation_method.txt"
                method=""
                ;;
        esac
    fi

    if [[ -n "${method}" ]]; then
        method_segmentation_complete "${method}" && segmentation_ok=1 || true
        method_final_complete "${method}" && final_ok=1 || true

        if [[ "${stitched_ok}" == "1" && "${segmentation_ok}" == "1" ]]; then
            [[ "${AUTO_APPROVE_PREVIOUS_STAGES_FROM_OUTPUTS:-1}" == "1" ]] && touch "${STATE_DIR}/stitching_approved.flag"
            if [[ ! -f "${STATE_DIR}/segmentation_complete.flag" ]]; then
                touch "${STATE_DIR}/segmentation_complete.flag"
                echo "  - Detected complete segmentation outputs → created segmentation_complete.flag"
            fi
        else
            rm -f "${STATE_DIR}/segmentation_complete.flag" "${STATE_DIR}/segmentation_approved.flag"
        fi

        if [[ "${stitched_ok}" == "1" && "${segmentation_ok}" == "1" && "${final_ok}" == "1" ]]; then
            [[ "${AUTO_APPROVE_PREVIOUS_STAGES_FROM_OUTPUTS:-1}" == "1" ]] && touch "${STATE_DIR}/stitching_approved.flag" "${STATE_DIR}/segmentation_approved.flag"
            if [[ ! -f "${STATE_DIR}/pipeline_complete.flag" ]]; then
                touch "${STATE_DIR}/pipeline_complete.flag"
                echo "  - Detected complete final outputs → created pipeline_complete.flag"
            fi
        else
            rm -f "${STATE_DIR}/pipeline_complete.flag"
        fi
    else
        rm -f "${STATE_DIR}/segmentation_complete.flag" "${STATE_DIR}/segmentation_approved.flag" "${STATE_DIR}/pipeline_complete.flag"
    fi

    echo "  └─ ✓ Smart state sync complete"
    echo ""
}

print_status() {
    local samples markers want_tif have_tif want_csv have_csv m method
    samples=$(count_samples)
    markers=$(marker_count)

    if declare -F ui_section >/dev/null 2>&1 && ui_enabled; then
        ui_section "Pipeline status" "What is done and what is still missing"
        [[ -f "${STATE_DIR}/segmentation_method.txt" ]] && \
            ui_note "Segmentation method: $(cat "${STATE_DIR}/segmentation_method.txt")"
        ui_note "Mesmer compartment: $(mesmer_compartment_current)"
        raw_dataset_confirmation_needed && \
            ui_warn "Raw dataset still needs your confirmation" || \
            ui_ok "Raw dataset confirmed"
        ui_blank
        ui_note "Progress by step:"
        ui_status_row "Stitched images" "$(_count_stitched_present)" "${samples}"
        for m in $(_methods_from_state_or_all); do
            ui_status_row "${m} cell masks" "$(_count_seg_present "${m}")" "${samples}"
            ui_status_row "${m} quantification tables" "$(_count_quant_present "${m}")" "${samples}"
            want_tif=$((samples * markers))
            ui_status_row "${m} filtered marker images" "$(_count_filtered_tif_present "${m}")" "${want_tif}"
            ui_status_row "${m} filtered result tables" "$(_count_filtered_csv_present "${m}")" "${samples}"
        done
        ui_blank
    else
        echo "Pipeline State:"
        ls -1 "${STATE_DIR}"/*.flag 2>/dev/null | xargs -r -n1 basename || true
        [[ -f "${STATE_DIR}/segmentation_method.txt" ]] && \
            echo "Segmentation method: $(cat "${STATE_DIR}/segmentation_method.txt")"
        echo "Mesmer compartment: $(mesmer_compartment_current)"
        echo "Output detection:"
        _print_step_count "Stitching" "$(_count_stitched_present)" "${samples}"
        for m in $(_methods_from_state_or_all); do
            _print_step_count "${m} masks" "$(_count_seg_present "${m}")" "${samples}"
            _print_step_count "${m} quant CSV" "$(_count_quant_present "${m}")" "${samples}"
            want_tif=$((samples * markers))
            _print_step_count "${m} filtered TIFF" "$(_count_filtered_tif_present "${m}")" "${want_tif}"
            _print_step_count "${m} filtered CSV" "$(_count_filtered_csv_present "${m}")" "${samples}"
        done
    fi
}

print_plan() {
    ensure_pipeline_dirs
    print_summary
    sync_state_from_outputs

    if raw_dataset_confirmation_needed; then
        compute_raw_stats
        write_raw_sample_manifest >/dev/null
        if declare -F ui_section >/dev/null 2>&1 && ui_enabled; then
            ui_section "What happens next" "Before processing can start"
            ui_step "Confirm your raw microscope files"
            ui_note "Samples: ${DATASET_SAMPLES} · files: ${DATASET_RAW_FILES}"
            ui_path "Manifest: ${STATE_DIR}/raw_sample_manifest.tsv"
        else
            echo "Next action: confirm raw dataset (${DATASET_SAMPLES} samples)"
        fi
        return
    fi

    if declare -F ui_section >/dev/null 2>&1 && ui_enabled; then
        ui_section "What happens next" "Based on files already on disk"
    else
        echo "Execution plan"
    fi
    print_status
    ui_blank 2>/dev/null || echo ""

    if [[ ! -f "${STATE_DIR}/stitching_complete.flag" ]]; then
        echo "Next action: run illumination correction + stitching"
        echo "CPU jobs:"
        echo "  Illumination : $(smart_jobs illumination "${ILLUMINATION_JOBS}")"
        echo "  Stitching    : $(smart_jobs stitching "${STITCHING_JOBS}")"
        return
    fi

    if [[ ! -f "${STATE_DIR}/stitching_approved.flag" ]]; then
        echo "Next action: ask user to approve stitched images"
        echo "Stitched images: ${STITCHED_DIR}"
        return
    fi

    if [[ ! -f "${STATE_DIR}/segmentation_complete.flag" ]]; then
        echo "Next action: choose/run segmentation"
        echo "GPU partition: ${SLURM_PARTITION_GPU}"
        echo "GPU jobs:"
        echo "  Mesmer   : $(smart_jobs mesmer "${MESMER_JOBS}")"
        echo "  StarDist : $(smart_jobs stardist "${STARDIST_JOBS}")"
        return
    fi

    if [[ ! -f "${STATE_DIR}/segmentation_approved.flag" ]]; then
        echo "Next action: ask user to approve segmentation masks"
        echo "Segmentation masks: ${SEGMENTED_DIR}"
        return
    fi

    if [[ ! -f "${STATE_DIR}/pipeline_complete.flag" ]]; then
        echo "Next action: run quantification + filtering"
        echo "CPU jobs:"
        echo "  Quantification : $(smart_jobs quantification "${QUANTIFICATION_JOBS}")"
        echo "  Filtering      : $(smart_jobs filtering "${FILTER_JOBS}")"
        return
    fi

    echo "Next action: pipeline already complete"
}

print_method_paths() {
    local method="$1" m
    echo "Routing for selected segmentation method: ${method}"
    echo "  Common raw input            : ${RAW_DIR}/<sample>/*.rcpnl"
    echo "  Stitching output/input      : ${STITCHED_DIR}/<sample>/<sample>.ome.tif"
    for m in $(_methods_from_state_or_all); do
        echo "  ${m} masks                  : $(segmentation_mask_path "${m}" "<sample>")"
        echo "  ${m} quantification         : $(quant_csv_path "${m}" "<sample>")"
        echo "  ${m} filtered TIFFs         : $(filtered_tif_path_shell "${m}" "<sample>" "<marker>")"
        echo "  ${m} filtered CSV           : $(filtered_csv_path_shell "${m}" "<sample>")"
    done
    echo ""
}

cleanup_transient_files() {
    echo ""
    echo "Cleaning transient SLURM/cache files..."

    local protected_prefix="${BASE}"
    local paths_to_remove=(
        "${PIPELINE_TMP_DIR}"
        "${XDG_CACHE_HOME}"
        "${XDG_CONFIG_HOME}"
        "${MPLCONFIGDIR}"
        "${NUMBA_CACHE_DIR}"
        "${PIP_CACHE_DIR}"
        "${MIOPEN_USER_DB_PATH}"
        "${MIOPEN_CUSTOM_CACHE_DIR}"
    )

    [[ "${CLEAN_SLURM_LOGS_ON_SUCCESS:-0}" == "1" ]] && paths_to_remove+=("${SNAKEMAKE_SLURM_LOG_DIR}" "${SCRIPTS_DIR}/.snakemake/slurm_logs")
    [[ "${CLEAN_WORKFLOW_METADATA_ON_SUCCESS:-0}" == "1" ]] && paths_to_remove+=("${SCRIPTS_DIR}/.snakemake" "${DONE_DIR}")
    [[ "${CLEAN_DEEPCELL_CACHE_ON_SUCCESS:-0}" == "1" ]] && paths_to_remove+=("${KERAS_HOME}" "${DEEPCELL_CACHE_DIR}")

    local p
    for p in "${paths_to_remove[@]}"; do
        [[ -n "${p}" ]] || continue
        case "${p}" in
            "${protected_prefix}"/*)
                if [[ -e "${p}" ]]; then
                    echo "  - Removing: ${p}"
                    rm -rf -- "${p}" || true
                fi
                ;;
            *)
                echo "  - SKIP unsafe cleanup path: ${p}"
                ;;
        esac
    done

    # Remove transient lock files created by the pipeline (mesmer cache lock,
    # stardist per-model lock files) — safe to delete after a successful run.
    if [[ -n "${PIPELINE_CACHE_DIR:-}" && "${PIPELINE_CACHE_DIR}" == "${protected_prefix}"/* ]]; then
        find "${PIPELINE_CACHE_DIR}" -maxdepth 1 \
            \( -name "mesmer_cache_setup.lock" -o -name "stardist_model_*.lock" \) \
            -delete 2>/dev/null || true
    fi

    [[ -d "${SCRIPTS_DIR}" ]] && find "${SCRIPTS_DIR}" -type d \
        \( -name "__pycache__" -o -name ".pytest_cache" -o -name ".ipynb_checkpoints" \) \
        -prune -exec rm -rf {} + 2>/dev/null || true

    echo "  └─ ✓ Transient cleanup complete"
    echo ""
}

write_final_summary() {
    local summary_file="${LOG_ROOT}/pipeline_summary_$(date +%Y%m%d_%H%M%S).txt"
    local method="unknown" m samples markers want_tif

    [[ -f "${STATE_DIR}/segmentation_method.txt" ]] && method="$(cat "${STATE_DIR}/segmentation_method.txt")"
    samples=$(count_samples)
    markers=$(marker_count)
    want_tif=$((samples * markers))

    {
        echo "Pipeline summary"
        echo "================"
        echo "Date                     : $(date)"
        echo "BASE                     : ${BASE}"
        echo "Samples                  : ${DATASET_SAMPLES:-unknown}"
        echo "Raw files                : ${DATASET_RAW_FILES:-unknown}"
        echo "Raw size GiB             : ${DATASET_SIZE_GIB:-unknown}"
        echo "Segmentation method      : ${method}"
        echo "Mesmer compartment       : $(mesmer_compartment_current)"
        echo "Filtering                : required/on"
        echo "Markers                  : ${markers}"
        echo "Stitching complete       : $(all_stitched_complete && echo yes || echo no) [$(_count_stitched_present)/${samples}]"
        for m in $(_methods_from_state_or_all); do
            echo "${m} masks complete      : $(_status_word "$(_count_seg_present "${m}")" "${samples}") [$(_count_seg_present "${m}")/${samples}]"
            echo "${m} quant complete      : $(all_quant_complete_for_method "${m}" && echo yes || echo no) [$(_count_quant_present "${m}")/${samples}]"
            echo "${m} filtered TIFFs      : $(_count_filtered_tif_present "${m}")/${want_tif}"
            echo "${m} filtered CSV        : $(_count_filtered_csv_present "${m}")/${samples}"
        done
        echo "Final complete           : $(method_final_complete "${method}" && echo yes || echo no)"
        echo "Logs                     : ${LOG_ROOT}"
    } > "${summary_file}"

    echo "Final summary written: ${summary_file}"
}

# ============================================================
# Stage-isolated overrides / safety hardening
# Added to make --only/--from/--until runs truly independent.
# ============================================================

raw_file_total_count() {
    if [[ -d "${RAW_DIR}" ]]; then
        find "${RAW_DIR}" -mindepth 2 -maxdepth 2 -type f -iname "*.rcpnl" 2>/dev/null | wc -l | awk '{print $1}'
    else
        echo 0
    fi
}

stitched_sample_count() {
    if declare -F normalize_stitched_layout >/dev/null 2>&1; then
        normalize_stitched_layout >/dev/null 2>&1 || true
    fi
    _count_stitched_present 2>/dev/null || echo 0
}

selected_stage_label() {
    local parts=()
    [[ "${RUN_STAGE_STITCHING:-0}" == "1" ]] && parts+=("stitching")
    [[ "${RUN_STAGE_SEGMENTATION:-0}" == "1" ]] && parts+=("segmentation")
    if [[ "${RUN_STAGE_QUANT_FILTER:-0}" == "1" ]]; then
        [[ "${RUN_SUBSTAGE_QUANT:-1}" == "1" ]] && parts+=("quantification")
        [[ "${RUN_SUBSTAGE_FILTER:-1}" == "1" ]] && parts+=("filtering")
    fi
    if [[ "${#parts[@]}" -eq 0 ]]; then
        echo "none"
    else
        local IFS=", "
        echo "${parts[*]}"
    fi
}

# Output-based state sync must not invalidate downstream-only runs because raw
# files are missing/changed. Raw fingerprinting is relevant only when stage 1 is
# selected and still needs to run.
sync_state_from_outputs() {
    [[ "${AUTO_SYNC_STATE_FROM_OUTPUTS:-1}" == "1" ]] || return 0

    echo "Smart state sync from existing outputs..."
    mkdir -p "${STATE_DIR}"

    if [[ "${RUN_STAGE_STITCHING:-1}" == "1" && ! -f "${STATE_DIR}/stitching_complete.flag" ]]; then
        if invalidate_state_for_raw_change; then
            echo "  └─ Raw dataset must be confirmed before output-based state sync continues"
            echo ""
            return 0
        fi
    fi

    local stitched_ok=0 segmentation_ok=0 final_ok=0 method="" inferred_method=""
    all_stitched_complete && stitched_ok=1 || true

    if [[ "${stitched_ok}" == "1" ]]; then
        if [[ ! -f "${STATE_DIR}/stitching_complete.flag" ]]; then
            touch "${STATE_DIR}/stitching_complete.flag"
            echo "  - Detected complete stitching outputs → created stitching_complete.flag"
        fi
        if [[ "${AUTO_APPROVE_PREVIOUS_STAGES_FROM_OUTPUTS:-1}" == "1" ]]; then
            touch "${STATE_DIR}/stitching_approved.flag"
        fi
    else
        # Only clear stitching state when stage 1 is actually part of this run.
        # For downstream-only runs, absence of raw/partial stitched discovery
        # should not delete useful approval flags.
        if [[ "${RUN_STAGE_STITCHING:-1}" == "1" ]]; then
            rm -f "${STATE_DIR}/stitching_complete.flag" "${STATE_DIR}/stitching_approved.flag"
        fi
    fi

    if [[ ! -f "${STATE_DIR}/segmentation_method.txt" ]]; then
        inferred_method="$(infer_method_from_outputs)"
        if [[ -n "${inferred_method}" ]]; then
            echo "${inferred_method}" > "${STATE_DIR}/segmentation_method.txt"
            echo "  - Inferred segmentation method from outputs: ${inferred_method}"
        fi
    fi

    if [[ -f "${STATE_DIR}/segmentation_method.txt" ]]; then
        method="$(cat "${STATE_DIR}/segmentation_method.txt" | tr '[:upper:]' '[:lower:]' | xargs)"
        case "${method}" in
            mesmer|stardist|both)
                echo "${method}" > "${STATE_DIR}/segmentation_method.txt"
                ;;
            *)
                echo "  - WARNING: invalid segmentation_method.txt value: ${method}"
                rm -f "${STATE_DIR}/segmentation_method.txt"
                method=""
                ;;
        esac
    fi

    if [[ -n "${method}" && ( "${method}" == "mesmer" || "${method}" == "both" ) ]]; then
        if [[ -z "${MESMER_COMPARTMENT:-}" ]]; then
            local inferred_comp
            inferred_comp="$(infer_mesmer_compartment)"
            if [[ -n "${inferred_comp}" ]]; then
                export MESMER_COMPARTMENT="${inferred_comp}"
                _MESMER_COMPARTMENT_USER_SET=1
                echo "  - Inferred Mesmer compartment from outputs: ${inferred_comp}"
            fi
        fi
    fi

    if [[ -n "${method}" ]]; then
        method_segmentation_complete "${method}" && segmentation_ok=1 || true
        method_final_complete "${method}" && final_ok=1 || true

        if [[ "${stitched_ok}" == "1" && "${segmentation_ok}" == "1" ]]; then
            [[ "${AUTO_APPROVE_PREVIOUS_STAGES_FROM_OUTPUTS:-1}" == "1" ]] && touch "${STATE_DIR}/stitching_approved.flag"
            if [[ ! -f "${STATE_DIR}/segmentation_complete.flag" ]]; then
                touch "${STATE_DIR}/segmentation_complete.flag"
                echo "  - Detected complete segmentation outputs → created segmentation_complete.flag"
            fi
            [[ "${AUTO_APPROVE_PREVIOUS_STAGES_FROM_OUTPUTS:-1}" == "1" ]] && touch "${STATE_DIR}/segmentation_approved.flag"
        else
            # Do not delete segmentation flags in a run that is not touching
            # segmentation/stage 3; otherwise a partial folder scan can erase
            # useful state before the intended stage starts.
            if [[ "${RUN_STAGE_SEGMENTATION:-0}" == "1" || "${RUN_STAGE_QUANT_FILTER:-0}" == "1" ]]; then
                rm -f "${STATE_DIR}/segmentation_complete.flag" "${STATE_DIR}/segmentation_approved.flag"
            fi
        fi

        if [[ "${stitched_ok}" == "1" && "${segmentation_ok}" == "1" && "${final_ok}" == "1" ]]; then
            [[ "${AUTO_APPROVE_PREVIOUS_STAGES_FROM_OUTPUTS:-1}" == "1" ]] && touch "${STATE_DIR}/stitching_approved.flag" "${STATE_DIR}/segmentation_approved.flag"
            if [[ ! -f "${STATE_DIR}/pipeline_complete.flag" ]]; then
                touch "${STATE_DIR}/pipeline_complete.flag"
                echo "  - Detected complete final outputs → created pipeline_complete.flag"
            fi
        else
            if [[ "${RUN_STAGE_QUANT_FILTER:-0}" == "1" ]]; then
                rm -f "${STATE_DIR}/pipeline_complete.flag"
            fi
        fi
    else
        if [[ "${RUN_STAGE_SEGMENTATION:-0}" == "1" || "${RUN_STAGE_QUANT_FILTER:-0}" == "1" ]]; then
            rm -f "${STATE_DIR}/segmentation_complete.flag" "${STATE_DIR}/segmentation_approved.flag" "${STATE_DIR}/pipeline_complete.flag"
        fi
    fi

    echo "  └─ ✓ Smart state sync complete"
    echo ""
}
