"""Extract, chunk, and persist lab database sections (Overview, Orders, Social, Wet-lab)."""
from __future__ import annotations

import argparse
import json
import logging
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app_skeleton.api import document_extraction as de
from app_skeleton.api.database_sections import DATABASE_SECTIONS, section_root
from app_skeleton.api.data_layout import (
    lab_processed_read_path,
    lab_processed_write_path,
    iter_lab_processed_files,
)
from app_skeleton.api.paths import DATABASE_ROOT, PROCESSED_DIR, PUBLIC_PROCESSED_DIR
from app_skeleton.api.project_processor import sync_public_processed

LOGGER = logging.getLogger(__name__)


def _iter_chunks_from_disk(section_id: str) -> list[dict[str, Any]]:
    """Load all chunks from jsonl (complete) with JSON fallback."""
    chunks: list[dict[str, Any]] = []
    jsonl_path = processed_chunks_path(section_id)
    if jsonl_path.exists():
        try:
            with jsonl_path.open(encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    chunks.append(json.loads(line))
            return chunks
        except Exception:
            pass
    twin = load_processed_section(section_id)
    return list(twin.get("vector_chunks") or []) if twin else []


def write_lab_manifest() -> Path:
    """Small index for the UI to discover processed lab sections without API."""
    PUBLIC_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sections": list_processed_summary(),
    }
    out = PUBLIC_PROCESSED_DIR / "lab__manifest.json"
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return out

LAB_STORAGE_PREFIX = "lab__"


def storage_key(section_id: str) -> str:
    return f"{LAB_STORAGE_PREFIX}{section_id}"


def processed_json_path(section_id: str) -> Path:
    return lab_processed_read_path(section_id, chunks=False)


def processed_chunks_path(section_id: str) -> Path:
    return lab_processed_read_path(section_id, chunks=True)


def processed_json_write_path(section_id: str) -> Path:
    return lab_processed_write_path(section_id, chunks=False)


def processed_chunks_write_path(section_id: str) -> Path:
    return lab_processed_write_path(section_id, chunks=True)


def _annotate_chunks(chunks: list[dict[str, Any]], section_id: str, section_label: str) -> list[dict[str, Any]]:
    out = []
    for chunk in chunks:
        row = dict(chunk)
        row["section_id"] = section_id
        row["section_label"] = section_label
        row["scope"] = "lab"
        row["project_code"] = None
        out.append(row)
    return out


def _folder_tree_from_assets(assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, dict[str, Any]] = defaultdict(lambda: {"file_count": 0, "extensions": set()})
    for asset in assets:
        folder = asset.get("folder") or "."
        counts[folder]["file_count"] += 1
        ext = asset.get("extension") or ""
        if ext:
            counts[folder]["extensions"].add(ext)
    rows = []
    for path, info in sorted(counts.items(), key=lambda x: x[0]):
        rows.append({
            "path": path,
            "file_count": info["file_count"],
            "categories": sorted(info["extensions"]),
        })
    return rows


def process_section(section_id: str) -> dict[str, Any]:
    if section_id not in DATABASE_SECTIONS:
        raise ValueError(f"Unknown database section: {section_id}")
    meta = DATABASE_SECTIONS[section_id]
    root = section_root(section_id)
    if not root.is_dir():
        raise FileNotFoundError(f"Section folder not found: {root}")

    file_inventory = de._scan_folder(root)
    all_assets = de._scan_all_assets(root)
    content_library = de._build_content_library(all_assets) if all_assets else {
        "sections": [], "figures_gallery": [], "totals": {}, "figure_count": 0,
    }

    document_records: list[de.ExtractionResult] = []
    vector_chunks: list[dict[str, Any]] = []
    extraction_summary: dict[str, Any] = {
        "total_scannable_assets": 0,
        "extracted_records": 0,
        "chunk_count": 0,
        "status_counts": {},
        "extractor_counts": {},
        "extension_counts": {},
        "errors": [],
    }
    if all_assets:
        document_records, vector_chunks, extraction_summary = de._extract_project_documents(root, all_assets)

    vector_chunks = _annotate_chunks(vector_chunks, section_id, meta["label"])
    combined_text = de._combine_text_records(document_records)
    document_index = [
        r.as_json(include_text=False, include_chunks=False)
        for r in document_records[: de.DEFAULT_MAX_DOCS_IN_JSON]
    ]

    extracted_count = extraction_summary.get("status_counts", {}).get("extracted", 0)
    return {
        "section_id": section_id,
        "storage_key": storage_key(section_id),
        "scope": "lab",
        "section_label": meta["label"],
        "description": meta["description"],
        "relative_root": meta["relative_root"],
        "database_root": str(DATABASE_ROOT),
        "content_root": str(root),
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "source_files_count": len(file_inventory),
        "total_assets_count": len(all_assets),
        "content_library": content_library,
        "document_index": document_index,
        "vector_chunks": vector_chunks[: de.DEFAULT_MAX_CHUNKS_IN_JSON],
        "extraction": extraction_summary,
        "folder_tree": _folder_tree_from_assets(all_assets)[:500],
        "combined_text_chars": len(combined_text),
        "metrics": {
            "document_count": len(file_inventory),
            "total_assets": len(all_assets),
            "scannable_assets": extraction_summary.get("total_scannable_assets", 0),
            "extracted_document_count": extracted_count,
            "knowledge_chunk_count": len(vector_chunks),
            "extraction_error_count": len(extraction_summary.get("errors", [])),
            "figure_count": content_library.get("figure_count", 0),
        },
    }


def save_processed_section(section_id: str, data: dict[str, Any] | None = None) -> Path:
    payload = data or process_section(section_id)
    out = processed_json_write_path(section_id)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    chunks = payload.get("vector_chunks") or []
    chunks_out = processed_chunks_write_path(section_id)
    with chunks_out.open("w", encoding="utf-8") as fh:
        for chunk in chunks:
            fh.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    sync_public_processed()
    write_lab_manifest()
    try:
        from app_skeleton.api.knowledge_indexer import index_section_twin
        from app_skeleton.api.platform_flags import knowledge_indexer_enabled

        if knowledge_indexer_enabled():
            index_section_twin(
                section_id=section_id,
                section_label=payload.get("section_label") or section_id,
                twin=payload,
            )
    except Exception as exc:
        LOGGER.warning("knowledge_indexer twin hook failed for %s: %s", section_id, exc)
    return out


def load_processed_section(section_id: str) -> dict[str, Any] | None:
    path = processed_json_path(section_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def get_section_record(section_id: str, *, refresh: bool = False) -> dict[str, Any]:
    if not refresh:
        cached = load_processed_section(section_id)
        if cached:
            return cached
    data = process_section(section_id)
    save_processed_section(section_id, data)
    return data


def _skip_on_bulk_process(section_id: str) -> bool:
    """Skip project-tree paths when bulk-processing lab corpus (projects handled separately)."""
    root = DATABASE_SECTIONS[section_id]["relative_root"]
    return root.startswith("projects/") or root == "projects"


def process_all_sections(*, refresh: bool = True) -> dict[str, Any]:
    results = []
    errors = []
    skipped: list[str] = []
    for section_id in DATABASE_SECTIONS:
        if _skip_on_bulk_process(section_id):
            skipped.append(section_id)
            continue
        try:
            twin = get_section_record(section_id, refresh=refresh)
            results.append({
                "section_id": section_id,
                "section_label": twin.get("section_label"),
                "metrics": twin.get("metrics"),
                "processed_at": twin.get("processed_at"),
                "output": str(processed_json_path(section_id)),
            })
        except Exception as exc:
            errors.append({"section_id": section_id, "error": str(exc)})
    manifest_path = write_lab_manifest()
    return {
        "processed": len(results),
        "skipped": skipped,
        "sections": results,
        "errors": errors,
        "output_dir": str(PROCESSED_DIR),
        "manifest": str(manifest_path),
    }


def _vault_asset_counts_by_section() -> dict[str, int]:
    """Count vault rows whose logical_path is under each section root (when Postgres is up)."""
    try:
        from app_skeleton.api.supabase_sync import local_postgres_conn

        import psycopg

        counts: dict[str, int] = {sid: 0 for sid in DATABASE_SECTIONS}
        with psycopg.connect(local_postgres_conn(), connect_timeout=8) as conn:
            with conn.cursor() as cur:
                for sid, meta in DATABASE_SECTIONS.items():
                    prefix = meta["relative_root"].replace("\\", "/").rstrip("/") + "/"
                    cur.execute(
                        """
                        SELECT COUNT(*) FROM platform.raw_asset_vault
                        WHERE logical_path LIKE %s OR logical_path = %s;
                        """,
                        (prefix + "%", meta["relative_root"].replace("\\", "/")),
                    )
                    row = cur.fetchone()
                    counts[sid] = int(row[0]) if row else 0
        return counts
    except Exception:
        return {}


def _document_preview_row(
    doc: dict[str, Any],
    *,
    relative_root: str | None = None,
) -> dict[str, Any]:
    path = (doc.get("path") or doc.get("relative_path") or "").replace("\\", "/")
    title = de.document_display_title(doc)
    excerpt = de.document_display_excerpt(doc)
    row = {
        "path": path,
        "name": doc.get("name") or (Path(path).name if path else ""),
        "title": title,
        "excerpt": excerpt,
        "extraction_status": doc.get("extraction_status") or doc.get("status"),
        "extension": doc.get("extension"),
        "word_count": doc.get("word_count"),
    }
    if relative_root and path:
        row["open_url"] = de.lab_database_asset_url(relative_root, path)
    return row


def _extraction_status_label(twin: dict[str, Any]) -> str:
    if not twin:
        return "not_processed"
    metrics = twin.get("metrics") or {}
    extracted = metrics.get("extracted_document_count")
    if extracted is None:
        extracted = (twin.get("extraction") or {}).get("status_counts", {}).get("extracted", 0)
    total = metrics.get("total_assets") or len(twin.get("document_index") or [])
    if extracted and total:
        return "extracted"
    if twin.get("processed_at"):
        return "processed"
    return "unknown"


def list_lab_sections_detail() -> list[dict[str, Any]]:
    """Sections with on-disk, processed-twin, and vault counts for lab corpus UI."""
    vault_counts = _vault_asset_counts_by_section()
    rows = []
    for section_id, meta in DATABASE_SECTIONS.items():
        root = DATABASE_ROOT / meta["relative_root"]
        cached = load_processed_section(section_id)
        metrics = (cached or {}).get("metrics") or {}
        doc_index = (cached or {}).get("document_index") or []
        extracted = metrics.get("extracted_document_count")
        if extracted is None and cached:
            extracted = (cached.get("extraction") or {}).get("status_counts", {}).get("extracted", 0)
        rows.append({
            "section_id": section_id,
            "section_label": meta["label"],
            "description": meta["description"],
            "relative_root": meta["relative_root"],
            "folder_exists": root.is_dir(),
            "processed": cached is not None,
            "processed_at": cached.get("processed_at") if cached else None,
            "extraction_status": _extraction_status_label(cached),
            "metrics": metrics,
            "disk_asset_count": metrics.get("total_assets") or len(doc_index),
            "document_index_count": len(doc_index),
            "extracted_document_count": extracted or 0,
            "vault_asset_count": vault_counts.get(section_id, 0),
            "storage_key": storage_key(section_id),
            "twin_path": str(processed_json_path(section_id).name) if cached else None,
        })
    return rows


def section_detail_for_api(section_id: str, *, document_preview_limit: int = 50) -> dict[str, Any]:
    """Processed twin summary for UI — reads local JSON under processed_projects (not Supabase)."""
    if section_id not in DATABASE_SECTIONS:
        raise ValueError(f"Unknown database section: {section_id}")
    twin = load_processed_section(section_id)
    if not twin:
        raise FileNotFoundError(
            "Section not processed yet. Run database_processor --all --refresh."
        )
    meta = DATABASE_SECTIONS[section_id]
    vault_counts = _vault_asset_counts_by_section()
    doc_index = twin.get("document_index") or []
    limit = max(1, min(int(document_preview_limit or 50), 200))
    return {
        "section_id": section_id,
        "section_label": twin.get("section_label") or meta["label"],
        "description": twin.get("description") or meta["description"],
        "relative_root": meta["relative_root"],
        "storage_key": storage_key(section_id),
        "source": "local_processed_json",
        "twin_file": processed_json_path(section_id).name,
        "metrics": twin.get("metrics"),
        "processed_at": twin.get("processed_at"),
        "extraction": twin.get("extraction"),
        "extraction_status": _extraction_status_label(twin),
        "document_index_count": len(doc_index),
        "document_index_preview": [
            _document_preview_row(d, relative_root=meta["relative_root"]) for d in doc_index[:limit]
        ],
        "folder_tree": (twin.get("folder_tree") or [])[:200],
        "content_library_totals": (twin.get("content_library") or {}).get("totals"),
        "vault_asset_count": vault_counts.get(section_id, 0),
        "knowledge_search_path": f"/knowledge_search?section_id={section_id}",
    }


def section_summary_for_api(section_id: str) -> dict[str, Any]:
    """Backward-compatible alias — same payload as section_detail_for_api."""
    return section_detail_for_api(section_id)


def section_documents_for_api(
    section_id: str,
    *,
    q: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> dict[str, Any]:
    """Paginated document list from processed twin (local JSON)."""
    if section_id not in DATABASE_SECTIONS:
        raise ValueError(f"Unknown database section: {section_id}")
    twin = load_processed_section(section_id)
    if not twin:
        raise FileNotFoundError(
            "Section not processed yet. Run database_processor --all --refresh."
        )
    rel_root = DATABASE_SECTIONS[section_id]["relative_root"]
    docs = twin.get("document_index") or []
    tokens = _tokenize_query(q or "")
    if tokens:
        filtered = []
        for doc in docs:
            blob = " ".join(
                str(doc.get(k) or "")
                for k in ("path", "title", "name", "excerpt", "extension")
            ).lower()
            if any(tok in blob for tok in tokens):
                filtered.append(doc)
        docs = filtered
    total = len(docs)
    offset = max(0, int(offset or 0))
    limit = max(1, min(int(limit or 50), 200))
    page = docs[offset : offset + limit]
    return {
        "section_id": section_id,
        "query": q,
        "total": total,
        "offset": offset,
        "limit": limit,
        "documents": [_document_preview_row(d, relative_root=rel_root) for d in page],
    }


def list_processed_summary() -> list[dict[str, Any]]:
    rows = []
    for section_id, meta in DATABASE_SECTIONS.items():
        cached = load_processed_section(section_id)
        root = DATABASE_ROOT / meta["relative_root"]
        rows.append({
            "section_id": section_id,
            "section_label": meta["label"],
            "relative_root": meta["relative_root"],
            "folder_exists": root.is_dir(),
            "processed": cached is not None,
            "processed_at": cached.get("processed_at") if cached else None,
            "metrics": cached.get("metrics") if cached else None,
        })
    return rows


def _tokenize_query(query: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9\u00c0-\uffff]{3,}", (query or "").lower()) if t]


def search_section_chunks(
    query: str,
    *,
    section_id: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Keyword search over processed lab chunks (works without Qdrant)."""
    tokens = _tokenize_query(query)
    if not tokens:
        return []
    limit = max(1, min(int(limit or 20), 50))
    section_ids = [section_id] if section_id else list(DATABASE_SECTIONS.keys())
    hits: list[tuple[int, dict[str, Any]]] = []

    for sid in section_ids:
        twin = load_processed_section(sid)
        if not twin:
            continue
        label = twin.get("section_label") or sid
        for chunk in _iter_chunks_from_disk(sid):
            text = (chunk.get("text") or "").lower()
            if not text:
                continue
            score = sum(3 if tok in text else 0 for tok in tokens)
            if score <= 0:
                continue
            hits.append((score, {
                "section_id": sid,
                "section_label": label,
                "chunk_id": chunk.get("chunk_id"),
                "source_file": chunk.get("source_file"),
                "chunk_index": chunk.get("chunk_index"),
                "text_preview": chunk.get("text")[:1600],
                "score": float(score),
                "scope": "lab",
            }))

    hits.sort(key=lambda x: -x[0])
    return [h[1] for h in hits[:limit]]


def build_vector_manifest(section_id: str) -> dict[str, Any]:
    twin = get_section_record(section_id, refresh=False)
    return {
        "section_id": section_id,
        "storage_key": storage_key(section_id),
        "scope": "lab",
        "section_label": twin.get("section_label"),
        "chunk_count": len(twin.get("vector_chunks") or []),
        "chunks_jsonl": str(processed_chunks_path(section_id).resolve()),
    }


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Process lab database folders into extracted twins.")
    parser.add_argument("--section", help="Single section id (e.g. overview_personnel)")
    parser.add_argument("--all", action="store_true", help="Process every configured database section")
    parser.add_argument("--refresh", action="store_true", help="Force re-extraction")
    parser.add_argument("--list", action="store_true", help="List processing status")
    args = parser.parse_args()

    if args.list:
        print(json.dumps(list_processed_summary(), indent=2, ensure_ascii=False))
        return 0
    if args.all:
        result = process_all_sections(refresh=True)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if not result.get("errors") else 1
    if args.section:
        twin = get_section_record(args.section, refresh=args.refresh or True)
        path = save_processed_section(args.section, twin)
        print(f"wrote {path}")
        print(json.dumps({"metrics": twin.get("metrics"), "extraction": twin.get("extraction", {}).get("status_counts")}, indent=2))
        return 0
    parser.error("Provide --section ID or --all")
    return 1


if __name__ == "__main__":
    raise SystemExit(_cli())
