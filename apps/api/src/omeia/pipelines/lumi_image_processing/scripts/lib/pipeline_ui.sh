#!/bin/bash
# Friendly terminal UI for the image-processing pipeline.
# Sourced by run_pipeline.sh (before pipeline_state.sh and pipeline_slurm.sh).

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Do not run pipeline_ui.sh directly."
    exit 1
fi

# Defaults: friendly on, verbose technical details off.
export PIPELINE_FRIENDLY_LOG="${PIPELINE_FRIENDLY_LOG:-1}"
export PIPELINE_VERBOSE_LOG="${PIPELINE_VERBOSE_LOG:-0}"

UI_WIDTH="${UI_WIDTH:-72}"

ui_enabled() {
    [[ "${PIPELINE_FRIENDLY_LOG}" == "1" ]]
}

ui_verbose() {
    [[ "${PIPELINE_VERBOSE_LOG}" == "1" ]]
}

ui_repeat() {
    local char="${1:-─}"
    local n="${2:-${UI_WIDTH}}"
    printf '%*s\n' "${n}" '' | tr ' ' "${char}"
}

ui_blank() {
    echo ""
}

ui_title() {
    local text="$1"
    ui_blank
    ui_repeat "═"
    printf '  %s\n' "${text}"
    ui_repeat "═"
    ui_blank
}

ui_section() {
    local step="$1"
    local title="$2"
    ui_blank
    printf '  %s\n' "${step}"
    printf '  %s\n' "${title}"
    ui_repeat "─" 68
}

ui_step() {
    printf '    • %s\n' "$*"
}

ui_note() {
    printf '    ℹ  %s\n' "$*"
}

ui_ok() {
    printf '    ✓  %s\n' "$*"
}

ui_warn() {
    printf '    ⚠  %s\n' "$*"
}

ui_err() {
    printf '    ✗  %s\n' "$*"
}

ui_dim() {
    ui_verbose || return 0
    printf '       %s\n' "$*"
}

ui_path() {
    printf '       → %s\n' "$*"
}

ui_live() {
    printf '  ▶ LIVE  %s\n' "$*"
}

ui_progress_bar() {
    local pct="$1"
    local label="${2:-Working}"
    local width=24
    local filled=$((pct * width / 100))
    local empty=$((width - filled))
    local bar=""
    local i

    for ((i = 0; i < filled; i++)); do bar+="#"; done
    for ((i = 0; i < empty; i++)); do bar+="-"; done

    printf '       %s  [%s] %3d%%\n' "${label}" "${bar}" "${pct}"
}

ui_stage_start() {
    local num="$1"
    local title="$2"
    local subtitle="${3:-}"

    if ui_enabled; then
        ui_section "Step ${num}" "${title}"
        [[ -n "${subtitle}" ]] && ui_note "${subtitle}"
        ui_blank
    else
        echo "▶ ${title}"
        [[ -n "${subtitle}" ]] && echo "  ${subtitle}"
    fi
}

ui_stage_done() {
    local title="$1"
    local detail="${2:-}"

    if ui_enabled; then
        ui_ok "${title} finished${detail:+ — ${detail}}"
        ui_blank
    else
        echo "  ├─ ✓ ${title} done${detail:+ (${detail})}"
    fi
}

ui_stage_fail() {
    local title="$1"
    local detail="${2:-}"

    if ui_enabled; then
        ui_err "${title} did not finish successfully"
        [[ -n "${detail}" ]] && ui_note "${detail}"
        ui_blank
    else
        echo "  ├─ ✗ ${title} failed${detail:+: ${detail}}"
    fi
}

ui_review_prompt() {
    local what="$1"
    local where="$2"

    ui_blank
    ui_repeat "─" 68
    printf '  Please review: %s\n' "${what}"
    ui_path "${where}"
    ui_note "When you are happy with the results, run this script again to continue."
    ui_repeat "─" 68
    ui_blank
}

ui_snakemake_intro() {
    local stage_name="$1"
    local jobs="$2"
    local log_file="$3"
    local live_hint="${4:-}"

    if ui_enabled; then
        ui_note "Running on the cluster: up to ${jobs} sample(s) in parallel."
        ui_note "Detailed technical log (for support): ${log_file}"
        [[ -n "${live_hint}" ]] && ui_note "${live_hint}"
        ui_blank
        printf '  %s\n' "Live updates (plain language):"
        ui_repeat "·" 68
    else
        echo "  ├─ Parallel jobs: ${jobs}"
        echo "  ├─ Log: ${log_file}"
        [[ -n "${live_hint}" ]] && echo "  │  ${live_hint}"
    fi
}

ui_status_row() {
    local label="$1"
    local have="$2"
    local want="$3"
    local word

    if [[ "${want}" -gt 0 && "${have}" -eq "${want}" ]]; then
        word="complete"
    else
        word="in progress"
    fi

    printf '  %-28s  %s / %s   (%s)\n' "${label}" "${have}" "${want}" "${word}"
}

ui_friendly_stage_for_target() {
    case "$1" in
        stage_illumination)
            echo "Lighting correction|Correcting uneven illumination across each microscope cycle"
            ;;
        stage_stitching)
            echo "Tile stitching|Combining individual tiles into one whole-slide image"
            ;;
        stage_segmentation_mesmer)
            echo "Cell segmentation (Mesmer)|Finding nuclei and/or cell boundaries with deep learning"
            ;;
        stage_segmentation_stardist)
            echo "Cell segmentation (StarDist)|Finding nuclei with StarDist"
            ;;
        stage_quantification_mesmer)
            echo "Marker quantification (Mesmer)|Measuring marker intensity inside each cell"
            ;;
        stage_quantification_stardist)
            echo "Marker quantification (StarDist)|Measuring marker intensity inside each nucleus"
            ;;
        stage_filtering_mesmer)
            echo "Marker filtering + quantification (Mesmer)|Enhancing markers and re-measuring intensities"
            ;;
        stage_filtering_stardist)
            echo "Marker filtering + quantification (StarDist)|Enhancing markers and re-measuring intensities"
            ;;
        *)
            echo "Processing step|Running pipeline step"
            ;;
    esac
}

ui_live_hint_for_target() {
    case "$1" in
        stage_illumination)
            echo "Per-cycle logs: ${LOG_ROOT}/illumination/<sample>/<cycle>.log"
            ;;
        stage_stitching)
            echo "Per-sample logs: ${LOG_ROOT}/stitching/<sample>/stitching_<sample>.log"
            ;;
        stage_segmentation_mesmer)
            echo "Per-sample logs: ${LOG_ROOT}/segmentation/mesmer/<sample>/"
            ;;
        stage_segmentation_stardist)
            echo "Per-sample logs: ${LOG_ROOT}/segmentation/stardist/<sample>/"
            ;;
        stage_quantification_*)
            echo "Per-sample logs: ${LOG_ROOT}/quantification/<method>/<sample>/"
            ;;
        stage_filtering_*)
            echo "Per-sample logs: ${LOG_ROOT}/filtering/<method>/<sample>/"
            ;;
        *)
            echo "Per-job logs under: ${LOG_ROOT}"
            ;;
    esac
}
