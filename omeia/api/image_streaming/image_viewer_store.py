"""Postgres CRUD for image viewer ROIs, overlays, presets — JSON fallback when DB unavailable."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg

from omeia.api.paths import BLUEPRINT_ROOT

LOGGER = logging.getLogger(__name__)

STORE_PATH = BLUEPRINT_ROOT / "omeia" / "data" / "image_viewer_store.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db_conn() -> str:
    from omeia.api.supabase_config import postgres_conn

    return postgres_conn()


def _load_json_store() -> dict[str, Any]:
    if not STORE_PATH.is_file():
        return {"rois": [], "overlays": [], "presets": [], "annotation_feedback": []}
    try:
        return json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        LOGGER.warning("image_viewer_store read failed: %s", exc)
        return {"rois": [], "overlays": [], "presets": [], "annotation_feedback": []}


def _save_json_store(data: dict[str, Any]) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STORE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _table_exists(cur, table: str) -> bool:
    cur.execute(
        """
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'platform' AND table_name = %s
        LIMIT 1;
        """,
        (table.split(".")[-1],),
    )
    return cur.fetchone() is not None


def _db_available() -> bool:
    try:
        with psycopg.connect(_db_conn(), connect_timeout=4) as conn:
            with conn.cursor() as cur:
                return _table_exists(cur, "image_roi")
    except Exception:
        return False


# --- ROI ---


def list_rois(*, asset_id: str, user_email: str) -> list[dict[str, Any]]:
    if _db_available():
        try:
            with psycopg.connect(_db_conn(), connect_timeout=6) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT roi_id::text, asset_id, user_email, project, name, description,
                               tags, geometry, roi_type, created_at::text, updated_at::text
                        FROM platform.image_roi
                        WHERE asset_id = %s AND user_email = %s
                        ORDER BY updated_at DESC;
                        """,
                        (asset_id, user_email),
                    )
                    rows = cur.fetchall()
                    return [
                        {
                            "roi_id": r[0],
                            "asset_id": r[1],
                            "user_email": r[2],
                            "project": r[3],
                            "name": r[4],
                            "description": r[5],
                            "tags": r[6] or [],
                            "geometry": r[7] or {},
                            "roi_type": r[8],
                            "created_at": r[9],
                            "updated_at": r[10],
                        }
                        for r in rows
                    ]
        except Exception as exc:
            LOGGER.warning("list_rois db failed: %s", exc)

    store = _load_json_store()
    return [
        r
        for r in store.get("rois", [])
        if r.get("asset_id") == asset_id and r.get("user_email") == user_email
    ]


def create_roi(
    *,
    asset_id: str,
    user_email: str,
    name: str,
    geometry: dict[str, Any],
    roi_type: str = "rectangle",
    project: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    region_type: str | None = None,
) -> dict[str, Any]:
    roi_id = str(uuid.uuid4())
    now = _utc_now()
    record = {
        "roi_id": roi_id,
        "asset_id": asset_id,
        "user_email": user_email,
        "project": project,
        "name": name,
        "description": description,
        "tags": list(tags or []),
        "geometry": geometry,
        "roi_type": roi_type,
        "region_type": region_type,
        "created_at": now,
        "updated_at": now,
    }

    if _db_available():
        try:
            with psycopg.connect(_db_conn(), connect_timeout=6) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO platform.image_roi (
                            roi_id, asset_id, user_email, project, name, description,
                            tags, geometry, roi_type
                        )
                        VALUES (%s::uuid, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
                        RETURNING roi_id::text, created_at::text, updated_at::text;
                        """,
                        (
                            roi_id,
                            asset_id,
                            user_email,
                            project,
                            name,
                            description,
                            json.dumps(record["tags"]),
                            json.dumps({**geometry, **({"region_type": region_type} if region_type else {})}),
                            roi_type,
                        ),
                    )
                    row = cur.fetchone()
                    conn.commit()
                    if row:
                        record["roi_id"] = row[0]
                        record["created_at"] = row[1]
                        record["updated_at"] = row[2]
                    return record
        except Exception as exc:
            LOGGER.warning("create_roi db failed: %s", exc)

    store = _load_json_store()
    store.setdefault("rois", []).append(record)
    _save_json_store(store)
    return record


def delete_roi(*, roi_id: str, asset_id: str, user_email: str) -> bool:
    if _db_available():
        try:
            with psycopg.connect(_db_conn(), connect_timeout=6) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        DELETE FROM platform.image_roi
                        WHERE roi_id = %s::uuid AND asset_id = %s AND user_email = %s;
                        """,
                        (roi_id, asset_id, user_email),
                    )
                    conn.commit()
                    return cur.rowcount > 0
        except Exception as exc:
            LOGGER.warning("delete_roi db failed: %s", exc)

    store = _load_json_store()
    before = len(store.get("rois", []))
    store["rois"] = [
        r
        for r in store.get("rois", [])
        if not (
            r.get("roi_id") == roi_id
            and r.get("asset_id") == asset_id
            and r.get("user_email") == user_email
        )
    ]
    _save_json_store(store)
    return len(store["rois"]) < before


# --- Overlays ---


def list_overlays(*, asset_id: str) -> list[dict[str, Any]]:
    if _db_available():
        try:
            with psycopg.connect(_db_conn(), connect_timeout=6) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT overlay_id::text, asset_id, overlay_asset_id, overlay_type,
                               label, metadata, created_at::text
                        FROM platform.image_overlay
                        WHERE asset_id = %s
                        ORDER BY created_at DESC;
                        """,
                        (asset_id,),
                    )
                    return [
                        {
                            "overlay_id": r[0],
                            "asset_id": r[1],
                            "overlay_asset_id": r[2],
                            "overlay_type": r[3],
                            "label": r[4],
                            "metadata": r[5] or {},
                            "created_at": r[6],
                        }
                        for r in cur.fetchall()
                    ]
        except Exception as exc:
            LOGGER.warning("list_overlays db failed: %s", exc)

    store = _load_json_store()
    return [o for o in store.get("overlays", []) if o.get("asset_id") == asset_id]


def create_overlay(
    *,
    asset_id: str,
    overlay_asset_id: str,
    overlay_type: str = "cell",
    label: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    overlay_id = str(uuid.uuid4())
    record = {
        "overlay_id": overlay_id,
        "asset_id": asset_id,
        "overlay_asset_id": overlay_asset_id,
        "overlay_type": overlay_type,
        "label": label,
        "metadata": metadata or {},
        "created_at": _utc_now(),
    }

    if _db_available():
        try:
            with psycopg.connect(_db_conn(), connect_timeout=6) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO platform.image_overlay (
                            overlay_id, asset_id, overlay_asset_id, overlay_type, label, metadata
                        )
                        VALUES (%s::uuid, %s, %s, %s, %s, %s::jsonb)
                        RETURNING overlay_id::text, created_at::text;
                        """,
                        (
                            overlay_id,
                            asset_id,
                            overlay_asset_id,
                            overlay_type,
                            label,
                            json.dumps(record["metadata"]),
                        ),
                    )
                    row = cur.fetchone()
                    conn.commit()
                    if row:
                        record["overlay_id"] = row[0]
                        record["created_at"] = row[1]
                    return record
        except Exception as exc:
            LOGGER.warning("create_overlay db failed: %s", exc)

    store = _load_json_store()
    store.setdefault("overlays", []).append(record)
    _save_json_store(store)
    return record


def delete_overlay(*, overlay_id: str, asset_id: str) -> bool:
    if _db_available():
        try:
            with psycopg.connect(_db_conn(), connect_timeout=6) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        DELETE FROM platform.image_overlay
                        WHERE overlay_id = %s::uuid AND asset_id = %s;
                        """,
                        (overlay_id, asset_id),
                    )
                    conn.commit()
                    return cur.rowcount > 0
        except Exception as exc:
            LOGGER.warning("delete_overlay db failed: %s", exc)

    store = _load_json_store()
    before = len(store.get("overlays", []))
    store["overlays"] = [
        o
        for o in store.get("overlays", [])
        if not (o.get("overlay_id") == overlay_id and o.get("asset_id") == asset_id)
    ]
    _save_json_store(store)
    return len(store["overlays"]) < before


# --- Channel presets (per user) ---


def list_channel_presets(*, user_email: str) -> list[dict[str, Any]]:
    if _db_available():
        try:
            with psycopg.connect(_db_conn(), connect_timeout=6) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT preset_id::text, user_email, name, channels, created_at::text, updated_at::text
                        FROM platform.image_channel_preset
                        WHERE user_email = %s
                        ORDER BY updated_at DESC;
                        """,
                        (user_email,),
                    )
                    return [
                        {
                            "preset_id": r[0],
                            "user_email": r[1],
                            "name": r[2],
                            "channels": r[3] or [],
                            "created_at": r[4],
                            "updated_at": r[5],
                        }
                        for r in cur.fetchall()
                    ]
        except Exception as exc:
            LOGGER.warning("list_channel_presets db failed: %s", exc)

    store = _load_json_store()
    return [p for p in store.get("presets", []) if p.get("user_email") == user_email]


def save_channel_preset(
    *,
    user_email: str,
    name: str,
    channels: list[dict[str, Any]],
    preset_id: str | None = None,
) -> dict[str, Any]:
    pid = preset_id or str(uuid.uuid4())
    now = _utc_now()
    record = {
        "preset_id": pid,
        "user_email": user_email,
        "name": name,
        "channels": channels,
        "created_at": now,
        "updated_at": now,
    }

    if _db_available():
        try:
            with psycopg.connect(_db_conn(), connect_timeout=6) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO platform.image_channel_preset (preset_id, user_email, name, channels)
                        VALUES (%s::uuid, %s, %s, %s::jsonb)
                        ON CONFLICT (preset_id) DO UPDATE SET
                            name = EXCLUDED.name,
                            channels = EXCLUDED.channels,
                            updated_at = now()
                        RETURNING preset_id::text, created_at::text, updated_at::text;
                        """,
                        (pid, user_email, name, json.dumps(channels)),
                    )
                    row = cur.fetchone()
                    conn.commit()
                    if row:
                        record["preset_id"] = row[0]
                        record["created_at"] = row[1]
                        record["updated_at"] = row[2]
                    return record
        except Exception as exc:
            LOGGER.warning("save_channel_preset db failed: %s", exc)

    store = _load_json_store()
    presets = store.setdefault("presets", [])
    presets = [p for p in presets if not (p.get("preset_id") == pid and p.get("user_email") == user_email)]
    presets.append(record)
    store["presets"] = presets
    _save_json_store(store)
    return record


def delete_channel_preset(*, preset_id: str, user_email: str) -> bool:
    if _db_available():
        try:
            with psycopg.connect(_db_conn(), connect_timeout=6) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        DELETE FROM platform.image_channel_preset
                        WHERE preset_id = %s::uuid AND user_email = %s;
                        """,
                        (preset_id, user_email),
                    )
                    conn.commit()
                    return cur.rowcount > 0
        except Exception as exc:
            LOGGER.warning("delete_channel_preset db failed: %s", exc)

    store = _load_json_store()
    before = len(store.get("presets", []))
    store["presets"] = [
        p
        for p in store.get("presets", [])
        if not (p.get("preset_id") == preset_id and p.get("user_email") == user_email)
    ]
    _save_json_store(store)
    return len(store["presets"]) < before


def save_annotation_feedback(
    *,
    asset_id: str,
    user_email: str,
    target_type: str,
    target_id: str,
    learning_category: str = "draft",
    feedback: str = "neutral",
    notes: str | None = None,
) -> dict[str, Any]:
    """Persist lab-memory feedback for viewer annotations."""
    feedback_id = str(uuid.uuid4())
    record = {
        "feedback_id": feedback_id,
        "asset_id": asset_id,
        "user_email": user_email,
        "target_type": target_type,
        "target_id": target_id,
        "learning_category": learning_category,
        "feedback": feedback,
        "notes": notes,
        "created_at": _utc_now(),
    }
    store = _load_json_store()
    entries = store.setdefault("annotation_feedback", [])
    entries = [e for e in entries if not (e.get("target_id") == target_id and e.get("user_email") == user_email)]
    entries.append(record)
    store["annotation_feedback"] = entries
    _save_json_store(store)
    return record


def inspect_cell(
    *,
    asset_id: str,
    cell_id: str,
    overlay_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return cell metrics from overlay metadata or deterministic stub for tests."""
    md = overlay_metadata or {}
    cells = md.get("cells") if isinstance(md.get("cells"), dict) else {}
    if cell_id in cells:
        entry = cells[cell_id]
        return {"asset_id": asset_id, "cell_id": cell_id, **entry}

    seed = sum(ord(c) for c in cell_id) % 1000
    return {
        "asset_id": asset_id,
        "cell_id": cell_id,
        "area_um2": round(120 + seed * 0.5, 2),
        "eccentricity": round(0.35 + (seed % 50) / 100, 3),
        "centroid": {"x": 100 + seed % 200, "y": 80 + seed % 150},
        "marker_intensities": {
            "CD3": round(0.2 + (seed % 30) / 100, 3),
            "CD8": round(0.15 + (seed % 25) / 100, 3),
        },
        "stub": True,
    }
