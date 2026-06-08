from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, HttpUrl

AccessLevel = Literal["public", "internal", "restricted"]
IngestionStatus = Literal["discovered", "fetched", "parsed", "chunked", "indexed", "evaluated", "failed"]

class ResearchSource(BaseModel):
    source_id: str | None = None
    source_type: str
    title: str
    url: str | None = None
    canonical_url: str | None = None
    doi: str | None = None
    pmid: str | None = None
    dataset_accession: str | None = None
    publisher: str | None = None
    journal: str | None = None
    publication_year: int | None = None
    authors: list[dict[str, Any]] = Field(default_factory=list)
    abstract: str | None = None
    license: str | None = None
    access_level: AccessLevel = "public"
    checksum: str | None = None
    status: IngestionStatus = "discovered"
    metadata: dict[str, Any] = Field(default_factory=dict)

class ResearchDocument(BaseModel):
    document_id: str | None = None
    source_id: str | None = None
    title: str
    document_type: str = "unknown"
    raw_text: str | None = None
    clean_text: str | None = None
    summary: str | None = None
    key_findings: list[str] = Field(default_factory=list)
    methods: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    data_availability: str | None = None
    citation_text: str | None = None
    visibility: AccessLevel = "public"
    metadata: dict[str, Any] = Field(default_factory=dict)

class ResearchChunk(BaseModel):
    chunk_id: str | None = None
    document_id: str
    chunk_index: int
    text: str
    text_hash: str
    token_count: int | None = None
    section_title: str | None = None
    qdrant_collection: str | None = None
    qdrant_point_id: str | None = None
    vector_status: str = "pending"
    metadata: dict[str, Any] = Field(default_factory=dict)

class ResearchDataset(BaseModel):
    dataset_id: str | None = None
    accession: str | None = None
    source_database: str
    title: str
    disease: str | None = None
    modality: list[str] = Field(default_factory=list)
    organism: str = "Homo sapiens"
    sample_count: str | None = None
    patient_count: str | None = None
    technology: list[str] = Field(default_factory=list)
    url: str | None = None
    related_source_id: str | None = None
    access_level: AccessLevel = "public"
    license: str | None = None
    usable_for: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

class KnowledgeEntity(BaseModel):
    entity_id: str | None = None
    name: str
    normalized_name: str
    entity_type: str
    aliases: list[str] = Field(default_factory=list)
    description: str | None = None
    source_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)

class KnowledgeRelation(BaseModel):
    relation_id: str | None = None
    subject_entity_id: str
    relation_type: str
    object_entity_id: str
    evidence_text: str | None = None
    source_id: str | None = None
    confidence: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)

class ResearchSearchHit(BaseModel):
    id: str
    bucket: str
    title: str
    snippet: str = ""
    score: float = 0.0
    source_url: str | None = None
    source_type: str | None = None
    doi: str | None = None
    pmid: str | None = None
    dataset_accession: str | None = None
    access_level: AccessLevel = "public"
    entities: list[str] = Field(default_factory=list)
    nav: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

class ResearchKnowledgeStatus(BaseModel):
    qdrant_connected: bool = False
    collection: str = "research_knowledge"
    vector_name: str = "text"
    schema_ok: bool = False
    points_count: int = 0
    source_count: int = 0
    document_count: int = 0
    chunk_count: int = 0
    dataset_count: int = 0
    entity_count: int = 0
    relation_count: int = 0
    warnings: list[str] = Field(default_factory=list)
