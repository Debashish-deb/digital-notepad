"""Project folder digitalization: scan LAB_STORAGE_ROOT, extract, store raw knowledge layer."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import psycopg

from app_skeleton.api import document_extraction as de
from app_skeleton.api.paths import DATABASE_ROOT, lab_storage_root, projects_roots_for_scan
from app_skeleton.api.raw_vault_store import ensure_vault_schema
from app_skeleton.api.vault_ingestion_engine import (
    STORAGE_PROVIDER,
    _db_conn,
    _guess_mime,
    _jsonb_dumps,
    _utc_now,
    _write_report,
    iter_scan_files,
    stable_asset_id,
    upsert_vault_from_extraction,
)

LOGGER = logging.getLogger(__name__)

STORAGE_ROOT_ID = "lab_storage_root"
BATCH_SIZE = int(os.environ.get("INGESTION_BATCH_SIZE", "50"))
MAX_TEXT_MB = float(os.environ.get("MAX_TEXT_FILE_MB", "25"))
MAX_CHECKSUM_MB = float(os.environ.get("MAX_CHECKSUM_FILE_MB", "50"))
ENABLE_OCR = os.environ.get("ENABLE_OCR", "false").strip().lower() in ("1", "true", "yes")
ENABLE_AI = os.environ.get("ENABLE_AI_CLASSIFICATION", "false").strip().lower() in ("1", "true", "yes")
ENABLE_VECTORS = os.environ.get("ENABLE_VECTOR_EMBEDDINGS", "false").strip().lower() in ("1", "true", "yes")

FILE_CATEGORIES = frozenset({
    "uncategorized", "project_document", "protocol", "SOP", "meeting_note", "publication",
    "software_guide", "troubleshooting", "clinical_metadata", "image_processing",
    "pipeline_script", "analysis_script", "dataset", "log", "report", "figure", "unknown",
})

EXT_TYPE_MAP: dict[str, str] = {
    ".pdf": "document", ".docx": "document", ".doc": "document", ".txt": "document",
    ".md": "document", ".html": "document", ".htm": "document", ".rtf": "document",
    ".xlsx": "spreadsheet", ".xls": "spreadsheet", ".csv": "spreadsheet", ".tsv": "spreadsheet",
    ".py": "script", ".r": "script", ".ipynb": "notebook", ".sh": "script", ".slurm": "script",
    ".yaml": "config", ".yml": "config", ".json": "config", ".toml": "config", ".xml": "config",
    ".tif": "image_data", ".tiff": "image_data", ".png": "image", ".jpg": "image", ".jpeg": "image",
    ".svs": "image_data", ".ndpi": "image_data", ".czi": "image_data", ".ims": "image_data",
    ".parquet": "dataset", ".h5ad": "dataset", ".h5": "dataset", ".rds": "dataset", ".feather": "dataset",
    ".log": "log", ".out": "log", ".err": "log",
}


def ensure_digitalization_schema() -> None:
    ensure_vault_schema()
    from app_skeleton.api.sql_migrations import apply_pending_migrations

    apply_pending_migrations()


def _project_candidate_id(name: str) -> str:
    return "proj_" + hashlib.sha1(name.encode("utf-8")).hexdigest()[:14]


def _folder_id(rel_path: str) -> str:
    return "fld_" + hashlib.sha1(rel_path.encode("utf-8")).hexdigest()[:14]


def detect_file_type(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in EXT_TYPE_MAP:
        return EXT_TYPE_MAP[ext]
    if de.is_vault_large_binary(path):
        return "image_data"
    if ext in de.EXTRACTABLE_TEXT_EXTENSIONS:
        return "document"
    return "unknown"


def rule_category(path: Path, detected_type: str) -> tuple[str, float]:
    p = str(path).lower()
    if detected_type == "log" or path.suffix.lower() in {".log", ".out", ".err"}:
        return "log", 0.7
    if detected_type in {"script", "notebook"}:
        return "pipeline_script", 0.55
    if detected_type == "spreadsheet":
        return "dataset", 0.5
    if detected_type == "image_data":
        return "figure", 0.45
    if re.search(r"protocol|sop", p):
        return "protocol", 0.6
    if re.search(r"meeting|minutes", p):
        return "meeting_note", 0.55
    return "uncategorized", 0.3


def iter_project_folders(scan_root: Path) -> Iterator[Path]:
    for child in sorted(scan_root.iterdir()):
        if child.is_dir() and not child.name.startswith("."):
            if any(part in de.SKIP_PARTS for part in child.parts):
                continue
            yield child


def _should_skip_unchanged(cur, asset_id: str, checksum: str, mtime_iso: str | None) -> bool:
    cur.execute(
        """
        SELECT ka.asset_id, v.checksum_sha256, v.modified_at::text
        FROM platform.knowledge_assets ka
        JOIN platform.raw_asset_vault v ON v.asset_id = ka.asset_id
        WHERE ka.asset_id = %s AND ka.extraction_status IN ('extracted', 'metadata_only', 'unsupported');
        """,
        (asset_id,),
    )
    row = cur.fetchone()
    if not row:
        return False
    _, old_cs, old_mt = row
    return bool(checksum and old_cs == checksum and (not mtime_iso or old_mt == mtime_iso))


def _persist_sidecars(
    cur,
    *,
    asset_id: str,
    result: de.ExtractionResult,
    project_candidate_id: str | None,
    ai_category: str,
    confidence: float,
    abs_path: Path,
    relative_path: str,
) -> None:
    meta = result.metadata or {}
    extraction_status = de.vault_extraction_status(result)
    if result.errors and extraction_status != "unsupported":
        extraction_status = "failed" if extraction_status != "metadata_only" else extraction_status

    embedding_status = "disabled"
    if ENABLE_VECTORS and result.text:
        embedding_status = "pending"

    review_status = "needs_review" if ai_category == "uncategorized" else "raw"
    err_msg = "; ".join(result.errors)[:2000] if result.errors else None

    cur.execute(
        """
        INSERT INTO platform.knowledge_assets (
            asset_id, storage_root_id, absolute_path, relative_path, filename, extension,
            file_size, modified_at, detected_type, project_candidate_id, pipeline_stage_guess,
            user_category, ai_category, confidence_score, ingestion_status, extraction_status,
            review_status, embedding_status, chunking_status, chunk_count, error_message, metadata_json
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s::timestamptz, %s, %s, %s, NULL, %s, %s,
            'processed', %s, %s, %s, 'not_started', %s, %s, %s::jsonb
        )
        ON CONFLICT (asset_id) DO UPDATE SET
            absolute_path = EXCLUDED.absolute_path,
            relative_path = EXCLUDED.relative_path,
            detected_type = EXCLUDED.detected_type,
            project_candidate_id = COALESCE(EXCLUDED.project_candidate_id, platform.knowledge_assets.project_candidate_id),
            ai_category = EXCLUDED.ai_category,
            confidence_score = EXCLUDED.confidence_score,
            extraction_status = EXCLUDED.extraction_status,
            review_status = EXCLUDED.review_status,
            embedding_status = EXCLUDED.embedding_status,
            error_message = EXCLUDED.error_message,
            metadata_json = EXCLUDED.metadata_json,
            updated_at = now();
        """,
        (
            asset_id,
            STORAGE_ROOT_ID,
            str(abs_path),
            relative_path,
            abs_path.name,
            abs_path.suffix.lower(),
            result.size_bytes,
            result.modified_at,
            detect_file_type(abs_path),
            project_candidate_id,
            meta.get("pipeline_stage_guess"),
            ai_category,
            confidence,
            extraction_status,
            review_status,
            embedding_status,
            len(result.chunks or []),
            err_msg,
            _jsonb_dumps({**meta, "engine": "project_digitalization_engine"}),
        ),
    )

    if result.text and extraction_status not in ("metadata_only", "unsupported", "skipped"):
        cur.execute(
            """
            INSERT INTO platform.extracted_texts (
                asset_id, raw_text, cleaned_text, extraction_method, quality_score,
                char_count, word_count, language_guess, ocr_needed
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            """,
            (
                asset_id,
                result.text[:500_000],
                de._clean(result.text)[:500_000],
                result.extractor,
                float(meta.get("quality_score") or (0.8 if result.char_count > 50 else 0.3)),
                result.char_count,
                result.word_count,
                meta.get("language_guess"),
                bool(meta.get("ocr_needed") or (result.extension == ".pdf" and result.char_count < 20)),
            ),
        )

    sheets = meta.get("sheets") or meta.get("excel_sheets")
    if sheets and isinstance(sheets, list):
        for sheet in sheets[:20]:
            if not isinstance(sheet, dict):
                continue
            cur.execute(
                """
                INSERT INTO platform.extracted_tables (
                    asset_id, sheet_name, row_count, column_count, column_names,
                    column_types, preview_rows, missing_summary, schema_json
                ) VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb);
                """,
                (
                    asset_id,
                    sheet.get("name"),
                    sheet.get("rows"),
                    sheet.get("columns"),
                    json.dumps(sheet.get("column_names") or []),
                    json.dumps(sheet.get("column_types") or {}),
                    json.dumps(sheet.get("preview_rows") or []),
                    json.dumps(sheet.get("missing_summary") or {}),
                    json.dumps(sheet),
                ),
            )

    if meta.get("script_summary") or result.document_kind in ("script", "notebook"):
        ss = meta.get("script_summary") or meta
        cur.execute(
            """
            INSERT INTO platform.script_metadata (
                asset_id, language, imports, functions, classes, input_paths, output_paths,
                cli_args, software_names, pipeline_stage_guess, summary_json
            ) VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s::jsonb);
            """,
            (
                asset_id,
                ss.get("language") or meta.get("language"),
                json.dumps(ss.get("imports") or []),
                json.dumps(ss.get("functions") or []),
                json.dumps(ss.get("classes") or []),
                json.dumps(ss.get("input_paths") or []),
                json.dumps(ss.get("output_paths") or []),
                json.dumps(ss.get("cli_args") or []),
                json.dumps(ss.get("software_names") or []),
                ss.get("pipeline_stage_guess"),
                json.dumps(ss),
            ),
        )

    if meta.get("log_summary") or detect_file_type(abs_path) == "log":
        ls = meta.get("log_summary") or meta
        cur.execute(
            """
            INSERT INTO platform.log_summaries (
                asset_id, job_id, software_name, error_messages, warnings, status_guess,
                failed_command, output_paths, pipeline_stage_guess, summary_json
            ) VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s::jsonb, %s, %s::jsonb);
            """,
            (
                asset_id,
                ls.get("job_id"),
                ls.get("software_name"),
                json.dumps(ls.get("error_messages") or []),
                json.dumps(ls.get("warnings") or []),
                ls.get("status_guess", "unknown"),
                ls.get("failed_command"),
                json.dumps(ls.get("output_paths") or []),
                ls.get("pipeline_stage_guess"),
                json.dumps(ls),
            ),
        )

    if project_candidate_id:
        cur.execute(
            """
            INSERT INTO platform.relationship_candidates (
                from_asset_id, relation_type, confidence_score, metadata_json
            ) VALUES (%s, 'file_belongs_to_project', 0.85, %s::jsonb);
            """,
            (asset_id, json.dumps({"project_candidate_id": project_candidate_id})),
        )


def upsert_project_candidate(cur, project_dir: Path, scan_root: Path) -> str:
    rel = str(project_dir.relative_to(scan_root)).replace("\\", "/")
    pid = _project_candidate_id(project_dir.name)
    counts = {"folders": 0, "files": 0, "documents": 0, "data": 0, "scripts": 0, "images": 0, "logs": 0}
    for p in project_dir.rglob("*"):
        if any(part in de.SKIP_PARTS for part in p.parts):
            continue
        if p.is_dir():
            counts["folders"] += 1
        elif p.is_file():
            counts["files"] += 1
            dt = detect_file_type(p)
            if dt == "document":
                counts["documents"] += 1
            elif dt in ("spreadsheet", "dataset"):
                counts["data"] += 1
            elif dt in ("script", "notebook"):
                counts["scripts"] += 1
            elif dt in ("image", "image_data"):
                counts["images"] += 1
            elif dt == "log":
                counts["logs"] += 1

    cur.execute(
        """
        INSERT INTO platform.project_candidates (
            project_candidate_id, storage_root_id, project_name, project_path, relative_path,
            folder_count, file_count, document_count, data_count, script_count, image_count, log_count
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (project_candidate_id) DO UPDATE SET
            project_path = EXCLUDED.project_path,
            folder_count = EXCLUDED.folder_count,
            file_count = EXCLUDED.file_count,
            document_count = EXCLUDED.document_count,
            data_count = EXCLUDED.data_count,
            script_count = EXCLUDED.script_count,
            image_count = EXCLUDED.image_count,
            log_count = EXCLUDED.log_count,
            updated_at = now();
        """,
        (
            pid,
            STORAGE_ROOT_ID,
            project_dir.name,
            str(project_dir),
            rel,
            counts["folders"],
            counts["files"],
            counts["documents"],
            counts["data"],
            counts["scripts"],
            counts["images"],
            counts["logs"],
        ),
    )
    return pid


def run_digitalization(
    *,
    mode: str = "project",
    project_name: str | None = None,
    resume: bool = False,
    dry_run: bool = False,
    retry_failed: bool = False,
    max_files: int | None = None,
) -> dict[str, Any]:
    ensure_digitalization_schema()
    scan_root = lab_storage_root()
    if scan_root is None:
        roots = projects_roots_for_scan()
        if not roots:
            raise FileNotFoundError(
                "NEEDS_USER_DECISION: set LAB_STORAGE_ROOT to mounted project storage or PROJECTS_ROOT"
            )
        scan_root = roots[0]

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_dig_" + uuid.uuid4().hex[:8]
    counts: dict[str, int] = {
        "folders_scanned": 0,
        "files_scanned": 0,
        "files_processed": 0,
        "files_skipped": 0,
        "files_failed": 0,
        "documents_extracted": 0,
        "tables_extracted": 0,
        "scripts_extracted": 0,
        "logs_extracted": 0,
        "large_metadata_only": 0,
        "uncategorized": 0,
        "review_needed": 0,
        "unsupported": 0,
    }

    projects: list[Path] = []
    if mode == "project" and project_name:
        for root in projects_roots_for_scan() or [scan_root]:
            candidate = root / project_name
            if candidate.is_dir():
                projects = [candidate]
                scan_root = root
                break
        if not projects:
            raise FileNotFoundError(f"Project folder not found: {project_name}")
    else:
        projects = list(iter_project_folders(scan_root))

    checkpoint_key = f"digitalization:{project_name or 'full'}"

    with psycopg.connect(_db_conn(), connect_timeout=120) as conn:
        with conn.cursor() as cur:
            if not dry_run:
                cur.execute(
                    """
                    INSERT INTO platform.digitalization_runs (run_id, mode, storage_root, project_name, dry_run, status)
                    VALUES (%s, %s, %s, %s, %s, 'running');
                    """,
                    (run_id, mode, str(scan_root), project_name, dry_run),
                )
                conn.commit()

            resume_after: str | None = None
            if resume:
                from app_skeleton.api.vault_ingestion_engine import _load_checkpoint

                cp = _load_checkpoint(cur, checkpoint_key)
                if cp:
                    resume_after = cp.get("last_logical_path")

            for project_dir in projects:
                if dry_run:
                    for _ in project_dir.rglob("*"):
                        if _.is_file():
                            counts["files_scanned"] += 1
                    continue

                pc_id = upsert_project_candidate(cur, project_dir, scan_root)
                for abs_path, logical in iter_scan_files(
                    project_dir,
                    resume_after=resume_after,
                    all_extensions=True,
                ):
                    if max_files and counts["files_scanned"] >= max_files:
                        break
                    counts["files_scanned"] += 1

                    stat = de._safe_stat(abs_path)
                    asset_id = stable_asset_id(logical, stat["size_bytes"])

                    try:
                        if stat["size_bytes"] > MAX_TEXT_MB * 1024 * 1024 and not de.is_vault_large_binary(abs_path):
                            result = de.ExtractionResult(
                                path=logical,
                                name=abs_path.name,
                                extension=abs_path.suffix.lower(),
                                document_kind="other",
                                mime_type=_guess_mime(abs_path),
                                size_bytes=stat["size_bytes"],
                                modified_at=stat.get("modified_at"),
                                status="skipped",
                                warnings=[f"file exceeds MAX_TEXT_FILE_MB={MAX_TEXT_MB}"],
                            )
                        else:
                            result = de.extract_for_vault(abs_path, project_dir)
                    except Exception as exc:
                        result = de.ExtractionResult(
                            path=logical,
                            name=abs_path.name,
                            extension=abs_path.suffix.lower(),
                            document_kind="other",
                            mime_type=_guess_mime(abs_path),
                            size_bytes=stat["size_bytes"],
                            modified_at=stat.get("modified_at"),
                            status="failed",
                            errors=[str(exc)],
                        )

                    checksum = result.sha256 or ""
                    if not retry_failed and _should_skip_unchanged(
                        cur, asset_id, checksum, stat.get("modified_at")
                    ):
                        counts["files_skipped"] += 1
                        continue

                    ext_status = de.vault_extraction_status(result)
                    ai_cat, conf = rule_category(abs_path, detect_file_type(abs_path))
                    if ENABLE_AI:
                        ai_cat = ai_cat  # hook for future LLM classify

                    vault_counts: dict[str, int] = {}
                    asset_id = upsert_vault_from_extraction(
                        cur,
                        logical_path=logical,
                        abs_path=abs_path,
                        project_hint=project_dir.name,
                        result=result,
                        counts=vault_counts,
                    )
                    _persist_sidecars(
                        cur,
                        asset_id=asset_id,
                        result=result,
                        project_candidate_id=pc_id,
                        ai_category=ai_cat,
                        confidence=conf,
                        abs_path=abs_path,
                        relative_path=logical,
                    )
                    if result.chunks:
                        from app_skeleton.api.vault_ingestion_engine import _maybe_knowledge_index

                        _maybe_knowledge_index(asset_id, result, logical_path=logical)

                    counts["files_processed"] += 1
                    if ext_status == "failed":
                        counts["files_failed"] += 1
                        cur.execute(
                            """
                            INSERT INTO platform.digitalization_errors (run_id, asset_id, relative_path, error_message)
                            VALUES (%s, %s, %s, %s);
                            """,
                            (run_id, asset_id, logical, "; ".join(result.errors)[:1000]),
                        )
                    elif ext_status == "metadata_only":
                        counts["large_metadata_only"] += 1
                    elif ext_status == "unsupported":
                        counts["unsupported"] += 1
                    elif ext_status == "extracted":
                        counts["documents_extracted"] += 1
                    if result.metadata.get("sheets") or result.metadata.get("excel_sheets"):
                        counts["tables_extracted"] += 1
                    if result.metadata.get("script_summary"):
                        counts["scripts_extracted"] += 1
                    if result.metadata.get("log_summary"):
                        counts["logs_extracted"] += 1
                    if ai_cat == "uncategorized":
                        counts["uncategorized"] += 1
                        counts["review_needed"] += 1

                    if counts["files_processed"] % BATCH_SIZE == 0:
                        from app_skeleton.api.vault_ingestion_engine import _save_checkpoint

                        _save_checkpoint(
                            cur,
                            checkpoint_id=checkpoint_key,
                            scan_root=str(scan_root),
                            project_hint=project_dir.name,
                            last_logical_path=logical,
                            files_processed=counts["files_processed"],
                            status="running",
                            manifest={"run_id": run_id, "counts": counts},
                            job_id=None,
                        )
                        conn.commit()

            if not dry_run:
                cur.execute(
                    """
                    UPDATE platform.digitalization_runs
                    SET status = 'completed', finished_at = now(), report_json = %s::jsonb
                    WHERE run_id = %s;
                    """,
                    (json.dumps({"counts": counts}), run_id),
                )
                conn.commit()

    report = {
        "run_id": run_id,
        "mode": mode,
        "storage_root": str(scan_root),
        "project_name": project_name,
        "dry_run": dry_run,
        "enable_ocr": ENABLE_OCR,
        "enable_vectors": ENABLE_VECTORS,
        "finished_at": _utc_now(),
        "counts": counts,
    }
    path = _write_report(run_id, report)
    report["report_path"] = str(path)
    return report


def search_knowledge(
    q: str,
    *,
    uncategorized_only: bool = False,
    limit: int = 50,
) -> list[dict[str, Any]]:
    ensure_digitalization_schema()
    pattern = f"%{q.strip()}%"
    clauses = [
        "(ka.filename ILIKE %s OR ka.relative_path ILIKE %s OR et.cleaned_text ILIKE %s OR et.raw_text ILIKE %s)",
    ]
    params: list[Any] = [pattern, pattern, pattern, pattern]
    if uncategorized_only:
        clauses.append("(ka.ai_category = 'uncategorized' OR ka.user_category IS NULL)")
    sql = f"""
        SELECT ka.asset_id, ka.filename, ka.relative_path, ka.detected_type,
               ka.ai_category, ka.extraction_status, ka.review_status,
               left(et.cleaned_text, 400) AS text_preview
        FROM platform.knowledge_assets ka
        LEFT JOIN LATERAL (
            SELECT cleaned_text, raw_text FROM platform.extracted_texts
            WHERE asset_id = ka.asset_id ORDER BY text_id DESC LIMIT 1
        ) et ON true
        WHERE {' AND '.join(clauses)}
        ORDER BY ka.updated_at DESC
        LIMIT %s;
    """
    params.append(limit)
    with psycopg.connect(_db_conn(), connect_timeout=30) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]


def list_review_queue(kind: str = "uncategorized", limit: int = 100) -> list[dict[str, Any]]:
    ensure_digitalization_schema()
    filters = {
        "uncategorized": "ka.ai_category = 'uncategorized' OR ka.review_status = 'needs_review'",
        "failed": "ka.extraction_status = 'failed'",
        "large_files": "ka.extraction_status = 'metadata_only'",
        "tables": "EXISTS (SELECT 1 FROM platform.extracted_tables t WHERE t.asset_id = ka.asset_id)",
        "texts": "EXISTS (SELECT 1 FROM platform.extracted_texts t WHERE t.asset_id = ka.asset_id)",
        "scripts": "EXISTS (SELECT 1 FROM platform.script_metadata s WHERE s.asset_id = ka.asset_id)",
        "logs": "EXISTS (SELECT 1 FROM platform.log_summaries l WHERE l.asset_id = ka.asset_id)",
        "projects": "TRUE",
    }
    where = filters.get(kind, filters["uncategorized"])
    with psycopg.connect(_db_conn(), connect_timeout=30) as conn:
        with conn.cursor() as cur:
            if kind == "projects":
                cur.execute(
                    """
                    SELECT project_candidate_id, project_name, project_path, file_count,
                           document_count, project_status, ai_category_status
                    FROM platform.project_candidates
                    ORDER BY updated_at DESC LIMIT %s;
                    """,
                    (limit,),
                )
            else:
                cur.execute(
                    f"""
                    SELECT ka.asset_id, ka.filename, ka.relative_path, ka.detected_type,
                           ka.ai_category, ka.extraction_status, ka.review_status, ka.error_message
                    FROM platform.knowledge_assets ka
                    WHERE {where}
                    ORDER BY ka.updated_at DESC LIMIT %s;
                    """,
                    (limit,),
                )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]


def patch_asset_review(
    asset_id: str,
    *,
    user_category: str | None = None,
    review_status: str | None = None,
    project_candidate_id: str | None = None,
) -> dict[str, Any]:
    ensure_digitalization_schema()
    updates: list[str] = []
    params: list[Any] = []
    if user_category and user_category in FILE_CATEGORIES:
        updates.append("user_category = %s")
        params.append(user_category)
    if review_status:
        updates.append("review_status = %s")
        params.append(review_status)
    if project_candidate_id:
        updates.append("project_candidate_id = %s")
        params.append(project_candidate_id)
    if not updates:
        return {"asset_id": asset_id, "updated": False}
    params.append(asset_id)
    with psycopg.connect(_db_conn(), connect_timeout=30) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE platform.knowledge_assets SET {', '.join(updates)}, updated_at = now() WHERE asset_id = %s;",
                params,
            )
            conn.commit()
    return {"asset_id": asset_id, "updated": True}
