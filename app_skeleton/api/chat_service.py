"""Gemini Research Copilot chat orchestration with unified-search RAG."""
from __future__ import annotations

import logging
import os
import re
from typing import Any, Callable

from app_skeleton.api.answer_grounding_service import (
    SYSTEM_PROMPT as RESEARCH_SYSTEM_PROMPT,
    build_grounded_prompt,
    empty_corpus_answer,
    enforce_citations,
    is_off_topic_query,
    off_topic_refusal,
    validate_answer_sources,
    CONVERSATIONAL_ANSWER_STYLES,
)
from app_skeleton.api.chat_intent import IntentDecision, classify_chat_intent
from app_skeleton.api.common import SourceInfo, _clinical_context_for_question, query_postgres_metadata
from app_skeleton.api.privacy_guardrails import allow_external_llm, guard_for_llm, is_external_provider
from app_skeleton.api.search_service import SearchService

LOGGER = logging.getLogger(__name__)

_FINNISH_MARKERS = re.compile(
    r"\b(miten|mikä|mikä|missä|milloin|miksi|voitko|kerro|lab|protokolla|tutkimus)\b|[äöåÄÖÅ]",
    re.I,
)


def _env_int(name: str, default: int, *, low: int, high: int) -> int:
    try:
        value = int(os.getenv(name, str(default)).strip())
    except Exception:
        value = default
    return max(low, min(value, high))


def _user_display_name(user: dict[str, Any] | None) -> str:
    if not user:
        return ""
    for key in ("display_name", "full_name", "name"):
        val = (user.get(key) or "").strip()
        if val:
            return val.split(",")[0].strip()
    email = (user.get("email") or "").strip()
    if email and "@" in email:
        local = email.split("@", 1)[0]
        return local.replace(".", " ").replace("_", " ").title()
    return ""


def _detect_response_language(message: str) -> str | None:
    if _FINNISH_MARKERS.search(message or ""):
        return "fi"
    return None


def _language_instruction(lang: str | None) -> str:
    if lang == "fi":
        return (
            " The user wrote in Finnish — respond in Finnish while keeping source titles, "
            "DOIs, and accession IDs in their original form. Still use [1], [2] citation markers."
        )
    return ""


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


def _format_db_counts_block(db_data: dict[str, Any]) -> str:
    patient_count = int(db_data.get("patient_count") or 0)
    sample_count = int(db_data.get("sample_count") or 0)
    if patient_count <= 0 and sample_count <= 0:
        return ""
    lines = ["Database counts:"]
    if patient_count > 0:
        lines.append(f"- Patient total: {patient_count}")
    if sample_count > 0:
        lines.append(f"- Sample total: {sample_count}")
    projects = db_data.get("project_samples") or {}
    modalities = db_data.get("modality_samples") or {}
    if projects:
        lines.append(f"- Projects: {projects}")
    if modalities:
        lines.append(f"- Modalities: {modalities}")
    return "\n".join(lines) + "\n\n"


def _intent_system_prompt(intent_decision: IntentDecision, *, user_name: str = "", lang: str | None = None) -> str:
    name_hint = f" The user's name is {user_name}." if user_name else ""
    lang_hint = _language_instruction(lang)

    if intent_decision.answer_style == "safety":
        return (
            "You are the OMEIA platform safety assistant. "
            "Decline to process or repeat sensitive identifiers or secrets. "
            "Ask the user to remove patient identifiers, credentials, or secrets and try again."
        )

    if intent_decision.answer_style in {"brief_conversational", "natural"}:
        return (
            "You are OMEIA Research Copilot, a friendly lab assistant for the Färkkilä research group."
            f"{name_hint}{lang_hint}"
            " Reply naturally in one or two short sentences."
            " Do not use headings, numbered sections, bullet lists, citations, or formal report structure."
            " Briefly offer help with research questions, lab protocols, document ingestion, or app setup."
        )

    if intent_decision.answer_style == "helpful_steps":
        return (
            "You are the OMEIA platform guide."
            f"{name_hint}{lang_hint}"
            " Explain how to use the app with clear, practical steps."
            " Stay conversational — avoid research-report formatting and citations unless unavoidable."
        )

    if intent_decision.answer_style == "technical":
        return (
            "You are the OMEIA engineering assistant."
            f"{name_hint}{lang_hint}"
            " Give concise technical guidance for code and debugging."
            " Use code blocks when helpful. No citations or source cards."
        )

    if intent_decision.answer_style == "practical_with_sources":
        return (
            "You are the OMEIA lab protocol assistant."
            f"{name_hint}{lang_hint}"
            " Give practical step-by-step guidance grounded in retrieved documentation."
            " Cite sources as [1], [2], etc. when using context. Be concise and actionable."
        )

    if intent_decision.answer_style == "search_summary":
        return (
            RESEARCH_SYSTEM_PROMPT
            + lang_hint
            + "\n\nSummarize the most relevant retrieved matches for the user's search request."
            " Cite sources as [1], [2], etc."
        )

    return (
        RESEARCH_SYSTEM_PROMPT
        + lang_hint
        + "\n\nCite every scientific claim with [1], [2], etc. Report patient/sample statistics "
        "only when non-zero database counts are provided. Do NOT invent figures."
    )


def _grounding_hits_from_retrieval(unified_hits: list[Any], rag_sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
    return grounding_hits[:12]


def _build_prompts(
    *,
    question: str,
    unified_hits: list[Any],
    rag_sources: list[dict[str, Any]],
    db_data: dict[str, Any],
    clinical_block: str,
    sources: list[dict[str, Any]],
    intent_decision: IntentDecision,
    user_name: str = "",
    lang: str | None = None,
) -> tuple[str, str]:
    if not intent_decision.use_rag:
        system_prompt = _intent_system_prompt(intent_decision, user_name=user_name, lang=lang)
        return system_prompt, question

    db_block = _format_db_counts_block(db_data)
    clinical_prefix = (
        f"Structured clinical/feature analysis:\n{clinical_block}\n\n" if clinical_block else ""
    )

    has_research = any(h.bucket == "research" for h in unified_hits)
    use_grounding_template = has_research or intent_decision.answer_style in {
        "scientific_with_sources",
        "search_summary",
    }

    if use_grounding_template:
        grounding_hits = _grounding_hits_from_retrieval(unified_hits, rag_sources)
        system_prompt = _intent_system_prompt(intent_decision, user_name=user_name, lang=lang)
        user_content = db_block + clinical_prefix + build_grounded_prompt(question, grounding_hits)
        return system_prompt, user_content

    context_str = ""
    for i, src in enumerate(sources):
        context_str += (
            f"[{i + 1}] Source: {src['title']} (Type: {src['source_type']})\n"
            f"{src['text_preview']}\n\n"
        )

    system_prompt = _intent_system_prompt(intent_decision, user_name=user_name, lang=lang)
    user_content = (
        db_block
        + clinical_prefix
        + f"Documentation Context:\n{context_str}\nQuestion: {question}"
    )
    return system_prompt, user_content


def _intent_metadata(intent_decision: IntentDecision) -> dict[str, Any]:
    return {
        "intent": intent_decision.intent,
        "use_rag": intent_decision.use_rag,
        "show_sources": intent_decision.show_sources,
        "require_citations": intent_decision.require_citations,
        "answer_style": intent_decision.answer_style,
        "reason": intent_decision.reason,
    }


def _llm_provenance(llm: Any, *, configured_provider: str) -> dict[str, Any]:
    provenance = getattr(llm, "synthesis_provenance", None)
    if callable(provenance):
        meta = provenance()
    else:
        meta = {
            "effective_provider": configured_provider,
            "model": getattr(llm, "model", ""),
            "fallback_used": False,
            "synthesis_mode": "mock" if configured_provider == "mock" else "live",
        }
    effective = meta.get("effective_provider") or configured_provider
    return {
        "provider": effective,
        "effective_provider": effective,
        "model": meta.get("model") or getattr(llm, "model", ""),
        "fallback_used": bool(meta.get("fallback_used")),
        "synthesis_mode": meta.get("synthesis_mode") or "mock",
    }


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
    """Answer a chat turn with privacy guardrails, intent routing, and optional RAG."""
    provider = getattr(llm, "provider", "mock") or "mock"
    max_sources = _env_int("CHAT_MAX_SOURCES", 12, low=4, high=24)
    intent_decision = classify_chat_intent(message)
    user_name = _user_display_name(user)
    response_lang = _detect_response_language(message)
    intent_meta = _intent_metadata(intent_decision)

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
            **intent_meta,
        }

    if intent_decision.intent == "sensitive_private":
        return {
            "answer": (
                "I can't help with messages that may contain patient identifiers, medical record numbers, "
                "or secrets. Please remove sensitive details and ask again."
            ),
            "limitations": limitations,
            "sources": [],
            "database_counts": {},
            "is_safe": True,
            "search_hits": [],
            "provider": provider,
            "blocked_by_guardrail": False,
            **intent_meta,
        }

    if is_off_topic_query(safe_message) and intent_decision.intent == "general_chat":
        return {
            "answer": off_topic_refusal(),
            "limitations": limitations + ["Off-topic query — answer is not lab-grounded."],
            "sources": [],
            "database_counts": {},
            "is_safe": True,
            "search_hits": [],
            "provider": provider,
            "blocked_by_guardrail": False,
            **_llm_provenance(llm, configured_provider=provider),
            **intent_meta,
        }

    db_data = query_postgres_metadata(project_codes) if intent_decision.use_rag else {}
    clinical_block = _clinical_context_for_question(safe_message, project_codes or []) if intent_decision.use_rag else ""

    unified_hits: list[Any] = []
    rag_sources: list[dict[str, Any]] = []
    retrieved_sources: list[dict[str, Any]] = []

    if intent_decision.use_rag:
        if search_fn is not None:
            unified_hits = search_fn(safe_message, project_codes, max_sources)
        else:
            unified_hits = search_svc.hits_for_copilot(
                safe_message,
                intent=intent_decision.intent,
                project_codes=project_codes,
                limit=max_sources,
            )
        use_legacy_rag = os.getenv("CHAT_USE_LEGACY_RAG", "false").lower() in {"1", "true", "yes"}
        if use_legacy_rag and len(unified_hits) < max(3, max_sources // 2):
            rag_sources = rag_agent.retrieve(safe_message, project_codes)
        retrieved_sources, unified_hits = _hits_to_sources(unified_hits, rag_sources, limit=max_sources)

        if not retrieved_sources:
            honest = empty_corpus_answer(safe_message, intent=intent_decision.intent)
            limitations.append(
                "No matching documents were retrieved above the relevance threshold — "
                "try platform search (⌘K) or ingest more sources."
            )
            return {
                "answer": honest,
                "limitations": limitations,
                "sources": [],
                "database_counts": db_data,
                "is_safe": True,
                "search_hits": [],
                "provider": provider,
                "blocked_by_guardrail": False,
                **_llm_provenance(llm, configured_provider=provider),
                **intent_meta,
            }

    system_prompt, user_content = _build_prompts(
        question=safe_message,
        unified_hits=unified_hits,
        rag_sources=rag_sources,
        db_data=db_data,
        clinical_block=clinical_block,
        sources=retrieved_sources,
        intent_decision=intent_decision,
        user_name=user_name,
        lang=response_lang,
    )

    answer = llm.generate(user_content, system_prompt)
    provenance = _llm_provenance(llm, configured_provider=provider)

    if intent_decision.require_citations and retrieved_sources:
        grounding_hits = _grounding_hits_from_retrieval(unified_hits, rag_sources)
        answer, citation_notes = enforce_citations(
            answer,
            grounding_hits,
            generate_fn=lambda p, s: llm.generate(p, s),
            user_content=user_content,
            system_prompt=system_prompt,
        )
        limitations.extend(citation_notes)
        validation = validate_answer_sources(answer, grounding_hits)
        if validation.get("warning") and not citation_notes:
            limitations.append(validation["warning"])

    if provenance["synthesis_mode"] == "mock" and intent_decision.use_rag:
        limitations.append("Running in local mock-synthesis mode because no cloud LLM API key is configured.")

    sources_payload: list[dict[str, Any]] = []
    search_hits_payload: list[dict[str, Any]] = []
    if intent_decision.show_sources:
        sources_payload = [
            SourceInfo(
                title=src["title"],
                source_type=src["source_type"],
                source_uuid=src["source_uuid"],
                chunk_id=src["chunk_id"],
                text_preview=src["text_preview"],
                score=src["score"],
                nav=src.get("nav"),
                bucket=src.get("bucket"),
            ).model_dump()
            for src in retrieved_sources
        ]
        search_hits_payload = [h.model_dump() for h in unified_hits]

    return {
        "answer": answer,
        "limitations": limitations,
        "sources": sources_payload,
        "database_counts": db_data,
        "is_safe": True,
        "search_hits": search_hits_payload,
        "blocked_by_guardrail": False,
        **provenance,
        "audit": {
            "redaction_count": audit.get("redaction_count", 0),
            "violations": audit.get("violations", []),
            "risk_level": audit.get("risk_level", "low"),
        },
        "system_prompt": system_prompt,
        "user_content": user_content,
        **intent_meta,
    }
