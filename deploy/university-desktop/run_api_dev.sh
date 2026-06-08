#!/usr/bin/env bash
# Cross-platform dev API: macOS (Darwin) and Linux. Loads .env and runs uvicorn.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OS="$(uname -s)"

ENV_CANDIDATES=(
  "${REPO_ROOT}/configs/.env"
  "${REPO_ROOT}/deploy/university-desktop/.env"
  "${OMEIA_DEPLOY:-/opt/omeia/deploy/university-desktop}/.env"
)

for env_file in "${ENV_CANDIDATES[@]}"; do
  if [[ -f "${env_file}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${env_file}"
    set +a
    echo "Loaded ${env_file}"
    break
  fi
done

if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  if [[ -x "${OMEIA_VENV:-/opt/omeia/venv}/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "${OMEIA_VENV:-/opt/omeia/venv}/bin/activate"
  elif [[ -f "${REPO_ROOT}/.venv-local/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "${REPO_ROOT}/.venv-local/bin/activate"
  elif [[ -f "${REPO_ROOT}/.venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "${REPO_ROOT}/.venv/bin/activate"
  else
    echo "No venv found. Create one: python3 -m venv ${REPO_ROOT}/.venv && pip install -r requirements.txt"
    exit 1
  fi
fi

cd "${REPO_ROOT}"
export PYTHONPATH="${REPO_ROOT}${PYTHONPATH:+:$PYTHONPATH}"

BIND_HOST="${OMEIA_BIND_HOST:-}"
if [[ -z "${BIND_HOST}" ]]; then
  if [[ "${OS}" == "Darwin" ]]; then
    BIND_HOST="127.0.0.1"
  else
    BIND_HOST="0.0.0.0"
  fi
fi
BIND_PORT="${OMEIA_BIND_PORT:-8000}"

echo "Starting uvicorn on ${BIND_HOST}:${BIND_PORT} (${OS})"
exec uvicorn omeia.api.main:app --host "${BIND_HOST}" --port "${BIND_PORT}" --reload
