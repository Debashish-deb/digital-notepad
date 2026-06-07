#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/check/check_tcycif_project_structure.py
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/check/check_tcycif_project_structure.py" "$@"
