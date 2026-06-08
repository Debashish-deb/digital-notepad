"""Shared search contracts for unified platform search."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

SearchBucket = Literal[
    "lab",
    "vault",
    "vault_review",
    "document_library",
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

ADVANCED_FILTER_FIELDS = (
    "category",
    "smart_chip",
    "domain_tab",
    "system_view",
    "file_type",
    "date_from",
    "date_to",
    "indexed_status",
    "project_codes",
    "section_id",
    "source_buckets",
)


class SearchFilters(BaseModel):
    """Optional advanced filters — all fields optional; AND logic when multiple set."""

    category: Optional[str] = None
    smart_chip: Optional[str] = None
    domain_tab: Optional[str] = None
    system_view: Optional[str] = None
    file_type: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    indexed_status: Optional[str] = None
    project_codes: Optional[str] = None
    section_id: Optional[str] = None
    source_buckets: Optional[str] = None

    def active_fields(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for name in ADVANCED_FILTER_FIELDS:
            val = getattr(self, name, None)
            if val is not None and str(val).strip():
                out[name] = str(val).strip()
        return out


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
    filters_applied: dict[str, Any] = Field(default_factory=dict)
    unsupported_filters: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchSuggestionsResponse(BaseModel):
    query: str = ""
    suggestions: list[str] = Field(default_factory=list)
    synonym_hints: list[str] = Field(default_factory=list)
    recent_queries: list[str] = Field(default_factory=list)
