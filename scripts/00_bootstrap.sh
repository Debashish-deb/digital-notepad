#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/dev/00_bootstrap.sh
exec "$(dirname "$0")/dev/00_bootstrap.sh" "$@"
