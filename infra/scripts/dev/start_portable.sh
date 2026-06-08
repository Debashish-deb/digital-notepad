#!/usr/bin/env bash
# Backward-compat — use scripts/start_mac.sh or scripts/start_linux.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
if [[ "$(uname -s)" == "Linux" ]]; then
  exec "$ROOT/scripts/dev/start_linux_desktop.sh" "$@"
fi
exec "$ROOT/scripts/dev/start_mac_thin_client.sh" "$@"
