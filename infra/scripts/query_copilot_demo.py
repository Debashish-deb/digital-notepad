#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/ops/query_copilot_demo.py
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/ops/query_copilot_demo.py" "$@"
