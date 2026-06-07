#!/usr/bin/env bash
# Copy full OMEIA-AI imaging + document library code to a USB path for Linux.
# Usage: ./scripts/network/sync_mac_repo_to_usb.sh /Volumes/YOUR_USB/OMEIA-AI-sync
set -euo pipefail
DEST="${1:?Usage: $0 /path/to/usb/OMEIA-AI-sync}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

rsync -av --delete \
  --exclude '.venv' --exclude 'node_modules' --exclude '.git' \
  "$ROOT/app_skeleton/api/imaging_capabilities.py" \
  "$ROOT/app_skeleton/api/image_streaming/" \
  "$ROOT/app_skeleton/api/document_library_service.py" \
  "$ROOT/app_skeleton/api/routers/document_library.py" \
  "$ROOT/app_skeleton/api/routers/image_assets.py" \
  "$ROOT/app_skeleton/api/metadata_engine/" \
  "$ROOT/app_skeleton/security/audit_log.py" \
  "$ROOT/app_skeleton/api/main.py" \
  "$ROOT/docker/" \
  "$ROOT/docker-compose.imaging.yml" \
  "$ROOT/scripts/imaging/linux_paste_install_imaging_worker.sh" \
  "$ROOT/scripts/imaging/linux_minimal_imaging_capabilities.sh" \
  "$DEST/"

echo "Copied to $DEST"
echo "On Linux USB mount:"
echo "  rsync -av /media/usb/OMEIA-AI-sync/ ~/data4TB/digital-notepad/"
