#!/usr/bin/env bash
# Allow inbound Tailscale (100.x.x.x) traffic to Docker-published Ollama/Qdrant ports.
# Run on Linux workstation when Mac curl to 100.x:11434 times out but local curl works.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "=== Linux Tailscale inbound fix ==="

if ! command -v tailscale >/dev/null 2>&1; then
  echo "ERROR: tailscale not installed"
  exit 1
fi

sudo tailscale set --shields-up=false 2>/dev/null || true

TS_IP="$(tailscale ip -4 2>/dev/null || true)"
echo "Tailscale IP: ${TS_IP:-unknown}"

# Accept tailnet traffic on tailscale0 (before ufw/docker drops)
if command -v iptables >/dev/null 2>&1; then
  sudo iptables -C INPUT -i tailscale0 -j ACCEPT 2>/dev/null || \
    sudo iptables -I INPUT 1 -i tailscale0 -j ACCEPT
  sudo iptables -C DOCKER-USER -i tailscale0 -j ACCEPT 2>/dev/null || \
    sudo iptables -I DOCKER-USER 1 -i tailscale0 -j ACCEPT
  sudo iptables -C DOCKER-USER -s 100.64.0.0/10 -j ACCEPT 2>/dev/null || \
    sudo iptables -I DOCKER-USER 1 -s 100.64.0.0/10 -j ACCEPT
  echo "iptables: INPUT + DOCKER-USER rules added"
fi

if command -v ufw >/dev/null 2>&1 && sudo ufw status 2>/dev/null | grep -q "Status: active"; then
  sudo ufw allow from 100.64.0.0/10 to any port 11434 proto tcp comment 'Tailscale Ollama' 2>/dev/null || true
  sudo ufw allow from 100.64.0.0/10 to any port 6333 proto tcp comment 'Tailscale Qdrant' 2>/dev/null || true
  echo "ufw: tailnet rules ensured"
fi

ln -sf configs/.env .env 2>/dev/null || true
grep -q '0.0.0.0:11434:11434' docker-compose.yml 2>/dev/null || \
  sed -i 's|127.0.0.1:11434:11434|0.0.0.0:11434:11434|' docker-compose.yml 2>/dev/null || true
grep -q '0.0.0.0:6333:6333' docker-compose.yml 2>/dev/null || \
  sed -i 's|127.0.0.1:6333:6333|0.0.0.0:6333:6333|' docker-compose.yml 2>/dev/null || true

docker compose up -d ollama ollama-proxy qdrant --force-recreate 2>/dev/null || \
  docker compose up -d ollama ollama-proxy qdrant 2>/dev/null || true

# Tailscale TCP proxy for Ollama + Qdrant (bypasses host firewall paths)
sudo tailscale serve reset 2>/dev/null || true
sudo tailscale serve --bg --tcp=11434 tcp://127.0.0.1:11434 2>/dev/null || \
  sudo tailscale serve --bg --tcp 11434 127.0.0.1:11434 2>/dev/null || true
sudo tailscale serve --bg --tcp=6333 tcp://127.0.0.1:6333 2>/dev/null || \
  sudo tailscale serve --bg --tcp 6333 127.0.0.1:6333 2>/dev/null || true

echo ""
echo "Local test (must print 'Ollama is running'):"
if [[ -f "$ROOT/configs/.env" ]]; then
  # shellcheck disable=SC1091
  eval "$("$ROOT/scripts/load_env.sh" "$ROOT/configs/.env")" 2>/dev/null || true
fi
if [[ -n "${OLLAMA_INTERNAL_TOKEN:-}" && -n "$TS_IP" ]]; then
  curl -sf -m 5 -H "Authorization: Bearer $OLLAMA_INTERNAL_TOKEN" "http://${TS_IP}:11434/" || echo "(local tailscale IP curl failed)"
fi
curl -sf -m 5 -H "Authorization: Bearer ${OLLAMA_INTERNAL_TOKEN:-}" http://127.0.0.1:11434/ || true

echo ""
echo "Qdrant local test (expect JSON with version):"
curl -sf -m 5 http://127.0.0.1:6333/ | head -c 120 || echo "(qdrant local failed)"
if [[ -n "$TS_IP" ]]; then
  curl -sf -m 5 "http://${TS_IP}:6333/" | head -c 120 || echo "(qdrant via tailscale IP failed)"
fi

echo ""
sudo tailscale serve status 2>/dev/null || true
echo ""
echo "Done. From Mac:"
echo "  ./scripts/mac_test_tailscale_ollama.sh"
echo "  curl -s --max-time 5 http://100.80.231.55:6333/"
