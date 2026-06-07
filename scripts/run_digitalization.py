#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/digitalization/run_digitalization.py
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/digitalization/run_digitalization.py" "$@"
