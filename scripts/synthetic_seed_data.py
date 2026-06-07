#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/database/synthetic_seed_data.py
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/database/synthetic_seed_data.py" "$@"
