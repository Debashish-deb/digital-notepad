#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/digitalization/build_raw_asset_inventory.py
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/digitalization/build_raw_asset_inventory.py" "$@"
