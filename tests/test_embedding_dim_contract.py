"""Embedding dimension contract — single source across qdrant modules."""
from __future__ import annotations

from unittest.mock import patch

from app_skeleton.api.embedding_service import embedding_dim
from app_skeleton.api.qdrant_collections import collection_dim
from app_skeleton.api.qdrant_research_indexer import vector_size
from app_skeleton.api.qdrant_vectors import embedding_dimension


def test_embedding_dim_default():
    with patch.dict("os.environ", {}, clear=False):
        dim = embedding_dim()
        assert 32 <= dim <= 4096


def test_collection_dim_follows_text_embedding_dim():
    with patch.dict("os.environ", {"TEXT_EMBEDDING_DIM": "768"}, clear=False):
        assert collection_dim() == 768
        assert embedding_dimension() == 768


def test_research_vector_size_defaults_from_embedding_dim():
    with patch.dict("os.environ", {"TEXT_EMBEDDING_DIM": "768", "RESEARCH_KB_VECTOR_SIZE": ""}, clear=False):
        assert vector_size() == 768


def test_research_vector_size_explicit_override():
    with patch.dict("os.environ", {"TEXT_EMBEDDING_DIM": "768", "RESEARCH_KB_VECTOR_SIZE": "512"}, clear=False):
        assert vector_size() == 512


def test_qdrant_collections_names():
    from app_skeleton.api import qdrant_collections as qc

    assert qc.DOC_CHUNKS
    assert qc.RESEARCH_KB
    assert qc.VAULT_CHUNKS
