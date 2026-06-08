"""Admin index health — Postgres vs Qdrant alignment checks."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import psycopg
from fastapi import APIRouter, Depends

from omeia.api.platform_flags import (
    knowledge_indexer_enabled,
    platform_chunk_write_enabled,
    require_auth_static_enabled,
    vault_json_fallback_enabled,
    vault_use_vector_indexer_enabled,
)
from omeia.api.qdrant_collections import all_collections, collection_dim
from omeia.api.qdrant_vectors import get_qdrant_client, ping_qdrant
from omeia.api.supabase_config import postgres_conn
from omeia.security.auth import require_admin_user

LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[3]

router = APIRouter(tags=["admin-index"])


def _pg_count(cur: Any, sql: str) -> int | None:
    try:
        cur.execute(sql)
        row = cur.fetchone()
        return int(row[0]) if row else 0
    except Exception as exc:
        LOGGER.debug("index-health pg count failed: %s", exc)
        return None


def _qdrant_collection_stats(client: Any, name: str) -> dict[str, Any]:
    try:
        info = client.get_collection(name)
        points = getattr(info, "points_count", None)
        if points is None and hasattr(info, "result"):
            points = getattr(info.result, "points_count", None)
        vectors = getattr(info.config.params, "vectors", None) if hasattr(info, "config") else None
        dim = None
        if vectors is not None:
            if hasattr(vectors, "text"):
                dim = getattr(vectors.text, "size", None)
            elif isinstance(vectors, dict) and "text" in vectors:
                dim = getattr(vectors["text"], "size", None)
        return {"collection": name, "points_count": points, "vector_dim": dim, "status": "ok"}
    except Exception as exc:
        return {"collection": name, "status": "missing_or_error", "error": str(exc)[:200]}


@router.get("/api/admin/index-health")
def admin_index_health(
    user: dict[str, Any] = Depends(require_admin_user),
) -> dict[str, Any]:
    """Compare Postgres chunk tables with Qdrant collection point counts."""
    _ = user
    expected_dim = collection_dim()
    postgres: dict[str, Any] = {}
    conn_str = postgres_conn().strip()
    if conn_str:
        try:
            with psycopg.connect(conn_str, connect_timeout=8) as conn:
                with conn.cursor() as cur:
                    postgres = {
                        "rag_document_chunk": _pg_count(cur, "SELECT COUNT(*) FROM rag.document_chunk;"),
                        "rag_document_source": _pg_count(cur, "SELECT COUNT(*) FROM rag.document_source;"),
                        "platform_document_chunk": _pg_count(
                            cur, "SELECT COUNT(*) FROM platform.document_chunk;"
                        ),
                        "raw_asset_vault": _pg_count(cur, "SELECT COUNT(*) FROM platform.raw_asset_vault;"),
                        "research_chunk": _pg_count(
                            cur, "SELECT COUNT(*) FROM platform.research_chunk;"
                        ),
                    }
        except Exception as exc:
            postgres = {"error": str(exc)[:300]}

    qdrant: dict[str, Any] = {"reachable": False, "collections": []}
    if ping_qdrant():
        qdrant["reachable"] = True
        try:
            client = get_qdrant_client()
            qdrant["collections"] = [
                _qdrant_collection_stats(client, name)
                for name in all_collections().values()
            ]
        except Exception as exc:
            qdrant["error"] = str(exc)[:300]

    from omeia.api.platform_flags import canonical_chunk_pipeline_enabled, project_rbac_enabled

    flags = {
        "KNOWLEDGE_INDEXER_ENABLED": knowledge_indexer_enabled(),
        "CANONICAL_CHUNK_PIPELINE": canonical_chunk_pipeline_enabled(),
        "PROJECT_RBAC_ENABLED": project_rbac_enabled(),
        "PLATFORM_CHUNK_WRITE": platform_chunk_write_enabled(),
        "VAULT_JSON_FALLBACK": vault_json_fallback_enabled(),
        "REQUIRE_AUTH_STATIC": require_auth_static_enabled(),
        "VAULT_USE_VECTOR_INDEXER": vault_use_vector_indexer_enabled(),
    }

    drift_hints: list[str] = []
    rag_n = postgres.get("rag_document_chunk")
    if rag_n is not None and qdrant.get("collections"):
        doc_coll = next(
            (c for c in qdrant["collections"] if c.get("collection") == all_collections()["doc_chunks"]),
            None,
        )
        if doc_coll and doc_coll.get("points_count") is not None:
            qn = int(doc_coll["points_count"])
            if rag_n > 0 and qn == 0:
                drift_hints.append("rag.document_chunk has rows but doc_chunks Qdrant collection is empty")
            elif abs(rag_n - qn) > max(rag_n, qn) * 0.25 and rag_n > 10:
                drift_hints.append(f"rag.document_chunk ({rag_n}) vs doc_chunks points ({qn}) differ >25%")

    return {
        "expected_embedding_dim": expected_dim,
        "postgres": postgres,
        "qdrant": qdrant,
        "feature_flags": flags,
        "drift_hints": drift_hints,
    }


@router.get("/api/admin/quality-eval/latest")
def admin_quality_eval_latest(
    user: dict[str, Any] = Depends(require_admin_user),
) -> dict[str, Any]:
    """Latest continuous quality evaluation snapshot."""
    _ = user
    from omeia.api.quality_eval_service import fetch_latest_eval_run

    latest = fetch_latest_eval_run()
    file_path = ROOT / "tests" / "quality_eval_last_run.json"
    file_snapshot = None
    if file_path.is_file():
        try:
            import json

            file_snapshot = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception:
            file_snapshot = None
    return {"latest": latest, "file_snapshot": file_snapshot}


@router.get("/api/admin/quality-eval/history")
def admin_quality_eval_history(
    limit: int = 30,
    user: dict[str, Any] = Depends(require_admin_user),
) -> dict[str, Any]:
    """Historical quality eval runs for trend charts."""
    _ = user
    from omeia.api.quality_eval_service import fetch_eval_history

    rows = fetch_eval_history(limit=limit)
    return {"count": len(rows), "runs": rows}


@router.post("/api/admin/quality-eval/run")
def admin_quality_eval_run(
    user: dict[str, Any] = Depends(require_admin_user),
) -> dict[str, Any]:
    """Trigger on-demand continuous quality evaluation (admin only)."""
    _ = user
    from omeia.api.quality_eval_service import run_continuous_eval

    report = run_continuous_eval(trigger_source="admin_api", persist=True)
    return {"status": report.get("status"), "composite_score": report.get("composite_score"), "report": report}
