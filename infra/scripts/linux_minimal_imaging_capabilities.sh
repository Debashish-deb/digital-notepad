#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/imaging/linux_minimal_imaging_capabilities.sh
exec "$(dirname "$0")/imaging/linux_minimal_imaging_capabilities.sh" "$@"
