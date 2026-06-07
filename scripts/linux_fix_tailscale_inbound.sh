#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/network/linux_fix_tailscale_inbound.sh
exec "$(dirname "$0")/network/linux_fix_tailscale_inbound.sh" "$@"
