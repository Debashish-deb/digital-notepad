"""Unified platform search — single service for UI and copilot retrieval."""
from __future__ import annotations

import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import psycopg
from qdrant_client import QdrantClient

from omeia.api.database_processor import search_section_chunks
from omeia.api.chat_intent import PROJECT_CODE_ALIASES, detect_project_code
from omeia.api.paths import PROCESSED_DIR, PUBLIC_PROCESSED_DIR
from omeia.api.project_processor import load_processed
from omeia.api.storage_stub import storage_roots
from omeia.api.lab_knowledge_store import get_lab_index_stats, search_lab_knowledge
from omeia.api.llm_client import LLMClient
from omeia.api.document_library_service import search_documents as search_document_library_rows
from omeia.api.raw_vault_store import deduplication_report, fetch_vault_assets_by_ids, review_queue, search_vault
from omeia.api.retrieval_cache import (
    get_cached,
    get_copilot_cached,
    make_cache_key,
    make_copilot_cache_key,
    set_cached,
    set_copilot_cached,
    should_cache,
)
from omeia.api.project_knowledge_store import search_project_knowledge
from omeia.api.search_models import (
    SearchFilters,
    SearchHit,
    SearchMode,
    SearchNavAction,
    UnifiedSearchResponse,
)
from omeia.api.research_knowledge_store import search_research
from omeia.api.people_index import search_people
from omeia.api.search_nav import hit_source_label, nav_for_bucket, vault_domain_for_page
from omeia.api.chunk_fts import search_chunks_fts
from omeia.api.rerank_service import rerank_hits as cross_rerank_hits

LOGGER = logging.getLogger(__name__)

DEFAULT_SCOPES = ("lab", "file", "vault", "notebook", "wiki", "decision", "task", "project", "research", "people")

BUCKET_WEIGHTS: dict[str, float] = {
    "lab": 1.0,
    "file": 0.95,
    "document_library": 0.90,
    "vault": 0.85,
    "vault_review": 0.75,
    "notebook": 0.78,
    "wiki": 0.78,
    "decision": 0.76,
    "task": 0.74,
    "project": 0.65,
    "research": 0.92,
    "people": 0.88,
}

FILTER_SOURCE_SUPPORT: dict[str, frozenset[str]] = {
    "document_library": frozenset({
        "category", "smart_chip", "domain_tab", "system_view", "file_type",
        "date_from", "date_to", "indexed_status", "project_codes", "section_id",
    }),
    "vault": frozenset({"project_codes", "section_id", "indexed_status"}),
    "vault_review": frozenset({"indexed_status", "project_codes"}),
    "lab": frozenset({"section_id", "project_codes"}),
    "file": frozenset({"section_id", "project_codes", "file_type"}),
    "research": frozenset({"project_codes"}),
    "people": frozenset(),
    "notebook": frozenset({"project_codes"}),
    "wiki": frozenset({"project_codes"}),
    "decision": frozenset({"project_codes"}),
    "task": frozenset({"project_codes"}),
    "project": frozenset({"project_codes"}),
}

COPILOT_MIN_SCORE_DEFAULT = float(os.getenv("COPILOT_MIN_SIMILARITY", "0.06"))

COPILOT_MIN_SCORE_BY_INTENT: dict[str, float] = {
    "project_question": 0.04,
    "protocol_question": 0.05,
    "research_question": 0.08,
    "search_request": 0.07,
    "people_question": 0.06,
}


def copilot_min_score(intent: str | None) -> float:
    """Per-intent relevance gate — stricter for research, looser for project workspace."""
    if not intent:
        return COPILOT_MIN_SCORE_DEFAULT
    env_key = f"COPILOT_MIN_SIMILARITY_{intent.upper()}"
    override = os.getenv(env_key, "").strip()
    if override:
        try:
            return float(override)
        except ValueError:
            pass
    return COPILOT_MIN_SCORE_BY_INTENT.get(intent, COPILOT_MIN_SCORE_DEFAULT)


# Backward-compatible alias for tests
COPILOT_MIN_SCORE = COPILOT_MIN_SCORE_DEFAULT

INTENT_SCOPES: dict[str, str] = {
    "research_question": "research,lab,file,vault,document_library,notebook,wiki",
    "project_question": "project,file,lab,vault,document_library,notebook,wiki,research",
    "protocol_question": "lab,vault,file,document_library,notebook,wiki",
    "search_request": "research,lab,file,vault,document_library,notebook,wiki",
    "people_question": "people,lab,research",
    "app_help": "lab,file,wiki",
    "document_ingestion_help": "lab,file,wiki,document_library,vault_review",
}

INTENT_BUCKET_CAPS: dict[str, dict[str, int]] = {
    "research_question": {"vault": 2, "file": 3, "lab": 4},
    "project_question": {"research": 5, "vault": 2, "file": 4},
    "search_request": {"vault": 2, "file": 3},
    "protocol_question": {"research": 1},
    "people_question": {"file": 2, "vault": 2},
}

RESEARCH_INTENTS = frozenset({"research_question", "search_request"})
PROJECT_INTENTS = frozenset({"project_question"})
PROTOCOL_INTENTS = frozenset({"protocol_question"})

INTENT_BUCKET_WEIGHTS: dict[str, dict[str, float]] = {
    "research_question": {
        **BUCKET_WEIGHTS,
        "research": 1.28,
        "lab": 1.08,
        "file": 0.88,
        "vault": 0.82,
    },
    "protocol_question": {
        **BUCKET_WEIGHTS,
        "lab": 1.22,
        "vault": 1.12,
        "file": 0.92,
        "research": 0.75,
    },
    "search_request": {
        **BUCKET_WEIGHTS,
        "research": 1.15,
        "lab": 1.05,
        "file": 1.0,
    },
    "app_help": {
        **BUCKET_WEIGHTS,
        "lab": 1.1,
        "wiki": 1.05,
        "file": 0.9,
    },
    "people_question": {
        **BUCKET_WEIGHTS,
        "people": 1.35,
        "lab": 1.05,
        "research": 0.9,
    },
    "project_question": {
        **BUCKET_WEIGHTS,
        "project": 1.38,
        "file": 1.28,
        "lab": 1.12,
        "vault": 0.95,
        "research": 0.98,
    },
}


def _copilot_include_restricted(
    user_role: str | None,
    *,
    include_restricted: bool | None = None,
) -> bool:
    """Lab copilot visibility — admin/editor/researcher see restricted lab content; not auth secrets."""
    if include_restricted is not None:
        return include_restricted
    return (user_role or "").lower() in {"admin", "editor", "researcher"}


_KNOWN_PROJECT_CODES = {canonical.upper() for canonical in PROJECT_CODE_ALIASES.values()}


def _known_project_code(code: str | None) -> str | None:
    if not code:
        return None
    upper = code.upper()
    if upper in _KNOWN_PROJECT_CODES:
        return code
    return None


def _project_research_query(query: str, project_codes: list[str] | None) -> str | None:
    """Enrich research retrieval when a project code is mentioned."""
    code = _known_project_code(detect_project_code(query))
    if not code and project_codes:
        code = _known_project_code(project_codes[0]) or project_codes[0]
    if not code:
        return None
    lower = (query or "").lower()
    if code.lower() in lower:
        return query
    return f"{code} {query}".strip()


def _tokenize_for_rerank(text: str) -> set[str]:
    return {
        t for t in re.findall(r"[a-z0-9\u00c0-\uffff]{3,}", (text or "").lower())
        if t not in {"the", "and", "for", "what", "how", "does", "with", "from"}
    }


def _rerank_hits(query: str, hits: list["SearchHit"], *, top_n: int = 20) -> list["SearchHit"]:
    """Lightweight lexical reranker — boosts hits whose snippet overlaps query terms."""
    if not hits:
        return hits
    q_tokens = _tokenize_for_rerank(query)
    if not q_tokens:
        return hits[:top_n]

    scored: list[tuple[float, SearchHit]] = []
    for hit in hits[:top_n]:
        blob = f"{hit.title} {hit.snippet}".lower()
        overlap = sum(1 for tok in q_tokens if tok in blob)
        overlap_ratio = overlap / max(len(q_tokens), 1)
        rerank_score = hit.score * (1.0 + 1.2 * overlap_ratio)
        scored.append((rerank_score, hit))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    reranked: list[SearchHit] = []
    for new_score, hit in scored:
        hit.score = new_score
        reranked.append(hit)
    return reranked


def _reserve_bucket_slots(
    hits: list[SearchHit],
    *,
    bucket: str,
    min_count: int,
    limit: int,
    bucket_caps: dict[str, int] | None = None,
    max_per_bucket: int = 4,
) -> list[SearchHit]:
    """Guarantee minimum hits from a bucket even when other buckets score higher."""
    if min_count <= 0:
        return _dedup_and_diversify(hits, limit, max_per_bucket=max_per_bucket, bucket_caps=bucket_caps)
    pool = sorted([h for h in hits if h.bucket == bucket], key=lambda h: h.score, reverse=True)
    reserved = pool[:min_count]
    reserved_ids = {id(h) for h in reserved}
    remainder = [h for h in hits if id(h) not in reserved_ids]
    rest_limit = max(0, limit - len(reserved))
    rest = _dedup_and_diversify(
        remainder,
        rest_limit,
        max_per_bucket=max_per_bucket,
        bucket_caps=bucket_caps,
    ) if rest_limit else []
    return (reserved + rest)[:limit]


def _dedup_and_diversify(
    hits: list["SearchHit"],
    limit: int,
    *,
    max_per_bucket: int = 4,
    bucket_caps: dict[str, int] | None = None,
    min_research: int = 0,
) -> list["SearchHit"]:
    """Deduplicate near-identical snippets and cap per-bucket dominance."""
    seen_snippets: set[str] = set()
    bucket_counts: dict[str, int] = {}
    diversified: list[SearchHit] = []

    for hit in hits:
        snippet_key = re.sub(r"\s+", " ", (hit.snippet or "")[:180].lower()).strip()
        if snippet_key and snippet_key in seen_snippets:
            continue
        if snippet_key:
            seen_snippets.add(snippet_key)

        bucket = hit.bucket or "unknown"
        cap = (bucket_caps or {}).get(bucket, max_per_bucket)
        if bucket_counts.get(bucket, 0) >= cap:
            continue
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
        diversified.append(hit)
        if len(diversified) >= limit:
            break

    if len(diversified) < limit:
        for hit in hits:
            if hit in diversified:
                continue
            snippet_key = re.sub(r"\s+", " ", (hit.snippet or "")[:180].lower()).strip()
            if snippet_key and snippet_key in seen_snippets:
                continue
            bucket = hit.bucket or "unknown"
            cap = (bucket_caps or {}).get(bucket, max_per_bucket)
            if bucket_counts.get(bucket, 0) >= cap:
                continue
            if snippet_key:
                seen_snippets.add(snippet_key)
            bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
            diversified.append(hit)
            if len(diversified) >= limit:
                break

    if min_research > 0 and bucket_counts.get("research", 0) < min_research:
        for hit in hits:
            if hit in diversified or hit.bucket != "research":
                continue
            diversified.append(hit)
            bucket_counts["research"] = bucket_counts.get("research", 0) + 1
            if bucket_counts.get("research", 0) >= min_research:
                break
    return diversified[:limit]


def _apply_intent_weights(hits: list["SearchHit"], intent: str | None) -> list["SearchHit"]:
    weights = INTENT_BUCKET_WEIGHTS.get(intent or "", BUCKET_WEIGHTS)
    for hit in hits:
        bucket_weight = weights.get(hit.bucket or "", BUCKET_WEIGHTS.get(hit.bucket or "", 1.0))
        base = BUCKET_WEIGHTS.get(hit.bucket or "", 1.0) or 1.0
        hit.score = hit.score * (bucket_weight / base)
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits

RESTRICTED_LEVELS = frozenset({"restricted", "confidential"})

LAB_QUERY_SYNONYMS: dict[str, list[str]] = {
    "cycif": ["tcycif", "t-cycif", "cyclic immunofluorescence"],
    "tcycif": ["cycif", "t-cycif"],
    "stardist": ["star dist", "cell segmentation"],
    "ashlar": ["stitching", "tile stitching"],
    "geomx": ["geo mx", "spatial transcriptomics"],
    "spacestat": ["space stat", "spatial statistics"],
    "gate": ["gating", "flow gating"],
    "protocol": ["sop", "standard operating procedure"],
    "wet lab": ["wetlab", "bench protocol"],
}

LAB_SUGGESTION_SEEDS: tuple[str, ...] = (
    "tCyCIF pipeline",
    "StarDist segmentation",
    "Ashlar stitching",
    "SPACEStat workflow",
    "GeoMx ROI selection",
    "Gate normalization",
    "wet lab protocol",
    "vault ingestion status",
    "notebook entry",
    "decision registry",
)


def _parse_scopes(raw: str | None) -> set[str]:
    if not raw:
        return set(DEFAULT_SCOPES)
    return {s.strip().lower() for s in raw.split(",") if s.strip()}


def _parse_project_codes(
    project_code: str | None,
    project_codes: str | None,
) -> list[str]:
    codes: list[str] = []
    if project_codes:
        codes.extend(c.strip() for c in project_codes.split(",") if c.strip())
    if project_code and project_code.strip():
        if project_code.strip() not in codes:
            codes.insert(0, project_code.strip())
    return codes


def _visibility_clause(include_restricted: bool, user_role: str | None) -> tuple[str, list[Any]]:
    if include_restricted or (user_role or "").lower() == "admin":
        return "", []
    return " AND COALESCE(ne.visibility_level, 'internal') NOT IN ('restricted', 'confidential')", []


def _expand_synonym_hints(query: str) -> list[str]:
    lower = (query or "").lower()
    hints: list[str] = []
    for key, alts in LAB_QUERY_SYNONYMS.items():
        if key in lower or any(alt.lower() in lower for alt in alts):
            for alt in alts:
                if alt.lower() not in lower and alt not in hints:
                    hints.append(alt)
        elif any(tok in key for tok in re.findall(r"[a-z0-9]{3,}", lower)):
            for alt in alts:
                if alt not in hints:
                    hints.append(alt)
    return hints[:6]


def _prefix_suggestions(query: str, *, limit: int = 8) -> list[str]:
    q = (query or "").strip().lower()
    if len(q) < 2:
        return list(LAB_SUGGESTION_SEEDS[:limit])
    return [seed for seed in LAB_SUGGESTION_SEEDS if q in seed.lower()][:limit]


def _highlight_tokens(query: str, text: str, max_hits: int = 3) -> list[str]:
    tokens = [t for t in re.findall(r"[a-z0-9\u00c0-\uffff]{3,}", (query or "").lower()) if t]
    if not tokens:
        return []
    lower = (text or "").lower()
    found = []
    for tok in tokens:
        idx = lower.find(tok)
        if idx >= 0:
            start = max(0, idx - 40)
            end = min(len(text), idx + len(tok) + 60)
            found.append(text[start:end].strip())
        if len(found) >= max_hits:
            break
    return found


def _build_search_filters(
    *,
    category: str | None = None,
    smart_chip: str | None = None,
    domain_tab: str | None = None,
    system_view: str | None = None,
    file_type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    indexed_status: str | None = None,
    filter_project_codes: str | None = None,
    filter_section_id: str | None = None,
    source_buckets: str | None = None,
    section_id: str | None = None,
    project_codes: str | None = None,
) -> SearchFilters:
    effective_section = filter_section_id or section_id
    effective_projects = filter_project_codes or project_codes
    return SearchFilters(
        category=category,
        smart_chip=smart_chip,
        domain_tab=domain_tab,
        system_view=system_view,
        file_type=file_type,
        date_from=date_from,
        date_to=date_to,
        indexed_status=indexed_status,
        project_codes=effective_projects,
        section_id=effective_section,
        source_buckets=source_buckets,
    )


def _resolve_filter_metadata(
    active_scopes: set[str],
    filters: SearchFilters,
) -> tuple[dict[str, str], list[str]]:
    active = filters.active_fields()
    if filters.source_buckets and not active.get("source_buckets"):
        active["source_buckets"] = filters.source_buckets
    unsupported: set[str] = set()
    for name, _val in active.items():
        if name == "source_buckets":
            continue
        supported_any = any(name in FILTER_SOURCE_SUPPORT.get(scope, frozenset()) for scope in active_scopes)
        if not supported_any:
            unsupported.add(name)
    applied = {k: v for k, v in active.items() if k not in unsupported and k != "source_buckets"}
    return applied, sorted(unsupported)


def _document_library_filter_dict(filters: SearchFilters) -> dict[str, Any]:
    dl: dict[str, Any] = {}
    if filters.category:
        dl["category"] = filters.category
    if filters.smart_chip:
        dl["smart_chip"] = filters.smart_chip
    if filters.file_type:
        dl["file_type"] = filters.file_type
    if filters.date_from:
        dl["modified_after"] = filters.date_from
    if filters.date_to:
        dl["modified_before"] = filters.date_to
    if filters.section_id:
        dl["section"] = filters.section_id
    if filters.project_codes:
        first = filters.project_codes.split(",")[0].strip()
        if first:
            dl["project"] = first
    return dl


def _document_library_system_view(filters: SearchFilters) -> str | None:
    if filters.system_view:
        return filters.system_view
    status = (filters.indexed_status or "").strip().lower()
    if status == "not_indexed":
        return "not_indexed"
    if status == "indexed":
        return "all_files"
    return None


def _row_matches_query(query: str, *parts: str | None) -> bool:
    tokens = [t for t in re.findall(r"[a-z0-9\u00c0-\uffff]{2,}", (query or "").lower()) if t]
    if not tokens:
        return True
    blob = " ".join(str(p or "") for p in parts).lower()
    return any(tok in blob for tok in tokens)


_CHECKSUM_DEDUPE_BUCKETS = frozenset({"vault", "file", "lab", "document_library"})


def _hit_asset_id(hit: SearchHit) -> str | None:
    meta = hit.metadata or {}
    aid = meta.get("asset_id")
    if aid:
        return str(aid)
    if hit.bucket == "vault":
        return str(hit.id)
    return None


def _suppress_checksum_duplicates(hits: list[SearchHit]) -> list[SearchHit]:
    """Keep the highest-scoring hit per checksum across vault/file/lab/document_library."""
    candidate_ids: list[str] = []
    for hit in hits:
        if hit.bucket not in _CHECKSUM_DEDUPE_BUCKETS:
            continue
        aid = _hit_asset_id(hit)
        if aid:
            candidate_ids.append(aid)

    assets = fetch_vault_assets_by_ids(list(dict.fromkeys(candidate_ids)))
    checksum_groups: dict[str, list[SearchHit]] = {}
    passthrough: list[SearchHit] = []

    for hit in hits:
        if hit.bucket not in _CHECKSUM_DEDUPE_BUCKETS:
            passthrough.append(hit)
            continue
        aid = _hit_asset_id(hit)
        checksum = ""
        if aid and aid in assets:
            checksum = (assets[aid].get("checksum_sha256") or "").strip()
        if not checksum:
            checksum = str((hit.metadata or {}).get("checksum_sha256") or "").strip()
        if not checksum:
            passthrough.append(hit)
            continue
        checksum_groups.setdefault(checksum, []).append(hit)

    kept: list[SearchHit] = list(passthrough)
    for group in checksum_groups.values():
        kept.append(max(group, key=lambda h: h.score))
    kept.sort(key=lambda h: h.score, reverse=True)
    return kept


def search_document_library(
    query: str,
    *,
    filters: SearchFilters,
    limit: int,
    seen_paths: set[str],
    seen_ids: set[str],
) -> list[SearchHit]:
    """Faceted document library search — logical_path only, deduped against vault/file."""
    dl_filters = _document_library_filter_dict(filters)
    system_view = _document_library_system_view(filters)
    if (filters.indexed_status or "").strip().lower() == "indexed":
        dl_filters.setdefault("digitalization_status", "indexed")

    result = search_document_library_rows(
        q=query,
        domain_tab=filters.domain_tab,
        system_view=system_view,
        filters=dl_filters,
        limit=limit,
    )
    hits: list[SearchHit] = []
    for item in result.get("items") or []:
        asset_id = str(item.get("asset_id") or "")
        logical_path = (item.get("logical_path") or "").strip()
        if not logical_path or logical_path in seen_paths or asset_id in seen_ids:
            continue
        seen_paths.add(logical_path)
        if asset_id:
            seen_ids.add(asset_id)
        title = item.get("display_title") or item.get("title") or item.get("filename") or logical_path.split("/")[-1]
        excerpt = item.get("processed_excerpt") or item.get("subtitle") or ""
        snippet = (excerpt or f"Document library entry — {logical_path}")[:1200]
        confidence = item.get("metadata_score") or item.get("assignment_confidence")
        hits.append(
            SearchHit(
                id=f"dl-{asset_id or logical_path}",
                bucket="document_library",
                title=title,
                snippet=snippet,
                score=min(1.0, 0.5 + float(item.get("metadata_score") or 0) / 200.0) * BUCKET_WEIGHTS["document_library"],
                source=hit_source_label("document_library"),
                project_code=item.get("project_hint"),
                section_id=item.get("section_hint"),
                relative_path=logical_path,
                highlights=_highlight_tokens(query, snippet),
                nav=nav_for_bucket("document_library", relative_path=logical_path or None),
                metadata={
                    "smart_chip": item.get("smart_chip"),
                    "domain_tab": filters.domain_tab or item.get("domain"),
                    "system_view": system_view,
                    "indexed_status": "indexed" if item.get("indexed_in_search") else "not_indexed",
                    "confidence": confidence,
                    "logical_path": logical_path,
                    "category": item.get("category"),
                    "file_type": item.get("file_type"),
                },
            )
        )
    return hits[:limit]


def search_vault_review(
    query: str,
    *,
    filters: SearchFilters,
    limit: int,
) -> list[SearchHit]:
    """Safe vault review queue hits — suggestions only, no original paths."""
    hits: list[SearchHit] = []
    queue_specs = (
        ("low_confidence", "low_confidence", "Review low-confidence vault classification"),
        ("uncategorized", "uncategorized", "Review uncategorized vault asset"),
        ("failed", "failed_extraction", "Review failed text extraction"),
    )
    for queue_name, review_reason, suggestion in queue_specs:
        for row in review_queue(limit=limit, queue=queue_name):
            logical_path = (row.get("logical_path") or "").strip()
            filename = row.get("filename") or logical_path.split("/")[-1]
            if not _row_matches_query(query, filename, logical_path, row.get("domain"), row.get("section_hint")):
                continue
            if filters.project_codes:
                codes = {c.strip().lower() for c in filters.project_codes.split(",") if c.strip()}
                if codes and (row.get("project_hint") or "").lower() not in codes:
                    continue
            if (filters.indexed_status or "").strip().lower() == "indexed" and not row.get("indexed_at"):
                continue
            if (filters.indexed_status or "").strip().lower() == "not_indexed" and row.get("indexed_at"):
                continue
            snippet = (
                f"{suggestion}: {filename}. "
                f"Confidence {float(row.get('assignment_confidence') or 0):.2f}; "
                f"status {row.get('review_status') or 'pending'}."
            )[:1200]
            hits.append(
                SearchHit(
                    id=f"vr-{row.get('asset_id') or logical_path}",
                    bucket="vault_review",
                    title=filename or "Vault review item",
                    snippet=snippet,
                    score=0.68 * BUCKET_WEIGHTS["vault_review"],
                    source=hit_source_label("vault_review"),
                    project_code=row.get("project_hint"),
                    section_id=row.get("section_hint"),
                    relative_path=logical_path or None,
                    highlights=_highlight_tokens(query, snippet),
                    nav=nav_for_bucket("vault_review", relative_path=logical_path or None),
                    metadata={
                        "review_reason": review_reason,
                        "suggestion": suggestion,
                        "assignment_confidence": row.get("assignment_confidence"),
                        "review_status": row.get("review_status"),
                        "extraction_status": row.get("extraction_status"),
                        "vector_status": row.get("vector_status"),
                        "indexed_status": "indexed" if row.get("indexed_at") else "not_indexed",
                        "action": "review_suggested",
                    },
                )
            )
            if len(hits) >= limit:
                return hits[:limit]

    if (filters.indexed_status or "").strip().lower() in {"", "not_indexed"}:
        for row in review_queue(limit=limit, queue="low_confidence"):
            if row.get("indexed_at") or row.get("vector_status") == "indexed":
                continue
            logical_path = (row.get("logical_path") or "").strip()
            filename = row.get("filename") or logical_path.split("/")[-1]
            if not _row_matches_query(query, filename, logical_path):
                continue
            snippet = f"Not indexed in search: {filename}. Suggest indexing or re-ingestion."[:1200]
            hits.append(
                SearchHit(
                    id=f"vr-ni-{row.get('asset_id') or logical_path}",
                    bucket="vault_review",
                    title=filename or "Not indexed asset",
                    snippet=snippet,
                    score=0.62 * BUCKET_WEIGHTS["vault_review"],
                    source=hit_source_label("vault_review"),
                    project_code=row.get("project_hint"),
                    relative_path=logical_path or None,
                    metadata={
                        "review_reason": "not_indexed",
                        "suggestion": "Consider indexing or re-ingesting this asset",
                        "action": "review_suggested",
                    },
                )
            )
            if len(hits) >= limit:
                return hits[:limit]

    dup_report = deduplication_report(limit=max(5, limit // 2))
    for group in dup_report.get("groups") or []:
        paths = group.get("logical_paths") or []
        if not paths:
            continue
        label = ", ".join(paths[:3])
        if not _row_matches_query(query, label):
            continue
        snippet = (
            f"Duplicate candidate group ({group.get('count', 0)} files). "
            f"Review duplicates before merging — suggestion only."
        )[:1200]
        hits.append(
            SearchHit(
                id=f"vr-dup-{group.get('checksum_sha256', '')[:12]}",
                bucket="vault_review",
                title=f"Duplicate group ({group.get('count', 0)} files)",
                snippet=snippet,
                score=0.58 * BUCKET_WEIGHTS["vault_review"],
                source=hit_source_label("vault_review"),
                metadata={
                    "review_reason": "duplicate",
                    "logical_paths": paths[:5],
                    "suggestion": "Review duplicate candidates — no automatic merge or delete",
                    "action": "review_suggested",
                },
            )
        )
        if len(hits) >= limit:
            break
    return hits[:limit]


def _post_filter_hits(hits: list[SearchHit], filters: SearchFilters, applied: dict[str, str]) -> list[SearchHit]:
    """Apply conservative AND filters to hits from sources with partial support."""
    if not applied:
        return hits
    out: list[SearchHit] = []
    for hit in hits:
        if applied.get("file_type"):
            ft = (hit.metadata or {}).get("file_type") or (hit.relative_path or "").split(".")[-1]
            if ft and ft.lower() != applied["file_type"].lower():
                continue
        if applied.get("section_id") and hit.section_id and hit.section_id != applied["section_id"]:
            continue
        if applied.get("project_codes"):
            codes = {c.strip() for c in applied["project_codes"].split(",") if c.strip()}
            if codes and hit.project_code and hit.project_code not in codes:
                continue
        out.append(hit)
    return out


class SearchService:
    def __init__(
        self,
        *,
        db_conn: str,
        qdrant: QdrantClient | None = None,
        llm: LLMClient | None = None,
    ) -> None:
        self.db_conn = db_conn
        self.qdrant = qdrant
        self.llm = llm

    def unified_search(
        self,
        q: str,
        *,
        scopes: str | None = None,
        project_code: str | None = None,
        project_codes: str | None = None,
        section_id: str | None = None,
        page_domain_id: str | None = None,
        mode: SearchMode = "hybrid",
        limit: int = 25,
        offset: int = 0,
        include_restricted: bool = False,
        explain: bool = False,
        user_role: str | None = None,
        user_email: str | None = None,
        category: str | None = None,
        smart_chip: str | None = None,
        domain_tab: str | None = None,
        system_view: str | None = None,
        file_type: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        indexed_status: str | None = None,
        filter_project_codes: str | None = None,
        filter_section_id: str | None = None,
        source_buckets: str | None = None,
    ) -> UnifiedSearchResponse:
        started = time.monotonic()
        query = (q or "").strip()
        if len(query) < 2:
            return UnifiedSearchResponse(query=query, mode=mode, scopes=[], limit=limit, offset=offset)

        search_filters = _build_search_filters(
            category=category,
            smart_chip=smart_chip,
            domain_tab=domain_tab,
            system_view=system_view,
            file_type=file_type,
            date_from=date_from,
            date_to=date_to,
            indexed_status=indexed_status,
            filter_project_codes=filter_project_codes,
            filter_section_id=filter_section_id,
            source_buckets=source_buckets,
            section_id=section_id,
            project_codes=project_codes,
        )
        effective_scopes = source_buckets or scopes
        active_scopes = _parse_scopes(effective_scopes)
        codes = _parse_project_codes(project_code, search_filters.project_codes or project_codes)
        if search_filters.section_id and not section_id:
            section_id = search_filters.section_id
        filters_applied, unsupported_filters = _resolve_filter_metadata(active_scopes, search_filters)

        cache_key = make_cache_key(
            query=query,
            scopes=effective_scopes,
            mode=mode,
            user_id=user_email,
            user_role=user_role,
            project_codes=codes,
            filters=filters_applied,
            include_restricted=include_restricted,
        )
        if should_cache(include_restricted=include_restricted, user_role=user_role):
            cached = get_cached(cache_key)
            if cached:
                cached["metadata"] = {**(cached.get("metadata") or {}), "cache_hit": True, "cache_key": cache_key}
                return UnifiedSearchResponse(**cached)
        per_bucket = max(3, min(limit, 50))
        raw_hits: list[SearchHit] = []
        explain_data: dict[str, Any] = {"engines": []} if explain else {}

        run_semantic = mode in ("semantic", "hybrid")
        run_keyword = mode in ("keyword", "hybrid", "exact")
        vault_domain = vault_domain_for_page(page_domain_id)

        if "lab" in active_scopes and run_semantic:
            for hit in search_lab_knowledge(
                query,
                section_id=section_id,
                limit=per_bucket,
                qdrant=self.qdrant,
                llm=self.llm,
            ):
                sid = hit.get("section_id")
                rel = hit.get("relative_path") or ""
                bucket: str = "lab"
                raw_hits.append(
                    SearchHit(
                        id=str(hit.get("chunk_uid") or hit.get("document_code") or rel or hit.get("title")),
                        bucket=bucket,
                        title=hit.get("title") or "Lab document",
                        snippet=(hit.get("excerpt") or "")[:1200],
                        score=float(hit.get("score") or 0.0) * BUCKET_WEIGHTS["lab"],
                        source=hit_source_label("lab", section_label=hit.get("section_label")),
                        source_type=hit.get("source_type"),
                        section_id=sid,
                        page_domain_id=page_domain_id,
                        document_code=hit.get("document_code"),
                        relative_path=rel or None,
                        highlights=_highlight_tokens(query, hit.get("excerpt") or ""),
                        nav=nav_for_bucket("lab", section_id=sid, relative_path=rel or None),
                        metadata={
                            "where_to_find": hit.get("where_to_find"),
                            "citation": hit.get("citation"),
                            "corpus": hit.get("corpus"),
                        },
                    )
                )
            if explain:
                explain_data["engines"].append({"scope": "lab", "engine": "qdrant+postgres", "count": len(raw_hits)})

        if "lab" in active_scopes and run_keyword:
            fts_before = len(raw_hits)
            seen_lab_ids = {h.id for h in raw_hits if h.bucket == "lab"}
            for fts in search_chunks_fts(query, section_id=section_id, limit=per_bucket):
                chunk_uid = fts.get("chunk_uid") or ""
                if chunk_uid in seen_lab_ids:
                    continue
                meta = fts.get("metadata") or {}
                sid = meta.get("section_id")
                rel = meta.get("relative_path") or ""
                raw_hits.append(
                    SearchHit(
                        id=str(chunk_uid or fts.get("document_code")),
                        bucket="lab",
                        title=fts.get("title") or "Lab document",
                        snippet=(fts.get("chunk_text") or "")[:1200],
                        score=float(fts.get("score") or 0.0) * BUCKET_WEIGHTS["lab"] * 1.1,
                        source=hit_source_label("lab"),
                        section_id=sid,
                        document_code=fts.get("document_code"),
                        relative_path=rel or None,
                        highlights=_highlight_tokens(query, fts.get("chunk_text") or ""),
                        nav=nav_for_bucket("lab", section_id=sid, relative_path=rel or None),
                        metadata={"engine": "postgres_fts", "corpus": meta.get("corpus")},
                    )
                )
                seen_lab_ids.add(chunk_uid)
            if explain:
                explain_data["engines"].append({
                    "scope": "lab",
                    "engine": "postgres_fts",
                    "count": len(raw_hits) - fts_before,
                })

        if "file" in active_scopes and run_keyword:
            file_before = len(raw_hits)
            for chunk in search_section_chunks(query, section_id=section_id, limit=per_bucket):
                sid = chunk.get("section_id")
                rel = chunk.get("source_file") or chunk.get("relative_path") or ""
                text = chunk.get("text") or chunk.get("excerpt") or ""
                source_type = chunk.get("source_type") or chunk.get("corpus") or ""
                is_lab_corpus = (
                    str(source_type).startswith("lab")
                    or (sid or "").startswith("overview")
                    or (sid or "").startswith("wet_lab")
                )
                bucket = "lab" if is_lab_corpus else "file"
                weight = BUCKET_WEIGHTS[bucket]
                score = min(1.0, float(chunk.get("score") or 3) / 12.0) * weight
                title = rel.split("/")[-1] if rel else chunk.get("section_label") or "Document"
                raw_hits.append(
                    SearchHit(
                        id=f"{bucket}-{sid}-{chunk.get('chunk_id') or rel}",
                        bucket=bucket,
                        title=title,
                        snippet=text[:1200],
                        score=score,
                        source=hit_source_label(bucket, section_label=chunk.get("section_label")),
                        source_type=source_type or None,
                        section_id=sid,
                        relative_path=rel or None,
                        highlights=_highlight_tokens(query, text),
                        nav=nav_for_bucket(bucket, section_id=sid, relative_path=rel or None),
                        metadata={"chunk_id": chunk.get("chunk_id")},
                    )
                )
            if explain:
                explain_data["engines"].append({"scope": "file", "engine": "processed_json", "count": len(raw_hits) - file_before})

        seen_paths: set[str] = set()
        seen_asset_ids: set[str] = set()
        for hit in raw_hits:
            if hit.relative_path:
                seen_paths.add(hit.relative_path)
            if hit.bucket in ("vault", "file", "lab") and hit.id:
                seen_asset_ids.add(hit.id)

        if "document_library" in active_scopes and run_keyword:
            dl_before = len(raw_hits)
            raw_hits.extend(
                search_document_library(
                    query,
                    filters=search_filters,
                    limit=per_bucket,
                    seen_paths=seen_paths,
                    seen_ids=seen_asset_ids,
                )
            )
            if explain:
                explain_data["engines"].append({
                    "scope": "document_library",
                    "engine": "document_library_service",
                    "count": len(raw_hits) - dl_before,
                })

        if "vault" in active_scopes and run_keyword:
            vault_before = len(raw_hits)
            vault_limit = per_bucket if mode != "exact" else per_bucket * 2
            vault_review_status = None
            if (search_filters.indexed_status or "").strip().lower() == "not_indexed":
                vault_review_status = "raw"
            vault_rows: list[dict[str, Any]] = []
            for row in search_vault(
                query,
                domain=vault_domain,
                project_hint=codes[0] if codes else None,
                limit=vault_limit,
                review_status=vault_review_status,
            ):
                vault_rows.append(row)
            if run_semantic:
                try:
                    from omeia.api.platform_flags import vectorization_enabled
                    from omeia.api.vault_vector_search import search_vault_vectors

                    if vectorization_enabled():
                        semantic = search_vault_vectors(
                            query, limit=vault_limit, qdrant=self.qdrant, llm=self.llm
                        )
                        seen_assets = {str(r.get("asset_id") or "") for r in vault_rows}
                        for sh in semantic:
                            aid = str(sh.get("asset_id") or "")
                            if aid and aid in seen_assets:
                                continue
                            vault_rows.append({
                                "asset_id": aid,
                                "filename": sh.get("filename"),
                                "logical_path": sh.get("logical_path"),
                                "checksum_sha256": sh.get("checksum_sha256"),
                                "review_status": sh.get("review_status"),
                                "vector_status": sh.get("vector_status"),
                                "page_domain_id": sh.get("page_domain_id"),
                                "project_hint": sh.get("project_hint"),
                                "metadata_preview": {"excerpt": sh.get("excerpt")},
                                "_semantic_score": sh.get("score"),
                            })
                            if aid:
                                seen_assets.add(aid)
                        if explain:
                            explain_data["engines"].append({
                                "scope": "vault",
                                "engine": "qdrant_semantic",
                                "count": len(semantic),
                            })
                except Exception as exc:
                    LOGGER.debug("Vault semantic merge skipped: %s", exc)
            for row in vault_rows:
                rel = row.get("logical_path") or row.get("filename") or ""
                if rel:
                    seen_paths.add(rel)
                asset_key = str(row.get("asset_id") or row.get("vault_id") or rel)
                if asset_key:
                    seen_asset_ids.add(asset_key)
                title = row.get("filename") or rel.split("/")[-1] or "Vault asset"
                excerpt = (row.get("metadata_preview") or {}).get("excerpt") or row.get("excerpt") or ""
                snippet = (excerpt or f"Vault asset in {row.get('page_domain_id') or 'lab storage'}")[:1200]
                base_score = 0.72
                if row.get("_semantic_score") is not None:
                    base_score = 0.72 + float(row["_semantic_score"]) * 0.28
                raw_hits.append(
                    SearchHit(
                        id=str(row.get("asset_id") or row.get("vault_id") or rel),
                        bucket="vault",
                        title=title,
                        snippet=snippet,
                        score=base_score * BUCKET_WEIGHTS["vault"],
                        source=hit_source_label("vault"),
                        page_domain_id=row.get("page_domain_id"),
                        project_code=row.get("project_hint"),
                        relative_path=rel or None,
                        highlights=_highlight_tokens(query, snippet),
                        nav=nav_for_bucket("vault", relative_path=rel or None),
                        metadata={
                            "asset_id": row.get("asset_id"),
                            "checksum_sha256": row.get("checksum_sha256"),
                            "review_status": row.get("review_status"),
                            "vector_status": row.get("vector_status"),
                            "domain": row.get("domain"),
                            "semantic": row.get("_semantic_score") is not None,
                        },
                    )
                )
            if explain:
                explain_data["engines"].append({"scope": "vault", "engine": "postgres_metadata", "count": len(raw_hits) - vault_before})

        if "vault_review" in active_scopes and run_keyword:
            vr_before = len(raw_hits)
            raw_hits.extend(search_vault_review(query, filters=search_filters, limit=per_bucket))
            if explain:
                explain_data["engines"].append({
                    "scope": "vault_review",
                    "engine": "raw_vault_review_queue",
                    "count": len(raw_hits) - vr_before,
                })

        if run_keyword:
            registry_hits = self._search_registry(
                query,
                scopes=active_scopes,
                project_codes=codes,
                limit=per_bucket,
                include_restricted=include_restricted,
                user_role=user_role,
            )
            raw_hits.extend(registry_hits)
            if explain:
                explain_data["engines"].append({"scope": "registry", "engine": "postgres_ilike", "count": len(registry_hits)})

        if "project" in active_scopes and run_keyword:
            proj_before = len(raw_hits)
            raw_hits.extend(self._search_projects(query, codes, limit=per_bucket))
            if explain:
                explain_data["engines"].append({"scope": "project", "engine": "postgres_ilike", "count": len(raw_hits) - proj_before})

        if "people" in active_scopes and run_keyword:
            people_before = len(raw_hits)
            for raw in search_people(query, limit=per_bucket):
                raw_hits.append(
                    SearchHit(
                        id=f"people-{raw.get('id')}",
                        bucket="people",
                        title=raw.get("title") or "Lab member",
                        snippet=(raw.get("snippet") or "")[:1200],
                        score=float(raw.get("score") or 0.0) * BUCKET_WEIGHTS["people"],
                        source=hit_source_label("people"),
                        source_type=raw.get("source_type"),
                        highlights=_highlight_tokens(query, raw.get("snippet") or ""),
                        nav=SearchNavAction(main="overview", sub="personnel", query=raw.get("username")),
                        metadata={
                            "username": raw.get("username"),
                            "role": raw.get("role"),
                            "email": raw.get("email"),
                            "profile_url": raw.get("profile_url"),
                        },
                    )
                )
            if explain:
                explain_data["engines"].append({"scope": "people", "engine": "lab_people_index", "count": len(raw_hits) - people_before})

        if "research" in active_scopes and (run_semantic or run_keyword):
            rk_before = len(raw_hits)
            rk_result = search_research(
                query,
                limit=per_bucket,
                qdrant=self.qdrant,
                llm=self.llm,
            )
            for raw in rk_result.get("hits") or []:
                nav_data = raw.get("nav") or {}
                raw_hits.append(
                    SearchHit(
                        id=str(raw.get("id") or raw.get("title")),
                        bucket="research",
                        title=raw.get("title") or "Research source",
                        snippet=(raw.get("snippet") or "")[:1200],
                        score=float(raw.get("score") or 0.0) * BUCKET_WEIGHTS["research"],
                        source=hit_source_label("research"),
                        source_type=raw.get("source_type"),
                        highlights=_highlight_tokens(query, raw.get("snippet") or ""),
                        nav=SearchNavAction(
                            main=nav_data.get("main", "ai_assistant"),
                            sub=nav_data.get("sub", "research_kb"),
                            query=query,
                        ),
                        metadata={
                            "source_url": raw.get("source_url"),
                            "doi": raw.get("doi"),
                            "pmid": raw.get("pmid"),
                            "dataset_accession": raw.get("dataset_accession"),
                        },
                    )
                )
            if explain:
                explain_data["engines"].append({"scope": "research", "engine": "qdrant+postgres", "count": len(raw_hits) - rk_before})

        if run_semantic and ("file" in active_scopes or "project" in active_scopes):
            pw_sem_before = len(raw_hits)
            seen_pw = {h.id for h in raw_hits if h.bucket == "file"}
            for hit in search_project_knowledge(
                query,
                project_codes=codes,
                limit=per_bucket,
                qdrant=self.qdrant,
                llm=self.llm,
            ):
                chunk_uid = hit.get("chunk_uid") or ""
                if chunk_uid in seen_pw:
                    continue
                seen_pw.add(chunk_uid)
                code = hit.get("project_code") or ""
                rel = hit.get("relative_path") or ""
                raw_hits.append(
                    SearchHit(
                        id=str(chunk_uid or hit.get("document_code")),
                        bucket="file",
                        title=hit.get("title") or "Project document",
                        snippet=(hit.get("excerpt") or "")[:1200],
                        score=float(hit.get("score") or 0.0) * BUCKET_WEIGHTS["file"] * 1.15,
                        source=f"Project workspace · {code}" if code else "Project workspace",
                        project_code=code or None,
                        relative_path=rel or None,
                        highlights=_highlight_tokens(query, hit.get("excerpt") or ""),
                        nav=nav_for_bucket("file", project_code=code or None, relative_path=rel or None),
                        metadata={"corpus": "project_workspace", "workspace": True, "engine": "qdrant"},
                    )
                )
            if explain:
                explain_data["engines"].append({
                    "scope": "project_workspace",
                    "engine": "qdrant+postgres",
                    "count": len(raw_hits) - pw_sem_before,
                })

        if run_keyword and ("file" in active_scopes or "project" in active_scopes):
            pw_before = len(raw_hits)
            raw_hits.extend(self._search_project_workspace_files(query, codes, limit=per_bucket))
            if explain:
                explain_data["engines"].append({
                    "scope": "project_files",
                    "engine": "processed_twin_json",
                    "count": len(raw_hits) - pw_before,
                })

        raw_hits = _post_filter_hits(raw_hits, search_filters, filters_applied)
        raw_hits = _suppress_checksum_duplicates(raw_hits)

        # Deduplicate by id+bucket, sort by score desc
        seen: set[str] = set()
        merged: list[SearchHit] = []
        for hit in sorted(raw_hits, key=lambda h: h.score, reverse=True):
            key = f"{hit.bucket}:{hit.id}"
            if key in seen:
                continue
            seen.add(key)
            merged.append(hit)

        total = len(merged)
        page = merged[offset : offset + limit]
        for i, hit in enumerate(page, start=offset + 1):
            hit.rank = i

        buckets: dict[str, int] = {}
        for hit in merged:
            buckets[hit.bucket] = buckets.get(hit.bucket, 0) + 1

        suggestions = _prefix_suggestions(query, limit=6)
        synonym_hints = _expand_synonym_hints(query)

        response = UnifiedSearchResponse(
            query=query,
            mode=mode,
            scopes=sorted(active_scopes),
            project_code=codes[0] if codes else None,
            section_id=section_id,
            page_domain_id=page_domain_id,
            total=total,
            offset=offset,
            limit=limit,
            hits=page,
            buckets=buckets,
            suggestions=suggestions,
            synonym_hints=synonym_hints,
            explain=explain_data if explain else None,
            filters_applied=filters_applied,
            unsupported_filters=unsupported_filters,
            metadata={"cache_hit": False, "cache_key": cache_key},
        )
        if should_cache(
            include_restricted=include_restricted,
            user_role=user_role,
            hits=[h.model_dump() for h in merged],
        ):
            set_cached(cache_key, response.model_dump())
        self._log_query(
            query,
            mode=mode,
            scopes=scopes,
            project_code=codes[0] if codes else None,
            hit_count=total,
            user_email=user_email,
            user_role=user_role,
            duration_ms=int((time.monotonic() - started) * 1000),
        )
        return response

    def _search_registry(
        self,
        query: str,
        *,
        scopes: set[str],
        project_codes: list[str],
        limit: int,
        include_restricted: bool,
        user_role: str | None,
    ) -> list[SearchHit]:
        hits: list[SearchHit] = []
        pattern = f"%{query}%"
        vis_sql, vis_params = _visibility_clause(include_restricted, user_role)

        try:
            with psycopg.connect(self.db_conn, connect_timeout=8) as conn:
                with conn.cursor() as cur:
                    if "notebook" in scopes:
                        nb_sql = f"""
                            SELECT ne.entry_id::text, p.project_code, ne.title,
                                   LEFT(ne.content, 400), ne.entry_type, ne.visibility_level, ne.created_at
                            FROM platform.notebook_entry ne
                            JOIN core.project p ON ne.project_id = p.project_id
                            WHERE (ne.title ILIKE %s OR ne.content ILIKE %s){vis_sql}
                        """
                        params: list[Any] = [pattern, pattern, *vis_params]
                        if project_codes:
                            nb_sql += " AND p.project_code = ANY(%s)"
                            params.append(project_codes)
                        nb_sql += " ORDER BY ne.created_at DESC LIMIT %s;"
                        params.append(limit)
                        cur.execute(nb_sql, tuple(params))
                        for r in cur.fetchall():
                            excerpt = r[3] or ""
                            hits.append(
                                SearchHit(
                                    id=r[0],
                                    bucket="notebook",
                                    title=r[2] or "Notebook entry",
                                    snippet=excerpt[:1200],
                                    score=0.7 * BUCKET_WEIGHTS["notebook"],
                                    source=hit_source_label("notebook"),
                                    project_code=r[1],
                                    visibility_level=r[5],
                                    created_at=r[6].isoformat() if r[6] else None,
                                    highlights=_highlight_tokens(query, excerpt),
                                    nav=nav_for_bucket("notebook", project_code=r[1], entry_id=r[0]),
                                    metadata={"entry_type": r[4]},
                                )
                            )

                    if "wiki" in scopes:
                        w_sql = """
                            SELECT w.wiki_id::text, p.project_code, w.title,
                                   LEFT(w.content, 400), w.wiki_type, w.updated_at
                            FROM platform.research_wiki w
                            LEFT JOIN core.project p ON w.project_id = p.project_id
                            WHERE (w.title ILIKE %s OR w.content ILIKE %s)
                        """
                        w_params: list[Any] = [pattern, pattern]
                        if project_codes:
                            w_sql += " AND p.project_code = ANY(%s)"
                            w_params.append(project_codes)
                        w_sql += " ORDER BY w.updated_at DESC LIMIT %s;"
                        w_params.append(limit)
                        cur.execute(w_sql, tuple(w_params))
                        for r in cur.fetchall():
                            excerpt = r[3] or ""
                            hits.append(
                                SearchHit(
                                    id=r[0],
                                    bucket="wiki",
                                    title=r[2] or "Wiki page",
                                    snippet=excerpt[:1200],
                                    score=0.68 * BUCKET_WEIGHTS["wiki"],
                                    source=hit_source_label("wiki"),
                                    project_code=r[1],
                                    updated_at=r[5].isoformat() if r[5] else None,
                                    highlights=_highlight_tokens(query, excerpt),
                                    nav=nav_for_bucket("wiki", project_code=r[1], wiki_id=r[0]),
                                    metadata={"wiki_type": r[4]},
                                )
                            )

                    if "decision" in scopes:
                        d_sql = """
                            SELECT d.decision_id::text, p.project_code, d.title,
                                   LEFT(d.decision_details, 400), d.rationale, d.decision_date
                            FROM platform.decision_registry d
                            JOIN core.project p ON d.project_id = p.project_id
                            WHERE (d.title ILIKE %s OR d.decision_details ILIKE %s OR d.rationale ILIKE %s)
                        """
                        d_params: list[Any] = [pattern, pattern, pattern]
                        if project_codes:
                            d_sql += " AND p.project_code = ANY(%s)"
                            d_params.append(project_codes)
                        d_sql += " ORDER BY d.decision_date DESC LIMIT %s;"
                        d_params.append(limit)
                        cur.execute(d_sql, tuple(d_params))
                        for r in cur.fetchall():
                            excerpt = r[3] or ""
                            hits.append(
                                SearchHit(
                                    id=r[0],
                                    bucket="decision",
                                    title=r[2] or "Decision",
                                    snippet=excerpt[:1200],
                                    score=0.66 * BUCKET_WEIGHTS["decision"],
                                    source=hit_source_label("decision"),
                                    project_code=r[1],
                                    highlights=_highlight_tokens(query, excerpt),
                                    nav=nav_for_bucket("decision", project_code=r[1], decision_id=r[0]),
                                    metadata={"rationale": (r[4] or "")[:500], "decision_date": str(r[5])},
                                )
                            )

                    if "task" in scopes:
                        t_sql = """
                            SELECT t.task_id::text, p.project_code, t.title,
                                   LEFT(t.description, 400), t.status, r.full_name, t.due_date
                            FROM platform.task t
                            JOIN core.project p ON t.project_id = p.project_id
                            LEFT JOIN platform.researcher r ON t.assigned_to = r.researcher_id
                            WHERE (t.title ILIKE %s OR t.description ILIKE %s)
                        """
                        t_params: list[Any] = [pattern, pattern]
                        if project_codes:
                            t_sql += " AND p.project_code = ANY(%s)"
                            t_params.append(project_codes)
                        t_sql += " ORDER BY t.due_date DESC NULLS LAST LIMIT %s;"
                        t_params.append(limit)
                        cur.execute(t_sql, tuple(t_params))
                        for r in cur.fetchall():
                            excerpt = r[3] or ""
                            hits.append(
                                SearchHit(
                                    id=r[0],
                                    bucket="task",
                                    title=r[2] or "Task",
                                    snippet=excerpt[:1200],
                                    score=0.64 * BUCKET_WEIGHTS["task"],
                                    source=hit_source_label("task"),
                                    project_code=r[1],
                                    highlights=_highlight_tokens(query, excerpt),
                                    nav=nav_for_bucket("task", project_code=r[1], task_id=r[0]),
                                    metadata={
                                        "status": r[4],
                                        "assignee": r[5],
                                        "due_date": str(r[6]) if r[6] else None,
                                    },
                                )
                            )
        except Exception as exc:
            LOGGER.warning("Registry search failed: %s", exc)
        return hits

    def _search_projects(self, query: str, project_codes: list[str], *, limit: int) -> list[SearchHit]:
        hits: list[SearchHit] = []
        pattern = f"%{query}%"
        try:
            with psycopg.connect(self.db_conn, connect_timeout=8) as conn:
                with conn.cursor() as cur:
                    sql = """
                        SELECT project_code, project_name,
                               COALESCE(short_description, '') || ' ' || COALESCE(long_description, '') AS blurb
                        FROM core.project
                        WHERE (project_code ILIKE %s OR project_name ILIKE %s
                               OR short_description ILIKE %s OR long_description ILIKE %s)
                    """
                    params: list[Any] = [pattern, pattern, pattern, pattern]
                    if project_codes:
                        sql += " AND project_code = ANY(%s)"
                        params.append(project_codes)
                    sql += " ORDER BY project_code LIMIT %s;"
                    params.append(limit)
                    cur.execute(sql, tuple(params))
                    for r in cur.fetchall():
                        desc = (r[2] or "").strip()
                        hits.append(
                            SearchHit(
                                id=r[0],
                                bucket="project",
                                title=r[1] or r[0],
                                snippet=desc[:800] or f"Project workspace {r[0]}",
                                score=0.6 * BUCKET_WEIGHTS["project"],
                                source=hit_source_label("project"),
                                project_code=r[0],
                                highlights=_highlight_tokens(query, f"{r[1]} {desc}"),
                                nav=nav_for_bucket("project", project_code=r[0]),
                            )
                        )
        except Exception as exc:
            LOGGER.warning("Project search failed: %s", exc)
        return hits

    def _iter_processed_twin_codes(self) -> list[str]:
        seen: set[str] = set()
        codes: list[str] = []
        for base in (PROCESSED_DIR, PUBLIC_PROCESSED_DIR):
            if not base.is_dir():
                continue
            for path in sorted(base.glob("*.json")):
                if path.name.startswith("lab__"):
                    continue
                code = path.stem
                if code not in seen:
                    seen.add(code)
                    codes.append(code)
        return codes

    def _project_twin_summary_hit(self, code: str, query: str) -> SearchHit | None:
        twin = load_processed(code)
        if not twin:
            return None
        identity = twin.get("identity") or {}
        name = identity.get("project_name") or code
        summary = (identity.get("project_summary") or "").strip()
        research_q = (identity.get("research_question") or "").strip()
        if research_q and research_q.lower() != summary.lower():
            blurb = f"{summary}\n\nResearch focus: {research_q}" if summary else research_q
        else:
            blurb = summary
        if not blurb:
            metrics = twin.get("metrics") or {}
            blurb = (
                f"Lab project {name} — "
                f"{metrics.get('document_count', 0)} documents, "
                f"{metrics.get('timeline_entries', 0)} timeline entries."
            )
        return SearchHit(
            id=f"pw-summary-{code}",
            bucket="file",
            title=f"{name} project overview",
            snippet=blurb[:1200],
            score=0.95 * BUCKET_WEIGHTS["file"],
            source=f"Project workspace · {code}",
            project_code=code,
            highlights=_highlight_tokens(query, blurb),
            nav=SearchNavAction(main="projects_data", sub="portfolio", project_code=code),
            metadata={"workspace": True, "project_summary": True},
        )

    def _search_project_workspace_files(
        self,
        query: str,
        project_codes: list[str],
        *,
        limit: int,
    ) -> list[SearchHit]:
        """Keyword search over processed project twins (portable JSON — no remote storage required)."""
        tokens = [t for t in re.findall(r"[a-z0-9\u00c0-\uffff]{3,}", (query or "").lower()) if t]
        available_codes = self._iter_processed_twin_codes()
        if not available_codes:
            return []

        query_code = detect_project_code(query)
        hits: list[SearchHit] = []

        if query_code:
            summary_hit = self._project_twin_summary_hit(query_code, query)
            if summary_hit:
                hits.append(summary_hit)

        for code in available_codes:
            if project_codes and code not in project_codes:
                continue
            twin = load_processed(code)
            if not twin:
                continue
            for doc in twin.get("document_index") or []:
                rel = (doc.get("path") or "").replace("\\", "/")
                blob = " ".join(
                    str(doc.get(k) or "") for k in ("path", "title", "name", "excerpt", "extension")
                ).lower()
                score = sum(2 if tok in blob else 0 for tok in tokens)
                if score <= 0:
                    continue
                title = doc.get("title") or doc.get("name") or rel.split("/")[-1] or code
                excerpt = (doc.get("excerpt") or "")[:1200]
                hits.append(
                    SearchHit(
                        id=f"pw-{code}-{rel}",
                        bucket="file",
                        title=title,
                        snippet=excerpt or f"Project file in {code}",
                        score=min(1.0, score / 10.0) * BUCKET_WEIGHTS["file"],
                        source=f"Project workspace · {code}",
                        project_code=code,
                        relative_path=rel or None,
                        highlights=_highlight_tokens(query, blob),
                        nav=SearchNavAction(
                            main="projects_data",
                            sub="portfolio",
                            project_code=code,
                            relative_path=rel or None,
                        ),
                        metadata={"workspace": True},
                    )
                )
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:limit]

    def _log_query(
        self,
        query: str,
        *,
        mode: str,
        scopes: str | None,
        project_code: str | None,
        hit_count: int,
        user_email: str | None,
        user_role: str | None,
        duration_ms: int,
    ) -> None:
        try:
            with psycopg.connect(self.db_conn, connect_timeout=4) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO platform.search_query_log (
                            query_text, mode, scopes, project_code, hit_count,
                            user_email, user_role, duration_ms
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                        """,
                        (
                            query[:500],
                            mode,
                            scopes,
                            project_code,
                            hit_count,
                            user_email,
                            user_role,
                            duration_ms,
                        ),
                    )
                conn.commit()
        except Exception as exc:
            LOGGER.debug("Search query log skipped (table may not exist yet): %s", exc)

    def search_suggestions(
        self,
        q: str = "",
        *,
        user_email: str | None = None,
        limit: int = 8,
    ) -> dict[str, Any]:
        """Prefix suggestions, synonym hints, and recent queries from the log."""
        query = (q or "").strip()
        suggestions = _prefix_suggestions(query, limit=limit)
        synonym_hints = _expand_synonym_hints(query) if query else []
        recent: list[str] = []
        try:
            with psycopg.connect(self.db_conn, connect_timeout=4) as conn:
                with conn.cursor() as cur:
                    if user_email:
                        cur.execute(
                            """
                            SELECT query_text
                            FROM (
                                SELECT query_text, max(created_at) AS last_at
                                FROM platform.search_query_log
                                WHERE user_email = %s
                                  AND length(query_text) >= 2
                                GROUP BY query_text
                            ) recent
                            ORDER BY last_at DESC
                            LIMIT %s;
                            """,
                            (user_email, limit),
                        )
                    else:
                        cur.execute(
                            """
                            SELECT query_text
                            FROM (
                                SELECT query_text, max(created_at) AS last_at
                                FROM platform.search_query_log
                                WHERE length(query_text) >= 2
                                GROUP BY query_text
                            ) recent
                            ORDER BY last_at DESC
                            LIMIT %s;
                            """,
                            (limit,),
                        )
                    recent = [r[0] for r in cur.fetchall() if r and r[0]]
        except Exception as exc:
            LOGGER.debug("Search suggestions log skipped: %s", exc)
        return {
            "query": query,
            "suggestions": suggestions,
            "synonym_hints": synonym_hints,
            "recent_queries": recent,
        }

    def index_status(self) -> dict[str, Any]:
        """Portable index freshness — works with stub storage + optional Qdrant/Postgres."""
        storage = storage_roots()
        lab_stats = get_lab_index_stats()
        return {
            "storage": storage,
            "lab_index": lab_stats,
            "search_endpoint": "/api/platform/unified-search",
            "fallback_chain": ["qdrant_semantic", "postgres_rag", "processed_json", "vault_metadata"],
            "portable": True,
        }

    def search_project_files(
        self,
        query: str,
        *,
        project_code: str | None = None,
        limit: int = 20,
    ) -> list[SearchHit]:
        codes = [project_code] if project_code else []
        return self._search_project_workspace_files(query, codes, limit=limit)

    def hits_for_copilot(
        self,
        query: str,
        *,
        intent: str | None = None,
        project_codes: list[str] | None = None,
        limit: int = 12,
        prioritize_buckets: tuple[str, ...] | list[str] | None = None,
        parallel_scopes: bool | None = None,
        user_role: str | None = None,
        include_restricted: bool | None = None,
    ) -> list[SearchHit]:
        """Intent-aware retrieval for chat/ask — rerank, gate, dedup, diversify."""
        codes = ",".join(project_codes) if project_codes else None
        scopes = INTENT_SCOPES.get(intent or "", "lab,file,vault,notebook,wiki,research,people")
        fetch_limit = max(limit * 3, 24)
        allow_restricted = _copilot_include_restricted(user_role, include_restricted=include_restricted)
        min_score = copilot_min_score(intent)

        cache_key = make_copilot_cache_key(
            query=query,
            intent=intent,
            project_codes=project_codes,
            user_role=user_role,
            include_restricted=allow_restricted,
            limit=limit,
        )
        if should_cache(include_restricted=allow_restricted, user_role=user_role):
            cached_hits = get_copilot_cached(cache_key)
            if cached_hits:
                return [SearchHit(**h) for h in cached_hits[:limit]]
        resp = self.unified_search(
            query,
            scopes=scopes,
            project_codes=codes,
            mode="hybrid",
            limit=fetch_limit,
            include_restricted=allow_restricted,
            user_role=user_role,
        )
        hits = list(resp.hits)

        use_parallel = (
            parallel_scopes
            if parallel_scopes is not None
            else os.getenv("CHAT_PARALLEL_RETRIEVAL", "true").strip().lower() in {"1", "true", "yes", "on"}
        )
        priority_buckets = tuple(dict.fromkeys(prioritize_buckets or ()))
        if use_parallel and priority_buckets:
            per_scope_limit = max(6, limit)
            max_workers = min(4, len(priority_buckets))
            seen_keys = {f"{h.bucket}:{h.id}" for h in hits}

            def _fetch_bucket(bucket: str) -> list[SearchHit]:
                scope_resp = self.unified_search(
                    query,
                    scopes=bucket,
                    project_codes=codes,
                    mode="hybrid",
                    limit=per_scope_limit,
                    include_restricted=allow_restricted,
                    user_role=user_role,
                )
                return list(scope_resp.hits)

            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = {pool.submit(_fetch_bucket, bucket): bucket for bucket in priority_buckets[:max_workers]}
                for future in as_completed(futures):
                    try:
                        scoped_hits = future.result()
                    except Exception as exc:
                        LOGGER.warning("Parallel copilot scope fetch failed (%s): %s", futures[future], exc)
                        continue
                    for hit in scoped_hits:
                        key = f"{hit.bucket}:{hit.id}"
                        if key not in seen_keys:
                            seen_keys.add(key)
                            hits.append(hit)

        # Research-heavy intents: pull extra research hits so vault/file cannot crowd them out.
        if intent in RESEARCH_INTENTS or intent in PROJECT_INTENTS:
            research_query = query
            if intent in PROJECT_INTENTS:
                enriched = _project_research_query(query, project_codes)
                if enriched:
                    research_query = enriched
            rk_resp = self.unified_search(
                research_query,
                scopes="research",
                project_codes=codes,
                mode="hybrid",
                limit=max(8, limit),
                include_restricted=allow_restricted,
                user_role=user_role,
            )
            seen = {f"{h.bucket}:{h.id}" for h in hits}
            for hit in rk_resp.hits:
                key = f"{hit.bucket}:{hit.id}"
                if key not in seen:
                    seen.add(key)
                    hits.append(hit)

        hits = _apply_intent_weights(hits, intent)
        hits.sort(key=lambda h: h.score, reverse=True)
        research_pool = (
            [h for h in hits if h.bucket == "research"]
            if intent in RESEARCH_INTENTS or intent in PROJECT_INTENTS
            else []
        )
        lab_pool = [h for h in hits if h.bucket == "lab"] if intent in PROTOCOL_INTENTS else []
        project_pool = [h for h in hits if h.bucket in {"project", "file"}] if intent in PROJECT_INTENTS else []
        hits = cross_rerank_hits(query, hits, top_n=min(fetch_limit, 30))
        hits = [h for h in hits if h.score >= min_score]
        for pool in (research_pool, lab_pool, project_pool):
            seen = {f"{h.bucket}:{h.id}" for h in hits}
            for hit in pool:
                key = f"{hit.bucket}:{hit.id}"
                if key not in seen and hit.score >= min_score:
                    hits.append(hit)
                    seen.add(key)
        bucket_caps = INTENT_BUCKET_CAPS.get(intent or "", {})
        min_research = 2 if intent in RESEARCH_INTENTS else (2 if intent in PROJECT_INTENTS else 0)
        min_lab = 1 if intent in PROTOCOL_INTENTS else 0
        min_project = 2 if intent in PROJECT_INTENTS else 0

        if min_project:
            result = _reserve_bucket_slots(
                hits,
                bucket="file",
                min_count=min_project,
                limit=limit,
                bucket_caps=bucket_caps,
            )
            if [h for h in project_pool if h.bucket == "project"]:
                result = _reserve_bucket_slots(
                    result,
                    bucket="project",
                    min_count=1,
                    limit=limit,
                    bucket_caps=bucket_caps,
                )
            if min_research:
                result = _reserve_bucket_slots(
                    result,
                    bucket="research",
                    min_count=min_research,
                    limit=limit,
                    bucket_caps=bucket_caps,
                )
        elif min_research:
            result = _reserve_bucket_slots(
                hits,
                bucket="research",
                min_count=min_research,
                limit=limit,
                bucket_caps=bucket_caps,
            )
            if min_lab:
                result = _reserve_bucket_slots(
                    result,
                    bucket="lab",
                    min_count=min_lab,
                    limit=limit,
                    bucket_caps=bucket_caps,
                )
        elif min_lab:
            result = _reserve_bucket_slots(
                hits,
                bucket="lab",
                min_count=min_lab,
                limit=limit,
                bucket_caps=bucket_caps,
            )
        else:
            result = _dedup_and_diversify(
                hits,
                limit,
                max_per_bucket=4,
                bucket_caps=bucket_caps,
            )

        try:
            from omeia.api.platform_flags import continuous_learning_enabled
            from omeia.api.learning_retrieval_service import merge_learning_into_copilot_hits

            if continuous_learning_enabled():
                result = merge_learning_into_copilot_hits(query, result, learning_limit=max(2, limit // 3))
        except Exception as exc:
            LOGGER.debug("Learning retrieval merge skipped: %s", exc)

        if should_cache(include_restricted=allow_restricted, user_role=user_role):
            set_copilot_cached(cache_key, [h.model_dump() for h in result])
        return result
