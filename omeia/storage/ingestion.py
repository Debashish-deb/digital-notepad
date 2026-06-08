"""Scan → manifest → Supabase metadata (storage_objects + optional vault linkage)."""
from __future__ import annotations

import logging
from typing import Any

import psycopg

from omeia.storage import datacloud_webdav, pdrive_smb

LOGGER = logging.getLogger(__name__)

PROVIDER_SCANNERS = {
    "datacloud_webdav": datacloud_webdav,
    "pdrive_smb": pdrive_smb,
}

ROOT_ID_BY_PROVIDER = {
    "datacloud_webdav": "datacloud_webdav",
    "pdrive_smb": "pdrive_smb",
}


def _db_conn() -> str:
    from omeia.api.supabase_config import postgres_conn

    return postgres_conn()


def build_manifest(provider_id: str, relative_path: str = "", *, max_entries: int = 500) -> dict[str, Any]:
    mod = PROVIDER_SCANNERS.get(provider_id)
    if mod is None:
        return {"ok": False, "error": f"unknown_provider:{provider_id}"}
    if not mod.is_configured():
        return {"ok": False, "error": "not_configured"}
    return mod.build_manifest(relative_path, max_entries=max_entries)


def upsert_manifest_rows(manifest: dict[str, Any]) -> dict[str, Any]:
    """Upsert file entries from manifest into platform.storage_objects (metadata only)."""
    provider_id = manifest.get("provider_id") or ""
    root_id = ROOT_ID_BY_PROVIDER.get(provider_id)
    if not root_id:
        return {"ok": False, "error": "invalid_manifest_provider"}

    files = manifest.get("files") or []
    upserted = 0
    try:
        with psycopg.connect(_db_conn(), connect_timeout=30) as conn:
            with conn.cursor() as cur:
                for f in files:
                    logical = f.get("logical_path")
                    if not logical:
                        continue
                    rel = f.get("relative_path") or ""
                    cur.execute(
                        """
                        INSERT INTO platform.storage_objects (
                          storage_root_id, storage_provider, logical_path, relative_path,
                          object_type, size_bytes, etag, mime_type, scan_status, last_seen_at, updated_at
                        ) VALUES (
                          %s, %s, %s, %s, %s, %s, %s, %s, 'discovered', now(), now()
                        )
                        ON CONFLICT (storage_provider, logical_path) DO UPDATE SET
                          size_bytes = EXCLUDED.size_bytes,
                          etag = EXCLUDED.etag,
                          mime_type = EXCLUDED.mime_type,
                          last_seen_at = now(),
                          updated_at = now();
                        """,
                        (
                            root_id,
                            provider_id,
                            logical,
                            rel,
                            f.get("type") or "file",
                            f.get("size_bytes"),
                            f.get("etag"),
                            f.get("mime_type"),
                        ),
                    )
                    upserted += 1
            conn.commit()
    except Exception as exc:
        LOGGER.warning("storage_objects upsert failed: %s", exc)
        return {"ok": False, "error": str(exc), "upserted": upserted}

    return {
        "ok": True,
        "provider_id": provider_id,
        "upserted": upserted,
        "truncated": manifest.get("truncated", False),
    }


def ingest_provider_scan(
    provider_id: str,
    relative_path: str = "",
    *,
    max_entries: int = 500,
) -> dict[str, Any]:
    """End-to-end: scan → manifest → storage_objects."""
    manifest = build_manifest(provider_id, relative_path, max_entries=max_entries)
    if not manifest.get("ok", True) and manifest.get("error"):
        return manifest
    persist = upsert_manifest_rows(manifest)
    return {"manifest": manifest, "persist": persist}
