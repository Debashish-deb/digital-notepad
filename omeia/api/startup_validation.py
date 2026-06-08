"""Deployment environment validation and startup checklist."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)

_REQUIRED_VARS = (
    "APP_ENV",
    "DATABASE_ROOT",
    "QDRANT_URL",
    "OLLAMA_BASE_URL",
    "TEXT_EMBEDDING_DIM",
)

_WARN_VARS = (
    "PLATFORM_AUTH_DISABLED",
    "PROJECTS_ROOT",
    "POSTGRES_CONN",
)


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name, default) or default).strip()


def validate_deployment_environment(*, strict: bool = False) -> dict[str, Any]:
    """Validate critical deployment variables. Returns report dict."""
    issues: list[str] = []
    warnings: list[str] = []
    checks: dict[str, Any] = {}

    for name in _REQUIRED_VARS:
        value = _env(name)
        checks[name] = value or None
        if not value:
            issues.append(f"{name} is not set")

    for name in _WARN_VARS:
        value = _env(name)
        checks[name] = value or None
        if not value and name != "PLATFORM_AUTH_DISABLED":
            warnings.append(f"{name} is not set (using defaults)")

    app_env = _env("APP_ENV", "development").lower()
    auth_disabled = _env("PLATFORM_AUTH_DISABLED", "false").lower() in ("1", "true", "yes")
    if app_env == "production" and auth_disabled:
        issues.append("PLATFORM_AUTH_DISABLED=true is unsafe when APP_ENV=production")

    db_root = _env("DATABASE_ROOT")
    if db_root:
        path = Path(db_root).expanduser()
        checks["database_root_exists"] = path.is_dir()
        if not path.is_dir():
            msg = f"DATABASE_ROOT does not exist: {db_root}"
            if strict:
                issues.append(msg)
            else:
                warnings.append(msg)

    projects_root = _env("PROJECTS_ROOT")
    if projects_root:
        path = Path(projects_root).expanduser()
        checks["projects_root_exists"] = path.is_dir()
        if not path.is_dir():
            warnings.append(f"PROJECTS_ROOT does not exist: {projects_root}")

    dim = _env("TEXT_EMBEDDING_DIM")
    if dim:
        try:
            checks["text_embedding_dim"] = int(dim)
        except ValueError:
            issues.append(f"TEXT_EMBEDDING_DIM must be an integer, got: {dim}")

    frontend_mode = _env("OMEIA_FRONTEND_MODE", "dev").lower()
    checks["omeia_frontend_mode"] = frontend_mode
    if frontend_mode == "prod":
        from omeia.api.paths import REPO_ROOT

        dist = REPO_ROOT / "apps" / "web" / "dist"
        checks["frontend_dist_exists"] = dist.is_dir()
        if not dist.is_dir():
            warnings.append(f"OMEIA_FRONTEND_MODE=prod but dist missing: {dist}")

    ok = not issues
    return {
        "ok": ok,
        "app_env": app_env,
        "issues": issues,
        "warnings": warnings,
        "checks": checks,
    }


def deployment_checklist_lines() -> list[str]:
    """Human-readable startup checklist for operators."""
    report = validate_deployment_environment()
    lines = [
        "=== OMEIA deployment checklist ===",
        f"APP_ENV={report['checks'].get('APP_ENV') or _env('APP_ENV', 'development')}",
        f"OMEIA_FRONTEND_MODE={report['checks'].get('omeia_frontend_mode', 'dev')}",
        f"DATABASE_ROOT={report['checks'].get('DATABASE_ROOT') or '(unset)'}",
        f"QDRANT_URL={report['checks'].get('QDRANT_URL') or '(unset)'}",
        f"OLLAMA_BASE_URL={report['checks'].get('OLLAMA_BASE_URL') or '(unset)'}",
        f"TEXT_EMBEDDING_DIM={report['checks'].get('TEXT_EMBEDDING_DIM') or '(unset)'}",
        f"PLATFORM_AUTH_DISABLED={report['checks'].get('PLATFORM_AUTH_DISABLED') or 'false'}",
        f"ENABLE_REQUEST_METRICS={_env('ENABLE_REQUEST_METRICS', 'false')}",
    ]
    if report["issues"]:
        lines.append("BLOCKERS:")
        lines.extend(f"  - {item}" for item in report["issues"])
    if report["warnings"]:
        lines.append("WARNINGS:")
        lines.extend(f"  - {item}" for item in report["warnings"])
    if not report["issues"] and not report["warnings"]:
        lines.append("All deployment checks passed.")
    lines.append("Endpoints: /live  /ready  /health  /metrics (when ENABLE_REQUEST_METRICS=true)")
    lines.append("Linux sync: python scripts/ops/check_linux_sync_health.py")
    lines.append("Backup dry-run: bash scripts/ops/backup_linux.sh --dry-run")
    return lines


def log_deployment_checklist() -> dict[str, Any]:
    """Emit checklist to logs at startup."""
    report = validate_deployment_environment()
    for line in deployment_checklist_lines():
        LOGGER.info(line)
    return report
