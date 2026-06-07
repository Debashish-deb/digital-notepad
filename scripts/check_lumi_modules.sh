#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/check/check_lumi_modules.sh
exec "$(dirname "$0")/check/check_lumi_modules.sh" "$@"
