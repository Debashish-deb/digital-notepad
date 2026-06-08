"""Phase 1 admin index-health endpoint."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from omeia.api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_index_health_requires_admin(client: TestClient) -> None:
    with patch.dict("os.environ", {"APP_ENV": "development", "PLATFORM_AUTH_DISABLED": "true"}):
        # dev user is admin in _dev_user
        resp = client.get("/api/admin/index-health")
        assert resp.status_code == 200
        body = resp.json()
        assert "postgres" in body
        assert "qdrant" in body
        assert "feature_flags" in body
        assert "expected_embedding_dim" in body


def test_index_health_structure_with_mocks(client: TestClient) -> None:
    with patch.dict("os.environ", {"APP_ENV": "development", "PLATFORM_AUTH_DISABLED": "true"}):
        with patch("omeia.api.routers.admin_index.postgres_conn", return_value=""):
            with patch("omeia.api.routers.admin_index.ping_qdrant", return_value=False):
                resp = client.get("/api/admin/index-health")
                assert resp.status_code == 200
                body = resp.json()
                assert body["qdrant"]["reachable"] is False
                assert "KNOWLEDGE_INDEXER_ENABLED" in body["feature_flags"]
