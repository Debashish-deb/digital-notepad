#!/usr/bin/env bash
# Copy imaging-worker bundle to Linux when plain scp to 100.x times out.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
BUNDLE="$ROOT/omeia-imaging-worker-bundle.tar.gz"
LINUX_NODE="${LINUX_TAILSCALE_NODE:-dx9-3049-11090}"
LINUX_USER="${LINUX_SSH_USER:-debdeba}"
LINUX_IP=""
if [[ -f "$ROOT/configs/.env" ]]; then
  LINUX_IP="$(grep -E '^TAILSCALE_LINUX_IP=' "$ROOT/configs/.env" | cut -d= -f2- | tr -d ' \"')"
fi

if [[ ! -f "$BUNDLE" ]]; then
  "$ROOT/scripts/imaging/pack_imaging_worker_bundle.sh"
fi

echo "Bundle: $BUNDLE"
echo ""

# 1) Tailscale file copy (no SSH port 22 required)
if command -v tailscale >/dev/null 2>&1; then
  echo "=== Try 1: tailscale file cp ==="
  if tailscale file cp "$BUNDLE" "${LINUX_USER}@${LINUX_NODE}:" 2>/dev/null; then
    echo "Sent via Tailscale file sharing."
    echo "On Linux: tailscale file get . && mv omeia-imaging-worker-bundle.tar.gz ~/data4TB/digital-notepad/"
    exit 0
  fi
  echo "tailscale file cp failed (enable File Sharing in Tailscale admin or use try 2/3)"
  echo ""
fi

# 2) Tailscale SSH (does not use port 22)
if command -v tailscale >/dev/null 2>&1; then
  echo "=== Try 2: tailscale ssh + scp ==="
  if tailscale ssh "${LINUX_USER}@${LINUX_NODE}" "mkdir -p ~/data4TB/digital-notepad" 2>/dev/null; then
    if command -v scp >/dev/null 2>&1; then
      # ProxyCommand via tailscale ssh
      if scp -o "ProxyCommand=tailscale ssh %r@%h --nc" "$BUNDLE" "${LINUX_USER}@${LINUX_NODE}:~/data4TB/digital-notepad/" 2>/dev/null; then
        echo "Copied via tailscale ssh proxy."
        exit 0
      fi
    fi
  fi
  echo "tailscale ssh failed — on Linux run: sudo tailscale set --ssh"
  echo ""
fi

# 3) Plain scp to Tailscale IP
if [[ -n "$LINUX_IP" ]]; then
  echo "=== Try 3: scp to $LINUX_IP (needs SSH open on Linux) ==="
  echo "On Linux first: ./scripts/network/linux_enable_tailscale_ssh.sh"
  scp "$BUNDLE" "${LINUX_USER}@${LINUX_IP}:~/data4TB/digital-notepad/" && exit 0
fi

echo ""
echo "=== Manual fallback (you are often already SSH'd into Linux) ==="
echo "On Linux workstation, PULL from Mac (enable Remote Login on Mac first):"
echo "  scp debashishdeb@100.84.193.30:~/Downloads/OMEIA-AI/omeia-imaging-worker-bundle.tar.gz ~/data4TB/digital-notepad/"
echo ""
echo "Or USB / shared folder: copy $BUNDLE manually."
exit 1
