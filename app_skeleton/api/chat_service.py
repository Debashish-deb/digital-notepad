"""Gemini Research Copilot chat orchestration with unified-search RAG."""
from __future__ import annotations

import logging
import os
from typing import Any, Callable

from app_skeleton.api.answer_grounding_service import (
    SYSTEM_PROMPT as RESEARCH_SYSTEM_PROMPT,
    build_grounded_prompt,
    validate_answer_sources,
)
from app_skeleton.api.common import SourceInfo, _clinical_context_for_question, query_postgres_metadata
from app_skeleton.api.privacy_guardrails import allow_external_llm, guard_for_llm, is_external_provider
from app_skeleton.api.search_service import SearchService

LOGGER = logging.getLogger(__name__)


def _env_int(name: str, default: int, *, low: int, high: int) -> int:
    try:
        value = int(os.getenv(name, str(default)).strip())
    except Exception:
        value = default
    return max(low, min(value, high))


def _hits_to_sources(unified_hits: list[Any], rag_sources: list[dict[str, Any]], *, limit: int) -> tuple[list[dict[str, Any]], list[Any]]:
    seen_ids = {h.id for h in unified_hits}
    retrieved_sources: list[dict[str, Any]] = []

    for hit in unified_hits:
        retrieved_sources.append({
            "title": hit.title,
            "source_type": hit.source_type or hit.bucket,
            "source_uuid": hit.document_code or hit.relative_path or hit.id,
            "chunk_id": hit.id,
            "text_preview": hit.snippet,
            "score": hit.score,
            "nav": hit.nav.model_dump() if hit.nav else None,
            "bucket": hit.bucket,
        })

    for src in rag_sources:
        cid = src.get("chunk_id")
        if cid and cid in seen_ids:
            continue
        if cid:
            seen_ids.add(cid)
        retrieved_sources.append({
            "title": src["title"],
            "source_type": src["source_type"],
            "source_uuid": src["source_uuid"],
            "chunk_id": cid,
            "text_preview": src["text_preview"],
            "score": src.get("score", 0.0),
            "nav": None,
            "bucket": "lab",
        })

    return retrieved_sources[:limit], unified_hits[:limit]


def _build_prompts(
    *,
    question: str,
    unified_hits: list[Any],
    rag_sources: list[dict[str, Any]],
    db_data: dict[str, Any],
    clinical_block: str,
    sources: list[dict[str, Any]],
) -> tuple[str, str]:
    has_research = any(h.bucket == "research" for h in unified_hits)

    if has_research:
        grounding_hits: list[dict[str, Any]] = []
        for hit in unified_hits:
            meta = hit.metadata or {}
            grounding_hits.append({
                "title": hit.title,
                "source_type": hit.source_type or hit.bucket,
                "source_url": meta.get("source_url"),
                "doi": meta.get("doi"),
                "pmid": meta.get("pmid"),
                "snippet": hit.snippet,
            })
        for src in rag_sources:
            grounding_hits.append({
                "title": src["title"],
                "source_type": src["source_type"],
                "source_url": None,
                "doi": None,
                "pmid": None,
                "snippet": src["text_preview"],
            })
        grounding_hits = grounding_hits[:12]

        system_prompt = (
            RESEARCH_SYSTEM_PROMPT
            + "\n\nReport patient/sample statistics exactly as provided in database counts. Do NOT invent figures."
        )
        user_content = (
            f"Database counts:\n"
            f"- Patient total: {db_data.get('patient_count', 0)}\n"
            f"- Sample total: {db_data.get('sample_count', 0)}\n"
            f"- Projects: {db_data.get('project_samples', {})}\n"
            f"- Modalities: {db_data.get('modality_samples', {})}\n\n"
            f"{('Structured clinical/feature analysis:\\n' + clinical_block + '\\n\\n') if clinical_block else ''}"
            + build_grounded_prompt(question, grounding_hits)
        )
        return system_prompt, user_content

    context_str = ""
    for i, src in enumerate(sources):
        context_str += (
            f"[{i + 1}] Source: {src['title']} (Type: {src['source_type']})\n"
            f"{src['text_preview']}\n\n"
        )

    system_prompt = (
        "You are the OMEIA Clinical-Spatial Biology Copilot, an expert AI platform assistant.\n"
        "Your task is to answer the researcher's query based on the database counts and documentation snippets.\n"
        "Follow these rules:\n"
        "1. Report patient/sample statistics exactly as provided in the database counts. Do NOT invent/hallucinate figures.\n"
        "2. If code installation commands or scripts are requested, return structured code blocks detailing required parameters.\n"
        "3. Cite references [1], [2], etc., corresponding to context blocks.\n"
        "4. Remain precise, professional, and highlight limitations."
    )
    user_content = (
        f"Database counts:\n"
        f"- Patient total: {db_data.get('patient_count', 0)}\n"
        f"- Sample total: {db_data.get('sample_count', 0)}\n"
        f"- Projects: {db_data.get('project_samples', {})}\n"
        f"- Modalities: {db_data.get('modality_samples', {})}\n\n"
        f"{('Structured clinical/feature analysis:\\n' + clinical_block + '\\n\\n') if clinical_block else ''}"
        f"Documentation Context:\n"
        f"{context_str}\n"
        f"Question: {question}"
    )
    return system_prompt, user_content


def answer_chat(
    message: str,
    *,
    project_codes: list[str] | None = None,
    user: dict[str, Any] | None = None,
    llm: Any,
    search_svc: SearchService,
    rag_agent: Any,
    search_fn: Callable[[str, list[str] | None, int], list[Any]] | None = None,
) -> dict[str, Any]:
    """Answer a chat turn with privacy guardrails, unified-search RAG, and LLM synthesis."""
    provider = getattr(llm, "provider", "mock") or "mock"
    max_sources = _env_int("CHAT_MAX_SOURCES", 12, low=4, high=24)

    safe_message, audit, limitations = guard_for_llm(message, provider)
    if is_external_provider(provider) and not allow_external_llm(audit, provider):
        return {
            "answer": (
                "Your message was blocked by local privacy guardrails because patient-identifiable "
                "data was detected and the copilot is configured to use an external cloud LLM. "
                "Remove identifiers and try again, or use a local provider (ollama/mock)."
            ),
            "limitations": limitations,
            "sources": [],
            "database_counts": {},
            "is_safe": False,
            "search_hits": [],
            "provider": provider,
            "blocked_by_guardrail": True,
        }

    db_data = query_postgres_metadata(project_codes)
    clinical_block = _clinical_context_for_question(safe_message, project_codes or [])

    if search_fn is not None:
        unified_hits = search_fn(safe_message, project_codes, max_sources)
    else:
        unified_hits = search_svc.hits_for_copilot(
            safe_message,
            project_codes=project_codes,
            limit=max_sources,
        )

    rag_sources = rag_agent.retrieve(safe_message, project_codes)
    retrieved_sources, unified_hits = _hits_to_sources(unified_hits, rag_sources, limit=max_sources)

    sources = [
        SourceInfo(
            title=src["title"],
            source_type=src["source_type"],
            source_uuid=src["source_uuid"],
            chunk_id=src["chunk_id"],
            text_preview=src["text_preview"],
            score=src["score"],
            nav=src.get("nav"),
            bucket=src.get("bucket"),
        )
        for src in retrieved_sources
    ]
    search_hits_payload = [h.model_dump() for h in unified_hits]

    system_prompt, user_content = _build_prompts(
        question=safe_message,
        unified_hits=unified_hits,
        rag_sources=rag_sources,
        db_data=db_data,
        clinical_block=clinical_block,
        sources=retrieved_sources,
    )

    answer = llm.generate(user_content, system_prompt)

    has_research = any(h.bucket == "research" for h in unified_hits)
    if has_research:
        grounding_hits = []
        for hit in unified_hits:
            meta = hit.metadata or {}
            grounding_hits.append({
                "title": hit.title,
                "source_type": hit.source_type or hit.bucket,
                "source_url": meta.get("source_url"),
                "doi": meta.get("doi"),
                "pmid": meta.get("pmid"),
                "snippet": hit.snippet,
            })
        validation = validate_answer_sources(answer, grounding_hits)
        if validation.get("warning"):
            limitations.append(validation["warning"])

    if provider == "mock":
        limitations.append("Running in local mock-synthesis mode because no cloud LLM API key is configured.")

    return {
        "answer": answer,
        "limitations": limitations,
        "sources": [s.model_dump() for s in sources],
        "database_counts": db_data,
        "is_safe": True,
        "search_hits": search_hits_payload,
        "provider": provider,
        "blocked_by_guardrail": False,
        "audit": {
            "redaction_count": audit.get("redaction_count", 0),
            "violations": audit.get("violations", []),
            "risk_level": audit.get("risk_level", "low"),
        },
    }
