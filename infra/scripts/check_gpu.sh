#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/check/check_gpu.sh
exec "$(dirname "$0")/check/check_gpu.sh" "$@"
