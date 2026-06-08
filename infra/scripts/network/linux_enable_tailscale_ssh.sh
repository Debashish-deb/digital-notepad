#!/usr/bin/env bash
# Allow Mac → Linux SSH over Tailscale (fixes scp timeout to 100.x).
# Run ON the Linux workstation.
set -euo pipefail

echo "=== Enable Tailscale SSH + inbound SSH from tailnet ==="

if ! command -v tailscale >/dev/null 2>&1; then
  echo "ERROR: tailscale not installed"
  exit 1
fi

sudo tailscale set --shields-up=false 2>/dev/null || true
sudo tailscale set --ssh 2>/dev/null || echo "Note: enable SSH in Tailscale admin console if --ssh fails"

# OpenSSH listening on all interfaces (default on many Ubuntu installs)
if command -v ufw >/dev/null 2>&1 && sudo ufw status 2>/dev/null | grep -q "Status: active"; then
  sudo ufw allow from 100.64.0.0/10 to any port 22 proto tcp comment 'Tailscale SSH' 2>/dev/null || true
  echo "ufw: allowed SSH from 100.64.0.0/10"
fi

if command -v iptables >/dev/null 2>&1; then
  sudo iptables -C INPUT -i tailscale0 -p tcp --dport 22 -j ACCEPT 2>/dev/null || \
    sudo iptables -I INPUT 1 -i tailscale0 -p tcp --dport 22 -j ACCEPT
  echo "iptables: SSH on tailscale0 allowed"
fi

TS_IP="$(tailscale ip -4 2>/dev/null || true)"
echo ""
echo "Linux Tailscale IP: ${TS_IP:-unknown}"
echo "From Mac test:"
echo "  ssh debdeba@${TS_IP}"
echo "  scp omeia-imaging-worker-bundle.tar.gz debdeba@${TS_IP}:~/data4TB/digital-notepad/"
