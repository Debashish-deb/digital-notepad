# Firewall (UFW) — university desktop API host

Goal: expose **HTTPS (443)** to the internet (or campus VPN); keep **uvicorn 8000** on localhost only.

## Recommended rules

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 443/tcp comment 'OMEIA HTTPS reverse proxy'
# Do NOT allow 8000/tcp from anywhere
sudo ufw enable
sudo ufw status verbose
```

## Verify backend is not public on 8000

```bash
ss -tlnp | grep 8000
# Expect 127.0.0.1:8000 only (omeia-api.service)

curl -s http://127.0.0.1:8000/health
curl -s --max-time 2 http://<public-ip>:8000/health || echo "8000 correctly unreachable"
```

## Campus VPN / split horizon

If the desktop is not on a public IP, use a university-approved tunnel (WireGuard, SSH reverse proxy, or cloudflared) and still terminate TLS at Caddy/nginx on the tunnel endpoint. **NEEDS_USER_DECISION:** which exposure method IT allows.
