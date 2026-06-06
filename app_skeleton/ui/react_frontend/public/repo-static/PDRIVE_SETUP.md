# P-drive (mounted path) setup

**Role:** Secondary research storage (CyCIF outputs, large imaging on lab share).  
**Model:** Read a **local mount point** already connected by the OS; no SMB authentication in application code unless you add it later.

## Environment variables

```bash
PDRIVE_ENABLED=true
PDRIVE_MOUNT_PATH=/Volumes/pdrive   # example — use your real mount
PDRIVE_LOGICAL_ROOT=pdrive://
```

Legacy alias: `PDRIVE_SMB_ROOT` → `PDRIVE_MOUNT_PATH`.

## storage_provider

Use `pdrive_smb` in vault rows and `platform.storage_objects` (historical id; implementation is mounted path, not in-process SMB).

## Connector capabilities

Module: `app_skeleton/storage/pdrive_smb.py`

| Operation | API |
|-----------|-----|
| List | `GET /api/storage/pdrive/list?relative_path=` |
| Scan | `GET /api/storage/pdrive/scan` |
| Manifest | `GET /api/storage/pdrive/manifest` |

Scans are **read-only** — no delete, move, or rename.

## Verification

```bash
test -d "$PDRIVE_MOUNT_PATH" && echo "mount ok"
curl -s "http://localhost:8000/api/storage/pdrive/list" | jq .
```

## NEEDS_USER_DECISION

| Blocker | Why | Info needed | Safe fallback |
|---------|-----|---------------|---------------|
| Path not mounted | `PDRIVE_MOUNT_PATH` missing or directory absent | Absolute mount path on server/workstation | `PDRIVE_ENABLED=false`; secondary assets indexed only on DataCloud or local mirror |
| SMB credentials later | VPN/mount requires lab IT | UNC path + service account (out of scope for v1) | Manual mount + `PDRIVE_MOUNT_PATH` only |

See: `docs/16_STORAGE_CONNECTOR_DESIGN.md`.
