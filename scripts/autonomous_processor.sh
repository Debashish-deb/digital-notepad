#!/usr/bin/env bash
# Backward-compat wrapper — use scripts/ops/autonomous_processor.sh
exec "$(dirname "$0")/ops/autonomous_processor.sh" "$@"
