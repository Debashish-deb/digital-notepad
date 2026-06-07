#!/bin/bash
# Friendly per-job log formatting for Snakemake rule shell blocks.
# Source once at the start of a rule, then use job_log_* instead of raw printf.

job_log_ts() {
    date '+%H:%M:%S'
}

job_log_open() {
    local title="$1"
    local context="$2"
    local blurb="${3:-}"

    printf '\n'
    printf '================================================================================\n'
    printf '  %s\n' "${title}"
    [[ -n "${context}" ]] && printf '  %s\n' "${context}"
    [[ -n "${blurb}" ]] && printf '  %s\n' "${blurb}"
    # Use '%s' format — bare strings starting with '-' are treated as printf options.
    printf '%s\n' '--------------------------------------------------------------------------------'
    printf '\n'
}

job_log_close_ok() {
    local msg="${1:-Finished successfully.}"
    printf '\n'
    printf '%s\n' '--------------------------------------------------------------------------------'
    printf '  Done — %s\n' "${msg}"
    printf '================================================================================\n'
    printf '\n'
}

job_log_close_fail() {
    local msg="${1:-Job failed.}"
    printf '\n'
    printf '%s\n' '--------------------------------------------------------------------------------'
    printf '  FAILED — %s\n' "${msg}"
    printf '================================================================================\n'
    printf '\n'
}

job_log() {
    printf '  %s  %s\n' "$(job_log_ts)" "$*"
}

job_log_ok() {
    printf '  %s  ✓ %s\n' "$(job_log_ts)" "$*"
}

job_log_warn() {
    printf '  %s  ⚠ %s\n' "$(job_log_ts)" "$*"
}

job_log_fail() {
    printf '  %s  ✗ %s\n' "$(job_log_ts)" "$*"
}
