"""Sync document metadata and truncated text from local Postgres to hosted Supabase.

Never uploads image/large binaries to Supabase Storage — Postgres rows only.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import psycopg

from app_skeleton.api.document_extraction import DOCUMENT_EXTENSIONS, IMAGE_EXTENSIONS, TEXT_EXTENSIONS
from app_skeleton.api.paths import BLUEPRINT_ROOT
from app_skeleton.api.supabase_config import postgres_conn

LOGGER = logging.getLogger(__name__)

INGESTION_REPORTS_DIR = BLUEPRINT_ROOT / "app_skeleton" / "data" / "ingestion_reports"
SYNC_REPORT_PATH = INGESTION_REPORTS_DIR / "sync_run_report.json"

DOCUMENT_ASSET_TYPES = frozenset({
    "document",
    "plain_text",
    "spreadsheet",
    "protocol",
    "publication",
    "meeting_note",
    "SOP",
    "html",
    "pdf",
    "log",
    "script",
    "notebook",
    "other",
})

LOCAL_STORAGE_PROVIDERS = frozenset({"local_dev", "local_database_mirror"})


def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        return int(raw)
    except ValueError:
        return default


def supabase_sync_enabled() -> bool:
    return _env_bool("SUPABASE_SYNC_ENABLED", "false")


def supabase_hosted_password_set() -> bool:
    return bool(os.getenv("SUPABASE_DB_PASSWORD", "").strip())


def local_postgres_conn() -> str:
    """Always the dev/local vault source (never the Supabase pooler override)."""
    explicit = os.getenv("POSTGRES_CONN", "").strip()
    if explicit:
        return explicit
    return "postgresql://farkki:farkki_dev_password@localhost:5432/farkki_ai"


def hosted_postgres_conn() -> str | None:
    if not supabase_hosted_password_set():
        return None
    return postgres_conn()


def max_text_bytes() -> int:
    return max(1024, _env_int("SUPABASE_MAX_TEXT_BYTES", 50_000))


def sync_batch_size() -> int:
    return max(1, min(500, _env_int("SUPABASE_SYNC_BATCH_SIZE", 100)))


def skip_image_sync() -> bool:
    return _env_bool("SUPABASE_SKIP_IMAGE_SYNC", "true")


def max_db_bytes_before_skip() -> int:
    """Free tier ~500MB — skip sync when hosted DB estimate exceeds this."""
    mb = _env_int("SUPABASE_MAX_DB_MB", 450)
    return max(50, mb) * 1024 * 1024


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def truncate_utf8(text: str, max_bytes: int) -> str:
    if not text:
        return ""
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    cut = encoded[:max_bytes]
    while cut and (cut[-1] & 0xC0) == 0x80:
        cut = cut[:-1]
    return cut.decode("utf-8", errors="ignore") + "…"


def sanitize_metadata_json(meta: dict[str, Any] | None, *, max_bytes: int) -> dict[str, Any]:
    if not meta:
        return {}
    out: dict[str, Any] = {}
    for key, value in meta.items():
        if isinstance(value, str) and key in {
            "extracted_text",
            "text_preview",
            "raw_text",
            "cleaned_text",
            "full_text",
            "preview_text",
        }:
            out[key] = truncate_utf8(value, max_bytes)
        elif isinstance(value, str) and len(value.encode("utf-8")) > max_bytes:
            out[key] = truncate_utf8(value, max_bytes)
        else:
            out[key] = value
    out["supabase_sync"] = {
        "truncated": True,
        "max_text_bytes": max_bytes,
        "synced_at": _utc_now(),
    }
    return out


def _extension(row: dict[str, Any]) -> str:
    ext = (row.get("extension") or "").strip().lower()
    if ext and not ext.startswith("."):
        ext = f".{ext}"
    return ext


def is_document_sync_eligible(row: dict[str, Any]) -> bool:
    """True when row should sync as document metadata (not image/large-binary blob)."""
    ext = _extension(row)
    asset_type = (row.get("asset_type") or "").strip().lower()
    extraction_status = (row.get("extraction_status") or "").strip().lower()
    storage_provider = (row.get("storage_provider") or "").strip().lower()
    meta = row.get("metadata_json") or {}
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except json.JSONDecodeError:
            meta = {}

    if storage_provider == "supabase_storage":
        return False

    if skip_image_sync():
        if ext in IMAGE_EXTENSIONS or asset_type == "image":
            return False

    if extraction_status == "metadata_only":
        if meta.get("vault_policy") == "large_binary_metadata_only":
            return False
        if ext in IMAGE_EXTENSIONS:
            return False
        has_text = bool(
            (row.get("text_preview") or "").strip()
            or (row.get("extracted_raw") or "").strip()
            or (row.get("extracted_clean") or "").strip()
            or meta.get("extracted_text")
            or meta.get("text_preview")
        )
        return has_text

    if asset_type in DOCUMENT_ASSET_TYPES and asset_type != "other":
        if asset_type == "image":
            return False
        return True

    if ext in DOCUMENT_EXTENSIONS or ext in TEXT_EXTENSIONS:
        return True

    if (row.get("extracted_raw") or row.get("extracted_clean") or "").strip():
        return True

    if meta.get("extracted_text") or meta.get("text_preview"):
        return True

    return False


def _estimate_hosted_db_bytes(conn_str: str) -> int | None:
    try:
        with psycopg.connect(conn_str, connect_timeout=10) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_database_size(current_database());")
                row = cur.fetchone()
                return int(row[0]) if row else None
    except Exception as exc:
        LOGGER.warning("Could not estimate hosted DB size: %s", exc)
        return None


def _fetch_local_candidates(
    *,
    limit: int | None,
    since: str | None,
) -> list[dict[str, Any]]:
    clauses = ["1=1"]
    params: list[Any] = []
    if since:
        clauses.append("v.updated_at >= %s::timestamptz")
        params.append(since)

    limit_sql = ""
    if limit is not None and limit > 0:
        limit_sql = " LIMIT %s"
        params.append(limit)

    sql = f"""
        SELECT
            v.asset_id,
            v.storage_provider,
            v.logical_path,
            v.filename,
            v.extension,
            v.size_bytes,
            v.checksum_sha256,
            v.mime_type,
            v.asset_type,
            v.domain,
            v.project_hint,
            v.section_hint,
            v.page_domain_id,
            v.page_section_id,
            v.sensitivity_level,
            v.assignment_confidence,
            v.sensitivity_confidence,
            v.review_status,
            v.vector_status,
            v.graph_status,
            v.extraction_status,
            v.modified_at,
            v.indexed_at,
            v.provenance,
            COALESCE(v.metadata_json, '{{}}'::jsonb) AS metadata_json,
            v.updated_at,
            et.raw_text AS extracted_raw,
            et.cleaned_text AS extracted_clean,
            ka.storage_root_id,
            ka.absolute_path,
            ka.relative_path,
            ka.detected_type,
            ka.project_candidate_id,
            ka.ingestion_status,
            ka.review_status AS ka_review_status,
            ka.extraction_status AS ka_extraction_status,
            ka.metadata_json AS ka_metadata_json
        FROM platform.raw_asset_vault v
        LEFT JOIN LATERAL (
            SELECT raw_text, cleaned_text
            FROM platform.extracted_texts t
            WHERE t.asset_id = v.asset_id
            ORDER BY t.version DESC, t.created_at DESC
            LIMIT 1
        ) et ON true
        LEFT JOIN platform.knowledge_assets ka ON ka.asset_id = v.asset_id
        WHERE {' AND '.join(clauses)}
        ORDER BY v.updated_at ASC, v.asset_id ASC
        {limit_sql};
    """
    local = local_postgres_conn()
    with psycopg.connect(local, connect_timeout=30) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    return [r for r in rows if is_document_sync_eligible(r)]


def _vault_payload(row: dict[str, Any], *, max_bytes: int) -> dict[str, Any]:
    meta = row.get("metadata_json")
    if isinstance(meta, str):
        meta = json.loads(meta) if meta else {}
    elif meta is None:
        meta = {}
    elif not isinstance(meta, dict):
        meta = dict(meta)

    preview = (row.get("extracted_clean") or row.get("extracted_raw") or "").strip()
    if preview:
        meta = {**meta, "text_preview": truncate_utf8(preview, max_bytes)}

    provider = (row.get("storage_provider") or "local_database_mirror").strip()
    if provider not in LOCAL_STORAGE_PROVIDERS:
        provider = "local_database_mirror"

    return {
        "asset_id": row["asset_id"],
        "storage_provider": provider,
        "logical_path": row["logical_path"],
        "filename": row["filename"],
        "extension": row.get("extension") or "",
        "size_bytes": row.get("size_bytes") or 0,
        "checksum_sha256": row.get("checksum_sha256") or "",
        "mime_type": row.get("mime_type") or "application/octet-stream",
        "asset_type": row.get("asset_type") or "document",
        "domain": row.get("domain"),
        "project_hint": row.get("project_hint") or "",
        "section_hint": row.get("section_hint") or "",
        "page_domain_id": row.get("page_domain_id"),
        "page_section_id": row.get("page_section_id"),
        "sensitivity_level": row.get("sensitivity_level") or "unknown",
        "assignment_confidence": row.get("assignment_confidence") or 0,
        "sensitivity_confidence": row.get("sensitivity_confidence") or 0,
        "review_status": row.get("review_status") or "raw",
        "vector_status": row.get("vector_status") or "not_evaluated",
        "graph_status": row.get("graph_status") or "not_asserted",
        "extraction_status": row.get("extraction_status") or "not_started",
        "modified_at": row.get("modified_at"),
        "indexed_at": row.get("indexed_at"),
        "provenance": json.dumps({
            **(
                row["provenance"]
                if isinstance(row.get("provenance"), dict)
                else (
                    json.loads(row["provenance"])
                    if isinstance(row.get("provenance"), str) and row["provenance"]
                    else {}
                )
            ),
            "supabase_document_sync": True,
            "source_conn": "local_postgres",
        }),
        "metadata_json": json.dumps(sanitize_metadata_json(meta, max_bytes=max_bytes)),
        "original_path": None,
    }


def _fetch_valid_project_candidate_ids(conn_str: str) -> set[str]:
    """Hosted project_candidates for FK-safe knowledge_assets sync."""
    try:
        with psycopg.connect(conn_str, connect_timeout=15) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT project_candidate_id FROM platform.project_candidates;"
                )
                return {str(r[0]) for r in cur.fetchall() if r and r[0]}
    except Exception as exc:
        LOGGER.warning("Could not load hosted project_candidates: %s", exc)
        return set()


def _knowledge_payload(
    row: dict[str, Any],
    *,
    max_bytes: int,
    valid_project_ids: set[str] | None = None,
) -> dict[str, Any] | None:
    if not row.get("absolute_path"):
        return None
    ka_meta = row.get("ka_metadata_json")
    if isinstance(ka_meta, str):
        ka_meta = json.loads(ka_meta) if ka_meta else {}
    elif ka_meta is None:
        ka_meta = {}
    elif not isinstance(ka_meta, dict):
        ka_meta = dict(ka_meta)

    pcid = row.get("project_candidate_id")
    if pcid and valid_project_ids is not None and str(pcid) not in valid_project_ids:
        pcid = None

    return {
        "asset_id": row["asset_id"],
        "storage_root_id": row.get("storage_root_id") or "lab_storage_root",
        "absolute_path": row["absolute_path"],
        "relative_path": row.get("relative_path") or row["logical_path"],
        "filename": row["filename"],
        "extension": row.get("extension") or "",
        "file_size": row.get("size_bytes") or 0,
        "modified_at": row.get("modified_at"),
        "detected_type": row.get("detected_type") or row.get("asset_type") or "document",
        "project_candidate_id": pcid,
        "ingestion_status": row.get("ingestion_status") or "registered",
        "extraction_status": row.get("ka_extraction_status") or row.get("extraction_status") or "not_started",
        "review_status": row.get("ka_review_status") or row.get("review_status") or "needs_review",
        "metadata_json": json.dumps(sanitize_metadata_json(ka_meta, max_bytes=max_bytes)),
    }


def _text_payload(row: dict[str, Any], *, max_bytes: int) -> dict[str, Any] | None:
    raw = (row.get("extracted_raw") or "").strip()
    cleaned = (row.get("extracted_clean") or "").strip()
    if not raw and not cleaned:
        return None
    raw_t = truncate_utf8(raw, max_bytes) if raw else None
    clean_t = truncate_utf8(cleaned or raw, max_bytes)
    return {
        "asset_id": row["asset_id"],
        "raw_text": raw_t,
        "cleaned_text": clean_t,
        "extraction_method": "supabase_sync_truncated",
        "char_count": len(clean_t or ""),
        "word_count": len((clean_t or "").split()),
    }


def _upsert_batch(
    cur,
    rows: list[dict[str, Any]],
    *,
    max_bytes: int,
    valid_project_ids: set[str] | None = None,
) -> dict[str, int]:
    counts = {"vault": 0, "knowledge": 0, "texts": 0}
    vault_rows = [_vault_payload(r, max_bytes=max_bytes) for r in rows]
    if vault_rows:
        cur.executemany(
            """
            INSERT INTO platform.raw_asset_vault (
                asset_id, storage_provider, logical_path, filename, extension,
                size_bytes, checksum_sha256, mime_type, asset_type, domain, project_hint, section_hint,
                page_domain_id, page_section_id,
                sensitivity_level, assignment_confidence, sensitivity_confidence,
                review_status, vector_status, graph_status, extraction_status,
                original_path, modified_at, indexed_at, provenance, metadata_json, updated_at
            ) VALUES (
                %(asset_id)s, %(storage_provider)s, %(logical_path)s, %(filename)s, %(extension)s,
                %(size_bytes)s, %(checksum_sha256)s, %(mime_type)s, %(asset_type)s, %(domain)s,
                %(project_hint)s, %(section_hint)s, %(page_domain_id)s, %(page_section_id)s,
                %(sensitivity_level)s, %(assignment_confidence)s, %(sensitivity_confidence)s,
                %(review_status)s, %(vector_status)s, %(graph_status)s, %(extraction_status)s,
                NULL, %(modified_at)s, COALESCE(%(indexed_at)s::timestamptz, now()),
                %(provenance)s::jsonb, %(metadata_json)s::jsonb, now()
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
                modified_at = EXCLUDED.modified_at,
                metadata_json = EXCLUDED.metadata_json,
                provenance = EXCLUDED.provenance,
                updated_at = now();
            """,
            vault_rows,
        )
        counts["vault"] = len(vault_rows)

    knowledge_rows = [
        p
        for r in rows
        if (p := _knowledge_payload(r, max_bytes=max_bytes, valid_project_ids=valid_project_ids))
    ]
    if knowledge_rows:
        cur.executemany(
            """
            INSERT INTO platform.knowledge_assets (
                asset_id, storage_root_id, absolute_path, relative_path, filename, extension,
                file_size, modified_at, detected_type, project_candidate_id,
                ingestion_status, extraction_status, review_status, metadata_json, updated_at
            ) VALUES (
                %(asset_id)s, %(storage_root_id)s, %(absolute_path)s, %(relative_path)s,
                %(filename)s, %(extension)s, %(file_size)s, %(modified_at)s, %(detected_type)s,
                %(project_candidate_id)s, %(ingestion_status)s, %(extraction_status)s,
                %(review_status)s, %(metadata_json)s::jsonb, now()
            )
            ON CONFLICT (asset_id) DO UPDATE SET
                relative_path = EXCLUDED.relative_path,
                filename = EXCLUDED.filename,
                extension = EXCLUDED.extension,
                file_size = EXCLUDED.file_size,
                modified_at = EXCLUDED.modified_at,
                detected_type = EXCLUDED.detected_type,
                project_candidate_id = EXCLUDED.project_candidate_id,
                ingestion_status = EXCLUDED.ingestion_status,
                extraction_status = EXCLUDED.extraction_status,
                review_status = EXCLUDED.review_status,
                metadata_json = EXCLUDED.metadata_json,
                updated_at = now();
            """,
            knowledge_rows,
        )
        counts["knowledge"] = len(knowledge_rows)

    for row in rows:
        text_p = _text_payload(row, max_bytes=max_bytes)
        if not text_p:
            continue
        cur.execute(
            """
            SELECT text_id, version FROM platform.extracted_texts
            WHERE asset_id = %(asset_id)s
            ORDER BY version DESC, created_at DESC
            LIMIT 1;
            """,
            text_p,
        )
        existing_text = cur.fetchone()
        if existing_text:
            cur.execute(
                """
                UPDATE platform.extracted_texts SET
                    raw_text = %(raw_text)s,
                    cleaned_text = %(cleaned_text)s,
                    extraction_method = %(extraction_method)s,
                    char_count = %(char_count)s,
                    word_count = %(word_count)s
                WHERE text_id = %(text_id)s;
                """,
                {
                    **text_p,
                    "text_id": existing_text[0],
                },
            )
        else:
            cur.execute(
                """
                INSERT INTO platform.extracted_texts (
                    asset_id, raw_text, cleaned_text, extraction_method,
                    char_count, word_count, version
                ) VALUES (
                    %(asset_id)s, %(raw_text)s, %(cleaned_text)s, %(extraction_method)s,
                    %(char_count)s, %(word_count)s, 1
                );
                """,
                text_p,
            )
        counts["texts"] += 1

    return counts


def write_sync_report(report: dict[str, Any]) -> Path:
    INGESTION_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    SYNC_REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return SYNC_REPORT_PATH


def read_last_sync_report() -> dict[str, Any] | None:
    if not SYNC_REPORT_PATH.is_file():
        return None
    try:
        return json.loads(SYNC_REPORT_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def supabase_sync_status() -> dict[str, Any]:
    last = read_last_sync_report() or {}
    return {
        "enabled": supabase_sync_enabled(),
        "hosted_db_password_set": supabase_hosted_password_set(),
        "skip_image_sync": skip_image_sync(),
        "max_text_bytes": max_text_bytes(),
        "batch_size": sync_batch_size(),
        "last_run": last.get("finished_at") or last.get("started_at"),
        "last_status": last.get("status"),
        "document_rows_synced": last.get("document_rows_synced"),
        "document_rows_eligible": last.get("document_rows_eligible"),
        "dry_run": last.get("dry_run"),
    }


def sync_documents_to_supabase(
    *,
    dry_run: bool = False,
    limit: int | None = None,
    since: str | None = None,
) -> dict[str, Any]:
    """
    Copy document registry rows from local Postgres to hosted Supabase Postgres.
    Idempotent upsert by asset_id. Does not use Supabase Storage.
    """
    started = _utc_now()
    report: dict[str, Any] = {
        "started_at": started,
        "dry_run": dry_run,
        "limit": limit,
        "since": since,
        "status": "skipped",
    }

    if not supabase_sync_enabled() and not dry_run:
        report["status"] = "disabled"
        report["message"] = "Set SUPABASE_SYNC_ENABLED=true to run hosted document sync."
        report["finished_at"] = _utc_now()
        write_sync_report(report)
        return report

    if not supabase_hosted_password_set():
        report["status"] = "needs_user_decision"
        report["message"] = (
            "SUPABASE_DB_PASSWORD is not set. Add it to configs/.env, apply migrations, "
            "then enable SUPABASE_SYNC_ENABLED. Do not run a full ~4800-row sync until then."
        )
        report["finished_at"] = _utc_now()
        write_sync_report(report)
        return report

    hosted = hosted_postgres_conn()
    if not hosted:
        report["status"] = "error"
        report["message"] = "Hosted Postgres connection unavailable."
        report["finished_at"] = _utc_now()
        write_sync_report(report)
        return report

    if hosted.strip() == local_postgres_conn().strip():
        report["status"] = "error"
        report["message"] = "Local and hosted POSTGRES_CONN are identical; refusing to sync in-place."
        report["finished_at"] = _utc_now()
        write_sync_report(report)
        return report

    max_bytes = max_text_bytes()
    batch = sync_batch_size()

    try:
        candidates = _fetch_local_candidates(limit=limit, since=since)
    except Exception as exc:
        report["status"] = "error"
        report["message"] = f"Local vault read failed: {exc}"
        report["finished_at"] = _utc_now()
        write_sync_report(report)
        raise

    report["document_rows_eligible"] = len(candidates)
    report["local_conn"] = "local_postgres"

    db_bytes = _estimate_hosted_db_bytes(hosted)
    report["hosted_db_bytes_estimate"] = db_bytes
    if db_bytes is not None and db_bytes >= max_db_bytes_before_skip():
        report["status"] = "skipped_db_size"
        report["message"] = (
            f"Hosted DB size estimate {db_bytes} bytes exceeds guardrail "
            f"{max_db_bytes_before_skip()} — sync skipped."
        )
        report["finished_at"] = _utc_now()
        write_sync_report(report)
        return report

    if dry_run:
        report["status"] = "dry_run"
        report["document_rows_synced"] = 0
        report["would_sync"] = len(candidates)
        report["finished_at"] = _utc_now()
        write_sync_report(report)
        return report

    valid_project_ids = _fetch_valid_project_candidate_ids(hosted)
    report["hosted_project_candidates"] = len(valid_project_ids)

    totals = {"vault": 0, "knowledge": 0, "texts": 0, "batches": 0}
    try:
        with psycopg.connect(hosted, connect_timeout=60) as conn:
            with conn.cursor() as cur:
                for i in range(0, len(candidates), batch):
                    chunk = candidates[i : i + batch]
                    counts = _upsert_batch(
                        cur,
                        chunk,
                        max_bytes=max_bytes,
                        valid_project_ids=valid_project_ids,
                    )
                    totals["vault"] += counts["vault"]
                    totals["knowledge"] += counts["knowledge"]
                    totals["texts"] += counts["texts"]
                    totals["batches"] += 1
            conn.commit()
    except Exception as exc:
        report["status"] = "error"
        report["message"] = str(exc)
        report["totals"] = totals
        report["finished_at"] = _utc_now()
        write_sync_report(report)
        raise

    report["status"] = "ok"
    report["document_rows_synced"] = totals["vault"]
    report["knowledge_rows_synced"] = totals["knowledge"]
    report["text_rows_synced"] = totals["texts"]
    report["batches"] = totals["batches"]
    report["max_text_bytes"] = max_bytes
    report["finished_at"] = _utc_now()
    write_sync_report(report)
    LOGGER.info(
        "Supabase document sync complete: %s vault rows (%s batches)",
        totals["vault"],
        totals["batches"],
    )
    return report
