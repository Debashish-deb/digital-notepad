"""Feature warehouse: definitions, matrices, and similarity search.

Drop-in premium upgrade:
- safer CSV parsing and numeric conversion
- idempotent Postgres seeding with JSONB metadata
- Qdrant vector creation with robust collection handling
- CSV fallback for offline demos/tests
"""
from __future__ import annotations

import csv
import hashlib
import json
import logging
import math
import os
import uuid
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb
from qdrant_client import QdrantClient
from qdrant_client.http import models

LOGGER = logging.getLogger(__name__)

ROOT = Path(os.environ.get("OMEIA_DATA_ROOT", str(Path(__file__).resolve().parents[2]))).resolve()
FEATURE_DICT_CSV = ROOT / "schemas" / "feature_dictionary_template.csv"
SAMPLE_MATRIX_CSV = ROOT / "synthetic_data" / "sample_feature_matrix.csv"
ROI_MATRIX_CSV = ROOT / "synthetic_data" / "roi_community_feature_matrix.csv"
from app_skeleton.api.supabase_config import postgres_conn as _postgres_conn

DB_CONN = _postgres_conn()
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
FEATURE_COLLECTION = os.getenv("FEATURE_COLLECTION", "spatial_feature_profiles")
VECTOR_DIM = int(os.getenv("FEATURE_VECTOR_DIM", "128"))

_ID_COLUMNS = {"sample_code", "project_code", "patient_code", "roi_code", "community_id", "entity_type"}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except Exception as exc:
        LOGGER.warning("Failed reading CSV %s: %s", path, exc)
        return []


def _numeric_feature_cols(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return []
    cols: list[str] = []
    for key in rows[0].keys():
        if key in _ID_COLUMNS:
            continue
        if any(str(row.get(key, "")).strip() not in ("", "NA", "nan", "None") for row in rows):
            cols.append(key)
    return cols


def _feature_vector_from_row(row: dict, feature_cols: list[str]) -> list[float]:
    """Deterministic normalized vector from numeric features for similarity search."""
    raw = [_safe_float(row.get(col), 0.0) for col in feature_cols] or [0.0]
    seed = hashlib.sha256(json.dumps(raw, sort_keys=True).encode("utf-8")).digest()
    out: list[float] = []
    for i in range(VECTOR_DIM):
        base = raw[i % len(raw)]
        jitter = seed[i % len(seed)] / 255.0
        harmonic = math.sin((i + 1) * (base + 0.131)) * 0.05
        out.append(base * (0.55 + jitter) + harmonic)
    norm = math.sqrt(sum(x * x for x in out)) or 1.0
    return [x / norm for x in out]


def _ensure_collection(client: QdrantClient) -> None:
    collections = [c.name for c in client.get_collections().collections]
    if FEATURE_COLLECTION in collections:
        return
    client.create_collection(
        collection_name=FEATURE_COLLECTION,
        vectors_config={"feature": models.VectorParams(size=VECTOR_DIM, distance=models.Distance.COSINE)},
    )


def seed_feature_warehouse() -> dict[str, Any]:
    """Load feature dictionary + sample/ROI matrices into Postgres and Qdrant."""
    stats: dict[str, Any] = {"features": 0, "matrices": 0, "values": 0, "vectors": 0, "errors": []}

    dict_rows = _read_csv(FEATURE_DICT_CSV)
    matrix_rows = _read_csv(SAMPLE_MATRIX_CSV)
    roi_rows = _read_csv(ROI_MATRIX_CSV)

    if not dict_rows or not matrix_rows:
        stats["errors"].append("Missing or empty CSV templates")
        return stats

    feature_cols = _numeric_feature_cols(matrix_rows)

    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                for row in dict_rows:
                    name = row.get("feature_name")
                    if not name:
                        continue
                    cur.execute(
                        """
                        INSERT INTO features.feature_definition
                          (feature_name, display_name, feature_group, entity_level, data_type, unit, source_modality, calculation_method)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (feature_name) DO UPDATE
                        SET display_name = EXCLUDED.display_name,
                            feature_group = EXCLUDED.feature_group,
                            entity_level = EXCLUDED.entity_level,
                            data_type = EXCLUDED.data_type,
                            unit = EXCLUDED.unit,
                            source_modality = EXCLUDED.source_modality,
                            calculation_method = EXCLUDED.calculation_method;
                        """,
                        (
                            name,
                            row.get("display_name") or name,
                            row.get("feature_group") or "uncategorized",
                            row.get("entity_level") or "sample",
                            row.get("data_type") or "numeric",
                            row.get("unit") or None,
                            row.get("source_modality") or None,
                            row.get("calculation_method") or "template",
                        ),
                    )
                    stats["features"] += 1

                cur.execute("SELECT feature_id, feature_name FROM features.feature_definition;")
                feat_map = {name: fid for fid, name in cur.fetchall()}

                matrix_code = "SYNTH_SAMPLE_MATRIX_V1"
                cur.execute(
                    """
                    INSERT INTO features.feature_matrix
                      (matrix_code, matrix_name, matrix_version, entity_level, row_entity_type, row_count, feature_count, qc_status, metadata)
                    VALUES (%s, %s, '1.0.0', 'sample', 'sample', %s, %s, 'passed', %s)
                    ON CONFLICT (matrix_code) DO UPDATE
                    SET row_count = EXCLUDED.row_count,
                        feature_count = EXCLUDED.feature_count,
                        metadata = EXCLUDED.metadata
                    RETURNING feature_matrix_id;
                    """,
                    (matrix_code, "Synthetic pilot sample features", len(matrix_rows), len(feature_cols), Jsonb({"source": "synthetic_data/sample_feature_matrix.csv"})),
                )
                sample_matrix_id = cur.fetchone()[0]
                stats["matrices"] += 1
                cur.execute("DELETE FROM features.feature_value WHERE feature_matrix_id = %s;", (sample_matrix_id,))

                for row in matrix_rows:
                    sample_code = row.get("sample_code")
                    if not sample_code:
                        continue
                    for col in feature_cols:
                        fid = feat_map.get(col)
                        if not fid or row.get(col) in (None, ""):
                            continue
                        cur.execute(
                            """
                            INSERT INTO features.feature_value
                              (feature_matrix_id, feature_id, entity_type, entity_code, value_numeric, qc_status)
                            VALUES (%s, %s, 'sample', %s, %s, 'passed');
                            """,
                            (sample_matrix_id, fid, sample_code, _safe_float(row.get(col))),
                        )
                        stats["values"] += 1

                if roi_rows:
                    roi_feature_cols = _numeric_feature_cols(roi_rows)
                    roi_matrix_code = "SYNTH_ROI_COMMUNITY_MATRIX_V1"
                    cur.execute(
                        """
                        INSERT INTO features.feature_matrix
                          (matrix_code, matrix_name, matrix_version, entity_level, row_entity_type, row_count, feature_count, qc_status, metadata)
                        VALUES (%s, %s, '1.0.0', 'roi', 'roi', %s, %s, 'passed', %s)
                        ON CONFLICT (matrix_code) DO UPDATE
                        SET row_count = EXCLUDED.row_count,
                            feature_count = EXCLUDED.feature_count,
                            metadata = EXCLUDED.metadata
                        RETURNING feature_matrix_id;
                        """,
                        (roi_matrix_code, "Synthetic pilot ROI/community features", len(roi_rows), len(roi_feature_cols), Jsonb({"source": "synthetic_data/roi_community_feature_matrix.csv", "includes_community": True})),
                    )
                    roi_matrix_id = cur.fetchone()[0]
                    stats["matrices"] += 1
                    cur.execute("DELETE FROM features.feature_value WHERE feature_matrix_id = %s;", (roi_matrix_id,))
                    for row in roi_rows:
                        entity_code = row.get("roi_code")
                        if not entity_code:
                            continue
                        for col in roi_feature_cols:
                            fid = feat_map.get(col)
                            if not fid or row.get(col) in (None, ""):
                                continue
                            cur.execute(
                                """
                                INSERT INTO features.feature_value
                                  (feature_matrix_id, feature_id, entity_type, entity_code, value_numeric, qc_status, value_json)
                                VALUES (%s, %s, %s, %s, %s, 'passed', %s);
                                """,
                                (
                                    roi_matrix_id,
                                    fid,
                                    row.get("entity_type") or "roi",
                                    entity_code,
                                    _safe_float(row.get(col)),
                                    Jsonb({
                                        "community_id": row.get("community_id"),
                                        "sample_code": row.get("sample_code"),
                                        "project_code": row.get("project_code"),
                                    }),
                                ),
                            )
                            stats["values"] += 1
            conn.commit()
    except Exception as exc:
        LOGGER.warning("Postgres feature warehouse seed failed: %s", exc)
        stats["errors"].append(f"postgres: {exc}")

    try:
        client = QdrantClient(url=QDRANT_URL)
        _ensure_collection(client)
        points: list[models.PointStruct] = []
        for row in matrix_rows:
            sample_code = row.get("sample_code")
            if not sample_code:
                continue
            points.append(models.PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, sample_code)),
                vector={"feature": _feature_vector_from_row(row, feature_cols)},
                payload={
                    "project_code": row.get("project_code"),
                    "entity_type": "sample",
                    "entity_code": sample_code,
                    "patient_code": row.get("patient_code"),
                    "feature_matrix_id": "SYNTH_SAMPLE_MATRIX_V1",
                    "feature_set_version": "1.0.0",
                    "qc_status": "passed",
                    "sensitivity_level": "restricted",
                },
            ))
        if points:
            client.upsert(collection_name=FEATURE_COLLECTION, points=points)
            stats["vectors"] = len(points)
    except Exception as exc:
        LOGGER.warning("Qdrant feature vector seed failed: %s", exc)
        stats["errors"].append(f"qdrant: {exc}")

    return stats


def list_feature_definitions() -> list[dict]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT feature_name, display_name, feature_group, entity_level, data_type, unit, source_modality
                    FROM features.feature_definition
                    WHERE COALESCE(status, 'active') = 'active'
                    ORDER BY feature_group, feature_name;
                    """
                )
                return [
                    {"feature_name": r[0], "display_name": r[1], "feature_group": r[2], "entity_level": r[3], "data_type": r[4], "unit": r[5], "source_modality": r[6]}
                    for r in cur.fetchall()
                ]
    except Exception as exc:
        LOGGER.debug("Feature definitions DB lookup failed, using CSV fallback: %s", exc)
        return _read_csv(FEATURE_DICT_CSV)


def list_feature_matrices(project_code: str | None = None) -> list[dict]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                if project_code:
                    cur.execute(
                        """
                        SELECT fm.matrix_code, fm.matrix_name, fm.matrix_version, fm.entity_level,
                               fm.row_count, fm.feature_count, fm.qc_status, p.project_code
                        FROM features.feature_matrix fm
                        LEFT JOIN core.project p ON fm.project_id = p.project_id
                        WHERE fm.metadata->>'project_code' = %s OR p.project_code = %s
                        ORDER BY fm.created_at DESC;
                        """,
                        (project_code, project_code),
                    )
                else:
                    cur.execute(
                        """
                        SELECT fm.matrix_code, fm.matrix_name, fm.matrix_version, fm.entity_level,
                               fm.row_count, fm.feature_count, fm.qc_status, p.project_code
                        FROM features.feature_matrix fm
                        LEFT JOIN core.project p ON fm.project_id = p.project_id
                        ORDER BY fm.created_at DESC;
                        """
                    )
                return [
                    {"matrix_code": r[0], "matrix_name": r[1], "matrix_version": r[2], "entity_level": r[3], "row_count": r[4], "feature_count": r[5], "qc_status": r[6], "project_code": r[7]}
                    for r in cur.fetchall()
                ]
    except Exception as exc:
        LOGGER.debug("Feature matrices DB lookup failed, using fallback: %s", exc)
        rows = _read_csv(SAMPLE_MATRIX_CSV)
        return [{
            "matrix_code": "SYNTH_SAMPLE_MATRIX_V1",
            "matrix_name": "Synthetic pilot (CSV)",
            "matrix_version": "1.0.0",
            "entity_level": "sample",
            "row_count": len(rows),
            "feature_count": len(_numeric_feature_cols(rows)),
            "qc_status": "passed",
            "project_code": project_code,
        }]


def get_sample_features(sample_code: str) -> dict[str, Any]:
    sample_code = (sample_code or "").strip()
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT fd.feature_name, fd.display_name, fd.unit, fv.value_numeric, fv.value_text
                    FROM features.feature_value fv
                    JOIN features.feature_definition fd ON fd.feature_id = fv.feature_id
                    WHERE fv.entity_code = %s AND fv.entity_type = 'sample'
                    ORDER BY fd.feature_group, fd.feature_name;
                    """,
                    (sample_code,),
                )
                features = [
                    {"feature_name": r[0], "display_name": r[1], "unit": r[2], "value": r[3] if r[3] is not None else r[4]}
                    for r in cur.fetchall()
                ]
                if features:
                    return {"sample_code": sample_code, "features": features, "source": "postgres"}
    except Exception as exc:
        LOGGER.debug("Sample feature DB lookup failed, using CSV fallback: %s", exc)

    for row in _read_csv(SAMPLE_MATRIX_CSV):
        if row.get("sample_code") == sample_code:
            features = [
                {"feature_name": key, "display_name": key, "unit": None, "value": _safe_float(value)}
                for key, value in row.items()
                if key not in _ID_COLUMNS and value not in (None, "")
            ]
            return {"sample_code": sample_code, "project_code": row.get("project_code"), "features": features, "source": "csv"}
    return {"sample_code": sample_code, "features": [], "source": "none"}


def _csv_similarity(row: dict[str, Any], feature_cols: list[str], limit: int, project_code: str | None) -> list[dict]:
    target = [_safe_float(row.get(col)) for col in feature_cols]
    target_code = row.get("sample_code")
    sims: list[dict[str, Any]] = []
    for candidate in _read_csv(SAMPLE_MATRIX_CSV):
        if candidate.get("sample_code") == target_code:
            continue
        if project_code and candidate.get("project_code") != project_code:
            continue
        vec = [_safe_float(candidate.get(col)) for col in feature_cols]
        dot = sum(a * b for a, b in zip(target, vec))
        na = math.sqrt(sum(a * a for a in target)) or 1.0
        nb = math.sqrt(sum(b * b for b in vec)) or 1.0
        sims.append({
            "sample_code": candidate.get("sample_code"),
            "project_code": candidate.get("project_code"),
            "similarity_score": round(dot / (na * nb), 4),
            "source": "csv",
        })
    sims.sort(key=lambda item: -item["similarity_score"])
    return sims[:limit]


def find_similar_samples(sample_code: str, limit: int = 5, project_code: str | None = None) -> list[dict]:
    sample_code = (sample_code or "").strip()
    limit = max(1, min(int(limit or 5), 50))
    rows = _read_csv(SAMPLE_MATRIX_CSV)
    feature_cols = _numeric_feature_cols(rows)
    row = next((r for r in rows if r.get("sample_code") == sample_code), None)
    if not row:
        return []

    query_vec = _feature_vector_from_row(row, feature_cols)

    try:
        client = QdrantClient(url=QDRANT_URL)
        filt = None
        if project_code:
            filt = models.Filter(must=[models.FieldCondition(key="project_code", match=models.MatchValue(value=project_code))])

        try:
            response = client.query_points(
                collection_name=FEATURE_COLLECTION,
                query=query_vec,
                using="feature",
                query_filter=filt,
                limit=limit + 1,
            )
            hits = getattr(response, "points", []) or []
        except Exception:
            hits = client.search(
                collection_name=FEATURE_COLLECTION,
                query_vector=("feature", query_vec),
                query_filter=filt,
                limit=limit + 1,
            )

        out: list[dict[str, Any]] = []
        for hit in hits:
            payload = hit.payload or {}
            code = payload.get("entity_code")
            if code == sample_code:
                continue
            out.append({
                "sample_code": code,
                "project_code": payload.get("project_code"),
                "similarity_score": round(float(getattr(hit, "score", 0.0)), 4),
                "source": "qdrant",
            })
            if len(out) >= limit:
                break
        if out:
            return out
    except Exception as exc:
        LOGGER.debug("Qdrant similarity lookup failed, using CSV fallback: %s", exc)

    return _csv_similarity(row, feature_cols, limit, project_code)
