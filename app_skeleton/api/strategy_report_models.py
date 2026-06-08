"""Structured Research Strategy Assistant answer schema."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ConfidenceLevel = Literal["high", "medium", "low"]


class StrategyEvidenceRef(BaseModel):
    title: str
    source_type: str = ""
    bucket: str = ""
    snippet: str = ""
    doi: str | None = None
    pmid: str | None = None
    source_url: str | None = None
    evidence_index: int | None = None


class RecommendedDirection(BaseModel):
    title: str
    rationale: str
    internal_evidence: list[StrategyEvidenceRef] = Field(default_factory=list)
    external_evidence: list[StrategyEvidenceRef] = Field(default_factory=list)
    confidence: ConfidenceLevel = "medium"
    risks: list[str] = Field(default_factory=list)
    validation_experiments: list[str] = Field(default_factory=list)
    expected_impact: str = ""


class ResearchStrategyReport(BaseModel):
    answer_type: Literal["research_strategy"] = "research_strategy"
    executive_summary: str
    recommended_directions: list[RecommendedDirection] = Field(default_factory=list)
    evidence_summary: str = ""
    knowledge_gaps: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    alternative_interpretations: list[str] = Field(default_factory=list)
    suggested_next_actions: list[str] = Field(default_factory=list)
    references: list[StrategyEvidenceRef] = Field(default_factory=list)
    confidence_overall: ConfidenceLevel = "medium"

    def to_public_dict(self) -> dict:
        return self.model_dump()
