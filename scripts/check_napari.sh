#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/check/check_napari.sh
exec "$(dirname "$0")/check/check_napari.sh" "$@"
