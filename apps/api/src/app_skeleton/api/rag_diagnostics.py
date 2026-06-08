"""Live RAG wiring diagnostics — timed step reports for chat/category pipelines."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

LOGGER = logging.getLogger(__name__)


@dataclass
class RagDiagnosticStep:
    name: str
    ok: bool
    elapsed_ms: float
    detail: str = ""
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class RagDiagnosticReport:
    query: str
    steps: list[RagDiagnosticStep] = field(default_factory=list)
    total_ms: float = 0.0
    ok: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "ok": self.ok,
            "total_ms": round(self.total_ms, 2),
            "steps": [
                {
                    "name": s.name,
                    "ok": s.ok,
                    "elapsed_ms": round(s.elapsed_ms, 2),
                    "detail": s.detail,
                    "data": s.data,
                }
                for s in self.steps
            ],
        }


def _timed_step(report: RagDiagnosticReport, name: str, fn: Callable[[], Any]) -> Any:
    started = time.monotonic()
    try:
        result = fn()
        elapsed = (time.monotonic() - started) * 1000.0
        report.steps.append(RagDiagnosticStep(name=name, ok=True, elapsed_ms=elapsed))
        return result
    except Exception as exc:
        elapsed = (time.monotonic() - started) * 1000.0
        report.ok = False
        report.steps.append(
            RagDiagnosticStep(name=name, ok=False, elapsed_ms=elapsed, detail=str(exc))
        )
        LOGGER.warning("RAG diagnostic step failed (%s): %s", name, exc)
        return None


def run_rag_diagnostics(
    query: str,
    *,
    search_svc: Any,
    llm: Any,
    rag_agent: Any,
    project_codes: list[str] | None = None,
    category_id: str = "cancer_oncology",
    mode: str = "balanced",
    probe_llm: bool = True,
) -> RagDiagnosticReport:
    """Run in-process RAG wiring checks with per-step timing."""
    from app_skeleton.api.chat_conversation import classify_and_enrich
    from app_skeleton.api.evidence_orchestrator import package_evidence, understand_query
    from app_skeleton.api.agent_orchestrator.rag_context import build_rag_bundle
    from app_skeleton.api.agent_orchestrator.registry import agents_for_category, get_agent

    report = RagDiagnosticReport(query=query)
    started = time.monotonic()
    codes = project_codes or []

    def _infra_topology() -> dict[str, Any]:
        import os

        from app_skeleton.api.docker_service_client import docker_services

        try:
            bootstrap = docker_services.bootstrap()
        except Exception as exc:
            bootstrap = {"error": str(exc)}
        return {
            "docker_local": docker_services.local_docker,
            "docker_auto_start": docker_services.auto_start_enabled,
            "ollama_base_url": os.getenv("OLLAMA_BASE_URL", ""),
            "qdrant_url": os.getenv("QDRANT_URL", ""),
            "tailscale_linux_ip": os.getenv("TAILSCALE_LINUX_IP", ""),
            "chat_llm_provider": os.getenv("CHAT_LLM_PROVIDER", os.getenv("LLM_PROVIDER", "")),
            "services": bootstrap.get("services") if isinstance(bootstrap, dict) else bootstrap,
        }

    topo = _timed_step(report, "infra_topology", _infra_topology)
    if topo is not None and not topo.get("docker_local"):
        report.steps[-1].detail = "Mac thin client — expect Postgres/Ollama/Qdrant on Linux host."

    intent = _timed_step(report, "classify_and_enrich", lambda: classify_and_enrich(query))
    if intent is None:
        report.total_ms = (time.monotonic() - started) * 1000.0
        return report

    understanding = _timed_step(
        report,
        "understand_query",
        lambda: understand_query(query, intent),
    )

    def _copilot_hits() -> list[Any]:
        plan_buckets = understanding.search_plan.prioritize_buckets if understanding else ()
        return search_svc.hits_for_copilot(
            query,
            intent=intent.intent,
            project_codes=codes,
            limit=12,
            prioritize_buckets=plan_buckets,
        )

    hits = _timed_step(report, "hits_for_copilot", _copilot_hits)
    if hits is not None:
        report.steps[-1].data = {
            "hit_count": len(hits),
            "buckets": sorted({getattr(h, "bucket", "unknown") for h in hits}),
            "top_scores": [round(float(getattr(h, "score", 0) or 0), 4) for h in hits[:5]],
        }

    def _legacy_rag() -> list[Any]:
        return rag_agent.retrieve(query, codes)

    legacy = _timed_step(report, "rag_agent.retrieve", _legacy_rag)
    if legacy is not None:
        report.steps[-1].data = {"source_count": len(legacy)}

    def _rag_bundle() -> dict[str, Any]:
        return build_rag_bundle(
            query,
            project_codes=codes,
            search_svc=search_svc,
            rag_agent=rag_agent,
        )

    bundle = _timed_step(report, "build_rag_bundle", _rag_bundle)
    if bundle is not None:
        report.steps[-1].data = {
            "context_chars": len(bundle.get("retrieval_context") or ""),
            "source_count": len(bundle.get("sources") or []),
            "limitations": bundle.get("limitations") or [],
        }

    if hits is not None:
        package = _timed_step(
            report,
            "package_evidence",
            lambda: package_evidence(
                hits,
                legacy or [],
                entities=understanding.entities if understanding else (),
                limit=12,
            ),
        )
        if package is not None:
            report.steps[-1].data = {
                "item_count": len(package.items),
                "confidence": package.confidence,
                "claim_validations": len(package.claim_validations),
            }

    agent_ids = agents_for_category(category_id, mode)
    report.steps.append(
        RagDiagnosticStep(
            name="category_agent_roster",
            ok=True,
            elapsed_ms=0.0,
            detail=f"{category_id}/{mode}",
            data={
                "agents": agent_ids,
                "models": [
                    {
                        "agent": aid,
                        "preferred": (get_agent(aid) or {}).get("preferred_model"),
                        "use_rag": (get_agent(aid) or {}).get("use_rag"),
                    }
                    for aid in agent_ids
                ],
            },
        )
    )

    if probe_llm:
        healthy = _timed_step(report, "llm.healthCheck", lambda: bool(llm.healthCheck()))
        if healthy is not None:
            report.steps[-1].data = {
                "provider": getattr(llm, "provider", "unknown"),
                "model": getattr(llm, "model", "unknown"),
                "healthy": healthy,
            }

        def _probe_generate() -> str:
            return llm.generate(
                f"Reply with one word: OK\n\nQuestion: {query[:120]}",
                "You are a diagnostic probe. Be extremely brief.",
            )

        snippet = _timed_step(report, "llm.generate_probe", _probe_generate)
        if snippet is not None:
            report.steps[-1].data = {"chars": len(snippet), "preview": snippet[:120]}

    report.total_ms = (time.monotonic() - started) * 1000.0
    return report
