#!/usr/bin/env bash
# Portable launcher — Mac thin client today, same repo on Linux desktop tomorrow.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/scripts/portable_apply_env.sh"

echo "Profile: ${OMEIA_DEPLOYMENT_PROFILE:-portable}"
echo "Repo:    $OMEIA_REPO_ROOT"
echo "Data:    $DATABASE_ROOT"
exec "$ROOT/start.sh"
