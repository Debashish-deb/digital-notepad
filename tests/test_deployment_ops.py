"""Deployment safety: metrics, startup validation, sync health."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from omeia.api.middleware.metrics import metrics_enabled, snapshot_metrics
from omeia.api.startup_validation import validate_deployment_environment


def test_metrics_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENABLE_REQUEST_METRICS", raising=False)
    assert metrics_enabled() is False


def test_metrics_endpoint_reports_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_REQUEST_METRICS", "false")
    from omeia.api.main import app

    client = TestClient(app)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert resp.json().get("enabled") is False


def test_metrics_collect_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_REQUEST_METRICS", "true")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATABASE_ROOT", "/tmp")
    monkeypatch.setenv("QDRANT_URL", "http://127.0.0.1:6333")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")
    monkeypatch.setenv("TEXT_EMBEDDING_DIM", "768")
    from omeia.api.main import app

    client = TestClient(app)
    client.get("/health")
    snap = snapshot_metrics()
    assert snap["requests_total"] >= 1
    assert "200" in snap["requests_by_status"]


def test_live_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_REQUEST_METRICS", "false")
    from omeia.api.main import app

    client = TestClient(app)
    resp = client.get("/live")
    assert resp.status_code == 200
    assert resp.json().get("status") == "alive"


def test_ready_endpoint_reports_postgres(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_REQUEST_METRICS", "false")
    from omeia.api.main import app

    client = TestClient(app)
    resp = client.get("/ready")
    body = resp.json()
    assert "ready" in body
    assert "checks" in body
    if body.get("ready"):
        assert resp.status_code == 200
    else:
        assert resp.status_code == 503


def test_health_still_works(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_REQUEST_METRICS", "false")
    from omeia.api.main import app

    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status") in ("ok", "degraded")
    assert "ready" in body
    assert "X-Request-ID" in resp.headers


def test_startup_validation_flags_missing_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("DATABASE_ROOT", "QDRANT_URL", "OLLAMA_BASE_URL", "TEXT_EMBEDDING_DIM"):
        monkeypatch.delenv(key, raising=False)
    report = validate_deployment_environment()
    assert report["ok"] is False
    assert report["issues"]


def test_sync_health_detects_missing_roots(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib.util
    from pathlib import Path

    missing_db = tmp_path / "missing-db"
    missing_projects = tmp_path / "missing-projects"
    monkeypatch.setenv("DATABASE_ROOT", str(missing_db))
    monkeypatch.setenv("PROJECTS_ROOT", str(missing_projects))

    script = Path(__file__).resolve().parents[1] / "scripts/ops/check_linux_sync_health.py"
    spec = importlib.util.spec_from_file_location("check_linux_sync_health", script)
    health = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(health)

    report = health.run_checks()
    assert report["ok"] is False
    failed = set(report["failed"])
    assert "database_root" in failed
    assert "projects_root" in failed


def test_backup_dry_run_exits_zero() -> None:
    import subprocess
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        ["bash", str(root / "scripts/ops/backup_linux.sh"), "--dry-run"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0
    assert "dry-run" in proc.stdout.lower()
