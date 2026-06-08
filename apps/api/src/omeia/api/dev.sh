#!/usr/bin/env bash
# Run the API from inside omeia/api (delegates to repo-root launcher).
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
exec "${REPO_ROOT}/scripts/dev/start_backend.sh"
