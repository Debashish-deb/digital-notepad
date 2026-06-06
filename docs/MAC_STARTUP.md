# Mac startup (thin client → Linux Docker)

No Docker Desktop on Mac. Linux workstation runs Ollama, Qdrant, Postgres.

## One-time setup

### 1. Mac `configs/.env`

Set your Linux SSH target (IP works from home; hostname needs VPN):

```env
OLLAMA_LINUX_SSH=debdeba@<linux-ip>
OLLAMA_INTERNAL_TOKEN=<same token as Linux configs/.env>
DOCKER_LOCAL=false
```

### 2. Linux (once per reboot)

```bash
cd ~/data4TB/digital-notepad
ln -sf configs/.env .env
docker compose up -d
docker exec omeia-ollama ollama list   # should show qwen2.5:3b+
```

### 3. Mac — university VPN (if at home)

Connect to Helsinki VPN so SSH to the workstation works.

---

## Every day — 3 steps

### Terminal 1 — tunnels (keep open)

```bash
cd /Users/debashishdeb/Downloads/OMEIA-AI
./scripts/mac_connect_linux.sh
```

### Terminal 2 — test + start app

```bash
cd /Users/debashishdeb/Downloads/OMEIA-AI
./scripts/mac_test_linux.sh
./start.sh
```

### Browser

Open **http://localhost:5173** and sign in with your Firebase account.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Could not resolve hostname` | Use Linux IP in `OLLAMA_LINUX_SSH`, or connect VPN |
| `Connection reset` on curl | On Linux: `docker compose up -d ollama-proxy --force-recreate` |
| Chat uses mock | Tunnel not running; run `mac_connect_linux.sh` |
| Search empty | Qdrant tunnel — included in `mac_connect_linux.sh` |
