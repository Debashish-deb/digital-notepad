"""Gemini Research Copilot chat orchestration with unified-search RAG."""
from __future__ import annotations

import logging
import os
import re
from typing import Any, Callable

from app_skeleton.api.answer_grounding_service import (
    build_grounded_prompt,
    empty_corpus_answer,
    enforce_citations,
    is_off_topic_query,
    off_topic_refusal,
    validate_answer_sources,
    CONVERSATIONAL_ANSWER_STYLES,
)
from app_skeleton.api.chat_conversation import (
    build_user_context,
    classify_and_enrich,
    conversational_system_prompt,
    instant_greeting_response,
    resolve_route_model,
    should_use_instant_greeting,
)
from app_skeleton.api.chat_intent import IntentDecision
from app_skeleton.api.chat_model_catalog import make_chat_llm
from app_skeleton.api.evidence_orchestrator import (
    build_orchestrator_system_prompt,
    build_orchestrator_user_prompt,
    evidence_items_to_grounding_hits,
    orchestrator_answer_metadata,
    orchestrator_metadata,
    package_evidence,
    should_use_orchestrator,
    understand_query,
)
from app_skeleton.api.chat_session_store import (
    append_turn,
    ensure_session,
    format_memory_block,
    load_session_context,
)
from app_skeleton.api.common import SourceInfo, _clinical_context_for_question, query_postgres_metadata
from app_skeleton.api.privacy_guardrails import allow_external_llm, guard_for_llm, is_external_provider
from app_skeleton.api.search_service import SearchService
from app_skeleton.api.platform_flags import research_strategy_assistant_enabled

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
    return conversational_system_prompt(intent_decision, user_name=user_name, lang=lang)


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
    evidence_package: Any | None = None,
    query_understanding: Any | None = None,
    memory_block: str = "",
) -> tuple[str, str]:
    memory_prefix = memory_block or ""
    if not intent_decision.use_rag:
        system_prompt = _intent_system_prompt(intent_decision, user_name=user_name, lang=lang)
        return system_prompt, memory_prefix + question

    db_block = _format_db_counts_block(db_data)
    clinical_prefix = (
        f"Structured clinical/feature analysis:\n{clinical_block}\n\n" if clinical_block else ""
    )

    if (
        should_use_orchestrator(intent_decision)
        and evidence_package is not None
        and query_understanding is not None
        and evidence_package.items
    ):
        system_prompt = build_orchestrator_system_prompt(
            query_understanding,
            evidence_package,
            user_name=user_name,
            lang=lang,
            answer_style=intent_decision.answer_style,
        )
        user_content = memory_prefix + build_orchestrator_user_prompt(
            question,
            evidence_package,
            db_block=db_block,
            clinical_block=clinical_prefix,
        )
        return system_prompt, user_content

    has_research = any(h.bucket == "research" for h in unified_hits)
    use_grounding_template = has_research or intent_decision.answer_style in {
        "scientific_with_sources",
        "search_summary",
    }

    if use_grounding_template:
        grounding_hits = _grounding_hits_from_retrieval(unified_hits, rag_sources)
        system_prompt = _intent_system_prompt(intent_decision, user_name=user_name, lang=lang)
        user_content = memory_prefix + db_block + clinical_prefix + build_grounded_prompt(question, grounding_hits)
        return system_prompt, user_content

    context_str = ""
    for i, src in enumerate(sources):
        context_str += (
            f"[{i + 1}] Source: {src['title']} (Type: {src['source_type']})\n"
            f"{src['text_preview']}\n\n"
        )

    system_prompt = _intent_system_prompt(intent_decision, user_name=user_name, lang=lang)
    user_content = (
        memory_prefix
        + db_block
        + clinical_prefix
        + f"Documentation Context:\n{context_str}\nQuestion: {question}"
    )
    return system_prompt, user_content


_REGEN_SYSTEM_APPEND = (
    "\n\nREGENERATION: A prior draft had weak or conflicting claim support. "
    "Only state facts directly supported by the evidence package. "
    "If uncertain, say evidence is insufficient. Do not invent statistics."
)


def _needs_evidence_regen(evidence_package: Any | None) -> bool:
    if not evidence_package:
        return False
    for claim in (getattr(evidence_package, "claim_validations", None) or [])[:6]:
        if claim.status in {"conflicting", "uncertain"}:
            return True
    return evidence_package.confidence in {"insufficient", "low"}


def _intent_metadata(intent_decision: IntentDecision) -> dict[str, Any]:
    return {
        "intent": intent_decision.intent,
        "intent_category": intent_decision.intent_category,
        "confidence": intent_decision.confidence,
        "use_rag": intent_decision.use_rag,
        "show_sources": intent_decision.show_sources,
        "require_citations": intent_decision.require_citations,
        "answer_style": intent_decision.answer_style,
        "reason": intent_decision.reason,
    }


def _route_llm_for_intent(
    llm: Any,
    intent_decision: IntentDecision,
    *,
    user_provider: str | None = None,
    user_model: str | None = None,
) -> Any:
    """Fast local models for greetings/chat; keep user-selected or premium models for research."""
    if user_provider or user_model:
        return llm
    provider, model = resolve_route_model(intent_decision)
    if not provider:
        return llm
    return make_chat_llm(provider, model, default_llm=llm)


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
    session_id: str | None = None,
    llm: Any,
    search_svc: SearchService,
    rag_agent: Any,
    search_fn: Callable[[str, list[str] | None, int], list[Any]] | None = None,
) -> dict[str, Any]:
    """Answer a chat turn with privacy guardrails, intent routing, and optional RAG."""
    provider = getattr(llm, "provider", "mock") or "mock"
    max_sources = _env_int("CHAT_MAX_SOURCES", 12, low=4, high=24)
    user_role = (user or {}).get("role")
    intent_decision = classify_and_enrich(message)
    query_understanding = understand_query(message, intent_decision)
    user_name = _user_display_name(user)
    user_email = (user or {}).get("email") or ""
    active_session = ensure_session(
        session_id=session_id,
        user_email=user_email,
        project_codes=project_codes,
    )
    session_ctx = load_session_context(active_session, user_email=user_email) if active_session else None
    memory_block = format_memory_block(session_ctx)
    response_lang = _detect_response_language(message)
    intent_meta = _intent_metadata(intent_decision)
    chat_ctx = build_user_context(message, user=user, project_codes=project_codes)

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

    if should_use_instant_greeting(intent_decision, message):
        answer = instant_greeting_response(message, chat_ctx)
        return {
            "answer": answer,
            "limitations": limitations,
            "sources": [],
            "database_counts": {},
            "is_safe": True,
            "search_hits": [],
            "provider": provider,
            "blocked_by_guardrail": False,
            "synthesis_mode": "template",
            "effective_provider": provider,
            "model": getattr(llm, "model", ""),
            "fallback_used": False,
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

    llm = _route_llm_for_intent(llm, intent_decision)
    provider = getattr(llm, "provider", provider) or provider

    if research_strategy_assistant_enabled() and intent_decision.use_rag:
        from app_skeleton.api.research_strategy_engine import (
            ResearchStrategyEngine,
            is_strategy_question,
        )

        if is_strategy_question(safe_message, intent_decision):
            engine = ResearchStrategyEngine(search_svc, llm)
            strategy_payload = engine.run(
                safe_message,
                intent_decision=intent_decision,
                project_codes=project_codes,
                user_role=user_role,
            )
            strategy_payload.update(_llm_provenance(llm, configured_provider=provider))
            strategy_payload.update(intent_meta)
            strategy_payload["database_counts"] = (
                query_postgres_metadata(project_codes) if intent_decision.use_rag else {}
            )
            strategy_payload["is_safe"] = True
            strategy_payload["blocked_by_guardrail"] = False
            strategy_payload["provider"] = strategy_payload.get("provider") or provider
            strategy_payload["intent"] = intent_decision.intent
            if active_session and user_email:
                append_turn(active_session, user_email=user_email, role="user", content=safe_message, intent=intent_decision.intent)
                append_turn(
                    active_session,
                    user_email=user_email,
                    role="assistant",
                    content=(strategy_payload.get("answer") or "")[:8000],
                    intent=intent_decision.intent,
                    metadata={"research_strategy": True},
                )
            strategy_payload["session_id"] = active_session or None
            return strategy_payload

    db_data = query_postgres_metadata(project_codes) if intent_decision.use_rag else {}
    chat_ctx = build_user_context(message, user=user, project_codes=project_codes, db_data=db_data)
    clinical_block = _clinical_context_for_question(safe_message, project_codes or []) if intent_decision.use_rag else ""

    unified_hits: list[Any] = []
    rag_sources: list[dict[str, Any]] = []
    retrieved_sources: list[dict[str, Any]] = []
    evidence_package = None

    if intent_decision.use_rag:
        if search_fn is not None:
            unified_hits = search_fn(safe_message, project_codes, max_sources)
        else:
            retrieval_limit = max_sources
            if intent_decision.intent == "project_question" and (user_role or "").lower() in {
                "admin",
                "editor",
                "researcher",
            }:
                retrieval_limit = min(max_sources + 4, 24)
            unified_hits = search_svc.hits_for_copilot(
                safe_message,
                intent=intent_decision.intent,
                project_codes=project_codes,
                limit=retrieval_limit,
                prioritize_buckets=query_understanding.search_plan.prioritize_buckets,
                user_role=user_role,
            )
        use_legacy_rag = os.getenv("CHAT_USE_LEGACY_RAG", "false").lower() in {"1", "true", "yes"}
        if use_legacy_rag and rag_agent is not None and len(unified_hits) < max(3, max_sources // 2):
            rag_sources = rag_agent.retrieve(safe_message, project_codes)
            limitations.append("Legacy RAGAgent supplement used — prefer unified SearchService only.")
        retrieved_sources, unified_hits = _hits_to_sources(unified_hits, rag_sources, limit=max_sources)
        evidence_package = package_evidence(
            unified_hits,
            rag_sources,
            entities=query_understanding.entities,
            limit=max_sources,
        )

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
        evidence_package=evidence_package,
        query_understanding=query_understanding,
        memory_block=memory_block,
    )

    answer = llm.generate(user_content, system_prompt)
    regenerated = False
    if intent_decision.use_rag and _needs_evidence_regen(evidence_package):
        regen_system = system_prompt + _REGEN_SYSTEM_APPEND
        answer = llm.generate(user_content, regen_system)
        regenerated = True
        limitations.append(
            "Answer regenerated after claim validation flagged weak or conflicting source support."
        )
    provenance = _llm_provenance(llm, configured_provider=provider)

    if intent_decision.require_citations and retrieved_sources:
        if evidence_package and evidence_package.items:
            grounding_hits = evidence_items_to_grounding_hits(evidence_package)
        else:
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

    response_meta = orchestrator_metadata(
        query_understanding,
        evidence_package if intent_decision.use_rag else None,
    )
    if should_use_orchestrator(intent_decision) and evidence_package:
        response_meta.update(orchestrator_answer_metadata(answer))

    if active_session and user_email:
        append_turn(active_session, user_email=user_email, role="user", content=safe_message, intent=intent_decision.intent)
        append_turn(
            active_session,
            user_email=user_email,
            role="assistant",
            content=answer[:8000],
            intent=intent_decision.intent,
            metadata={"regenerated": regenerated},
        )

    return {
        "answer": answer,
        "limitations": limitations,
        "sources": sources_payload,
        "database_counts": db_data,
        "is_safe": True,
        "search_hits": search_hits_payload,
        "blocked_by_guardrail": False,
        "session_id": active_session or None,
        "answer_regenerated": regenerated,
        **provenance,
        "audit": {
            "redaction_count": audit.get("redaction_count", 0),
            "violations": audit.get("violations", []),
            "risk_level": audit.get("risk_level", "low"),
        },
        "system_prompt": system_prompt,
        "user_content": user_content,
        **response_meta,
        **intent_meta,
    }
