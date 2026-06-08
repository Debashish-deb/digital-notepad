"""Authenticated lab catalog index and document previews (replaces public/database/*)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from omeia.api.database_sections import DATABASE_SECTIONS
from omeia.api.database_processor import (
    _iter_chunks_from_disk,
    load_processed_section,
    list_processed_summary,
)
from omeia.api.document_extraction import document_display_title

# Legacy UI buckets from buildDatabase.js wiki sections.
_LEGACY_BUCKETS: dict[str, str] = {
    "overview_research_materials": "01_Overview",
    "overview_onboarding": "01_Overview",
    "overview_guidelines": "01_Overview",
    "overview_documents": "01_Overview",
    "overview_personnel": "01_Overview",
    "overview_cleaning": "01_Overview",
    "meetings": "01_Overview",
    "orders_billing": "02_Orders",
    "orders_archive": "02_Orders",
    "social_misc": "03_Social",
    "wet_lab_files": "04_Wet_Lab",
}

_DOC_INDEX: dict[str, tuple[str, str]] = {}


def _legacy_bucket(section_id: str) -> str:
    return _LEGACY_BUCKETS.get(section_id, "01_Overview")


def stable_doc_id(section_id: str, relative_path: str) -> str:
    raw = f"{section_id}|{relative_path}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def _register_doc(section_id: str, path: str, doc_id: str) -> None:
    _DOC_INDEX[doc_id] = (section_id, path)


@lru_cache(maxsize=1)
def build_catalog_index() -> dict[str, Any]:
    """Catalog shape compatible with legacy /database/catalog.json consumers."""
    global _DOC_INDEX
    _DOC_INDEX = {}
    sections: dict[str, list[dict[str, Any]]] = {}
    total = 0

    for section_id in DATABASE_SECTIONS:
        twin = load_processed_section(section_id)
        if not twin:
            continue
        bucket = _legacy_bucket(section_id)
        rel_root = DATABASE_SECTIONS[section_id]["relative_root"]
        for doc in twin.get("document_index") or []:
            path = (doc.get("path") or doc.get("relative_path") or "").replace("\\", "/")
            if not path:
                continue
            doc_id = stable_doc_id(section_id, path)
            _register_doc(section_id, path, doc_id)
            title = document_display_title(doc)
            entry = {
                "id": doc_id,
                "document_id": doc_id,
                "path": path,
                "title": title,
                "filename": doc.get("name") or Path(path).name,
                "section": bucket,
                "section_id": section_id,
                "relative_root": rel_root,
                "has_text": bool(doc.get("excerpt") or doc.get("word_count")),
                "excerpt": (doc.get("excerpt") or "")[:400],
            }
            sections.setdefault(bucket, []).append(entry)
            total += 1

    for bucket in sections:
        sections[bucket].sort(key=lambda d: (d.get("path") or "").lower())

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_documents": total,
        "sections": sections,
        "processed_summary": list_processed_summary(),
    }


def invalidate_catalog_cache() -> None:
    build_catalog_index.cache_clear()
    global _DOC_INDEX
    _DOC_INDEX = {}


def resolve_doc_location(doc_id: str) -> tuple[str, str] | None:
    if not _DOC_INDEX:
        build_catalog_index()
    return _DOC_INDEX.get(doc_id)


def load_catalog_document(doc_id: str) -> dict[str, Any] | None:
    loc = resolve_doc_location(doc_id)
    if not loc:
        build_catalog_index()
        loc = resolve_doc_location(doc_id)
    if not loc:
        return None
    section_id, path = loc
    twin = load_processed_section(section_id)
    if not twin:
        return None

    meta_doc: dict[str, Any] | None = None
    for doc in twin.get("document_index") or []:
        doc_path = (doc.get("path") or doc.get("relative_path") or "").replace("\\", "/")
        if doc_path == path:
            meta_doc = doc
            break

    parts: list[tuple[int, str]] = []
    for chunk in _iter_chunks_from_disk(section_id):
        src = (chunk.get("source_file") or "").replace("\\", "/")
        if src == path:
            parts.append((chunk.get("chunk_index") or 0, chunk.get("text") or ""))
    parts.sort(key=lambda x: x[0])
    full_text = "\n\n".join(t for _, t in parts if t)
    if not full_text and meta_doc:
        full_text = meta_doc.get("excerpt") or meta_doc.get("text") or ""

    title = document_display_title(meta_doc or {"path": path})
    filename = (meta_doc or {}).get("name") or Path(path).name
    metadata = (meta_doc or {}).get("metadata") or {}
    if not metadata.get("source"):
        metadata = {
            **metadata,
            "source": {
                "relative_path": path,
                "path": path,
                "filename": filename,
            },
        }

    return {
        "id": doc_id,
        "document_id": doc_id,
        "title": title,
        "filename": filename,
        "relative_path": path,
        "path": path,
        "full_text": full_text,
        "metadata": metadata,
        "section_id": section_id,
    }


def find_document_by_path(relative_path: str) -> dict[str, Any] | None:
    norm = relative_path.strip().lstrip("/").replace("\\", "/").lower()
    catalog = build_catalog_index()
    for docs in (catalog.get("sections") or {}).values():
        for doc in docs:
            if (doc.get("path") or "").replace("\\", "/").lower() == norm:
                return load_catalog_document(doc["id"])
    basename = norm.split("/")[-1]
    for docs in (catalog.get("sections") or {}).values():
        for doc in docs:
            if (doc.get("path") or "").replace("\\", "/").split("/")[-1].lower() == basename:
                return load_catalog_document(doc["id"])
    return None


def lab_manifest_for_api() -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sections": list_processed_summary(),
    }
