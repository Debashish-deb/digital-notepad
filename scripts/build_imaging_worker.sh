#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/docker/build_imaging_worker.sh
exec "$(dirname "$0")/docker/build_imaging_worker.sh" "$@"
