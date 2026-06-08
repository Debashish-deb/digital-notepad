"""Unified taxonomy assignment read/write helpers."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import psycopg

LOGGER = logging.getLogger(__name__)


def _db_conn() -> str:
    from omeia.api.supabase_config import postgres_conn

    return postgres_conn()


def list_assignments(
    asset_id: str,
    *,
    active_only: bool = True,
) -> list[dict[str, Any]]:
    clause = "AND superseded_at IS NULL" if active_only else ""
    sql = f"""
        SELECT asset_id, taxonomy_key, source, confidence, assigned_at, assigned_by, superseded_at
        FROM platform.taxonomy_assignment
        WHERE asset_id = %s {clause}
        ORDER BY assigned_at DESC;
    """
    try:
        with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (asset_id,))
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
    except Exception as exc:
        LOGGER.debug("taxonomy list failed: %s", exc)
        return []


def assign_taxonomy(
    *,
    asset_id: str,
    taxonomy_key: str,
    source: str,
    confidence: float = 1.0,
    assigned_by: str | None = "system",
    supersede_prior: bool = True,
) -> bool:
    """Write or update a taxonomy assignment."""
    try:
        with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
            with conn.cursor() as cur:
                if supersede_prior:
                    cur.execute(
                        """
                        UPDATE platform.taxonomy_assignment
                        SET superseded_at = %s
                        WHERE asset_id = %s AND taxonomy_key = %s AND source = %s AND superseded_at IS NULL;
                        """,
                        (datetime.now(timezone.utc), asset_id, taxonomy_key, source),
                    )
                cur.execute(
                    """
                    INSERT INTO platform.taxonomy_assignment (
                        asset_id, taxonomy_key, source, confidence, assigned_by
                    ) VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (asset_id, taxonomy_key, source) DO UPDATE SET
                        confidence = EXCLUDED.confidence,
                        assigned_by = EXCLUDED.assigned_by,
                        assigned_at = now(),
                        superseded_at = NULL;
                    """,
                    (asset_id, taxonomy_key, source, confidence, assigned_by),
                )
                conn.commit()
                return True
    except Exception as exc:
        LOGGER.warning("taxonomy assign failed: %s", exc)
        return False


def lookup_by_taxonomy_key(taxonomy_key: str, *, limit: int = 50) -> list[dict[str, Any]]:
    sql = """
        SELECT asset_id, taxonomy_key, source, confidence, assigned_at, assigned_by
        FROM platform.taxonomy_assignment
        WHERE taxonomy_key = %s AND superseded_at IS NULL
        ORDER BY confidence DESC, assigned_at DESC
        LIMIT %s;
    """
    try:
        with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (taxonomy_key, limit))
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
    except Exception as exc:
        LOGGER.debug("taxonomy lookup failed: %s", exc)
        return []
