#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/imaging/copy_imaging_bundle_to_linux.sh
exec "$(dirname "$0")/imaging/copy_imaging_bundle_to_linux.sh" "$@"
