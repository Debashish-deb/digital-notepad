"""Unified platform search — single service for UI and copilot retrieval."""
from __future__ import annotations

import logging
import re
import time
from typing import Any

import psycopg
from qdrant_client import QdrantClient

from app_skeleton.api.database_processor import search_section_chunks
from app_skeleton.api.paths import PROCESSED_DIR
from app_skeleton.api.project_processor import load_processed
from app_skeleton.api.storage_stub import storage_roots
from app_skeleton.api.lab_knowledge_store import get_lab_index_stats, search_lab_knowledge
from app_skeleton.api.llm_client import LLMClient
from app_skeleton.api.raw_vault_store import search_vault
from app_skeleton.api.search_models import SearchHit, SearchMode, SearchNavAction, UnifiedSearchResponse
from app_skeleton.api.research_knowledge_store import search_research
from app_skeleton.api.search_nav import hit_source_label, nav_for_bucket, vault_domain_for_page

LOGGER = logging.getLogger(__name__)

DEFAULT_SCOPES = ("lab", "file", "vault", "notebook", "wiki", "decision", "task", "project", "research")

BUCKET_WEIGHTS: dict[str, float] = {
    "lab": 1.0,
    "file": 0.95,
    "vault": 0.85,
    "notebook": 0.78,
    "wiki": 0.78,
    "decision": 0.76,
    "task": 0.74,
    "project": 0.65,
    "research": 0.92,
}

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
    ) -> UnifiedSearchResponse:
        started = time.monotonic()
        query = (q or "").strip()
        if len(query) < 2:
            return UnifiedSearchResponse(query=query, mode=mode, scopes=[], limit=limit, offset=offset)

        active_scopes = _parse_scopes(scopes)
        codes = _parse_project_codes(project_code, project_codes)
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

        if "file" in active_scopes and run_keyword:
            file_before = len(raw_hits)
            for chunk in search_section_chunks(query, section_id=section_id, limit=per_bucket):
                sid = chunk.get("section_id")
                rel = chunk.get("source_file") or chunk.get("relative_path") or ""
                text = chunk.get("text") or chunk.get("excerpt") or ""
                score = min(1.0, float(chunk.get("score") or 3) / 12.0) * BUCKET_WEIGHTS["file"]
                title = rel.split("/")[-1] if rel else chunk.get("section_label") or "Document"
                raw_hits.append(
                    SearchHit(
                        id=f"file-{sid}-{chunk.get('chunk_id') or rel}",
                        bucket="file",
                        title=title,
                        snippet=text[:1200],
                        score=score,
                        source=hit_source_label("file", section_label=chunk.get("section_label")),
                        section_id=sid,
                        relative_path=rel or None,
                        highlights=_highlight_tokens(query, text),
                        nav=nav_for_bucket("file", section_id=sid, relative_path=rel or None),
                        metadata={"chunk_id": chunk.get("chunk_id")},
                    )
                )
            if explain:
                explain_data["engines"].append({"scope": "file", "engine": "processed_json", "count": len(raw_hits) - file_before})

        if "vault" in active_scopes and run_keyword:
            vault_before = len(raw_hits)
            vault_limit = per_bucket if mode != "exact" else per_bucket * 2
            for row in search_vault(
                query,
                domain=vault_domain,
                project_hint=codes[0] if codes else None,
                limit=vault_limit,
            ):
                rel = row.get("logical_path") or row.get("filename") or ""
                title = row.get("filename") or rel.split("/")[-1] or "Vault asset"
                excerpt = (row.get("metadata_preview") or {}).get("excerpt") or row.get("excerpt") or ""
                snippet = (excerpt or f"Vault asset in {row.get('page_domain_id') or 'lab storage'}")[:1200]
                raw_hits.append(
                    SearchHit(
                        id=str(row.get("asset_id") or row.get("vault_id") or rel),
                        bucket="vault",
                        title=title,
                        snippet=snippet,
                        score=0.72 * BUCKET_WEIGHTS["vault"],
                        source=hit_source_label("vault"),
                        page_domain_id=row.get("page_domain_id"),
                        project_code=row.get("project_hint"),
                        relative_path=rel or None,
                        highlights=_highlight_tokens(query, snippet),
                        nav=nav_for_bucket("vault", relative_path=rel or None),
                        metadata={
                            "review_status": row.get("review_status"),
                            "vector_status": row.get("vector_status"),
                            "domain": row.get("domain"),
                        },
                    )
                )
            if explain:
                explain_data["engines"].append({"scope": "vault", "engine": "postgres_metadata", "count": len(raw_hits) - vault_before})

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

        if run_keyword and ("file" in active_scopes or "project" in active_scopes):
            pw_before = len(raw_hits)
            raw_hits.extend(self._search_project_workspace_files(query, codes, limit=per_bucket))
            if explain:
                explain_data["engines"].append({
                    "scope": "project_files",
                    "engine": "processed_twin_json",
                    "count": len(raw_hits) - pw_before,
                })

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
        )
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

    def _search_project_workspace_files(
        self,
        query: str,
        project_codes: list[str],
        *,
        limit: int,
    ) -> list[SearchHit]:
        """Keyword search over processed project twins (portable JSON — no remote storage required)."""
        tokens = [t for t in re.findall(r"[a-z0-9\u00c0-\uffff]{3,}", (query or "").lower()) if t]
        if not tokens or not PROCESSED_DIR.is_dir():
            return []

        hits: list[SearchHit] = []
        for path in sorted(PROCESSED_DIR.glob("*.json")):
            if path.name.startswith("lab__"):
                continue
            code = path.stem
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

    def hits_for_copilot(self, query: str, *, project_codes: list[str] | None = None, limit: int = 12) -> list[SearchHit]:
        """Shared retrieval path for /ask — same ranking as unified search."""
        codes = ",".join(project_codes) if project_codes else None
        resp = self.unified_search(
            query,
            scopes="lab,file,vault,notebook,wiki,research",
            project_codes=codes,
            mode="hybrid",
            limit=limit,
            include_restricted=False,
        )
        return resp.hits
