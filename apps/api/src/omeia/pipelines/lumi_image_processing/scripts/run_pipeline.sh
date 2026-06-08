#!/bin/bash
# ============================================================
# run_pipeline.sh — Unified smart image-processing launcher
#
# Usage:
#   bash run_pipeline.sh                    # Smart normal run
#   bash run_pipeline.sh --status           # Show pipeline state
#   bash run_pipeline.sh --plan             # Show next action without submitting jobs
#   bash run_pipeline.sh --doctor           # Check config, folders, tools, containers
#   bash run_pipeline.sh --sync-state       # Sync state flags from real output files
#   bash run_pipeline.sh --reset            # Delete state flags only; data is not deleted
#   bash run_pipeline.sh --resume-from stitching_approved
#   bash run_pipeline.sh --clean-transient  # Remove temporary SLURM/cache files only
#
# Single-stage / partial runs:
#   bash run_pipeline.sh --only stitching        # Run ONLY stage 1 (illumination + stitching)
#   bash run_pipeline.sh --only segmentation
#   bash run_pipeline.sh --only quantification
#   bash run_pipeline.sh --only filtering
#   bash run_pipeline.sh --from segmentation     # Run this stage and everything after
#   bash run_pipeline.sh --until segmentation    # Run up to and including this stage
#
# Valid stage names:
#   stitching | illumination   -> stage 1 (illumination correction + stitching)
#   segmentation               -> stage 2
#   quantification | filtering -> stage 3
# ============================================================
set -euo pipefail

# Stage gating (set by --only/--from/--until). Default = run everything.
RUN_STAGE_STITCHING=1
RUN_STAGE_SEGMENTATION=1
RUN_STAGE_QUANT_FILTER=1
# Sub-gates inside stage 3 (only meaningful when RUN_STAGE_QUANT_FILTER=1).
RUN_SUBSTAGE_QUANT=1
RUN_SUBSTAGE_FILTER=1

_stage_index() {
    case "$1" in
        stitching|illumination|illum) echo 1 ;;
        segmentation|seg) echo 2 ;;
        quantification|quant) echo 3 ;;
        filtering|filter) echo 3 ;;
        *) echo "" ;;
    esac
}

_apply_only() {
    local s="$1"
    RUN_STAGE_STITCHING=0
    RUN_STAGE_SEGMENTATION=0
    RUN_STAGE_QUANT_FILTER=0
    case "${s}" in
        stitching|illumination|illum) RUN_STAGE_STITCHING=1 ;;
        segmentation|seg)             RUN_STAGE_SEGMENTATION=1 ;;
        quantification|quant)
            RUN_STAGE_QUANT_FILTER=1
            RUN_SUBSTAGE_QUANT=1
            RUN_SUBSTAGE_FILTER=0
            ;;
        filtering|filter)
            RUN_STAGE_QUANT_FILTER=1
            RUN_SUBSTAGE_QUANT=0
            RUN_SUBSTAGE_FILTER=1
            ;;
        *) echo "ERROR: unknown stage for --only: ${s}"; exit 1 ;;
    esac
}

_apply_from() {
    local s="$1"
    local idx
    idx="$(_stage_index "${s}")"
    [[ -z "${idx}" ]] && { echo "ERROR: unknown stage for --from: ${s}"; exit 1; }
    [[ "${idx}" -gt 1 ]] && RUN_STAGE_STITCHING=0
    [[ "${idx}" -gt 2 ]] && RUN_STAGE_SEGMENTATION=0
    # Within stage 3: --from filtering => skip quant sub-stage.
    case "${s}" in
        filtering|filter) RUN_SUBSTAGE_QUANT=0 ;;
    esac
}

_apply_until() {
    local s="$1"
    local idx
    idx="$(_stage_index "${s}")"
    [[ -z "${idx}" ]] && { echo "ERROR: unknown stage for --until: ${s}"; exit 1; }
    [[ "${idx}" -lt 2 ]] && RUN_STAGE_SEGMENTATION=0
    [[ "${idx}" -lt 3 ]] && RUN_STAGE_QUANT_FILTER=0
    # Within stage 3: --until quantification => skip filter sub-stage.
    case "${s}" in
        quantification|quant) RUN_SUBSTAGE_FILTER=0 ;;
    esac
}

# Track whether user already constrained the run via CLI flags.
STAGE_FLAGS_FROM_CLI=0

select_run_mode_interactive() {
    # Show an interactive dropdown menu when:
    #   - stdin is a TTY (real user, not cron/SLURM)
    #   - the user did NOT already pass --only/--from/--until on the CLI
    #   - INTERACTIVE_MENU is not explicitly disabled
    [[ "${INTERACTIVE_MENU:-1}" == "1" ]] || return 0
    [[ "${STAGE_FLAGS_FROM_CLI}" == "1" ]] && return 0
    [[ -t 0 ]] || return 0

    ui_blank
    ui_section "What would you like to run?" "Choose one option"
    ui_step "1 — Full pipeline (recommended, resumes where you left off)"
    ui_step "2 — Step 1 only: fix lighting + stitch tiles into one image"
    ui_step "3 — Step 2 only: find cells (segmentation)"
    ui_step "4 — Step 3a only: measure marker intensity in each cell"
    ui_step "5 — Step 3b only: enhance markers and re-measure"
    ui_step "6 — Start from a chosen step onward"
    ui_step "7 — Run up to and including a chosen step"
    ui_step "0 — Cancel"
    ui_blank

    local choice
    read -p "Enter choice [1-7] (default: 1): " -r choice
    choice="${choice:-1}"

    case "${choice}" in
        1) ;;  # complete — keep defaults
        2) _apply_only stitching ;;
        3) _apply_only segmentation ;;
        4) _apply_only quantification ;;
        5) _apply_only filtering ;;
        6)
            local s
            read -p "  From which stage? [illumination|segmentation|quantification|filtering]: " -r s
            _apply_from "${s}"
            ;;
        7)
            local s
            read -p "  Up to which stage? [illumination|segmentation|quantification|filtering]: " -r s
            _apply_until "${s}"
            ;;
        0) echo "Cancelled."; exit 0 ;;
        *) echo "Invalid choice: ${choice}"; exit 1 ;;
    esac

    echo ""
    local q_state f_state
    if [[ "${RUN_STAGE_QUANT_FILTER}" == "1" ]]; then
        q_state="$([[ "${RUN_SUBSTAGE_QUANT}" == "1" ]] && echo run || echo skip)"
        f_state="$([[ "${RUN_SUBSTAGE_FILTER}" == "1" ]] && echo run || echo skip)"
    else
        q_state=skip
        f_state=skip
    fi

    ui_section "Your plan" "These steps will run in this session"
    ui_step "Step 1 — Lighting + stitching: $([[ "${RUN_STAGE_STITCHING}" == "1" ]] && echo yes || echo skip)"
    ui_step "Step 2 — Cell segmentation: $([[ "${RUN_STAGE_SEGMENTATION}" == "1" ]] && echo yes || echo skip)"
    ui_step "Step 3a — Marker quantification: ${q_state}"
    ui_step "Step 3b — Marker filtering: ${f_state}"
    ui_blank
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/pipeline_config.sh"
LIB_DIR="${SCRIPT_DIR}/lib"

if [[ ! -f "${CONFIG_FILE}" ]]; then
    echo "ERROR: Configuration file not found: ${CONFIG_FILE}"
    exit 1
fi

if [[ ! -f "${LIB_DIR}/pipeline_state.sh" || ! -f "${LIB_DIR}/pipeline_slurm.sh" ]]; then
    echo "ERROR: Required library files not found in: ${LIB_DIR}"
    echo "Expected:"
    echo "  ${LIB_DIR}/pipeline_state.sh"
    echo "  ${LIB_DIR}/pipeline_slurm.sh"
    exit 1
fi

source "${CONFIG_FILE}"
source "${LIB_DIR}/pipeline_ui.sh"
source "${LIB_DIR}/pipeline_state.sh"
source "${LIB_DIR}/pipeline_slurm.sh"

# Never accept a pre-exported DeepCell token.
unset DEEPCELL_ACCESS_TOKEN || true
unset APPTAINERENV_DEEPCELL_ACCESS_TOKEN || true
unset SINGULARITYENV_DEEPCELL_ACCESS_TOKEN || true

clear_deepcell_token_on_exit() {
    unset DEEPCELL_ACCESS_TOKEN || true
    unset APPTAINERENV_DEEPCELL_ACCESS_TOKEN || true
    unset SINGULARITYENV_DEEPCELL_ACCESS_TOKEN || true
}

launcher_exit_cleanup() {
    local status="$?"
    clear_deepcell_token_on_exit || true
    if declare -F unlock_snakemake_workdir >/dev/null 2>&1; then
        unlock_snakemake_workdir || true
    fi
    return "${status}"
}

trap launcher_exit_cleanup EXIT

initialize_launcher_log() {
    mkdir -p "${STATE_DIR}" "${LOG_ROOT}" "${SNAKEMAKE_SLURM_LOG_DIR}"

    RUN_LOG="${LOG_ROOT}/run_pipeline_launcher_$(date +%Y%m%d_%H%M%S).log"
    exec > >(tee -a "${RUN_LOG}") 2>&1

    if ui_enabled; then
        ui_title "${PIPELINE_TITLE:-Microscopy image processing pipeline}"
        ui_note "Session log (everything): ${RUN_LOG}"
        ui_path "Project folder: ${BASE}"
        ui_dim "Technical details: set PIPELINE_VERBOSE_LOG=1"
        ui_blank
    else
        echo "Launcher log: ${RUN_LOG}"
        echo "BASE          : ${BASE}"
        echo ""
    fi

    if ui_verbose; then
        echo "Running script: $(readlink -f "$0")"
        echo "Config file   : ${CONFIG_FILE}"
        echo "PWD           : $(pwd)"
        echo ""
    fi

    if [[ "${SHOW_DIRECTORY_REPORT:-0}" == "1" ]] && declare -F pipeline_config_print_directories >/dev/null 2>&1; then
        pipeline_config_print_directories
    fi
}

usage() {
    grep "^#" "$0" | head -n 20
}

handle_command_line() {
    case "${1:-}" in
        --status)
            ensure_pipeline_dirs
            sync_state_from_outputs
            print_status
            exit 0
            ;;

        --plan)
            print_plan
            exit 0
            ;;

        --doctor)
            doctor
            exit 0
            ;;

        --sync-state)
            ensure_pipeline_dirs
            print_summary
            sync_state_from_outputs
            print_status
            exit 0
            ;;

        --reset)
            echo "Resetting pipeline state..."
            rm -f "${STATE_DIR}"/*.flag "${STATE_DIR}/segmentation_method.txt" "${STATE_DIR}/mesmer_compartment.txt"
            unset MESMER_COMPARTMENT 2>/dev/null || true
            echo "Done. Data is NOT deleted."
            exit 0
            ;;

        --resume-from)
            if [[ -z "${2:-}" ]]; then
                echo "Need stage to resume from."
                exit 1
            fi

            mkdir -p "${STATE_DIR}"
            touch "${STATE_DIR}/${2}.flag"
            echo "Set ${2}.flag"
            echo "NOTE: --sync-state or normal run will still verify real outputs."
            exit 0
            ;;

        --clean-transient)
            cleanup_transient_files
            exit 0
            ;;

        --only)
            [[ -z "${2:-}" ]] && { echo "ERROR: --only requires a stage name"; exit 1; }
            _apply_only "$2"
            STAGE_FLAGS_FROM_CLI=1
            shift 2
            handle_command_line "$@"
            return $?
            ;;

        --from)
            [[ -z "${2:-}" ]] && { echo "ERROR: --from requires a stage name"; exit 1; }
            _apply_from "$2"
            STAGE_FLAGS_FROM_CLI=1
            shift 2
            handle_command_line "$@"
            return $?
            ;;

        --until)
            [[ -z "${2:-}" ]] && { echo "ERROR: --until requires a stage name"; exit 1; }
            _apply_until "$2"
            STAGE_FLAGS_FROM_CLI=1
            shift 2
            handle_command_line "$@"
            return $?
            ;;

        --help|-h)
            usage
            exit 0
            ;;

        "")
            return 0
            ;;

        *)
            echo "ERROR: Unknown option: ${1}"
            echo ""
            usage
            exit 1
            ;;
    esac
}

_print_pipeline_complete_banner() {
    local method="$1" n_samples="$2" markers="$3" want_tif="$4"

    local n_stitched n_seg n_quant n_fcsv n_ftif m comp_label
    n_stitched=$(_count_stitched_present)
    comp_label="$(mesmer_compartment_current)"

    if ui_enabled; then
        ui_title "All done — pipeline finished successfully"
        ui_note "Finished: $(date '+%Y-%m-%d %H:%M:%S')"
        ui_path "Project folder: ${BASE}"
        ui_blank
        ui_section "Step 1 — Prepare images" "Lighting correction + stitching"
        ui_status_row "Stitched whole-slide images" "${n_stitched}" "${n_samples}"
        ui_note "Files: <sample>/<sample>.ome.tif in ${STITCHED_DIR}"
        ui_blank
        ui_section "Step 2 — Find cells" "Segmentation (${method})"
        for m in $(_methods_from_selection "${method}"); do
            n_seg=$(_count_seg_present "${m}")
            if [[ "${m}" == "mesmer" ]]; then
                ui_status_row "Mesmer cell masks (${comp_label})" "${n_seg}" "${n_samples}"
            else
                ui_status_row "StarDist nuclear masks" "${n_seg}" "${n_samples}"
            fi
        done
        ui_path "Masks folder: ${SEGMENTED_DIR}"
        ui_blank
        ui_section "Step 3 — Measure markers" "Quantification + filtering"
        for m in $(_methods_from_selection "${method}"); do
            n_quant=$(_count_quant_present "${m}")
            n_fcsv=$(_count_filtered_csv_present "${m}")
            n_ftif=$(_count_filtered_tif_present "${m}")
            ui_status_row "${m} quantification tables" "${n_quant}" "${n_samples}"
            ui_status_row "${m} filtered result tables" "${n_fcsv}" "${n_samples}"
            ui_status_row "${m} enhanced marker images" "${n_ftif}" "${want_tif}"
        done
        ui_note "Markers configured: ${markers}"
        ui_path "All logs: ${LOG_ROOT}"
        ui_blank
        return
    fi

    echo "PIPELINE COMPLETED SUCCESSFULLY — $(date '+%Y-%m-%d %H:%M:%S')"
    echo "  Stitched: ${n_stitched}/${n_samples}  Logs: ${LOG_ROOT}"
    echo ""
}

run_stage_1_illumination_and_stitching() {
    if [[ -f "${STATE_DIR}/stitching_complete.flag" ]]; then
        return 0
    fi

    ui_stage_start "1" "Prepare images" "Fix uneven lighting, then stitch microscope tiles into one whole-slide image"

    local ijobs sjobs n_samples n_stitched
    n_samples=$(count_samples)

    # --- Sub-step 1a: Illumination Correction ---
    ijobs=$(smart_jobs illumination "${ILLUMINATION_JOBS}")
    run_snakemake "Illumination Correction" "stage_illumination" "${ijobs}" "cpu"
    ui_ok "Lighting correction finished"

    # --- Sub-step 1b: Stitching ---
    sjobs=$(smart_jobs stitching "${STITCHING_JOBS}")
    run_snakemake "Ashlar Stitching" "stage_stitching" "${sjobs}" "cpu"

    # --- Validate + Retry ---
    n_stitched=$(_count_stitched_present)
    if [[ "${n_stitched}" -lt "${n_samples}" ]]; then
        echo "  ├─ ⚠ Validation: ${n_stitched}/${n_samples} stitched — retrying missing samples..."
        run_snakemake "Stitching (retry missing)" "stage_stitching" "${sjobs}" "cpu"
        n_stitched=$(_count_stitched_present)
    fi

    if all_stitched_complete; then
        touch "${STATE_DIR}/stitching_complete.flag"
    else
        echo "  ├─ ✗ Validation failed: ${n_stitched}/${n_samples} stitched after retry."
        echo "  │    Run: bash run_pipeline.sh --status"
        exit 1
    fi

    local n_stitched n_samples
    n_stitched=$(_count_stitched_present)
    n_samples=$(count_samples)

    ui_section "Step 1 complete" "Your stitched whole-slide images are ready"
    ui_ok "${n_stitched} of ${n_samples} samples stitched successfully"
    ui_path "Output folder: ${STITCHED_DIR}"
    ui_note "Each sample is saved as <sample>/<sample>.ome.tif"
    ui_review_prompt "stitched whole-slide images" "${STITCHED_DIR}"
    exit 0
}

review_stitching_if_needed() {
    if [[ -f "${STATE_DIR}/stitching_approved.flag" ]]; then
        return 0
    fi

    ui_section "Quick check" "Please confirm the stitched images look correct"
    read -p "Have you checked and approved the stitched images? [y/N] " -r

    if [[ ${REPLY} =~ ^[Yy]$ ]]; then
        if all_stitched_complete; then
            touch "${STATE_DIR}/stitching_approved.flag"
            echo "  └─ ✓ Stitching approved."
        else
            echo "ERROR: Cannot approve stitching because stitched outputs are incomplete."
            echo "Run: bash run_pipeline.sh --status"
            exit 1
        fi
    else
        echo "Stopping."
        exit 0
    fi
}

configure_segmentation_interactive() {
    local method=""
    [[ -f "${STATE_DIR}/segmentation_method.txt" ]] && method="$(cat "${STATE_DIR}/segmentation_method.txt")"

    local compartment="${MESMER_COMPARTMENT:-}"
    local compartment_file="${STATE_DIR}/mesmer_compartment.txt"
    local compartment_choice_flag="${STATE_DIR}/mesmer_compartment_choice_v2.flag"

    if [[ -s "${compartment_file}" && -f "${compartment_choice_flag}" ]]; then
        compartment="$(tr -d '[:space:]' < "${compartment_file}")"
        case "${compartment}" in
            nuclear|whole-cell|both)
                export MESMER_COMPARTMENT="${compartment}"
                _MESMER_COMPARTMENT_USER_SET=1
                ;;
            *)
                compartment=""
                ;;
        esac
    fi

    # If fully configured, skip.
    if [[ -n "${method}" ]]; then
        if [[ "${method}" == "stardist" ]] || [[ "${_MESMER_COMPARTMENT_USER_SET:-0}" == "1" ]]; then
            return 0
        fi
    fi

    # Sequential flow
    echo "Configure segmentation settings:"

    # 1. Method
    echo "  1) Mesmer"
    echo "  2) StarDist"
    echo "  3) Both"

    local m_default=""
    case "${method}" in
        mesmer) m_default="1" ;;
        stardist) m_default="2" ;;
        both) m_default="3" ;;
    esac

    local m_choice
    if [[ -n "${m_default}" ]]; then
        read -p "Choose segmentation method [1/2/3] (default: ${m_default}): " -r
        m_choice="${REPLY:-${m_default}}"
    else
        read -p "Choose segmentation method [1/2/3]: " -r
        m_choice="${REPLY}"
    fi

    case "${m_choice}" in
        1) method="mesmer" ;;
        2) method="stardist" ;;
        3) method="both" ;;
        *) echo "Invalid choice."; exit 1 ;;
    esac
    echo "${method}" > "${STATE_DIR}/segmentation_method.txt"

    # 2. Mesmer compartment
    if [[ "${method}" == "mesmer" || "${method}" == "both" ]]; then
        echo ""
        echo "Choose Mesmer compartment:"
        echo "  1) Nuclear only"
        echo "  2) Whole-cell only"
        echo "  3) Both nuclear and whole-cell"

        local c_default="3"
        case "${compartment}" in
            nuclear) c_default="1" ;;
            whole-cell) c_default="2" ;;
            both) c_default="3" ;;
        esac

        local c_choice
        read -p "Choose Mesmer compartment [1/2/3] (default: ${c_default}): " -r
        c_choice="${REPLY:-${c_default}}"

        case "${c_choice}" in
            1) compartment="nuclear" ;;
            2) compartment="whole-cell" ;;
            3) compartment="both" ;;
            *) echo "Invalid Mesmer compartment choice."; exit 1 ;;
        esac

        export MESMER_COMPARTMENT="${compartment}"
        _MESMER_COMPARTMENT_USER_SET=1
        printf '%s\n' "${compartment}" > "${compartment_file}"
        touch "${compartment_choice_flag}"
        echo "Mesmer compartment: ${compartment}"
    fi
}

cap_segmentation_jobs() {
    local method="$1"
    local jobs="$2"
    local cap="${SEGMENTATION_JOB_CAP:-${MAX_GPU_JOBS:-4}}"

    # Defensive default for GPU segmentation: never allow an empty/invalid cap.
    if ! [[ "${cap}" =~ ^[0-9]+$ ]] || [[ "${cap}" -lt 1 ]]; then
        cap=32
    fi

    if ! [[ "${jobs}" =~ ^[0-9]+$ ]] || [[ "${jobs}" -lt 1 ]]; then
        jobs=1
    fi

    if [[ "${jobs}" -gt "${cap}" ]]; then
        # Informational message must go to stderr; this function's stdout is
        # captured by the caller via $(...) and used as the --jobs value.
        if declare -F ui_warn >/dev/null 2>&1; then
            ui_warn "Limiting ${method} parallel jobs: ${jobs} → ${cap} (one LUMI GCD per image)" >&2
        else
            echo "  ├─ Capping ${method} parallel jobs: ${jobs} → ${cap}" >&2
        fi
        jobs="${cap}"
    fi

    echo "${jobs}"
}

run_stage_2_segmentation() {
    if [[ -f "${STATE_DIR}/segmentation_complete.flag" ]]; then
        return 0
    fi

    ui_blank
    ui_stage_start "2" "Find cells" "Segment nuclei and/or whole cells using Mesmer or StarDist"

    configure_segmentation_interactive

    local method
    method="$(cat "${STATE_DIR}/segmentation_method.txt")"

    ui_note "Segmentation method: ${method}"
    if [[ "${method}" == "mesmer" || "${method}" == "both" ]]; then
        ui_note "Mesmer will segment: ${MESMER_COMPARTMENT:-nuclear}"
    fi
    if declare -F ensure_runnable_samples_available >/dev/null 2>&1; then
        ensure_runnable_samples_available "segmentation" || exit 1
    fi
    echo "  ├─ Segmentation partition forced to: ${SLURM_PARTITION_GPU}"
    print_method_paths "${method}"

    if [[ "${method}" == "mesmer" || "${method}" == "both" ]]; then
        prompt_deepcell_token_always
    fi

    validate_method_inputs "${method}"

    # Keep Snakemake's target list aligned with the interactive/state method choice.
    export SEGMENTATION_METHOD="${method}"
    export PIPELINE_SEGMENTATION_METHOD="${method}"

    if [[ "${method}" == "mesmer" || "${method}" == "both" ]]; then
        local jobs n_seg_m
        jobs=$(smart_jobs mesmer "${MESMER_JOBS:-auto}")
        jobs=$(cap_segmentation_jobs "Mesmer" "${jobs}")
        run_snakemake "Mesmer Segmentation" "stage_segmentation_mesmer" "${jobs}" "gpu"

        # Validate + Retry
        n_seg_m=$(_count_seg_present mesmer)
        if [[ "${n_seg_m}" -lt "$(count_samples)" ]]; then
            echo "  ├─ ⚠ Validation: ${n_seg_m}/$(count_samples) mesmer masks — retrying missing..."
            run_snakemake "Mesmer Segmentation (retry)" "stage_segmentation_mesmer" "${jobs}" "gpu"
        fi

        unset DEEPCELL_ACCESS_TOKEN || true
        unset APPTAINERENV_DEEPCELL_ACCESS_TOKEN || true
        unset SINGULARITYENV_DEEPCELL_ACCESS_TOKEN || true
        echo "  ├─ DeepCell token cleared from launcher environment."
    fi

    if [[ "${method}" == "stardist" || "${method}" == "both" ]]; then
        local jobs n_seg_s
        jobs=$(smart_jobs stardist "${STARDIST_JOBS:-auto}")
        jobs=$(cap_segmentation_jobs "StarDist" "${jobs}")
        run_snakemake "StarDist Segmentation" "stage_segmentation_stardist" "${jobs}" "gpu"

        # Validate + Retry
        n_seg_s=$(_count_seg_present stardist)
        if [[ "${n_seg_s}" -lt "$(count_samples)" ]]; then
            echo "  ├─ ⚠ Validation: ${n_seg_s}/$(count_samples) stardist masks — retrying missing..."
            run_snakemake "StarDist Segmentation (retry)" "stage_segmentation_stardist" "${jobs}" "gpu"
        fi
    fi

    if method_segmentation_complete "${method}"; then
        touch "${STATE_DIR}/segmentation_complete.flag"
    else
        echo "  ├─ ✗ Validation failed: segmentation outputs still incomplete for method: ${method}"
        echo "  │    Run: bash run_pipeline.sh --status"
        exit 1
    fi

    local n_masks n_samples comp_label
    n_samples=$(count_samples)
    comp_label="$(mesmer_compartment_current)"

    ui_section "Step 2 complete" "Cell masks are ready for your review"
    if [[ "${method}" == "mesmer" || "${method}" == "both" ]]; then
        n_masks=$(_count_seg_present mesmer)
        ui_ok "Mesmer: ${n_masks} of ${n_samples} samples (compartment: ${comp_label})"
    fi
    if [[ "${method}" == "stardist" || "${method}" == "both" ]]; then
        n_masks=$(_count_seg_present stardist)
        ui_ok "StarDist: ${n_masks} of ${n_samples} samples"
    fi
    ui_path "Masks folder: ${SEGMENTED_DIR}"
    ui_review_prompt "segmentation masks" "${SEGMENTED_DIR}"
    exit 0
}

review_segmentation_if_needed() {
    if [[ -f "${STATE_DIR}/segmentation_approved.flag" ]]; then
        return 0
    fi

    ui_section "Quick check" "Please confirm the cell masks look correct"
    read -p "Have you checked and approved the segmentation masks? [y/N] " -r

    local method=""
    [[ -f "${STATE_DIR}/segmentation_method.txt" ]] && method="$(cat "${STATE_DIR}/segmentation_method.txt")"
    if [[ -z "${method}" ]]; then
        echo "ERROR: No segmentation method configured. Cannot review."
        exit 1
    fi

    if [[ ${REPLY} =~ ^[Yy]$ ]]; then
        if method_segmentation_complete "${method}"; then
            touch "${STATE_DIR}/segmentation_approved.flag"
            echo "  └─ ✓ Segmentation approved."
        else
            echo "ERROR: Cannot approve segmentation because outputs are incomplete for method: ${method}"
            echo "Run: bash run_pipeline.sh --status"
            exit 1
        fi
    else
        echo "Stopping."
        exit 0
    fi
}

_methods_from_selection() {
    local method="$1"

    case "${method}" in
        mesmer)
            echo "mesmer"
            ;;
        stardist)
            echo "stardist"
            ;;
        both)
            echo "mesmer stardist"
            ;;
        *)
            echo "ERROR: Unknown segmentation method: ${method}" >&2
            return 1
            ;;
    esac
}

run_quantification_and_filtering_for_method() {
    local selected_method="$1"
    local methods
    methods="$(_methods_from_selection "${selected_method}")"
    local n_samples
    n_samples=$(count_samples)

    local m
    for m in ${methods}; do
        if [[ "${RUN_SUBSTAGE_QUANT:-1}" == "1" ]]; then
            local qjobs n_quant target_q
            qjobs=$(smart_jobs quantification "${QUANTIFICATION_JOBS}")

            if [[ "${m}" == "mesmer" ]]; then
                target_q="stage_quantification_mesmer"
            else
                target_q="stage_quantification_stardist"
            fi

            run_snakemake "${m^} Quantification" "${target_q}" "${qjobs}" "cpu"

            # Validate + Retry
            n_quant=$(_count_quant_present "${m}")
            if [[ "${n_quant}" -lt "${n_samples}" ]]; then
                echo "  ├─ ⚠ Validation: ${n_quant}/${n_samples} ${m} quant CSVs — retrying missing..."
                run_snakemake "${m^} Quantification (retry)" "${target_q}" "${qjobs}" "cpu"
            fi
        else
            echo "  ├─ Skipping ${m} quantification — requested by --only/--from/--until."
        fi

        if [[ "${RUN_SUBSTAGE_FILTER:-1}" == "1" ]]; then
            local fjobs n_fcsv target_f
            fjobs=$(smart_jobs filtering "${FILTER_JOBS}")

            if [[ "${m}" == "mesmer" ]]; then
                target_f="stage_filtering_mesmer"
            else
                target_f="stage_filtering_stardist"
            fi

            run_snakemake "${m^} Filtering + Filtered Quantification" "${target_f}" "${fjobs}" "cpu"

            # Validate + Retry
            n_fcsv=$(_count_filtered_csv_present "${m}")
            if [[ "${n_fcsv}" -lt "${n_samples}" ]]; then
                echo "  ├─ ⚠ Validation: ${n_fcsv}/${n_samples} ${m} filtered CSVs — retrying missing..."
                run_snakemake "${m^} Filtering (retry)" "${target_f}" "${fjobs}" "cpu"
            fi
        else
            echo "  ├─ Skipping ${m} filtering — requested by --only/--from/--until."
        fi
    done
}

run_stage_3_quantification_and_filtering() {
    if [[ -f "${STATE_DIR}/pipeline_complete.flag" ]]; then
        return 0
    fi

    echo ""

    ui_stage_start "3" "Measure markers" "Quantify marker intensity, then enhance markers and quantify again"

    local method
    if [[ -f "${STATE_DIR}/segmentation_method.txt" ]]; then
        method="$(cat "${STATE_DIR}/segmentation_method.txt")"
    else
        echo "ERROR: No segmentation method configured."
        echo "  Run the full pipeline or stage 2 first, or use: bash run_pipeline.sh --sync-state"
        exit 1
    fi

    print_method_paths "${method}"
    validate_quant_filter_inputs

    run_quantification_and_filtering_for_method "${method}"

    # When the user ran only one sub-stage (quant XOR filter), the *full*
    # final-output completeness check would falsely fail. Only verify and
    # mark the pipeline as complete when BOTH sub-stages were enabled.
    local ran_both_substages=0
    if [[ "${RUN_SUBSTAGE_QUANT:-1}" == "1" && "${RUN_SUBSTAGE_FILTER:-1}" == "1" ]]; then
        ran_both_substages=1
    fi

    if [[ "${ran_both_substages}" == "1" ]]; then
        if method_final_complete "${method}"; then
            touch "${STATE_DIR}/pipeline_complete.flag"
        else
            echo "ERROR: Snakemake finished, but final outputs are still incomplete for method: ${method}"
            echo ""
            print_status || true
            echo ""
            echo "Run: bash run_pipeline.sh --status"
            exit 1
        fi

        local n_samples markers n_quant n_fcsv n_ftif want_tif m
        n_samples=$(count_samples)
        markers=$(marker_count)
        want_tif=$((n_samples * markers))

        ui_section "Step 3 complete" "Marker quantification and filtering finished"
        for m in $(_methods_from_selection "${method}"); do
            n_quant=$(_count_quant_present "${m}")
            n_fcsv=$(_count_filtered_csv_present "${m}")
            n_ftif=$(_count_filtered_tif_present "${m}")
            ui_status_row "${m} quantification tables" "${n_quant}" "${n_samples}"
            ui_status_row "${m} filtered result tables" "${n_fcsv}" "${n_samples}"
            ui_status_row "${m} enhanced marker images" "${n_ftif}" "${want_tif}"
        done
        ui_blank

        _print_pipeline_complete_banner "${method}" "${n_samples}" "${markers}" "${want_tif}"

        write_final_summary
        send_email "Pipeline Complete" "All stages finished successfully."
    else
        echo "  └─ ✓ Stage 3 sub-stage(s) complete"
        echo "     (skipping pipeline_complete.flag because --only/--from/--until limited the run)"
        echo ""
        return 0
    fi

    if [[ "${CLEAN_TRANSIENT_ON_SUCCESS}" == "1" ]]; then
        cleanup_transient_files
    else
        echo "Transient cleanup skipped because CLEAN_TRANSIENT_ON_SUCCESS=${CLEAN_TRANSIENT_ON_SUCCESS}"
    fi

    exit 0
}

main() {
    initialize_launcher_log
    handle_command_line "$@"
    select_run_mode_interactive

    log_header
    ensure_pipeline_dirs
    print_summary

    # Stage-aware state + validation.
    # Important: sync first so existing stitched/mask outputs can recreate
    # missing flags and infer segmentation_method.txt before validation.
    sync_state_from_outputs
    validate_selected_stage_inputs

    # Raw dataset confirmation is only relevant when stage 1 actually needs
    # raw .rcpnl input. Segmentation/quantification/filtering-only runs may
    # legitimately have an empty RAW_DIR.
    if [[ "${RUN_STAGE_STITCHING:-1}" == "1" && ! -f "${STATE_DIR}/stitching_complete.flag" ]]; then
        confirm_raw_dataset_if_needed
    fi

    if [[ "${RUN_STAGE_STITCHING}" == "1" ]]; then
        run_stage_1_illumination_and_stitching
        review_stitching_if_needed
    else
        echo "Skipping stage 1 (illumination + stitching) — requested by --only/--from/--until."
    fi

    if [[ "${RUN_STAGE_SEGMENTATION}" == "1" ]]; then
        run_stage_2_segmentation
        review_segmentation_if_needed
    else
        echo "Skipping stage 2 (segmentation) — requested by --only/--from/--until."
    fi

    if [[ "${RUN_STAGE_QUANT_FILTER}" == "1" ]]; then
        run_stage_3_quantification_and_filtering
    else
        echo "Skipping stage 3 (quantification + filtering) — requested by --only/--from/--until."
        exit 0
    fi

    echo "Pipeline is already complete. Use --reset to start over."
}

main "$@"
