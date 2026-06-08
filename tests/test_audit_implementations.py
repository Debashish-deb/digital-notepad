"""Smoke tests for OMEIA_INFORMATION_FLOW audit implementations."""
from __future__ import annotations

import inspect
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


def test_lazy_service_clients_export_proxies() -> None:
    from omeia.api import service_clients

    assert hasattr(service_clients.qdrant_client, "__getattr__")
    assert callable(service_clients.get_qdrant_client)


def test_lab_catalog_service_builds_index() -> None:
    from omeia.api.lab_catalog_service import build_catalog_index

    catalog = build_catalog_index()
    assert "sections" in catalog
    assert "total_documents" in catalog


def test_scheduled_scanner_status_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_REQUEST_METRICS", "false")
    from omeia.api.main import app

    client = TestClient(app)
    resp = client.get("/api/platform/scheduled-scanner/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "enabled" in body
    assert "directories" in body


def test_database_catalog_routes_require_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    from omeia.api.main import app

    with patch("omeia.security.auth.AUTH_DISABLED", False):
        client = TestClient(app)
        assert client.get("/api/database/catalog").status_code == 401
        assert client.get("/api/database/catalog/document/test-id").status_code == 401


def test_agent_run_route_has_request_response() -> None:
    from omeia.api.routers import agent_categories

    sig = inspect.signature(agent_categories.run_category)
    assert "request" in sig.parameters
    assert "response" in sig.parameters
