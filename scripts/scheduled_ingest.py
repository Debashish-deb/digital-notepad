#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/ops/scheduled_ingest.py
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/ops/scheduled_ingest.py" "$@"
