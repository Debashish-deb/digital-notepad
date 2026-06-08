#!/usr/bin/env bash
# Run the UI from inside react_frontend (delegates to repo-root launcher).
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
exec "${REPO_ROOT}/scripts/dev/start_frontend.sh"
