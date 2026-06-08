#!/usr/bin/env bash
# Shared paths for OMEIA shell scripts.
# Source from any script:  source "$(dirname "$0")/../lib/common.sh"  (adjust depth)

if [[ -z "${OMEIA_LIB_COMMON_LOADED:-}" ]]; then
  OMEIA_LIB_COMMON_LOADED=1

  _omeia_lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  export OMEIA_SCRIPTS_ROOT="$(cd "${_omeia_lib_dir}/.." && pwd)"
  if [[ -z "${OMEIA_REPO_ROOT:-}" ]]; then
    if git rev-parse --show-toplevel &>/dev/null; then
      export OMEIA_REPO_ROOT="$(git rev-parse --show-toplevel)"
    else
      # infra/scripts -> repo is two levels up (not one: that lands on infra/)
      export OMEIA_REPO_ROOT="$(cd "${OMEIA_SCRIPTS_ROOT}/../.." && pwd)"
    fi
  fi
  export OMEIA_REPO_ROOT

  omeia_load_env() {
    local env_file="${1:-${OMEIA_REPO_ROOT}/configs/.env}"
    if [[ -f "${env_file}" && -x "${OMEIA_SCRIPTS_ROOT}/dev/load_env.sh" ]]; then
      # shellcheck disable=SC1091
      eval "$("${OMEIA_SCRIPTS_ROOT}/dev/load_env.sh" "${env_file}")"
    fi
  }
fi
