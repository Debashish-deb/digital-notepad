"""Production RAG fixes — project workspace, copilot cache, intent min scores."""
from __future__ import annotations

from unittest.mock import patch

from omeia.api.embedding_service import embedding_provider
from omeia.api.retrieval_cache import (
    clear_cache,
    get_copilot_cached,
    make_copilot_cache_key,
    set_copilot_cached,
)
from omeia.api.search_service import copilot_min_score


def test_embedding_provider_auto_falls_back_to_hash():
    with patch("omeia.api.embedding_service._ollama_embed_available", return_value=False):
        with patch.dict("os.environ", {"EMBEDDING_PROVIDER": "auto"}, clear=False):
            assert embedding_provider() == "hash"


def test_embedding_provider_auto_uses_ollama_when_up():
    with patch("omeia.api.embedding_service._ollama_embed_available", return_value=True):
        with patch.dict("os.environ", {"EMBEDDING_PROVIDER": "auto"}, clear=False):
            assert embedding_provider() == "ollama"


def test_copilot_min_score_per_intent():
    assert copilot_min_score("project_question") < copilot_min_score("research_question")
    assert copilot_min_score("unknown_intent") == copilot_min_score(None)


def test_copilot_cache_roundtrip():
    clear_cache()
    key = make_copilot_cache_key(
        query="EyeMT project overview",
        intent="project_question",
        project_codes=["EyeMT"],
        user_role="researcher",
        include_restricted=False,
        limit=12,
    )
    payload = [{"id": "x", "bucket": "file", "title": "t", "snippet": "s", "score": 0.5}]
    set_copilot_cached(key, payload)
    assert get_copilot_cached(key) == payload


def test_project_knowledge_format_hit():
    from omeia.api.project_knowledge_store import _format_hit

    hit = _format_hit(
        1,
        0.82,
        {
            "chunk_id": "DOC-CHK-0",
            "document_code": "EYEMT-DOC-1",
            "title": "slides.pptx",
            "relative_path": "docs/slides.pptx",
            "project_code": "EyeMT",
            "text_preview": "GeoMx spatial transcriptomics progress",
        },
    )
    assert hit["corpus"] == "project_workspace"
    assert hit["project_code"] == "EyeMT"
