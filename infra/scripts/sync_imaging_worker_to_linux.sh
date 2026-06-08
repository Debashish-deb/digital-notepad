#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/imaging/sync_imaging_worker_to_linux.sh
exec "$(dirname "$0")/imaging/sync_imaging_worker_to_linux.sh" "$@"
