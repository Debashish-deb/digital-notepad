#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/dev/load_env.sh
exec "$(dirname "$0")/dev/load_env.sh" "$@"
