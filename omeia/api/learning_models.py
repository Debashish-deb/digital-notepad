"""Pydantic models and enums for Teacher-Student continuous learning."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class StorageStatus(str, Enum):
    VERIFIED = "VERIFIED"
    DRAFT = "DRAFT"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    REJECTED = "REJECTED"
    DEPRECATED = "DEPRECATED"


class KnowledgeEntityType(str, Enum):
    CANCER_TYPE = "cancer_type"
    MARKER = "marker"
    GENE = "gene"
    PROTEIN = "protein"
    CELL_TYPE = "cell_type"
    PATHWAY = "pathway"
    DRUG = "drug"
    THERAPY = "therapy"
    PATIENT_COHORT = "patient_cohort"
    DATASET = "dataset"
    EXPERIMENT = "experiment"
    PUBLICATION = "publication"
    RESEARCH_PROJECT = "research_project"
    METHOD = "method"
    OUTCOME = "outcome"


class FeedbackType(str, Enum):
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    MARK_USEFUL = "mark_useful"
    MARK_INCORRECT = "mark_incorrect"
    NEEDS_REVIEW = "needs_review"
    SAVE_TO_KNOWLEDGE_BASE = "save_to_knowledge_base"


class ModelRole(str, Enum):
    TEACHER = "teacher"
    STUDENT = "student"
    EXPERT = "expert"


class PipelineStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ClaimType(str, Enum):
    FACTUAL = "factual"
    METHOD = "method"
    INTERPRETATION = "interpretation"
    HYPOTHESIS = "hypothesis"
    NOTE = "note"


class ReviewAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    DEPRECATE = "deprecate"


class EvidenceSourceInput(BaseModel):
    source_type: str = "citation"
    title: Optional[str] = None
    url: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    accession: Optional[str] = None
    chunk_id: Optional[str] = None
    source_uuid: Optional[str] = None
    excerpt: Optional[str] = None
    confidence_score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class RecordResponseRequest(BaseModel):
    query_text: str
    answer_text: str
    session_id: Optional[str] = None
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    model_role: ModelRole = ModelRole.STUDENT
    intent: Optional[str] = None
    project_codes: list[str] = Field(default_factory=list)
    sources: list[EvidenceSourceInput] = Field(default_factory=list)
    run_pipeline: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class FeedbackRequest(BaseModel):
    response_id: UUID
    feedback_type: FeedbackType
    rating: Optional[int] = Field(default=None, ge=-1, le=1)
    comment: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeReviewRequest(BaseModel):
    action: ReviewAction
    comment: Optional[str] = None


class AIResponseRecord(BaseModel):
    response_id: UUID
    session_id: Optional[str] = None
    user_email: Optional[str] = None
    query_text: str
    answer_text: str
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    model_role: str = "student"
    intent: Optional[str] = None
    project_codes: list[str] = Field(default_factory=list)
    citation_count: int = 0
    has_citations: bool = False
    pipeline_status: str = "pending"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


class ExtractedClaimRecord(BaseModel):
    claim_id: UUID
    response_id: UUID
    claim_text: str
    claim_type: str = "factual"
    confidence_score: float = 0.0
    has_citation: bool = False
    extraction_method: str = "rule_based"
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeItemRecord(BaseModel):
    knowledge_id: UUID
    response_id: Optional[UUID] = None
    claim_id: Optional[UUID] = None
    title: str
    content: str
    storage_status: StorageStatus = StorageStatus.DRAFT
    confidence_score: float = 0.0
    has_citation: bool = False
    entity_type: Optional[str] = None
    classification: Optional[str] = None
    version: int = 1
    supersedes_id: Optional[UUID] = None
    contradiction_flags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


class GraphEdgeRecord(BaseModel):
    edge_id: UUID
    knowledge_id: Optional[UUID] = None
    subject_name: str
    subject_type: str
    relation_type: str
    object_name: str
    object_type: str
    confidence_score: float = 0.0
    evidence_text: Optional[str] = None
    storage_status: StorageStatus = StorageStatus.DRAFT
    version: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)


class PipelineResult(BaseModel):
    response_id: UUID
    pipeline_status: PipelineStatus
    claims: list[ExtractedClaimRecord] = Field(default_factory=list)
    knowledge_items: list[KnowledgeItemRecord] = Field(default_factory=list)
    graph_edges: list[GraphEdgeRecord] = Field(default_factory=list)
    contradictions: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class LearningRetrievalHit(BaseModel):
    knowledge_id: str
    title: str
    content: str
    storage_status: StorageStatus
    confidence_score: float
    has_citation: bool
    bucket: str = "lab_knowledge"
    score: float = 0.0
    warning: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
