#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/imaging/linux_paste_install_imaging_worker.sh
exec "$(dirname "$0")/imaging/linux_paste_install_imaging_worker.sh" "$@"
