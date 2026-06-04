#!/usr/bin/env bash
# Cross-platform wrapper for scripts/scheduled_ingest.py (cron, launchd, systemd).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

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
    break
  fi
done

PYTHON="${PYTHON:-}"
if [[ -z "${PYTHON}" ]]; then
  if [[ -x "${OMEIA_VENV:-/opt/omeia/venv}/bin/python" ]]; then
    PYTHON="${OMEIA_VENV:-/opt/omeia/venv}/bin/python"
  elif [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
    PYTHON="${REPO_ROOT}/.venv/bin/python"
  else
    PYTHON="python3"
  fi
fi

MAX_ENTRIES="${INGEST_SCHEDULE_MAX_ENTRIES:-500}"
cd "${REPO_ROOT}"
exec "${PYTHON}" scripts/scheduled_ingest.py --max-entries "${MAX_ENTRIES}" "$@"
