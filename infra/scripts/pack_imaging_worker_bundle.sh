#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/imaging/pack_imaging_worker_bundle.sh
exec "$(dirname "$0")/imaging/pack_imaging_worker_bundle.sh" "$@"
