"""Clinical/statistical tool wrappers for synthetic, auditable cohorts.

Drop-in upgrade:
- robust CSV loading and project scoping
- safer numeric handling
- Kaplan-Meier curves with event/censor counts
- Welch-style group comparison with effect size
- graceful Postgres fallbacks
"""
from __future__ import annotations

import csv
import logging
import math
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

LOGGER = logging.getLogger(__name__)

ROOT = Path(os.environ.get("OMEIA_DATA_ROOT", str(Path(__file__).resolve().parents[2]))).resolve()
SYNTH_PATIENTS = ROOT / "synthetic_data" / "synthetic_patients.csv"
SYNTH_SAMPLES = ROOT / "synthetic_data" / "synthetic_samples.csv"
SAMPLE_MATRIX = ROOT / "synthetic_data" / "sample_feature_matrix.csv"
from omeia.api.supabase_config import postgres_conn as _postgres_conn

DB_CONN = _postgres_conn()


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


def _load_patients() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in _read_csv(SYNTH_PATIENTS):
        pfs = _safe_float(row.get("pfs_months"))
        os_m = _safe_float(row.get("os_months"))
        rows.append({
            "patient_code": row.get("patient_code", ""),
            "histology": row.get("histology", "unknown"),
            "hrd_status": row.get("hrd_status", "unknown"),
            "brca_status": row.get("brca_status", "unknown"),
            "platinum_response": row.get("platinum_response", "unknown"),
            "pfs_months": pfs,
            "pfs_event": int(_safe_float(row.get("pfs_event"), 1 if pfs < 24 else 0)),
            "os_months": os_m,
            "os_event": int(_safe_float(row.get("os_event"), 1 if os_m < 48 else 0)),
        })
    return rows


def _project_patient_codes(project_code: str | None) -> set[str]:
    if not project_code:
        return set()
    return {
        row.get("patient_code", "")
        for row in _read_csv(SYNTH_SAMPLES)
        if row.get("project_code") == project_code and row.get("patient_code")
    }


def _kaplan_meier(times: list[float], events: list[int]) -> list[dict[str, float]]:
    pairs = sorted((float(t), int(e)) for t, e in zip(times, events) if t is not None)
    at_risk = len(pairs)
    survival = 1.0
    curve: list[dict[str, float]] = [{"time": 0.0, "survival": 1.0, "at_risk": float(at_risk), "events": 0.0, "censored": 0.0}]
    i = 0
    while i < len(pairs):
        t = pairs[i][0]
        deaths = 0
        censored = 0
        while i < len(pairs) and pairs[i][0] == t:
            if pairs[i][1]:
                deaths += 1
            else:
                censored += 1
            i += 1
        if deaths and at_risk:
            survival *= max(0.0, 1.0 - deaths / at_risk)
        at_risk -= deaths + censored
        curve.append({
            "time": round(float(t), 4),
            "survival": round(survival, 4),
            "at_risk": float(max(at_risk, 0)),
            "events": float(deaths),
            "censored": float(censored),
        })
    return curve


def _survival_median(curve: list[dict[str, float]]) -> float | None:
    for point in curve:
        if point.get("survival", 1.0) <= 0.5:
            return point.get("time")
    return None


def run_survival_analysis(
    duration_col: str = "pfs_months",
    event_col: str = "pfs_event",
    group_col: str = "brca_status",
    project_code: str | None = None,
) -> dict[str, Any]:
    patients = _load_patients()
    valid_cols = set(patients[0].keys()) if patients else {"pfs_months", "pfs_event", "os_months", "os_event", "brca_status", "hrd_status"}
    if duration_col not in valid_cols or event_col not in valid_cols or group_col not in valid_cols:
        return {
            "analysis_type": "survival",
            "error": "Unknown column requested.",
            "available_columns": sorted(valid_cols),
            "disclaimer": "Synthetic de-identified cohort — not for clinical decisions.",
        }

    scoped_codes = _project_patient_codes(project_code)
    if scoped_codes:
        patients = [p for p in patients if p.get("patient_code") in scoped_codes]

    groups: dict[str, list[dict[str, Any]]] = {}
    for patient in patients:
        groups.setdefault(str(patient.get(group_col) or "unknown"), []).append(patient)

    curves: dict[str, list[dict[str, float]]] = {}
    summary: dict[str, dict[str, Any]] = {}
    for name, cohort in sorted(groups.items()):
        times = [_safe_float(p.get(duration_col)) for p in cohort]
        events = [int(_safe_float(p.get(event_col))) for p in cohort]
        curve = _kaplan_meier(times, events)
        curves[name] = curve
        summary[name] = {
            "n": len(cohort),
            "median_observed_duration": round(float(median(times)), 2) if times else None,
            "km_median_duration": _survival_median(curve),
            "event_rate": round(sum(events) / len(events), 3) if events else 0,
            "event_count": int(sum(events)),
            "censored_count": int(len(events) - sum(events)),
        }

    return {
        "analysis_type": "survival",
        "duration_col": duration_col,
        "event_col": event_col,
        "group_col": group_col,
        "project_code": project_code,
        "n_patients": len(patients),
        "groups": summary,
        "curves": curves,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": "Synthetic de-identified cohort — not for clinical decisions.",
    }


def _sample_variance(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mu = sum(values) / len(values)
    return sum((v - mu) ** 2 for v in values) / (len(values) - 1)


def _welch_p_approx(t_stat: float) -> float:
    # Normal approximation to two-sided p-value; sufficient for synthetic demo summaries.
    return max(0.0001, min(0.9999, 2 * (1 - 0.5 * (1 + math.erf(abs(t_stat) / math.sqrt(2))))))


def run_group_comparison(
    feature_col: str,
    group_col: str = "hrd_status",
    project_code: str | None = None,
) -> dict[str, Any]:
    feature_col = (feature_col or "").strip()
    patients = {p["patient_code"]: p for p in _load_patients()}
    matrix_rows = _read_csv(SAMPLE_MATRIX)
    if not matrix_rows:
        return {
            "analysis_type": "group_compare",
            "feature_col": feature_col,
            "group_col": group_col,
            "project_code": project_code,
            "group_stats": {},
            "error": "No sample feature matrix available.",
            "disclaimer": "Synthetic de-identified data — exploratory statistics only.",
        }

    rows: list[dict[str, Any]] = []
    for row in matrix_rows:
        if project_code and row.get("project_code") != project_code:
            continue
        if feature_col not in row or row.get(feature_col) in (None, ""):
            continue
        patient = patients.get(row.get("patient_code", ""), {})
        rows.append({"group": patient.get(group_col, "unknown"), "value": _safe_float(row.get(feature_col))})

    by_group: dict[str, list[float]] = {}
    for row in rows:
        by_group.setdefault(str(row["group"] or "unknown"), []).append(float(row["value"]))

    stats: dict[str, dict[str, Any]] = {}
    for group, values in sorted(by_group.items()):
        mu = sum(values) / len(values) if values else 0.0
        std = math.sqrt(_sample_variance(values))
        stats[group] = {
            "n": len(values),
            "mean": round(mu, 4),
            "median": round(float(median(values)), 4) if values else None,
            "std": round(std, 4),
            "min": round(min(values), 4) if values else None,
            "max": round(max(values), 4) if values else None,
        }

    groups = list(by_group.keys())
    p_value = None
    mean_diff = None
    cohen_d = None
    if len(groups) == 2:
        a_name, b_name = groups
        a, b = by_group[a_name], by_group[b_name]
        if a and b:
            ma = sum(a) / len(a)
            mb = sum(b) / len(b)
            va = _sample_variance(a)
            vb = _sample_variance(b)
            se = math.sqrt((va / len(a)) + (vb / len(b))) if a and b else 0.0
            t_stat = (ma - mb) / se if se else 0.0
            pooled = math.sqrt(((len(a) - 1) * va + (len(b) - 1) * vb) / max(len(a) + len(b) - 2, 1))
            mean_diff = round(ma - mb, 4)
            cohen_d = round((ma - mb) / pooled, 4) if pooled else None
            p_value = round(_welch_p_approx(t_stat), 4)

    return {
        "analysis_type": "group_compare",
        "feature_col": feature_col,
        "group_col": group_col,
        "project_code": project_code,
        "n_observations": len(rows),
        "group_stats": stats,
        "effect_size_mean_diff": mean_diff,
        "effect_size_cohen_d": cohen_d,
        "p_value_approx": p_value,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": "Synthetic de-identified data — exploratory statistics only.",
    }


def register_analysis_run(
    analysis_type: str,
    parameters: dict,
    results: dict,
    project_code: str | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    run_code = f"{analysis_type}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:6]}"
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                project_id = None
                if project_code:
                    cur.execute("SELECT project_id FROM core.project WHERE project_code = %s;", (project_code,))
                    row = cur.fetchone()
                    project_id = row[0] if row else None
                cur.execute(
                    """
                    INSERT INTO platform.analysis_run
                      (project_id, run_code, analysis_type, title, parameters, status, results, finished_at)
                    VALUES (%s, %s, %s, %s, %s, 'completed', %s, now())
                    RETURNING analysis_run_id, created_at;
                    """,
                    (project_id, run_code, analysis_type, title or analysis_type, Jsonb(parameters), Jsonb(results)),
                )
                run_id, created_at = cur.fetchone()
                conn.commit()
                return {"run_code": run_code, "analysis_run_id": str(run_id), "created_at": created_at.isoformat(), "registered": True}
    except Exception as exc:
        LOGGER.warning("Could not register analysis run %s: %s", run_code, exc)
        return {"run_code": run_code, "registered": False, "error": str(exc)}


def list_analysis_runs(limit: int = 20) -> list[dict]:
    limit = max(1, min(int(limit or 20), 200))
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT ar.run_code, ar.analysis_type, ar.title, ar.status, ar.created_at,
                           p.project_code, ar.results
                    FROM platform.analysis_run ar
                    LEFT JOIN core.project p ON ar.project_id = p.project_id
                    ORDER BY ar.created_at DESC LIMIT %s;
                    """,
                    (limit,),
                )
                return [
                    {
                        "run_code": row[0],
                        "analysis_type": row[1],
                        "title": row[2],
                        "status": row[3],
                        "created_at": row[4].isoformat() if row[4] else None,
                        "project_code": row[5],
                        "summary": (row[6] or {}).get("groups") or (row[6] or {}).get("group_stats"),
                    }
                    for row in cur.fetchall()
                ]
    except Exception as exc:
        LOGGER.debug("Could not list analysis runs: %s", exc)
        return []


def get_clinical_variables() -> list[dict]:
    try:
        with psycopg.connect(DB_CONN, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT variable_name, display_name, data_type, unit, definition "
                    "FROM clinical.variable_dictionary ORDER BY variable_name;"
                )
                return [
                    {"variable_name": r[0], "display_name": r[1], "data_type": r[2], "unit": r[3], "definition": r[4]}
                    for r in cur.fetchall()
                ]
    except Exception as exc:
        LOGGER.debug("Clinical variable DB lookup failed, using template fallback: %s", exc)

    template = ROOT / "schemas" / "clinical_dictionary_template.csv"
    return _read_csv(template)
