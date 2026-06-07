#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/search/run_ai_lab_assistant_eval.py
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/search/run_ai_lab_assistant_eval.py" "$@"
