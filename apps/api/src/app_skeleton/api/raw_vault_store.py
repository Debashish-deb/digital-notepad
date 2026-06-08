"""Raw knowledge vault — JSON inventory + optional Postgres registry (Phases 2–3)."""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg

from app_skeleton.api.page_registry import resolve_page_ids
from app_skeleton.api.data_layout import inventory_json, inventory_summary_json, inventory_write_dir
from app_skeleton.api.paths import BLUEPRINT_ROOT, DATABASE_ROOT, SCRIPTS_DIR

LOGGER = logging.getLogger(__name__)

INVENTORY_DIR = inventory_write_dir()
INVENTORY_JSON = inventory_json()
AUDIT_INVENTORY_JSON = (
    BLUEPRINT_ROOT / "reports" / "document_library_audit" / "first_pass" / "document_inventory.json"
)
INVENTORY_SUMMARY = inventory_summary_json()
VAULT_SQL = BLUEPRINT_ROOT / "sql" / "111_raw_asset_vault.sql"

_PUBLIC_FIELDS = (
    "asset_id",
    "storage_provider",
    "logical_path",
    "filename",
    "extension",
    "size_bytes",
    "checksum_sha256",
    "asset_type",
    "domain",
    "project_hint",
    "section_hint",
    "sensitivity_level",
    "assignment_confidence",
    "sensitivity_confidence",
    "review_status",
    "vector_status",
    "graph_status",
    "modified_at",
    "indexed_at",
    "extraction_status",
    "mime_type",
    "page_domain_id",
    "page_section_id",
    "page_domain_label",
    "page_section_label",
    "metadata_json",
)


def _db_conn() -> str:
    from app_skeleton.api.supabase_config import postgres_conn

    return postgres_conn()


def _vault_active_sql_clauses(*, table: str = "v") -> list[str]:
    """SQL fragments excluding duplicate copies and inventory-inactive assets."""
    col = f"{table}.metadata_json" if table else "metadata_json"
    return [
        f"COALESCE({col}->>'duplicate_status', 'unique') != 'duplicate'",
        f"COALESCE({col}->>'inventory_active', 'true') NOT IN ('false', '0', 'no')",
    ]


def _is_vault_row_active(row: dict[str, Any]) -> bool:
    """JSON-side filter mirroring _vault_active_sql_clauses."""
    md = row.get("metadata_json") or row.get("metadata_preview") or {}
    if isinstance(md, str):
        try:
            md = json.loads(md)
        except Exception:
            md = {}
    if not isinstance(md, dict):
        md = {}
    if (md.get("duplicate_status") or "unique") == "duplicate":
        return False
    inv = str(md.get("inventory_active", "true")).strip().lower()
    return inv not in ("false", "0", "no")


def _public_row(row: dict[str, Any]) -> dict[str, Any]:
    out = {k: row[k] for k in _PUBLIC_FIELDS if k in row}
    conf = float(row.get("assignment_confidence") or 0)
    if conf < 0.6:
        out["review_status"] = row.get("review_status") or "raw"
    elif conf < 0.86:
        out["review_status"] = row.get("review_status") or "tentative"
    return out


def _row_from_pg(record: tuple, columns: list[str]) -> dict[str, Any]:
    row = dict(zip(columns, record))
    for key in ("assignment_confidence", "sensitivity_confidence"):
        if key in row and row[key] is not None:
            row[key] = float(row[key])
    if row.get("size_bytes") is not None:
        row["size_bytes"] = int(row["size_bytes"])
    return _public_row(row)


def ensure_vault_schema() -> None:
    from app_skeleton.api.sql_migrations import apply_pending_migrations

    applied = apply_pending_migrations(conn_str=_db_conn())
    if applied:
        LOGGER.info("Vault schema: applied migrations %s", ", ".join(applied))


def load_summary() -> dict[str, Any]:
    if not INVENTORY_SUMMARY.exists():
        return {"asset_count": 0, "generated_at": None, "needs_review_count": 0}
    try:
        summary = json.loads(INVENTORY_SUMMARY.read_text(encoding="utf-8"))
    except Exception as exc:
        LOGGER.warning("Failed to read vault summary: %s", exc)
        return {"asset_count": 0, "error": str(exc)}
    try:
        with psycopg.connect(_db_conn(), connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM platform.raw_asset_vault;")
                summary["postgres_asset_count"] = cur.fetchone()[0]
    except Exception:
        summary["postgres_asset_count"] = None
    public = {k: v for k, v in summary.items() if k != "database_root"}
    return public


def load_inventory_rows() -> list[dict[str, Any]]:
    for path, label in (
        (INVENTORY_JSON, "raw_asset_inventory"),
        (AUDIT_INVENTORY_JSON, "audit_inventory"),
    ):
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                if label == "audit_inventory":
                    LOGGER.info("Vault inventory fallback: using audit document_inventory.json")
                return data
        except Exception as exc:
            LOGGER.warning("Failed to read vault inventory from %s: %s", path, exc)
    return []


def _search_vault_json(
    query: str,
    *,
    domain: str | None,
    project_hint: str | None,
    review_status: str | None,
    vector_status: str | None,
    extraction_status: str | None,
    uncategorized_only: bool,
    limit: int,
) -> list[dict[str, Any]]:
    q = (query or "").strip().lower()
    tokens = [t for t in q.split() if len(t) >= 2] if q else []
    hits: list[tuple[float, dict[str, Any]]] = []

    for row in load_inventory_rows():
        if not _is_vault_row_active(row):
            continue
        if domain and row.get("domain") != domain:
            continue
        if project_hint and (row.get("project_hint") or "").lower() != project_hint.lower():
            continue
        if review_status and row.get("review_status") != review_status:
            continue
        if vector_status and row.get("vector_status") != vector_status:
            continue
        if extraction_status and row.get("extraction_status") != extraction_status:
            continue
        if uncategorized_only and row.get("page_domain_id"):
            continue
        if uncategorized_only and row.get("review_status") not in (None, "uncategorized", "raw"):
            if row.get("page_domain_id"):
                continue
        blob = " ".join(
            str(row.get(k, ""))
            for k in ("logical_path", "filename", "asset_type", "domain", "section_hint", "project_hint")
        ).lower()
        if tokens:
            score = sum(2.0 if tok in blob else 0.0 for tok in tokens)
            if score <= 0:
                continue
        else:
            score = 0.0
        hits.append((score, _public_row(row)))

    hits.sort(key=lambda x: -x[0])
    return [h[1] for h in hits[:limit]]


def _search_vault_postgres(
    query: str,
    *,
    domain: str | None,
    project_hint: str | None,
    review_status: str | None,
    vector_status: str | None,
    extraction_status: str | None,
    uncategorized_only: bool,
    limit: int,
) -> list[dict[str, Any]]:
    tokens = [t for t in (query or "").lower().split() if len(t) >= 2]
    clauses = ["1=1"]
    params: list[Any] = []
    if domain:
        clauses.append("v.domain = %s")
        params.append(domain)
    if project_hint:
        clauses.append("lower(v.project_hint) = lower(%s)")
        params.append(project_hint)
    if review_status:
        clauses.append("v.review_status = %s")
        params.append(review_status)
    if vector_status:
        clauses.append("v.vector_status = %s")
        params.append(vector_status)
    if extraction_status:
        clauses.append("v.extraction_status = %s")
        params.append(extraction_status)
    if uncategorized_only:
        clauses.append("v.page_domain_id IS NULL")
    clauses.extend(_vault_active_sql_clauses(table="v"))
    if tokens:
        ors = [
            "(lower(v.logical_path || ' ' || coalesce(v.filename, '')) LIKE %s)"
            for _ in tokens
        ]
        clauses.append(f"({' OR '.join(ors)})")
        params.extend(f"%{tok}%" for tok in tokens)

    sql = f"""
        SELECT
            v.asset_id, v.storage_provider, v.logical_path, v.filename, v.extension,
            v.size_bytes, v.checksum_sha256, v.asset_type, v.domain, v.project_hint, v.section_hint,
            v.sensitivity_level, v.assignment_confidence, v.sensitivity_confidence,
            v.review_status, v.vector_status, v.graph_status, v.extraction_status,
            v.modified_at, v.indexed_at, v.mime_type, v.page_domain_id, v.page_section_id,
            pd.label AS page_domain_label, ps.label AS page_section_label,
            v.metadata_json
        FROM platform.raw_asset_vault v
        LEFT JOIN platform.page_domain pd ON pd.page_domain_id = v.page_domain_id
        LEFT JOIN platform.page_section ps ON ps.page_section_id = v.page_section_id
        WHERE {' AND '.join(clauses)}
        ORDER BY assignment_confidence DESC, logical_path
        LIMIT %s;
    """
    params.append(limit)
    columns = [
        "asset_id", "storage_provider", "logical_path", "filename", "extension",
        "size_bytes", "checksum_sha256", "asset_type", "domain", "project_hint", "section_hint",
        "sensitivity_level", "assignment_confidence", "sensitivity_confidence",
        "review_status", "vector_status", "graph_status", "extraction_status",
        "modified_at", "indexed_at", "mime_type", "page_domain_id", "page_section_id",
        "page_domain_label", "page_section_label", "metadata_json",
    ]
    with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return [_row_from_pg(r, columns) for r in cur.fetchall()]


def search_vault(
    query: str,
    *,
    domain: str | None = None,
    project_hint: str | None = None,
    review_status: str | None = None,
    vector_status: str | None = None,
    extraction_status: str | None = None,
    uncategorized_only: bool = False,
    limit: int = 25,
) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 100))
    try:
        hits = _search_vault_postgres(
            query,
            domain=domain,
            project_hint=project_hint,
            review_status=review_status,
            vector_status=vector_status,
            extraction_status=extraction_status,
            uncategorized_only=uncategorized_only,
            limit=limit,
        )
        if hits:
            return _sanitize_metadata_in_rows(hits)
    except Exception as exc:
        LOGGER.debug("Postgres vault search unavailable: %s", exc)

    from app_skeleton.api.platform_flags import vault_json_fallback_enabled

    if not vault_json_fallback_enabled():
        return []
    return _sanitize_metadata_in_rows(
        _search_vault_json(
            query,
            domain=domain,
            project_hint=project_hint,
            review_status=review_status,
            vector_status=vector_status,
            extraction_status=extraction_status,
            uncategorized_only=uncategorized_only,
            limit=limit,
        )
    )


_FETCH_VAULT_BY_IDS_COLUMNS = [
    "asset_id", "storage_provider", "logical_path", "filename", "extension",
    "size_bytes", "checksum_sha256", "asset_type", "domain", "project_hint", "section_hint",
    "sensitivity_level", "assignment_confidence", "sensitivity_confidence",
    "review_status", "vector_status", "graph_status", "extraction_status",
    "modified_at", "indexed_at", "mime_type", "page_domain_id", "page_section_id",
    "metadata_json",
]


def fetch_vault_assets_by_ids(asset_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Load vault rows by asset_id for semantic enrichment and checksum dedupe."""
    ids = [str(i).strip() for i in asset_ids if str(i).strip()]
    if not ids:
        return {}
    try:
        with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT {", ".join(_FETCH_VAULT_BY_IDS_COLUMNS)}
                    FROM platform.raw_asset_vault
                    WHERE asset_id = ANY(%s);
                    """,
                    (ids,),
                )
                return {
                    str(record[0]): _row_from_pg(record, _FETCH_VAULT_BY_IDS_COLUMNS)
                    for record in cur.fetchall()
                }
    except Exception as exc:
        LOGGER.debug("fetch_vault_assets_by_ids unavailable: %s", exc)
        return {}


def vault_postgres_reachable() -> bool:
    """True when platform.raw_asset_vault is queryable."""
    try:
        with psycopg.connect(_db_conn(), connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM platform.raw_asset_vault LIMIT 1;")
                return True
    except Exception:
        return False


def _sanitize_metadata_in_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Expose safe metadata subset; never leak original_path from metadata."""
    out: list[dict[str, Any]] = []
    for row in rows:
        r = dict(row)
        md = r.pop("metadata_json", None) or {}
        if isinstance(md, str):
            try:
                md = json.loads(md)
            except Exception:
                md = {}
        if isinstance(md, dict):
            r["metadata_preview"] = {
                k: md[k]
                for k in ("excerpt", "vault_policy", "error", "sheet_count", "line_count")
                if k in md
            }
        out.append(_public_row(r))
    return out


def review_queue(
    *,
    limit: int = 50,
    max_confidence: float = 0.85,
    queue: str = "low_confidence",
    extraction_status: str | None = None,
    review_status: str | None = None,
) -> list[dict[str, Any]]:
    """Review queues: low_confidence | uncategorized | failed."""
    limit = max(1, min(limit, 200))
    queue = (queue or "low_confidence").strip().lower()
    try:
        with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
            with conn.cursor() as cur:
                clauses: list[str] = []
                params: list[Any] = []
                if queue == "uncategorized":
                    clauses.append("(page_domain_id IS NULL OR review_status = 'uncategorized')")
                elif queue == "failed":
                    clauses.append("extraction_status = 'failed'")
                else:
                    clauses.append("assignment_confidence < %s")
                    params.append(max_confidence)
                if extraction_status:
                    clauses.append("extraction_status = %s")
                    params.append(extraction_status)
                if review_status:
                    clauses.append("review_status = %s")
                    params.append(review_status)
                clauses.extend(_vault_active_sql_clauses(table="raw_asset_vault"))
                params.append(limit)
                cur.execute(
                    f"""
                    SELECT
                        asset_id, storage_provider, logical_path, filename, extension,
                        size_bytes, checksum_sha256, asset_type, domain, project_hint, section_hint,
                        sensitivity_level, assignment_confidence, sensitivity_confidence,
                        review_status, vector_status, graph_status, extraction_status,
                        modified_at, indexed_at, mime_type, page_domain_id, page_section_id,
                        metadata_json
                    FROM platform.raw_asset_vault
                    WHERE {' AND '.join(clauses) if clauses else '1=1'}
                    ORDER BY updated_at DESC NULLS LAST, logical_path
                    LIMIT %s;
                    """,
                    params,
                )
                cols = [d[0] for d in cur.description]
                return _sanitize_metadata_in_rows([_row_from_pg(r, cols) for r in cur.fetchall()])
    except Exception as exc:
        LOGGER.debug("Postgres review queue unavailable: %s", exc)

    rows = load_inventory_rows()
    filtered: list[dict[str, Any]] = []
    for r in rows:
        if not _is_vault_row_active(r):
            continue
        if queue == "uncategorized" and r.get("page_domain_id"):
            continue
        if queue == "failed" and r.get("extraction_status") != "failed":
            continue
        if queue == "low_confidence" and float(r.get("assignment_confidence") or 0) >= max_confidence:
            continue
        if extraction_status and r.get("extraction_status") != extraction_status:
            continue
        if review_status and r.get("review_status") != review_status:
            continue
        filtered.append(_public_row(r))
    filtered.sort(key=lambda r: float(r.get("assignment_confidence") or 0))
    return filtered[:limit]


def mark_asset_reviewed(asset_id: str, *, review_status: str = "reviewed") -> dict[str, Any]:
    ensure_vault_schema()
    with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE platform.raw_asset_vault
                SET review_status = %s, updated_at = now()
                WHERE asset_id = %s
                RETURNING asset_id, review_status;
                """,
                (review_status, asset_id),
            )
            row = cur.fetchone()
            if not row:
                return {"status": "not_found", "asset_id": asset_id}
            cur.execute(
                """
                INSERT INTO platform.vault_audit_event (asset_id, event_type, actor, details)
                VALUES (%s, 'review_marked', 'api', %s::jsonb);
                """,
                (asset_id, json.dumps({"review_status": review_status})),
            )
        conn.commit()
    return {"status": "ok", "asset_id": asset_id, "review_status": review_status}


def list_failed_assets(*, project_hint: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    rows = review_queue(limit=limit, queue="failed")
    if project_hint:
        rows = [r for r in rows if (r.get("project_hint") or "").lower() == project_hint.lower()]
    return rows


def deduplication_report(*, limit: int = 30) -> dict[str, Any]:
    """Duplicate groups by checksum (logical paths only in response)."""
    limit = max(1, min(int(limit or 30), 200))
    try:
        with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT checksum_sha256, COUNT(*), array_agg(logical_path ORDER BY logical_path)
                    FROM platform.raw_asset_vault
                    WHERE checksum_sha256 IS NOT NULL AND checksum_sha256 <> ''
                    GROUP BY checksum_sha256
                    HAVING COUNT(*) > 1
                    ORDER BY COUNT(*) DESC
                    LIMIT %s;
                    """,
                    (limit,),
                )
                groups = [
                    {
                        "checksum_sha256": digest,
                        "count": count,
                        "logical_paths": sorted(paths or [])[:20],
                    }
                    for digest, count, paths in cur.fetchall()
                ]
                return {
                    "duplicate_checksum_groups": len(groups),
                    "groups": groups,
                    "source": "postgres",
                }
    except Exception as exc:
        LOGGER.debug("Postgres deduplication_report unavailable: %s", exc)

    by_hash: dict[str, list[str]] = defaultdict(list)
    for row in load_inventory_rows():
        digest = (row.get("checksum_sha256") or "").strip()
        if not digest:
            continue
        by_hash[digest].append(row.get("logical_path") or row.get("filename") or "?")

    groups = [
        {"checksum_sha256": h, "count": len(paths), "logical_paths": sorted(paths)[:20]}
        for h, paths in by_hash.items()
        if len(paths) > 1
    ]
    groups.sort(key=lambda g: -g["count"])
    return {
        "duplicate_checksum_groups": len(groups),
        "groups": groups[:limit],
        "source": "json",
    }


def sync_inventory_to_postgres(*, batch_size: int = 400) -> dict[str, Any]:
    rows = load_inventory_rows()
    if not rows:
        raise FileNotFoundError("Run vault rebuild first — raw_asset_inventory.json missing")

    ensure_vault_schema()
    upserted = 0
    review_created = 0
    with psycopg.connect(_db_conn(), connect_timeout=30) as conn:
        with conn.cursor() as cur:
            for i in range(0, len(rows), batch_size):
                batch = rows[i : i + batch_size]
                payloads = []
                for r in batch:
                    page_domain_id, page_section_id = resolve_page_ids(
                        domain=r.get("domain"),
                        section_hint=r.get("section_hint"),
                        logical_path=r.get("logical_path"),
                    )
                    payloads.append({
                        "asset_id": r["asset_id"],
                        "storage_provider": r.get("storage_provider", "local_database_mirror"),
                        "logical_path": r["logical_path"],
                        "filename": r["filename"],
                        "extension": r.get("extension", ""),
                        "size_bytes": r.get("size_bytes", 0),
                        "checksum_sha256": r.get("checksum_sha256") or "",
                        "mime_type": r.get("mime_type") or "application/octet-stream",
                        "asset_type": r.get("asset_type", "other"),
                        "domain": r.get("domain"),
                        "project_hint": r.get("project_hint") or "",
                        "section_hint": r.get("section_hint") or "",
                        "page_domain_id": page_domain_id,
                        "page_section_id": page_section_id,
                        "sensitivity_level": r.get("sensitivity_level", "unknown"),
                        "assignment_confidence": r.get("assignment_confidence", 0),
                        "sensitivity_confidence": r.get("sensitivity_confidence", 0),
                        "review_status": r.get("review_status", "raw"),
                        "vector_status": r.get("vector_status", "not_evaluated"),
                        "graph_status": r.get("graph_status", "not_asserted"),
                        "extraction_status": r.get("extraction_status", "not_started"),
                        "original_path": r.get("original_path"),
                        "modified_at": r.get("modified_at"),
                        "indexed_at": r.get("indexed_at"),
                        "provenance": json.dumps({"source": "build_raw_asset_inventory"}),
                    })
                cur.executemany(
                    """
                    INSERT INTO platform.raw_asset_vault (
                        asset_id, storage_provider, logical_path, filename, extension,
                        size_bytes, checksum_sha256, mime_type, asset_type, domain, project_hint, section_hint,
                        page_domain_id, page_section_id,
                        sensitivity_level, assignment_confidence, sensitivity_confidence,
                        review_status, vector_status, graph_status, extraction_status,
                        original_path, modified_at, indexed_at, provenance, updated_at
                    ) VALUES (
                        %(asset_id)s, %(storage_provider)s, %(logical_path)s, %(filename)s, %(extension)s,
                        %(size_bytes)s, %(checksum_sha256)s, %(mime_type)s, %(asset_type)s, %(domain)s,
                        %(project_hint)s, %(section_hint)s, %(page_domain_id)s, %(page_section_id)s,
                        %(sensitivity_level)s, %(assignment_confidence)s, %(sensitivity_confidence)s,
                        %(review_status)s, %(vector_status)s, %(graph_status)s, %(extraction_status)s,
                        %(original_path)s, %(modified_at)s, %(indexed_at)s,
                        %(provenance)s::jsonb, now()
                    )
                    ON CONFLICT (asset_id) DO UPDATE SET
                        storage_provider = EXCLUDED.storage_provider,
                        logical_path = EXCLUDED.logical_path,
                        filename = EXCLUDED.filename,
                        extension = EXCLUDED.extension,
                        size_bytes = EXCLUDED.size_bytes,
                        checksum_sha256 = EXCLUDED.checksum_sha256,
                        mime_type = EXCLUDED.mime_type,
                        asset_type = EXCLUDED.asset_type,
                        domain = EXCLUDED.domain,
                        project_hint = EXCLUDED.project_hint,
                        section_hint = EXCLUDED.section_hint,
                        page_domain_id = EXCLUDED.page_domain_id,
                        page_section_id = EXCLUDED.page_section_id,
                        sensitivity_level = EXCLUDED.sensitivity_level,
                        assignment_confidence = EXCLUDED.assignment_confidence,
                        sensitivity_confidence = EXCLUDED.sensitivity_confidence,
                        review_status = EXCLUDED.review_status,
                        vector_status = EXCLUDED.vector_status,
                        graph_status = EXCLUDED.graph_status,
                        extraction_status = EXCLUDED.extraction_status,
                        original_path = EXCLUDED.original_path,
                        modified_at = EXCLUDED.modified_at,
                        indexed_at = EXCLUDED.indexed_at,
                        provenance = EXCLUDED.provenance,
                        updated_at = now();
                    """,
                    payloads,
                )
                upserted += len(batch)
                cur.execute(
                    """
                    INSERT INTO platform.vault_audit_event (asset_id, event_type, actor, details)
                    VALUES (NULL, 'vault_sync_batch', 'system', %s::jsonb);
                    """,
                    (json.dumps({"batch_size": len(batch), "offset": i}),),
                )
            cur.execute(
                """
                INSERT INTO platform.review_task (asset_id, task_type, status, assignment_confidence, sensitivity_level)
                SELECT v.asset_id, 'classification_review', 'open', v.assignment_confidence, v.sensitivity_level
                FROM platform.raw_asset_vault v
                WHERE v.assignment_confidence < 0.86
                  AND NOT EXISTS (
                    SELECT 1 FROM platform.review_task rt
                    WHERE rt.asset_id = v.asset_id AND rt.status = 'open'
                  );
                """
            )
            review_created = cur.rowcount
            cur.execute(
                """
                UPDATE platform.storage_root SET configured = %s, updated_at = now()
                WHERE storage_root_id = 'local_database_mirror';
                """,
                (DATABASE_ROOT.is_dir(),),
            )
            from app_skeleton.storage.env import datacloud_webdav_base_url

            datacloud_url = datacloud_webdav_base_url()
            cur.execute(
                """
                UPDATE platform.storage_root SET configured = %s, updated_at = now()
                WHERE storage_root_id = 'datacloud_webdav';
                """,
                (bool(datacloud_url),),
            )
        conn.commit()

    return {
        "status": "ok",
        "upserted": upserted,
        "inventory_rows": len(rows),
        "review_tasks_created": review_created,
    }


def vault_manifest_page(*, offset: int = 0, limit: int = 100) -> dict[str, Any]:
    """Paginated manifest for workers (LUMI-W110)."""
    offset = max(0, offset)
    limit = max(1, min(limit, 500))
    with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM platform.raw_asset_vault;")
            total = cur.fetchone()[0]
            cur.execute(
                """
                SELECT asset_id, logical_path, filename, storage_provider, asset_type,
                       assignment_confidence, review_status, vector_status, page_domain_id
                FROM platform.raw_asset_vault
                ORDER BY logical_path
                OFFSET %s LIMIT %s;
                """,
                (offset, limit),
            )
            items = [
                {
                    "asset_id": r[0],
                    "logical_path": r[1],
                    "filename": r[2],
                    "storage_provider": r[3],
                    "asset_type": r[4],
                    "assignment_confidence": float(r[5]) if r[5] is not None else 0,
                    "review_status": r[6],
                    "vector_status": r[7],
                    "page_domain_id": r[8],
                }
                for r in cur.fetchall()
            ]
    return {"total": total, "offset": offset, "limit": limit, "items": items}


def rebuild_inventory() -> dict[str, Any]:
    script = SCRIPTS_DIR / "digitalization" / "build_raw_asset_inventory.py"
    if not script.is_file():
        raise FileNotFoundError(f"Inventory script not found: {script}")
    proc = subprocess.run(
        [sys.executable, str(script), "--database-root", str(DATABASE_ROOT)],
        capture_output=True,
        text=True,
        cwd=str(BLUEPRINT_ROOT),
        timeout=600,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "inventory build failed")

    reconcile_stats: dict[str, Any] | None = None
    reconcile_script = SCRIPTS_DIR / "digitalization" / "reconcile_inventory_status.py"
    if reconcile_script.is_file():
        rec = subprocess.run(
            [sys.executable, str(reconcile_script)],
            capture_output=True,
            text=True,
            cwd=str(BLUEPRINT_ROOT),
            timeout=300,
            check=False,
        )
        if rec.returncode == 0:
            try:
                reconcile_stats = json.loads(rec.stdout.strip() or "{}")
            except json.JSONDecodeError:
                reconcile_stats = {"status": "ok", "stdout": rec.stdout.strip()[:500]}
        else:
            LOGGER.warning(
                "Inventory reconcile after rebuild failed: %s",
                rec.stderr.strip() or rec.stdout.strip(),
            )

    try:
        from app_skeleton.api.document_library_service import invalidate_cache

        invalidate_cache()
    except Exception as exc:
        LOGGER.debug("Could not invalidate document library cache: %s", exc)

    return {"status": "ok", "summary": load_summary(), "reconcile": reconcile_stats}
