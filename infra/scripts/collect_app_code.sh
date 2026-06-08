#!/usr/bin/env bash
# Collect OMEIA app source into a single indexed markdown file for review.
# Usage:
#   ./scripts/collect_app_code.sh
#   ./scripts/collect_app_code.sh --include-pipelines -o docs/my_bundle.md
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "${ROOT}/scripts/ops/collect_app_code_bundle.py" "$@"
