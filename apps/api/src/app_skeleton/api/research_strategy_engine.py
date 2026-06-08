"""Research Strategy Engine — multi-agent strategic synthesis over SearchService evidence."""
from __future__ import annotations

import logging
import re
from typing import Any, Literal

from app_skeleton.api.chat_intent import IntentDecision
from app_skeleton.api.evidence_orchestrator import (
    EvidencePackage,
    QueryUnderstanding,
    package_evidence,
    understand_query,
)
from app_skeleton.api.platform_flags import (
    strategy_external_search_enabled,
    strategy_report_mode_enabled,
    strategy_require_citations_enabled,
)
from app_skeleton.api.search_service import SearchService
from app_skeleton.api.strategy_agents import (
    BioinformaticsAgent,
    BiomarkerAgent,
    ExperimentalDesignAgent,
    LiteratureAgent,
    ResearchGapAgent,
    SpatialBiologyAgent,
)
from app_skeleton.api.strategy_agents._base import EXTERNAL_BUCKETS, INTERNAL_BUCKETS, item_to_ref
from app_skeleton.api.strategy_report_models import (
    RecommendedDirection,
    ResearchStrategyReport,
    StrategyEvidenceRef,
)

LOGGER = logging.getLogger(__name__)

STRATEGY_QUESTION_RE = re.compile(
    r"\b("
    r"what should (?:we|i) (?:investigate|study|prioritize|focus)|"
    r"which (?:biomarker|experiment|dataset|direction|project)|"
    r"what gaps? (?:exist|in)|"
    r"highest[- ]value|"
    r"strongest (?:direction|evidence)|"
    r"risks? (?:exist|in)|"
    r"next study|research plan|research strategy|"
    r"recommend(?:ation)?s? for (?:our|the) (?:next|future)|"
    r"three strongest directions|"
    r"underexplored|knowledge gap|validation experiment"
    r")\b",
    re.I,
)

STRATEGY_SCOPES = (
    "research",
    "lab",
    "file",
    "vault",
    "document_library",
    "notebook",
    "wiki",
    "project",
    "people",
)

STRATEGY_BUCKET_PRIORITY = (
    "research",
    "lab",
    "project",
    "file",
    "vault",
    "document_library",
    "notebook",
    "wiki",
)

INSUFFICIENT_MESSAGE = (
    "Available evidence is insufficient to make a strong recommendation."
)


def is_strategy_question(message: str, intent_decision: IntentDecision | None = None) -> bool:
    text = (message or "").strip()
    if not text or len(text) < 12:
        return False
    if STRATEGY_QUESTION_RE.search(text):
        return True
    if intent_decision and intent_decision.intent in {"research_question", "project_question"}:
        if re.search(r"\b(direction|priorit|strategy|gap|risk|validation|next step)\b", text, re.I):
            return True
    return False


def _confidence_from_package(package: EvidencePackage) -> Literal["high", "medium", "low"]:
    mapping = {"high": "high", "medium": "medium", "low": "low", "insufficient": "low"}
    return mapping.get(package.confidence, "low")  # type: ignore[return-value]


def _rank_directions(
    *,
    biomarker: dict[str, Any],
    spatial: dict[str, Any],
    bioinfo: dict[str, Any],
    literature: dict[str, Any],
    experimental: dict[str, Any],
    package: EvidencePackage,
) -> list[RecommendedDirection]:
    directions: list[RecommendedDirection] = []
    overall_conf = _confidence_from_package(package)

    if spatial.get("internal_refs") or spatial.get("spatial_patterns"):
        directions.append(
            RecommendedDirection(
                title="Spatial TME / multiplex imaging follow-up",
                rationale=" ".join(spatial.get("spatial_patterns") or [])[:500],
                internal_evidence=spatial.get("internal_refs") or [],
                external_evidence=(literature.get("external_refs") or [])[:3],
                confidence=overall_conf if len(spatial.get("internal_refs") or []) >= 2 else "medium",
                risks=experimental.get("risks") or [],
                validation_experiments=(experimental.get("experiments") or [])[:3],
                expected_impact="Clarifies immune architecture and candidate niches for translational hypotheses.",
            )
        )

    if biomarker.get("internal_refs"):
        directions.append(
            RecommendedDirection(
                title="Biomarker prioritization and panel refinement",
                rationale=" ".join(biomarker.get("marker_suggestions") or [])[:500],
                internal_evidence=biomarker.get("internal_refs") or [],
                external_evidence=(literature.get("external_refs") or [])[:2],
                confidence="high" if biomarker.get("evidence_strength") == "high" else "medium",
                risks=["Marker redundancy or batch effects may inflate apparent signal."],
                validation_experiments=[
                    "Orthogonal IHC or targeted spatial validation of top-ranked markers.",
                ],
                expected_impact="Focuses wet-lab and analysis resources on markers with indexed support.",
            )
        )

    if bioinfo.get("workflows"):
        directions.append(
            RecommendedDirection(
                title="Computational / dataset integration",
                rationale=" ".join(bioinfo.get("workflows") or [])[:500],
                internal_evidence=[r for r in (bioinfo.get("refs") or []) if r.bucket in INTERNAL_BUCKETS],
                external_evidence=[r for r in (bioinfo.get("refs") or []) if r.bucket in EXTERNAL_BUCKETS],
                confidence=overall_conf,
                risks=["Analysis reproducibility risk without frozen pipeline parameters."],
                validation_experiments=bioinfo.get("validation_analyses") or [],
                expected_impact="Links internal cohorts to reproducible bioinformatics workflows.",
            )
        )

    if not directions and package.items:
        top = package.items[0]
        directions.append(
            RecommendedDirection(
                title="Evidence-guided exploratory study",
                rationale=f"Top retrieved source: {top.title}. Expand ingestion before large commits.",
                internal_evidence=[item_to_ref(top)],
                external_evidence=[],
                confidence="low",
                risks=["Single-source strategic basis — high uncertainty."],
                validation_experiments=experimental.get("experiments") or ["Small pilot before scale-up."],
                expected_impact="Low until additional corroborating evidence is indexed.",
            )
        )

    return directions[:3]


def _references_from_package(package: EvidencePackage, limit: int = 12) -> list[StrategyEvidenceRef]:
    refs: list[StrategyEvidenceRef] = []
    for item in package.items[:limit]:
        if item.doi or item.pmid or item.source_url or item.bucket == "research":
            refs.append(item_to_ref(item))
    return refs


def _render_answer_text(report: ResearchStrategyReport) -> str:
    """Human-readable fallback (UI uses structured strategy_report)."""
    lines = [report.executive_summary, ""]
    for i, direction in enumerate(report.recommended_directions, 1):
        lines.append(f"### {i}. {direction.title}")
        lines.append(direction.rationale)
        if direction.validation_experiments:
            lines.append("**Validation:** " + "; ".join(direction.validation_experiments[:3]))
        lines.append("")
    if report.limitations:
        lines.append("**Limitations:** " + " ".join(report.limitations[:3]))
    return "\n".join(lines).strip()


class ResearchStrategyEngine:
    """Orchestrates strategy agents over retrieved evidence — never answers without retrieval."""

    def __init__(self, search_svc: SearchService, llm: Any | None = None) -> None:
        self.search_svc = search_svc
        self.llm = llm
        self.literature = LiteratureAgent()
        self.biomarker = BiomarkerAgent()
        self.spatial = SpatialBiologyAgent()
        self.bioinformatics = BioinformaticsAgent()
        self.gap = ResearchGapAgent()
        self.experimental = ExperimentalDesignAgent()

    def run(
        self,
        question: str,
        *,
        intent_decision: IntentDecision,
        project_codes: list[str] | None = None,
        user_role: str | None = None,
        limit: int = 18,
    ) -> dict[str, Any]:
        """Execute full strategy workflow; returns chat-compatible payload."""
        # 1–2. Understand + retrieval plan
        understanding = understand_query(question, intent_decision)

        # 3. Internal evidence
        unified_hits = self.search_svc.hits_for_copilot(
            question,
            intent=intent_decision.intent or "research_question",
            project_codes=project_codes,
            limit=limit,
            prioritize_buckets=STRATEGY_BUCKET_PRIORITY,
            user_role=user_role,
        )

        # 4. External evidence (optional extra research pull)
        external_hits: list[Any] = []
        if strategy_external_search_enabled():
            try:
                from app_skeleton.api.research_knowledge_store import search_research

                for row in search_research(question, limit=8):
                    external_hits.append(row)
            except Exception as exc:
                LOGGER.debug("Strategy external search skipped: %s", exc)

        rag_sources: list[dict[str, Any]] = []
        evidence_package = package_evidence(
            unified_hits,
            rag_sources,
            entities=understanding.entities,
            limit=limit,
        )

        # 5–8. Agent analysis
        lit = self.literature.analyze(evidence_package, question=question)
        bio = self.biomarker.analyze(evidence_package, question=question)
        spat = self.spatial.analyze(evidence_package, question=question)
        binfo = self.bioinformatics.analyze(evidence_package, question=question)
        gaps = self.gap.analyze(evidence_package, understanding=understanding, question=question)
        design = self.experimental.analyze(evidence_package, understanding=understanding, question=question)

        contradictions = list(lit.get("contradictions") or [])
        for claim in (evidence_package.claim_validations or []):
            if claim.status == "conflicting" and claim.claim not in contradictions:
                contradictions.append(claim.claim[:220])

        insufficient = (
            len(evidence_package.items) < 2
            or evidence_package.confidence == "insufficient"
        )

        directions = [] if insufficient else _rank_directions(
            biomarker=bio,
            spatial=spat,
            bioinfo=binfo,
            literature=lit,
            experimental=design,
            package=evidence_package,
        )

        if insufficient:
            executive = INSUFFICIENT_MESSAGE
            limitations = [
                INSUFFICIENT_MESSAGE,
                "Retrieve more lab publications, protocols, project twins, or research KB sources.",
            ]
            confidence_overall: Literal["high", "medium", "low"] = "low"
        else:
            domain_label = ", ".join(understanding.domains) or "oncology/spatial biology"
            executive = (
                f"Based on {len(evidence_package.items)} indexed sources across "
                f"{len(evidence_package.by_bucket)} buckets ({domain_label}), "
                f"the platform recommends {len(directions)} strategic direction(s). "
                f"Overall evidence confidence: {evidence_package.confidence}."
            )
            limitations = [
                "Recommendations are retrieval-grounded only — not clinical treatment advice.",
                f"Cross-source summary: {evidence_package.cross_source_summary or 'see evidence summary'}.",
            ]
            if strategy_require_citations_enabled():
                limitations.append("Citations limited to retrieved package indices — no invented references.")
            confidence_overall = _confidence_from_package(evidence_package)

        report = ResearchStrategyReport(
            executive_summary=executive,
            recommended_directions=directions,
            evidence_summary=evidence_package.cross_source_summary or "",
            knowledge_gaps=gaps.get("knowledge_gaps") or [],
            contradictions=contradictions[:6],
            limitations=limitations,
            alternative_interpretations=gaps.get("research_questions") or [],
            suggested_next_actions=[
                "Run platform search (⌘K) to fill identified gaps.",
                "Ingest missing protocols or publications into research KB.",
                "Link question to specific project codes for twin context.",
            ],
            references=_references_from_package(evidence_package),
            confidence_overall=confidence_overall,
        )

        answer_text = _render_answer_text(report) if strategy_report_mode_enabled() else executive

        sources_payload: list[dict[str, Any]] = []
        for hit in unified_hits[:limit]:
            sources_payload.append({
                "title": getattr(hit, "title", "Untitled"),
                "source_type": getattr(hit, "source_type", None) or getattr(hit, "bucket", "unknown"),
                "source_uuid": getattr(hit, "document_code", None) or getattr(hit, "relative_path", None) or getattr(hit, "id", ""),
                "chunk_id": getattr(hit, "id", None),
                "text_preview": getattr(hit, "snippet", ""),
                "score": float(getattr(hit, "score", 0) or 0),
                "nav": hit.nav.model_dump() if getattr(hit, "nav", None) else None,
                "bucket": getattr(hit, "bucket", None),
            })

        return {
            "answer": answer_text,
            "strategy_report": report.to_public_dict(),
            "research_strategy": True,
            "limitations": report.limitations,
            "sources": sources_payload,
            "search_hits": [h.model_dump() for h in unified_hits[:limit]],
            "evidence_orchestrator": True,
            "evidence_confidence": evidence_package.confidence,
            "evidence_count": len(evidence_package.items),
            "evidence_buckets": evidence_package.by_bucket,
            "cross_source_summary": evidence_package.cross_source_summary,
            "evidence_validation_notes": evidence_package.validation_notes,
            "claim_validations": [
                {
                    "claim": c.claim,
                    "status": c.status,
                    "supporting_indices": list(c.supporting_indices),
                    "conflicting_indices": list(c.conflicting_indices),
                    "note": c.note,
                }
                for c in (evidence_package.claim_validations or [])
            ],
            "query_domains": list(understanding.domains),
            "query_entities": list(understanding.entities),
            "search_plan": {
                "scopes": list(STRATEGY_SCOPES),
                "prioritize_buckets": list(STRATEGY_BUCKET_PRIORITY),
                "rationale": understanding.search_plan.rationale,
            },
            "strategy_agents": [
                lit.get("agent"),
                bio.get("agent"),
                spat.get("agent"),
                binfo.get("agent"),
                gaps.get("agent"),
                design.get("agent"),
            ],
            "synthesis_mode": "research_strategy",
            "use_rag": True,
            "show_sources": True,
            "require_citations": strategy_require_citations_enabled(),
        }
