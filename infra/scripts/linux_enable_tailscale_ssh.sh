#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/network/linux_enable_tailscale_ssh.sh
exec "$(dirname "$0")/network/linux_enable_tailscale_ssh.sh" "$@"
