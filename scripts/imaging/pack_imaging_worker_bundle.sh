#!/usr/bin/env bash
# Pack imaging-worker files into a tarball for copying to Linux workstation.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="$ROOT/omeia-imaging-worker-bundle.tar.gz"

cd "$ROOT"
tar czf "$OUT" \
  docker-compose.imaging.yml \
  docker/imaging-worker/Dockerfile \
  docker/imaging-worker/environment-core.yml \
  docker/imaging-worker/environment-cycif-amd64.yml \
  docker/imaging-worker/environment.yml \
  docker/imaging-worker/healthcheck.py \
  app_skeleton/api/imaging_capabilities.py \
  scripts/docker/build_imaging_worker.sh

echo "Created: $OUT"
echo ""

LINUX_USER="${LINUX_SSH_USER:-debdeba}"
LINUX_IP=""
if [[ -f "$ROOT/configs/.env" ]]; then
  LINUX_IP="$(grep -E '^TAILSCALE_LINUX_IP=' "$ROOT/configs/.env" | cut -d= -f2- | tr -d ' \"')"
fi
LINUX_HOST="${LINUX_SSH_HOST:-${LINUX_IP:+${LINUX_USER}@${LINUX_IP}}}"

echo "Copy to Linux (use Tailscale IP or LAN IP — NOT the Linux hostname dx9-...):"
if [[ -n "$LINUX_HOST" ]]; then
  echo "  scp $OUT ${LINUX_HOST}:~/data4TB/digital-notepad/"
else
  echo "  scp $OUT debdeba@<LINUX_TAILSCALE_IP>:~/data4TB/digital-notepad/"
  echo "  (Set TAILSCALE_LINUX_IP in configs/.env — yours may be 100.80.231.55)"
fi
echo ""
echo "On Linux:"
echo "  cd ~/data4TB/digital-notepad"
echo "  tar xzf omeia-imaging-worker-bundle.tar.gz"
echo "  chmod +x scripts/docker/build_imaging_worker.sh"
echo "  ./scripts/docker/build_imaging_worker.sh"
