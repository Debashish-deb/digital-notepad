#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/network/portable_apply_env.sh
exec "$(dirname "$0")/network/portable_apply_env.sh" "$@"
