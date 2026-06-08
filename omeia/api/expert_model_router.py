"""Layer 3 expert model routing — map intent + agent category to specialist Ollama models."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Literal

from omeia.api.chat_intent import IntentDecision
from omeia.api.platform_flags import expert_routing_enabled

LayerName = Literal["conversation", "expert", "default"]

_ONCOLOGY_TERMS = re.compile(
    r"\b(hgsc|hgsoc|ovarian|oncolog|tumor|tumour|immunotherap|biomarker|tls|tme|"
    r"microenvironment|chemotherap|brca|tp53|hrd|checkpoint|car-t|pd-1|pd-l1)\b",
    re.I,
)
_SPATIAL_TERMS = re.compile(
    r"\b(spatial|visium|geomx|cycif|tcycif|multiplex|imaging|stardist|ashlar|"
    r"cell neighborhood|deconvolution|mihc|imc)\b",
    re.I,
)
_LITERATURE_TERMS = re.compile(
    r"\b(literature|publication|paper|pubmed|doi|review|meta-analysis|citation|manuscript)\b",
    re.I,
)
_BIOINFO_TERMS = re.compile(
    r"\b(single.?cell|scrna|rna-seq|bioinformatic|pipeline|deseq|scanpy|seurat|statistics)\b",
    re.I,
)

_CATEGORY_DEFAULTS: dict[str, str] = {
    "cancer_oncology": "OMEIA_ONCOLOGY_MODEL",
    "spatial_multiplex": "OMEIA_SPATIAL_MODEL",
    "literature_evidence": "OMEIA_LITERATURE_MODEL",
    "bioinformatics_omics": "OMEIA_BIOINFORMATICS_MODEL",
    "wet_lab_cycif": "OMEIA_PROTOCOL_MODEL",
    "general_research": "OLLAMA_MODEL",
}

_ENV_DEFAULTS: dict[str, str] = {
    "OMEIA_ONCOLOGY_MODEL": "medllama2:7b",
    "OMEIA_ONCOLOGY_FALLBACK_MODEL": "medgemma:4b",
    "OMEIA_SPATIAL_MODEL": "qwen2.5:7b-instruct",
    "OMEIA_LITERATURE_MODEL": "meditron:7b",
    "OMEIA_BIOINFORMATICS_MODEL": "qwen2.5:7b-instruct",
    "OMEIA_PROTOCOL_MODEL": "llama3.1:8b",
    "CHAT_GREETING_MODEL": "qwen2.5:3b",
    "CHAT_CONVERSATION_MODEL": "qwen2.5:7b-instruct",
    "CHAT_SUMMARY_MODEL": "qwen2.5:7b-instruct",
    "OLLAMA_MODEL": "qwen2.5:3b",
}


@dataclass(frozen=True)
class ExpertRouteDecision:
    provider: str
    model: str
    reason: str
    confidence: float
    layer: LayerName
    routing_enabled: bool = True


def _env_model(key: str) -> str:
    default = _ENV_DEFAULTS.get(key, "qwen2.5:3b")
    return (os.getenv(key, default) or default).strip() or default


def is_conversation_only_intent(decision: IntentDecision) -> bool:
    """Layer 2 — no retrieval, no expert models."""
    if decision.intent == "smalltalk":
        return True
    if decision.intent in {"app_help", "coding_request", "document_ingestion_help", "sensitive_private"}:
        return True
    if decision.intent == "general_chat" and not decision.use_rag:
        return True
    return False


def resolve_expert_model(
    decision: IntentDecision,
    message: str = "",
    *,
    agent_category: str | None = None,
) -> ExpertRouteDecision | None:
    """
    Return specialist model routing when OMEIA_EXPERT_ROUTING_ENABLED=true.
    None → caller keeps existing resolve_route_model / default LLM.
    """
    if not expert_routing_enabled():
        return None

    if is_conversation_only_intent(decision):
        if decision.intent == "smalltalk":
            return ExpertRouteDecision(
                provider="ollama",
                model=_env_model("CHAT_GREETING_MODEL"),
                reason="smalltalk_greeting",
                confidence=0.95,
                layer="conversation",
            )
        return ExpertRouteDecision(
            provider="ollama",
            model=_env_model("CHAT_CONVERSATION_MODEL"),
            reason="conversation_no_rag",
            confidence=0.9,
            layer="conversation",
        )

    text = (message or "").lower()
    category = (agent_category or "").strip().lower()

    if category == "cancer_oncology":
        model = _env_model("OMEIA_ONCOLOGY_MODEL")
        return ExpertRouteDecision(
            provider="ollama",
            model=model,
            reason="oncology_expert",
            confidence=0.88,
            layer="expert",
        )

    if category == "spatial_multiplex":
        return ExpertRouteDecision(
            provider="ollama",
            model=_env_model("OMEIA_SPATIAL_MODEL"),
            reason="spatial_expert",
            confidence=0.86,
            layer="expert",
        )

    if category == "literature_evidence":
        return ExpertRouteDecision(
            provider="ollama",
            model=_env_model("OMEIA_LITERATURE_MODEL"),
            reason="literature_synthesis",
            confidence=0.84,
            layer="expert",
        )

    if category == "bioinformatics_omics":
        return ExpertRouteDecision(
            provider="ollama",
            model=_env_model("OMEIA_BIOINFORMATICS_MODEL"),
            reason="bioinformatics_expert",
            confidence=0.83,
            layer="expert",
        )

    if category == "wet_lab_cycif":
        return ExpertRouteDecision(
            provider="ollama",
            model=_env_model("OMEIA_PROTOCOL_MODEL"),
            reason="protocol_wet_lab",
            confidence=0.82,
            layer="expert",
        )

    if _ONCOLOGY_TERMS.search(text):
        return ExpertRouteDecision(
            provider="ollama",
            model=_env_model("OMEIA_ONCOLOGY_MODEL"),
            reason="oncology_terms_detected",
            confidence=0.88,
            layer="expert",
        )

    if _SPATIAL_TERMS.search(text):
        return ExpertRouteDecision(
            provider="ollama",
            model=_env_model("OMEIA_SPATIAL_MODEL"),
            reason="spatial_terms_detected",
            confidence=0.86,
            layer="expert",
        )

    if decision.intent == "search_request" or _LITERATURE_TERMS.search(text):
        return ExpertRouteDecision(
            provider="ollama",
            model=_env_model("OMEIA_LITERATURE_MODEL"),
            reason="literature_synthesis",
            confidence=0.84,
            layer="expert",
        )

    if _BIOINFO_TERMS.search(text):
        return ExpertRouteDecision(
            provider="ollama",
            model=_env_model("OMEIA_BIOINFORMATICS_MODEL"),
            reason="bioinformatics_expert",
            confidence=0.83,
            layer="expert",
        )

    if decision.intent == "protocol_question":
        return ExpertRouteDecision(
            provider="ollama",
            model=_env_model("OMEIA_PROTOCOL_MODEL"),
            reason="protocol_wet_lab",
            confidence=0.82,
            layer="expert",
        )

    if category and category in _CATEGORY_DEFAULTS:
        env_key = _CATEGORY_DEFAULTS[category]
        return ExpertRouteDecision(
            provider="ollama",
            model=_env_model(env_key),
            reason=f"category_default:{category}",
            confidence=0.75,
            layer="expert",
        )

    if decision.use_rag and decision.intent in {"research_question", "project_question"}:
        return ExpertRouteDecision(
            provider="ollama",
            model=_env_model("CHAT_SUMMARY_MODEL"),
            reason="research_with_retrieval",
            confidence=0.8,
            layer="default",
        )

    return None


def route_metadata(decision: ExpertRouteDecision | None) -> dict[str, str | float | bool]:
    if not decision:
        return {}
    return {
        "expert_routing_enabled": decision.routing_enabled,
        "expert_layer": decision.layer,
        "expert_model": decision.model,
        "expert_route_reason": decision.reason,
        "expert_route_confidence": decision.confidence,
    }
