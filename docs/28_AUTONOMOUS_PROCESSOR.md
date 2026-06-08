# Autonomous processor (OS daemon)

The vault ingest → project digitalization → Supabase document sync pipeline can run **without Cursor IDE**, cloud agents, or an open terminal in the editor.

Switching to a different Cursor project **does not** stop this work. Only explicit stop, process crash, or machine reboot ends it (systemd/launchd may restart on boot if enabled).

## Components

| Piece | Role |
|-------|------|
| `scripts/ops/autonomous_processor.py` | Supervisor: `--once`, `--daemon`, `--resume`, `--stop`, `--force` |
| `scripts/ops/autonomous_processor.sh` | `start` / `stop` / `status` / `once` wrapper (`nohup` + `disown`) |
| `omeia/data/processor_state.json` | Last step, checkpoint hints, errors, run history |
| `omeia/data/processor.pid` | Single-instance lock |
| `omeia/data/logs/autonomous_processor.log` | Append log (rotate externally if needed) |

## Pipeline steps

Configured with `PROCESSOR_STEPS` (default: `vault,digitalize,supabase_sync`):

1. **vault** — `run_ingest_scan` on `DATABASE_ROOT` and `LAB_STORAGE_ROOT` (when mounted), with `--resume` when requested.
2. **digitalize** — `run_digitalization(mode="full")` against lab project storage.
3. **supabase_sync** — `sync_documents_to_supabase` when `SUPABASE_SYNC_ENABLED=true` and DB password is set.

Daemon mode sleeps `PROCESSOR_INTERVAL_SEC` (default `3600`) between full cycles. After the first cycle, resume is enabled automatically for vault/digitalize checkpoints.

## Environment

Copy from `configs/.env.example`:

```bash
PROCESSOR_AUTONOMOUS=true
PROCESSOR_INTERVAL_SEC=3600
PROCESSOR_STEPS=vault,digitalize,supabase_sync
# optional cap per step:
# PROCESSOR_MAX_FILES=500
```

Loads `configs/.env` and `deploy/university-desktop/.env`.

## macOS (dev / lab Mac)

Manual start (survives closing Cursor and the shell that launched it):

```bash
cd farkki_ai_platform_blueprint
chmod +x scripts/ops/autonomous_processor.sh
./scripts/ops/autonomous_processor.sh start
./scripts/ops/autonomous_processor.sh status
./scripts/ops/autonomous_processor.sh stop
```

One-shot foreground run:

```bash
./scripts/ops/autonomous_processor.sh once
# or with resume:
./scripts/ops/autonomous_processor.sh once -- --resume
```

**launchd** (login auto-start): edit `deploy/university-desktop/launchd/com.omeia.processor.plist` placeholders, then:

```bash
cp deploy/university-desktop/launchd/com.omeia.processor.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.omeia.processor.plist
launchctl start com.omeia.processor
```

## Linux (production desktop)

Install unit (from repo clone under `/opt/omeia/...`):

```bash
sudo cp deploy/university-desktop/omeia-processor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable omeia-processor.service
sudo systemctl start omeia-processor.service
sudo systemctl status omeia-processor.service
```

Stop:

```bash
sudo systemctl stop omeia-processor.service
# or from repo checkout as omeia user:
./scripts/ops/autonomous_processor.sh stop
```

## API status (optional)

Unauthenticated health-style endpoint:

```bash
curl -s http://127.0.0.1:8000/api/processor/status | jq .
```

Reads `processor_state.json` and checks whether `processor.pid` is alive.

## What does *not* stop the processor

- Changing Cursor workspace / project
- Closing the chat or agent panel
- Stopping the FastAPI dev server (unless you rely on the same venv lock — processor is a separate process)

## What *does* stop it

- `./scripts/ops/autonomous_processor.sh stop`
- `python scripts/ops/autonomous_processor.py --stop`
- `sudo systemctl stop omeia-processor.service`
- `launchctl unload ~/Library/LaunchAgents/com.omeia.processor.plist`
- Reboot (unless systemd/launchd is enabled to start again)
