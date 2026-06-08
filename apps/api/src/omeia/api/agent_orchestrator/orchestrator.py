"""Category-based multi-agent orchestration for OMEIA chat."""
from __future__ import annotations

import logging
from typing import Any, Callable

from omeia.api.agent_orchestrator.registry import (
    agents_for_category,
    get_agent,
    get_category,
    load_categories_config,
)
from omeia.api.agent_orchestrator.trace_store import create_trace, finalize_trace

LOGGER = logging.getLogger(__name__)

_BIOMEDICAL_SAFETY = """
Biomedical safety rules:
- Distinguish established fact, supported hypothesis, and speculation.
- State evidence strength (strong / moderate / weak / not verified).
- Never invent citations or PMIDs.
- If not verified against retrieved sources, say so explicitly.
- Do not give clinical treatment instructions; frame as research/educational context.
"""


def _agent_system_prompt(agent: dict[str, Any], category: dict[str, Any]) -> str:
    parts = [
        f"You are the internal '{agent.get('label')}' agent for OMEIA Research Copilot.",
        f"Category: {category.get('label')}.",
        f"Specialty: {agent.get('specialty', '')}.",
        "Answer only within your specialty. Be concise and structured.",
    ]
    if agent.get("safety") == "biomedical":
        parts.append(_BIOMEDICAL_SAFETY)
    if agent.get("role") == "planner":
        parts.append("Return a short numbered plan of subtasks for specialist agents. No final answer.")
    if agent.get("role") == "critic":
        parts.append("Critique prior specialist outputs. Flag unsupported claims and uncertainty.")
    if agent.get("role") == "synthesizer":
        parts.append(
            "Merge specialist outputs into one coherent answer for the lab user. "
            "Do not mention internal agent or model names."
        )
    return "\n".join(parts)


def _run_agent_llm(
    *,
    agent: dict[str, Any],
    message: str,
    context: str,
    llm_factory: Callable[[str | None, str | None], Any],
    trace: dict[str, Any],
) -> dict[str, Any]:
    preferred = agent.get("preferred_model") or {}
    fallback = agent.get("fallback_model") or {}
    agent_id = agent["id"]

    def _attempt(provider: str | None, model: str | None, *, is_fallback: bool) -> dict[str, Any]:
        llm = llm_factory(provider, model)
        system = _agent_system_prompt(agent, trace.get("_category_meta") or {})
        user = message if not context else f"User question:\n{message}\n\nContext from other agents:\n{context}"
        text = llm.generate(user, system)
        trace["agents_started"].append(agent_id)
        trace["models_used"].append({
            "agent": agent_id,
            "provider": getattr(llm, "provider", provider),
            "model": getattr(llm, "model", model),
            "fallback": is_fallback,
        })
        trace["intermediate_outputs"].append({"agent": agent_id, "text": text[:4000]})
        return {"agent": agent_id, "text": text, "fallback": is_fallback}

    try:
        return _attempt(preferred.get("provider"), preferred.get("model"), is_fallback=False)
    except Exception as exc:
        LOGGER.warning("Agent %s primary model failed: %s", agent_id, exc)
        trace["warnings"].append(f"{agent_id}: primary failed — {exc}")
        try:
            return _attempt(fallback.get("provider"), fallback.get("model"), is_fallback=True)
        except Exception as exc2:
            trace["warnings"].append(f"{agent_id}: fallback failed — {exc2}")
            return {"agent": agent_id, "text": "", "error": str(exc2), "fallback": True}


def run_category_chat(
    message: str,
    *,
    category_id: str,
    mode: str,
    project_codes: list[str] | None,
    user: dict[str, Any] | None,
    llm_factory: Callable[[str | None, str | None], Any],
    rag_answer_fn: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    """Execute category-scoped agent pipeline."""
    cfg = load_categories_config()
    category = get_category(category_id) or get_category(cfg.get("default_category", "general_research"))
    if not category:
        return {"answer": "Unknown agent category.", "confidence": "low", "warnings": ["invalid_category"]}

    mode = mode if mode in {"fast", "balanced", "deep"} else category.get("default_mode", "balanced")
    agent_ids = agents_for_category(category["id"], mode)
    trace = create_trace(category=category["id"], mode=mode)
    trace["_category_meta"] = category

    specialist_outputs: list[dict[str, Any]] = []
    context_blocks: list[str] = []
    citations: list[dict[str, Any]] = []
    limitations: list[str] = []
    confidence = "medium"

    # Optional shared RAG pass for retrieval-heavy agents
    needs_rag = any((get_agent(a) or {}).get("use_rag") for a in agent_ids)
    rag_bundle: dict[str, Any] = {}
    if needs_rag:
        primary = next((a for a in agent_ids if a not in ("synthesizer", "task_planner")), agent_ids[0])
        pref = (get_agent(primary) or {}).get("preferred_model") or {}
        rag_bundle = rag_answer_fn(
            message,
            project_codes=project_codes,
            user=user,
            provider=pref.get("provider"),
            model=pref.get("model"),
            retrieval_only=True,
        )
        if rag_bundle.get("sources"):
            citations.extend(rag_bundle.get("sources") or [])
        limitations.extend(rag_bundle.get("limitations") or [])

    for agent_id in agent_ids:
        if agent_id == "synthesizer":
            continue
        agent = get_agent(agent_id)
        if not agent:
            trace["agents_skipped"].append(agent_id)
            continue
        if agent.get("runs_in_modes") and mode not in agent["runs_in_modes"]:
            trace["agents_skipped"].append(agent_id)
            continue

        ctx = "\n\n".join(context_blocks)
        if rag_bundle.get("retrieval_context"):
            ctx = (ctx + "\n\n" + rag_bundle["retrieval_context"]).strip()

        out = _run_agent_llm(
            agent={**agent, "id": agent_id},
            message=message,
            context=ctx,
            llm_factory=llm_factory,
            trace=trace,
        )
        if out.get("text"):
            specialist_outputs.append(out)
            context_blocks.append(f"[{agent.get('label', agent_id)}]\n{out['text']}")

    # Synthesizer or single-agent fast path
    synthesizer_id = "synthesizer"
    if synthesizer_id in agent_ids and len(specialist_outputs) > 1:
        synth_agent = get_agent(synthesizer_id)
        if synth_agent:
            synth_out = _run_agent_llm(
                agent={**synth_agent, "id": synthesizer_id},
                message=message,
                context="\n\n".join(context_blocks),
                llm_factory=llm_factory,
                trace=trace,
            )
            answer = synth_out.get("text") or _fallback_merge(specialist_outputs)
        else:
            answer = _fallback_merge(specialist_outputs)
    elif specialist_outputs:
        answer = specialist_outputs[-1].get("text") or _fallback_merge(specialist_outputs)
    else:
        answer = "I could not complete this request with the selected research team. Try Fast Local or another category."
        confidence = "low"

    if "evidence_checker" in agent_ids:
        confidence = "medium" if citations else "low"
    if trace.get("warnings"):
        limitations.extend(trace["warnings"][:3])

    source_buckets: list[str] = []
    source_counts: dict[str, int] = {}
    for src in rag_bundle.get("sources") or []:
        bucket = src.get("bucket") or src.get("source_type") or "unknown"
        source_buckets.append(str(bucket))
        source_counts[bucket] = source_counts.get(bucket, 0) + 1
    for hit in rag_bundle.get("search_hits") or []:
        bucket = hit.get("bucket") or "unknown"
        if bucket not in source_buckets:
            source_buckets.append(str(bucket))
        source_counts[bucket] = source_counts.get(bucket, 0) + 1

    grounding_outcome = "grounded" if citations else "ungrounded"
    if trace.get("warnings"):
        grounding_outcome = "warnings"

    primary_model = (trace.get("models_used") or [{}])[0] if trace.get("models_used") else {}
    db_conn = None
    try:
        from omeia.api.common import DB_CONN as _db

        db_conn = _db
    except Exception:
        pass

    finalize_trace(
        trace,
        db_conn=db_conn,
        source_buckets=source_buckets,
        source_counts=source_counts,
        provider=primary_model.get("provider"),
        model=primary_model.get("model"),
        grounding_outcome=grounding_outcome,
        user_email=(user or {}).get("email"),
        user_role=(user or {}).get("role"),
    )

    agents_used = [o["agent"] for o in specialist_outputs]
    if synthesizer_id in trace["agents_started"]:
        agents_used.append(synthesizer_id)

    return {
        "answer": answer.strip(),
        "category": category.get("label"),
        "category_id": category["id"],
        "mode": mode,
        "agents_used": agents_used,
        "team_preview": category.get("team_preview") or [],
        "confidence": confidence,
        "citations": citations[:12],
        "warnings": trace.get("warnings") or [],
        "limitations": limitations,
        "trace_id": trace["run_id"],
        "is_safe": True,
        "show_sources": bool(citations),
        "sources": citations,
        "search_hits": rag_bundle.get("search_hits") or [],
        "synthesis_mode": "category_agents",
        "intent": f"category_{category['id']}",
    }


def _fallback_merge(outputs: list[dict[str, Any]]) -> str:
    parts = [o.get("text", "").strip() for o in outputs if o.get("text")]
    return "\n\n".join(parts) if parts else ""
