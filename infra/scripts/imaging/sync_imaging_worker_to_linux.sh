#!/usr/bin/env bash
# Copy imaging-worker Docker files from this Mac repo to Linux workstation.
# Usage: ./scripts/imaging/sync_imaging_worker_to_linux.sh user@host:~/data4TB/digital-notepad
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 user@host:/path/to/digital-notepad"
  echo "Example: $0 debdeba@dx9-3049-11090:~/data4TB/digital-notepad"
  exit 1
fi

DEST="$1"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

rsync -avz \
  "$ROOT/docker/imaging-worker" \
  "$ROOT/docker-compose.imaging.yml" \
  "$ROOT/omeia/api/imaging_capabilities.py" \
  "$ROOT/scripts/docker/build_imaging_worker.sh" \
  "$ROOT/scripts/imaging/sync_imaging_worker_to_linux.sh" \
  "${DEST}/"

rsync -avz "$ROOT/docker/imaging-worker/" "${DEST}/docker/imaging-worker/"
rsync -avz "$ROOT/omeia/api/imaging_capabilities.py" "${DEST}/omeia/api/"

echo ""
echo "Synced. On Linux run:"
echo "  cd ~/data4TB/digital-notepad"
echo "  chmod +x scripts/docker/build_imaging_worker.sh"
echo "  ./scripts/docker/build_imaging_worker.sh"
