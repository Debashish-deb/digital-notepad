"""Shared search contracts for unified platform search."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

SearchBucket = Literal[
    "lab",
    "vault",
    "notebook",
    "wiki",
    "decision",
    "task",
    "project",
    "file",
    "model",
    "dataset",
    "research",
    "people",
    "conversation",
]

SearchMode = Literal["keyword", "semantic", "hybrid", "exact"]


class SearchNavAction(BaseModel):
    main: str
    sub: Optional[str] = None
    project_code: Optional[str] = None
    section_id: Optional[str] = None
    document_id: Optional[str] = None
    entry_id: Optional[str] = None
    wiki_id: Optional[str] = None
    decision_id: Optional[str] = None
    task_id: Optional[str] = None
    relative_path: Optional[str] = None
    query: Optional[str] = None
    hash: Optional[str] = None


class SearchHit(BaseModel):
    id: str
    bucket: SearchBucket
    title: str
    snippet: str = ""
    score: float = 0.0
    rank: int = 0
    source: str = ""
    source_type: Optional[str] = None
    project_code: Optional[str] = None
    section_id: Optional[str] = None
    page_domain_id: Optional[str] = None
    document_code: Optional[str] = None
    relative_path: Optional[str] = None
    visibility_level: Optional[str] = None
    updated_at: Optional[str] = None
    created_at: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    nav: Optional[SearchNavAction] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class UnifiedSearchResponse(BaseModel):
    query: str
    mode: SearchMode = "hybrid"
    scopes: list[str] = Field(default_factory=list)
    project_code: Optional[str] = None
    section_id: Optional[str] = None
    page_domain_id: Optional[str] = None
    total: int = 0
    offset: int = 0
    limit: int = 25
    hits: list[SearchHit] = Field(default_factory=list)
    buckets: dict[str, int] = Field(default_factory=dict)
    suggestions: list[str] = Field(default_factory=list)
    synonym_hints: list[str] = Field(default_factory=list)
    explain: Optional[dict[str, Any]] = None


class SearchSuggestionsResponse(BaseModel):
    query: str = ""
    suggestions: list[str] = Field(default_factory=list)
    synonym_hints: list[str] = Field(default_factory=list)
    recent_queries: list[str] = Field(default_factory=list)
