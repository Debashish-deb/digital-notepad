# Tailscale — Mac ↔ Linux Ollama (bypass EduVPN peer block)

EduVPN blocks Mac (`10.116.96.17`) ↔ workstation (`10.116.129.24`). Tailscale creates a private mesh (`100.x.x.x`) that works on top of any network.

## 1. Install Tailscale

### Mac
```bash
brew install tailscale
# Or download from https://tailscale.com/download/mac
sudo tailscale up
```
Sign in with Google/Microsoft/GitHub when the browser opens.

### Linux (workstation)
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```
Sign in with the **same Tailscale account** as the Mac.

## 2. Get Linux Tailscale IP

On Linux:
```bash
tailscale ip -4
```
Example: `100.64.0.12`

## 3. Ensure Ollama proxy is reachable (Linux)

```bash
cd ~/data4TB/digital-notepad
ln -sf configs/.env .env

# Ports on all interfaces (if not already)
grep "0.0.0.0:11434" docker-compose.yml || \
  sed -i 's|127.0.0.1:11434:11434|0.0.0.0:11434:11434|' docker-compose.yml

docker compose up -d ollama-proxy qdrant --force-recreate

# Optional: allow Tailscale interface through ufw
sudo ufw allow in on tailscale0 to any port 11434
sudo ufw allow in on tailscale0 to any port 6333
```

Test on Linux:
```bash
curl -H "Authorization: Bearer $OLLAMA_INTERNAL_TOKEN" http://127.0.0.1:11434/
```

## 4. Test from Mac

Replace `100.64.0.12` with your Linux Tailscale IP:

```bash
curl -H "Authorization: Bearer 449af4028256e7f34a84de016acc22e3c05d181577881387bb52e72187985278" \
  http://100.64.0.12:11434/
```

Expected: `Ollama is running`

## 5. Mac `configs/.env`

```env
DOCKER_LOCAL=false
LLM_PROVIDER=ollama
CHAT_LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_BASE_URL=http://100.64.0.12:11434/v1
OLLAMA_INTERNAL_TOKEN=<same token as Linux>
QDRANT_URL=http://100.64.0.12:6333
LLM_FALLBACK_PROVIDERS=ollama,gemini,mock
```

Restart app:
```bash
./start.sh
```

## 6. Quick test script (Mac)

```bash
./scripts/mac_test_tailscale_ollama.sh
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `tailscale: command not found` | Finish install; `sudo tailscale up` |
| Mac can't curl Linux 100.x | Check same Tailscale account; `tailscale status` on both |
| Connection refused | `docker compose ps`; proxy on `0.0.0.0:11434` |
| 401 Unauthorized | Match `OLLAMA_INTERNAL_TOKEN` on Mac and Linux |
| IT blocks Tailscale | Ask IT; fallback: Gemini on Mac |

## Security

- Keep `OLLAMA_INTERNAL_TOKEN` set (Caddy bearer proxy).
- Do not expose `0.0.0.0:11434` on the public university IP without auth — Tailscale traffic uses the `100.x` mesh.
