"""Phase 1 feature flags."""
from __future__ import annotations

import os

import pytest

from app_skeleton.api.platform_flags import (
    canonical_chunk_pipeline_enabled,
    knowledge_indexer_enabled,
    platform_chunk_write_enabled,
    require_auth_static_enabled,
    vault_json_fallback_enabled,
    vault_use_vector_indexer_enabled,
)


@pytest.mark.parametrize(
    "env,expected",
    [
        ("true", True),
        ("false", False),
        ("1", True),
        ("0", False),
    ],
)
def test_knowledge_indexer_flag(monkeypatch: pytest.MonkeyPatch, env: str, expected: bool) -> None:
    monkeypatch.setenv("KNOWLEDGE_INDEXER_ENABLED", env)
    assert knowledge_indexer_enabled() is expected


def test_platform_chunk_write_defaults_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PLATFORM_CHUNK_WRITE", raising=False)
    assert platform_chunk_write_enabled() is True


def test_vault_json_fallback_defaults_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VAULT_JSON_FALLBACK", raising=False)
    assert vault_json_fallback_enabled() is True


def test_require_auth_static_defaults_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REQUIRE_AUTH_STATIC", raising=False)
    assert require_auth_static_enabled() is False


def test_vault_use_vector_indexer_defaults_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VAULT_USE_VECTOR_INDEXER", raising=False)
    assert vault_use_vector_indexer_enabled() is False


def test_canonical_chunk_pipeline_defaults_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CANONICAL_CHUNK_PIPELINE", raising=False)
    assert canonical_chunk_pipeline_enabled() is False
