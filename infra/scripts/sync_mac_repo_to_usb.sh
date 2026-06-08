#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/network/sync_mac_repo_to_usb.sh
exec "$(dirname "$0")/network/sync_mac_repo_to_usb.sh" "$@"
