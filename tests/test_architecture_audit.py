"""Tests for architecture audit items (pool, lazy clients, readiness, catalog API)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

_AUTH_SKIP_HEADERS = {"X-Platform-Auth-Skip": "testing"}


def _catalog_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Client for knowledge routes with auth enabled and dev skip header."""
    monkeypatch.setenv("ENABLE_REQUEST_METRICS", "false")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("PLATFORM_AUTH_DISABLED", "false")
    monkeypatch.setenv("PLATFORM_AUTH_ALLOW_SKIP", "true")
    from app_skeleton.security import auth

    monkeypatch.setattr(auth, "APP_ENV", "development")
    monkeypatch.setattr(auth, "AUTH_DISABLED", False)
    monkeypatch.setattr(auth, "AUTH_ALLOW_SKIP", True)
    from app_skeleton.api.main import app

    return TestClient(app)


def test_db_pool_init_and_close(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_POOL_MIN", "1")
    monkeypatch.setenv("POSTGRES_POOL_MAX", "2")
    from app_skeleton.api import db_pool

    db_pool.close_pool()
    assert db_pool.pool_available() is False
    db_pool.init_pool("postgresql://user:pass@127.0.0.1:5432/testdb")
    if db_pool.pool_available():
        db_pool.close_pool()
        assert db_pool.pool_available() is False


def test_db_pool_accepts_size_suffix_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_POOL_MIN_SIZE", "2")
    monkeypatch.setenv("POSTGRES_POOL_MAX_SIZE", "8")
    from app_skeleton.api import db_pool

    min_size, max_size = db_pool._pool_bounds()
    assert min_size == 2
    assert max_size == 8


def test_lazy_clients_warm_on_demand(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QDRANT_URL", "http://127.0.0.1:6333")
    from app_skeleton.api import service_clients as sc

    sc._ServiceHolder.qdrant = None
    sc._ServiceHolder.llm = None
    sc._ServiceHolder.rag = None
    assert sc._ServiceHolder.qdrant is None
    with patch("app_skeleton.api.service_clients.QdrantClient") as mock_qdrant:
        mock_qdrant.return_value = MagicMock(name="qdrant")
        with patch("app_skeleton.api.service_clients.LLMClient") as mock_llm:
            mock_llm.return_value = MagicMock(name="llm")
            with patch("app_skeleton.api.service_clients.RAGAgent") as mock_rag:
                mock_rag.return_value = MagicMock(name="rag")
                sc.warm_clients()
    assert sc._ServiceHolder.qdrant is not None


def test_readiness_requires_qdrant_when_indexing_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KNOWLEDGE_INDEXER_ENABLED", "true")
    monkeypatch.setenv("VECTORIZATION_ENABLED", "false")
    from app_skeleton.api.readiness import check_readiness

    bad_client = MagicMock()
    bad_client.get_collections.side_effect = RuntimeError("connection refused")
    report = check_readiness(db_conn="", qdrant_client=bad_client, llm_client=MagicMock())
    assert report["ready"] is False
    assert any("qdrant" in b for b in report["blockers"])


def test_scheduled_scanner_status_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_REQUEST_METRICS", "false")
    from app_skeleton.api.main import app

    client = TestClient(app)
    resp = client.get("/api/platform/scheduled-scanner/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "enabled" in body
    assert "directories" in body


def test_catalog_api_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _catalog_client(monkeypatch)
    resp = client.get("/api/database/catalog", headers=_AUTH_SKIP_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert "sections" in body
    assert "total_documents" in body


def test_lab_manifest_api(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _catalog_client(monkeypatch)
    resp = client.get("/api/database/manifest", headers=_AUTH_SKIP_HEADERS)
    assert resp.status_code == 200
    assert "sections" in resp.json()
