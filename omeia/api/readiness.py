"""Liveness and readiness probes for launchers and orchestrators."""
from __future__ import annotations

import os
from typing import Any


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, "true" if default else "false").lower() in ("1", "true", "yes", "on")


def _indexing_enabled() -> bool:
    return _env_bool("KNOWLEDGE_INDEXER_ENABLED") or _env_bool("VECTORIZATION_ENABLED")


def _postgres_ready(conn_str: str) -> tuple[bool, str | None]:
    if not (conn_str or "").strip():
        return False, "POSTGRES_CONN unset"
    try:
        from omeia.api.db_pool import get_db_connection

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return True, None
    except Exception as exc:
        return False, str(exc)


def _qdrant_ready(qdrant_client: Any) -> tuple[bool, str | None]:
    require = _env_bool("READINESS_REQUIRE_QDRANT", False) or _indexing_enabled()
    if not require:
        return True, None

    try:
        qdrant_client.get_collections()
    except Exception as exc:
        return False, f"Qdrant unreachable: {exc}"

    try:
        from omeia.api.qdrant_collections import collection_dim, readiness_collections

        expected = collection_dim()
        mismatches: list[str] = []
        missing: list[str] = []
        for label, name in readiness_collections().items():
            try:
                info = qdrant_client.get_collection(name)
                vectors = getattr(getattr(info, "config", None), "params", None)
                size = None
                if vectors and getattr(vectors, "vectors", None):
                    vec_cfg = vectors.vectors
                    if hasattr(vec_cfg, "size"):
                        size = vec_cfg.size
                    elif isinstance(vec_cfg, dict):
                        for v in vec_cfg.values():
                            size = getattr(v, "size", None) or (v.get("size") if isinstance(v, dict) else None)
                            break
                if size is not None and int(size) != int(expected):
                    mismatches.append(f"{name}: vector size {size} != TEXT_EMBEDDING_DIM {expected}")
            except Exception as exc:
                if _indexing_enabled():
                    missing.append(f"{name}: {exc}")
                continue
        if mismatches:
            return False, "; ".join(mismatches)
        if missing and _indexing_enabled():
            return False, "; ".join(missing[:3])
        return True, None
    except Exception as exc:
        return False, str(exc)


def _llm_ready(llm_client: Any) -> tuple[bool, str | None]:
    if not _env_bool("READINESS_REQUIRE_LLM", False):
        return True, None
    try:
        if llm_client.healthCheck():
            return True, None
        return False, f"LLM provider {getattr(llm_client, 'provider', '?')} unhealthy"
    except Exception as exc:
        return False, str(exc)


def check_readiness(*, db_conn: str, qdrant_client: Any, llm_client: Any) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    blockers: list[str] = []

    pg_ok, pg_err = _postgres_ready(db_conn)
    checks["database_connected"] = pg_ok
    if pg_err:
        checks["database_error"] = pg_err
    if not pg_ok:
        blockers.append(f"postgres: {pg_err}")

    q_ok, q_err = _qdrant_ready(qdrant_client)
    checks["qdrant_reachable"] = q_ok
    checks["qdrant_vector_dim_ok"] = q_ok
    if q_err:
        checks["qdrant_error"] = q_err
    if not q_ok:
        blockers.append(f"qdrant: {q_err}")

    llm_ok, llm_err = _llm_ready(llm_client)
    checks["llm_healthy"] = llm_ok
    if llm_err:
        checks["llm_error"] = llm_err
    if not llm_ok:
        blockers.append(f"llm: {llm_err}")

    ready = not blockers
    return {
        "ready": ready,
        "status": "ok" if ready else "degraded",
        "checks": checks,
        "blockers": blockers,
        "indexing_enabled": _indexing_enabled(),
    }
