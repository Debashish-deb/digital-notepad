#!/usr/bin/env bash
# Shared paths for OMEIA shell scripts.
# Source from any script:  source "$(dirname "$0")/../lib/common.sh"  (adjust depth)

if [[ -z "${OMEIA_LIB_COMMON_LOADED:-}" ]]; then
  OMEIA_LIB_COMMON_LOADED=1

  _omeia_lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  export OMEIA_SCRIPTS_ROOT="$(cd "${_omeia_lib_dir}/.." && pwd)"
  export OMEIA_REPO_ROOT="${OMEIA_REPO_ROOT:-$(cd "${OMEIA_SCRIPTS_ROOT}/.." && pwd)}"

  omeia_load_env() {
    local env_file="${1:-${OMEIA_REPO_ROOT}/configs/.env}"
    if [[ -f "${env_file}" && -x "${OMEIA_SCRIPTS_ROOT}/dev/load_env.sh" ]]; then
      # shellcheck disable=SC1091
      eval "$("${OMEIA_SCRIPTS_ROOT}/dev/load_env.sh" "${env_file}")"
    fi
  }
fi
