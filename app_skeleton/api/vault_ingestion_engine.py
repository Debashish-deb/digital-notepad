"""Raw Knowledge Vault ingestion: resumable scan, per-project ingest, failed retry, reports."""
from __future__ import annotations

import hashlib
import json
import logging
import mimetypes
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import psycopg

from app_skeleton.api import document_extraction as de
from app_skeleton.api.page_registry import resolve_page_ids
from app_skeleton.api.paths import BLUEPRINT_ROOT, DATABASE_ROOT, PROJECTS_ROOT
from app_skeleton.api.qdrant_collections import VAULT_CHUNKS as VAULT_QDRANT_COLLECTION
from app_skeleton.api.raw_vault_store import ensure_vault_schema

LOGGER = logging.getLogger(__name__)


def _scrub_null_chars(value: Any) -> Any:
    """Postgres jsonb rejects U+0000 in string values."""
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, dict):
        return {k: _scrub_null_chars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub_null_chars(v) for v in value]
    return value


def _jsonb_dumps(payload: Any) -> str:
    return json.dumps(_scrub_null_chars(payload), ensure_ascii=False)


from app_skeleton.api.data_layout import ingestion_report_write_dir, iter_ingestion_report_files

INGESTION_REPORTS_DIR = ingestion_report_write_dir()
STORAGE_PROVIDER = "local_database_mirror"
SKIP_PARTS = de.SKIP_PARTS

VECTORIZATION_ENABLED = os.environ.get("VECTORIZATION_ENABLED", "false").strip().lower() in {
    "1", "true", "yes", "on",
}
def _db_conn() -> str:
    from app_skeleton.api.supabase_config import postgres_conn

    return postgres_conn()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_asset_id(relative_path: str, size_bytes: int) -> str:
    digest = hashlib.sha1(f"local_mirror:{relative_path}:{size_bytes}".encode("utf-8")).hexdigest()
    return f"asset_{digest[:16]}"


def _guess_mime(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    return mime or "application/octet-stream"


def _scan_root_for_project(project_id: str) -> Path:
    """Resolve project folder under DATABASE_ROOT/projects or PROJECTS_ROOT."""
    for base in (DATABASE_ROOT / "projects", PROJECTS_ROOT):
        candidate = base / project_id
        if candidate.is_dir():
            return candidate.resolve()
    raise FileNotFoundError(f"Project folder not found: {project_id}")


def iter_scan_files(
    scan_root: Path,
    *,
    resume_after: str | None = None,
    all_extensions: bool = False,
) -> Iterator[tuple[Path, str]]:
    """Yield (absolute_path, logical_path) relative to DATABASE_ROOT when possible."""
    scan_root = scan_root.resolve()
    db_root = DATABASE_ROOT.resolve()
    try:
        rel_prefix = str(scan_root.relative_to(db_root)).replace("\\", "/")
        if rel_prefix == ".":
            rel_prefix = ""
    except ValueError:
        rel_prefix = str(scan_root.name)

    resume_after = (resume_after or "").strip()
    passed_resume = not resume_after

    for path in sorted(scan_root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        try:
            rel_to_scan = str(path.relative_to(scan_root)).replace("\\", "/")
        except ValueError:
            continue
        logical = f"{rel_prefix}/{rel_to_scan}".strip("/") if rel_prefix else rel_to_scan

        if not passed_resume:
            if logical == resume_after:
                passed_resume = True
            continue

        ext = path.suffix.lower()
        if not all_extensions and ext not in de.SCANNABLE_EXTENSIONS:
            if not de.is_vault_large_binary(path):
                continue
        yield path, logical


def _load_checkpoint(cur, checkpoint_id: str) -> dict[str, Any] | None:
    cur.execute(
        """
        SELECT checkpoint_id, scan_root, project_hint, last_logical_path,
               files_processed, status, manifest_json, job_id
        FROM platform.vault_scan_checkpoint
        WHERE checkpoint_id = %s;
        """,
        (checkpoint_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    cols = [d[0] for d in cur.description]
    out = dict(zip(cols, row))
    if isinstance(out.get("manifest_json"), str):
        out["manifest_json"] = json.loads(out["manifest_json"])
    return out


def _save_checkpoint(
    cur,
    *,
    checkpoint_id: str,
    scan_root: str,
    project_hint: str | None,
    last_logical_path: str | None,
    files_processed: int,
    status: str,
    manifest: dict[str, Any],
    job_id: str | None,
) -> None:
    cur.execute(
        """
        INSERT INTO platform.vault_scan_checkpoint (
            checkpoint_id, scan_root, project_hint, last_logical_path,
            files_processed, status, manifest_json, job_id, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, now())
        ON CONFLICT (checkpoint_id) DO UPDATE SET
            last_logical_path = EXCLUDED.last_logical_path,
            files_processed = EXCLUDED.files_processed,
            status = EXCLUDED.status,
            manifest_json = EXCLUDED.manifest_json,
            job_id = EXCLUDED.job_id,
            updated_at = now();
        """,
        (
            checkpoint_id,
            scan_root,
            project_hint,
            last_logical_path,
            files_processed,
            status,
            _jsonb_dumps(manifest),
            job_id,
        ),
    )


def _vector_status_for_result(result: de.ExtractionResult, extraction_status: str) -> str:
    if not VECTORIZATION_ENABLED:
        return "disabled"
    if extraction_status in {"failed", "skipped", "not_started"}:
        return "not_evaluated"
    if extraction_status == "metadata_only":
        return "metadata_summary_only"
    if result.text and result.chunks:
        return "pending"
    if result.text:
        return "pending"
    return "not_evaluated"


def _review_status_uncategorized(page_domain_id: str | None, domain: str | None) -> str:
    if page_domain_id:
        return "raw"
    if not domain or domain in {"unknown", ""}:
        return "uncategorized"
    return "raw"


def upsert_vault_from_extraction(
    cur,
    *,
    logical_path: str,
    abs_path: Path,
    project_hint: str,
    result: de.ExtractionResult,
    counts: dict[str, int],
) -> str:
    stat = de._safe_stat(abs_path)
    size_bytes = stat["size_bytes"]
    asset_id = stable_asset_id(logical_path, size_bytes)
    extraction_status = de.vault_extraction_status(result)
    if result.errors and extraction_status != "failed":
        extraction_status = "failed"

    metadata_json: dict[str, Any] = {
        "ingestion_engine": "vault_ingestion_engine",
        "ingested_at": _utc_now(),
        "extractor": result.extractor,
        "document_kind": result.document_kind,
        "char_count": result.char_count,
        "word_count": result.word_count,
        "warnings": result.warnings[:20],
        **result.metadata,
    }
    if result.errors:
        metadata_json["error"] = "; ".join(result.errors)[:2000]
    if result.excerpt:
        metadata_json["excerpt"] = result.excerpt[:1200]

    domain = None
    section_hint = None
    assignment_confidence = 0.0
    if project_hint:
        domain = "project"
        assignment_confidence = 0.72
    page_domain_id, page_section_id = resolve_page_ids(
        domain=domain,
        section_hint=section_hint,
        logical_path=logical_path,
    )
    if not page_domain_id:
        counts["uncategorized"] = counts.get("uncategorized", 0) + 1

    vector_status = _vector_status_for_result(result, extraction_status)
    if extraction_status == "metadata_only" and metadata_json.get("vault_policy") == "large_binary_metadata_only":
        counts["skipped_large"] = counts.get("skipped_large", 0) + 1

    review_status = _review_status_uncategorized(page_domain_id, domain)

    cur.execute(
        """
        SELECT asset_id, checksum_sha256, extraction_status
        FROM platform.raw_asset_vault WHERE asset_id = %s;
        """,
        (asset_id,),
    )
    existing = cur.fetchone()
    is_new = existing is None

    cur.execute(
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
            %(original_path)s, %(modified_at)s::timestamptz, now(), %(provenance)s::jsonb,
            %(metadata_json)s::jsonb, now()
        )
        ON CONFLICT (asset_id) DO UPDATE SET
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
            page_domain_id = COALESCE(EXCLUDED.page_domain_id, platform.raw_asset_vault.page_domain_id),
            page_section_id = COALESCE(EXCLUDED.page_section_id, platform.raw_asset_vault.page_section_id),
            review_status = EXCLUDED.review_status,
            vector_status = EXCLUDED.vector_status,
            extraction_status = EXCLUDED.extraction_status,
            modified_at = EXCLUDED.modified_at,
            metadata_json = EXCLUDED.metadata_json,
            provenance = EXCLUDED.provenance,
            updated_at = now();
        """,
        {
            "asset_id": asset_id,
            "storage_provider": STORAGE_PROVIDER,
            "logical_path": logical_path,
            "filename": abs_path.name,
            "extension": abs_path.suffix.lower() or "",
            "size_bytes": size_bytes,
            "checksum_sha256": result.sha256 or "",
            "mime_type": result.mime_type or _guess_mime(abs_path),
            "asset_type": result.document_kind,
            "domain": domain,
            "project_hint": project_hint or "",
            "section_hint": section_hint or "",
            "page_domain_id": page_domain_id,
            "page_section_id": page_section_id,
            "sensitivity_level": "unknown",
            "assignment_confidence": assignment_confidence,
            "sensitivity_confidence": 0.3,
            "review_status": review_status,
            "vector_status": vector_status,
            "graph_status": "not_asserted",
            "extraction_status": extraction_status,
            "original_path": str(abs_path),
            "modified_at": result.modified_at,
            "provenance": _jsonb_dumps({"source": "vault_ingestion_engine", "logical_path": logical_path}),
            "metadata_json": _jsonb_dumps(metadata_json),
        },
    )

    if is_new:
        counts["new"] = counts.get("new", 0) + 1
    else:
        counts["updated"] = counts.get("updated", 0) + 1
    if extraction_status == "failed":
        counts["failed"] = counts.get("failed", 0) + 1

    return asset_id


def _maybe_vectorize(cur, asset_id: str, result: de.ExtractionResult) -> None:
    if not VECTORIZATION_ENABLED or not result.chunks:
        return
    try:
        from app_skeleton.api.platform_flags import vault_use_vector_indexer_enabled
        from app_skeleton.api.qdrant_vectors import get_qdrant_client, ping_qdrant
    except ImportError:
        cur.execute(
            "UPDATE platform.raw_asset_vault SET vector_status = 'disabled' WHERE asset_id = %s;",
            (asset_id,),
        )
        return

    if not ping_qdrant():
        cur.execute(
            "UPDATE platform.raw_asset_vault SET vector_status = 'disabled' WHERE asset_id = %s;",
            (asset_id,),
        )
        return

    qc = get_qdrant_client()
    try:
        if vault_use_vector_indexer_enabled():
            from app_skeleton.api.vector_indexer import upsert_vault_asset_chunks

            n = upsert_vault_asset_chunks(
                qc,
                asset_id,
                result.chunks,
                source_path=result.path,
            )
        else:
            from app_skeleton.api.llm_client import LLMClient
            from app_skeleton.api.qdrant_vectors import upsert_text_points
            from qdrant_client.http import models

            llm = LLMClient()
            points = []
            for chunk in result.chunks[:50]:
                text = chunk.get("text") or ""
                if not text.strip():
                    continue
                vec = llm.embed(text)
                point_id = hashlib.md5(f"{asset_id}:{chunk.get('chunk_id', '')}".encode()).hexdigest()
                points.append(
                    models.PointStruct(
                        id=point_id,
                        vector=vec,
                        payload={
                            "asset_id": asset_id,
                            "source_file": result.path,
                            "chunk_index": chunk.get("chunk_index"),
                            "text_preview": text[:2000],
                            "embedding_model": "llm_client_hashed_embed",
                        },
                    )
                )
            n = upsert_text_points(qc, points, collection=VAULT_QDRANT_COLLECTION) if points else 0

        if n:
            cur.execute(
                "UPDATE platform.raw_asset_vault SET vector_status = 'vectorized' WHERE asset_id = %s;",
                (asset_id,),
            )
        else:
            cur.execute(
                "UPDATE platform.raw_asset_vault SET vector_status = 'failed' WHERE asset_id = %s;",
                (asset_id,),
            )
    except Exception as exc:
        LOGGER.warning("Qdrant upsert failed for %s: %s", asset_id, exc)
        cur.execute(
            "UPDATE platform.raw_asset_vault SET vector_status = 'failed' WHERE asset_id = %s;",
            (asset_id,),
        )


def _write_report(run_id: str, payload: dict[str, Any]) -> Path:
    report_dir = ingestion_report_write_dir(failed="fail" in run_id.lower() or "error" in run_id.lower())
    path = report_dir / f"ingestion_{run_id}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def run_ingest_scan(
    *,
    scan_root: Path | None = None,
    project_hint: str | None = None,
    resume: bool = False,
    job_id: str | None = None,
    max_files: int | None = None,
) -> dict[str, Any]:
    """Full or project-scoped resumable vault ingest."""
    ensure_vault_schema()
    scan_root = (scan_root or DATABASE_ROOT).resolve()
    if not scan_root.is_dir():
        raise FileNotFoundError(f"Scan root not found: {scan_root}")

    checkpoint_id = f"project:{project_hint}" if project_hint else "full_scan"
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8]
    counts: dict[str, int] = {
        "scanned": 0,
        "new": 0,
        "updated": 0,
        "failed": 0,
        "skipped_large": 0,
        "uncategorized": 0,
    }
    resume_after: str | None = None
    files_processed = 0

    with psycopg.connect(_db_conn(), connect_timeout=60) as conn:
        with conn.cursor() as cur:
            if resume:
                cp = _load_checkpoint(cur, checkpoint_id)
                if cp and cp.get("status") in ("running", "paused"):
                    resume_after = cp.get("last_logical_path")
                    files_processed = int(cp.get("files_processed") or 0)
                    manifest = cp.get("manifest_json") or {}
                    if isinstance(manifest, dict):
                        for k, v in manifest.get("counts", {}).items():
                            counts[k] = counts.get(k, 0) + int(v)

            _save_checkpoint(
                cur,
                checkpoint_id=checkpoint_id,
                scan_root=str(scan_root),
                project_hint=project_hint,
                last_logical_path=resume_after,
                files_processed=files_processed,
                status="running",
                manifest={"run_id": run_id, "counts": counts},
                job_id=job_id,
            )
            conn.commit()

            last_logical: str | None = resume_after
            scan_finished = False
            for abs_path, logical in iter_scan_files(scan_root, resume_after=resume_after):
                if max_files is not None and counts["scanned"] >= max_files:
                    break
                counts["scanned"] += 1
                try:
                    result = de.extract_for_vault(abs_path, scan_root)
                except Exception as exc:
                    result = de.ExtractionResult(
                        path=logical,
                        name=abs_path.name,
                        extension=abs_path.suffix.lower(),
                        document_kind="other",
                        mime_type=_guess_mime(abs_path),
                        size_bytes=de._safe_stat(abs_path)["size_bytes"],
                        modified_at=None,
                        status="failed",
                        errors=[str(exc)],
                    )
                asset_id = upsert_vault_from_extraction(
                    cur,
                    logical_path=logical,
                    abs_path=abs_path,
                    project_hint=project_hint or "",
                    result=result,
                    counts=counts,
                )
                if VECTORIZATION_ENABLED and result.chunks:
                    _maybe_vectorize(cur, asset_id, result)

                files_processed += 1
                last_logical = logical
                if files_processed % 25 == 0:
                    _save_checkpoint(
                        cur,
                        checkpoint_id=checkpoint_id,
                        scan_root=str(scan_root),
                        project_hint=project_hint,
                        last_logical_path=last_logical,
                        files_processed=files_processed,
                        status="running",
                        manifest={"run_id": run_id, "counts": counts},
                        job_id=job_id,
                    )
                    conn.commit()
            else:
                scan_finished = True

            _save_checkpoint(
                cur,
                checkpoint_id=checkpoint_id,
                scan_root=str(scan_root),
                project_hint=project_hint,
                last_logical_path=last_logical,
                files_processed=files_processed,
                status="completed" if scan_finished else "paused",
                manifest={"run_id": run_id, "counts": counts},
                job_id=job_id,
            )
            cur.execute(
                """
                INSERT INTO platform.vault_audit_event (asset_id, event_type, actor, details)
                VALUES (NULL, 'vault_ingest_scan', 'system', %s::jsonb);
                """,
                (json.dumps({"checkpoint_id": checkpoint_id, "counts": counts, "run_id": run_id}),),
            )
            conn.commit()

    report = {
        "run_id": run_id,
        "checkpoint_id": checkpoint_id,
        "scan_root": str(scan_root),
        "project_hint": project_hint,
        "vectorization_enabled": VECTORIZATION_ENABLED,
        "finished_at": _utc_now(),
        "counts": counts,
    }
    report_path = _write_report(run_id, report)
    report["report_path"] = str(report_path)
    return report


def ingest_project(project_id: str, *, resume: bool = False, job_id: str | None = None) -> dict[str, Any]:
    folder = _scan_root_for_project(project_id)
    return run_ingest_scan(
        scan_root=folder,
        project_hint=project_id,
        resume=resume,
        job_id=job_id,
    )


def retry_failed_extractions(
    *,
    project_hint: str | None = None,
    limit: int = 500,
    job_id: str | None = None,
) -> dict[str, Any]:
    """Re-process vault rows with extraction_status=failed."""
    ensure_vault_schema()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_retry_" + uuid.uuid4().hex[:8]
    counts = {"retried": 0, "new": 0, "updated": 0, "failed": 0, "recovered": 0}

    with psycopg.connect(_db_conn(), connect_timeout=60) as conn:
        with conn.cursor() as cur:
            clauses = ["extraction_status = 'failed'"]
            params: list[Any] = []
            if project_hint:
                clauses.append("lower(project_hint) = lower(%s)")
                params.append(project_hint)
            params.append(limit)
            cur.execute(
                f"""
                SELECT asset_id, logical_path, original_path, project_hint
                FROM platform.raw_asset_vault
                WHERE {' AND '.join(clauses)}
                ORDER BY updated_at DESC
                LIMIT %s;
                """,
                params,
            )
            rows = cur.fetchall()

            for asset_id, logical_path, original_path, phint in rows:
                counts["retried"] += 1
                abs_path = Path(original_path) if original_path else DATABASE_ROOT / logical_path
                if not abs_path.is_file():
                    counts["failed"] += 1
                    continue
                scan_root = abs_path.parent
                try:
                    result = de.extract_for_vault(abs_path, scan_root)
                except Exception as exc:
                    result = de.ExtractionResult(
                        path=logical_path,
                        name=abs_path.name,
                        extension=abs_path.suffix.lower(),
                        document_kind="other",
                        mime_type=_guess_mime(abs_path),
                        size_bytes=de._safe_stat(abs_path)["size_bytes"],
                        modified_at=None,
                        status="failed",
                        errors=[str(exc)],
                    )
                upsert_vault_from_extraction(
                    cur,
                    logical_path=logical_path,
                    abs_path=abs_path,
                    project_hint=phint or project_hint or "",
                    result=result,
                    counts=counts,
                )
                if de.vault_extraction_status(result) != "failed":
                    counts["recovered"] += 1

            conn.commit()

    report = {
        "run_id": run_id,
        "mode": "retry_failed",
        "project_hint": project_hint,
        "counts": counts,
        "finished_at": _utc_now(),
    }
    report_path = _write_report(run_id, report)
    report["report_path"] = str(report_path)
    return report
