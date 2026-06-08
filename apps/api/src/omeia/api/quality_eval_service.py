"""Continuous quality evaluation — search, copilot, strategy, feedback trends."""
from __future__ import annotations

import json
import logging
import os
import socket
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import psycopg

from omeia.api.evaluation_service import EVAL_CASES, score_retrieval_case
from omeia.api.platform_flags import quality_gate_strict_enabled

LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]

EvalStatus = Literal["pass", "warn", "fail"]

REGRESSION_THRESHOLDS = {
    "search_qa_pass_rate": 0.05,
    "copilot_overall_pass_pct": 5.0,
    "composite_score": 3.0,
    "avg_quality_score": 0.3,
}


def _db_conn() -> str:
    from omeia.api.supabase_config import postgres_conn

    return postgres_conn()


def _git_ref() -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0:
            return proc.stdout.strip() or None
    except Exception:
        pass
    return None


def _feedback_summary(*, days: int = 14) -> dict[str, Any]:
    try:
        with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      COUNT(*) FILTER (WHERE rating > 0),
                      COUNT(*) FILTER (WHERE rating = 0),
                      COUNT(*) FILTER (WHERE rating < 0),
                      COUNT(*)
                    FROM platform.copilot_feedback
                    WHERE created_at >= now() - (%s || ' days')::interval;
                    """,
                    (str(days),),
                )
                pos, neutral, neg, total = cur.fetchone()
                return {
                    "window_days": days,
                    "positive": int(pos or 0),
                    "neutral": int(neutral or 0),
                    "negative": int(neg or 0),
                    "total": int(total or 0),
                    "positive_rate": round((pos or 0) / max(total or 1, 1), 3),
                }
    except Exception as exc:
        LOGGER.debug("feedback summary unavailable: %s", exc)
        return {"window_days": days, "total": 0, "error": str(exc)[:200]}


def _run_retrieval_eval() -> dict[str, Any]:
    from omeia.api.common import DB_CONN, llm_client, qdrant_client
    from omeia.api.search_service import SearchService

    svc = SearchService(db_conn=DB_CONN, qdrant=qdrant_client, llm=llm_client)
    rows: list[dict[str, Any]] = []
    for case in EVAL_CASES:
        try:
            resp = svc.unified_search(case.query, mode="hybrid", limit=8, user_role="admin")
            hits = [h.model_dump() for h in (resp.hits or [])]
            rows.append(score_retrieval_case(case, hits))
        except Exception as exc:
            rows.append({
                "query": case.query,
                "category": case.category,
                "score": 0.0,
                "error": str(exc)[:200],
            })
    scores = [float(r.get("score") or 0) for r in rows]
    avg = round(sum(scores) / max(len(scores), 1), 3)
    return {
        "cases": rows,
        "avg_score": avg,
        "pass": avg >= 0.45,
    }


def _load_script_module(module_name: str, script_path: Path) -> Any:
    import importlib.util

    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load script module: {script_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_search_qa() -> dict[str, Any]:
    mod = _load_script_module("run_search_qa", ROOT / "scripts" / "search" / "run_search_qa.py")
    return mod.run_search_qa_report()


def _run_copilot_eval(*, role: str = "researcher") -> dict[str, Any]:
    mod = _load_script_module(
        "run_ai_lab_assistant_eval",
        ROOT / "scripts" / "search" / "run_ai_lab_assistant_eval.py",
    )
    report = mod.run_eval(role=role)
    report["strategy_benchmark"] = mod._strategy_benchmark()
    out = ROOT / "tests" / "search_qa_ai_last_run.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def _run_strategy_engine_sample() -> dict[str, Any]:
    """In-process strategy answers on golden fixture (retrieval-based)."""
    from unittest.mock import MagicMock

    from omeia.api.chat_conversation import classify_and_enrich
    from omeia.api.research_strategy_engine import ResearchStrategyEngine

    fixture = ROOT / "tests" / "fixtures" / "research_strategy_questions.json"
    if not fixture.is_file():
        return {"enabled": False, "reason": "fixture missing"}

    specs = json.loads(fixture.read_text(encoding="utf-8"))
    strategy_specs = [s for s in specs if s.get("expect_strategy_detect") is not False][:5]
    rows: list[dict[str, Any]] = []

    search_svc = MagicMock()
    search_svc.hits_for_copilot.return_value = []

    engine = ResearchStrategyEngine(search_svc)
    for spec in strategy_specs:
        q = spec.get("question") or ""
        intent = classify_and_enrich(q)
        t0 = time.perf_counter()
        try:
            result = engine.run(q, intent_decision=intent)
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
            report = result.get("strategy_report") or {}
            rows.append({
                "id": spec.get("id"),
                "pass": report.get("answer_type") == "research_strategy",
                "directions": len(report.get("recommended_directions") or []),
                "confidence": report.get("confidence_overall"),
                "latency_ms": elapsed_ms,
                "insufficient": "insufficient" in (report.get("executive_summary") or "").lower(),
            })
        except Exception as exc:
            rows.append({"id": spec.get("id"), "pass": False, "error": str(exc)[:200]})

    passed = sum(1 for r in rows if r.get("pass"))
    return {
        "enabled": True,
        "passed": passed,
        "failed": len(rows) - passed,
        "avg_latency_ms": round(
            sum(r.get("latency_ms", 0) for r in rows) / max(len(rows), 1),
            1,
        ),
        "rows": rows,
    }


def _compute_composite_score(metrics: dict[str, Any]) -> float:
    search = metrics.get("search_qa") or {}
    copilot = metrics.get("copilot") or {}
    strategy_det = (copilot.get("strategy_benchmark") or {})
    strategy_eng = metrics.get("strategy_engine") or {}
    retrieval = metrics.get("retrieval") or {}
    feedback = metrics.get("feedback") or {}

    search_rate = (search.get("passed") or 0) / max(search.get("total") or 1, 1)
    gates = copilot.get("release_gates") or {}
    copilot_rate = float(gates.get("overall_pass_pct") or 0) / 100.0
    strat_det_rate = (strategy_det.get("passed") or 0) / max(
        (strategy_det.get("passed") or 0) + (strategy_det.get("failed") or 0),
        1,
    )
    strat_eng_rate = (strategy_eng.get("passed") or 0) / max(
        (strategy_eng.get("passed") or 0) + (strategy_eng.get("failed") or 0),
        1,
    ) if strategy_eng.get("enabled") else 1.0
    retrieval_score = float(retrieval.get("avg_score") or 0)
    feedback_bonus = float(feedback.get("positive_rate") or 0) * 0.05

    raw = (
        search_rate * 25
        + copilot_rate * 35
        + strat_det_rate * 10
        + strat_eng_rate * 10
        + retrieval_score * 15
        + feedback_bonus * 5
    )
    return round(min(100.0, raw), 2)


def _detect_regressions(
    current: dict[str, Any],
    previous: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not previous:
        return []
    regressions: list[dict[str, Any]] = []
    cur_m = current.get("metrics") or {}
    prev_m = previous.get("metrics") or {}

    cur_search = (cur_m.get("search_qa") or {}).get("pass_rate")
    prev_search = (prev_m.get("search_qa") or {}).get("pass_rate")
    if cur_search is not None and prev_search is not None:
        if prev_search - cur_search > REGRESSION_THRESHOLDS["search_qa_pass_rate"]:
            regressions.append({
                "metric": "search_qa_pass_rate",
                "previous": prev_search,
                "current": cur_search,
            })

    cur_gates = (cur_m.get("copilot") or {}).get("release_gates") or {}
    prev_gates = (prev_m.get("copilot") or {}).get("release_gates") or {}
    cur_overall = cur_gates.get("overall_pass_pct")
    prev_overall = prev_gates.get("overall_pass_pct")
    if cur_overall is not None and prev_overall is not None:
        if float(prev_overall) - float(cur_overall) > REGRESSION_THRESHOLDS["copilot_overall_pass_pct"]:
            regressions.append({
                "metric": "copilot_overall_pass_pct",
                "previous": prev_overall,
                "current": cur_overall,
            })

    cur_score = current.get("composite_score")
    prev_score = previous.get("composite_score")
    if cur_score is not None and prev_score is not None:
        if float(prev_score) - float(cur_score) > REGRESSION_THRESHOLDS["composite_score"]:
            regressions.append({
                "metric": "composite_score",
                "previous": prev_score,
                "current": cur_score,
            })

    return regressions


def _resolve_status(
    *,
    metrics: dict[str, Any],
    gates: dict[str, Any],
    regressions: list[dict[str, Any]],
) -> EvalStatus:
    search = metrics.get("search_qa") or {}
    if (search.get("failed") or 0) > 0:
        return "fail"
    if gates.get("overall_gate_pass") is False and quality_gate_strict_enabled():
        return "fail"
    if regressions and quality_gate_strict_enabled():
        return "fail"
    if gates.get("overall_gate_pass") is False or regressions:
        return "warn"
    if (metrics.get("copilot") or {}).get("http_errors", 0) > 0:
        return "warn"
    return "pass"


def run_continuous_eval(
    *,
    trigger_source: str = "manual",
    copilot_role: str = "researcher",
    skip_copilot: bool = False,
    persist: bool = True,
) -> dict[str, Any]:
    """Run full quality battery and optionally persist to Postgres."""
    t0 = time.perf_counter()
    metrics: dict[str, Any] = {}

    search_report = _run_search_qa()
    metrics["search_qa"] = {
        "passed": search_report.get("passed"),
        "failed": search_report.get("failed"),
        "total": (search_report.get("passed") or 0) + (search_report.get("failed") or 0),
        "pass_rate": round(
            (search_report.get("passed") or 0)
            / max((search_report.get("passed") or 0) + (search_report.get("failed") or 0), 1),
            3,
        ),
    }

    if skip_copilot:
        metrics["copilot"] = {"skipped": True}
        gates: dict[str, Any] = {}
    else:
        copilot_report = _run_copilot_eval(role=copilot_role)
        gates = copilot_report.get("release_gates") or {}
        avg_q = 0.0
        scores = [r.get("quality_score") for r in copilot_report.get("chat_results") or [] if r.get("quality_score")]
        if scores:
            avg_q = round(sum(scores) / len(scores), 2)
        metrics["copilot"] = {
            "http_errors": copilot_report.get("http_errors"),
            "release_gates": gates,
            "avg_quality_score": avg_q,
            "providers_seen": copilot_report.get("providers_seen"),
            "strategy_benchmark": copilot_report.get("strategy_benchmark"),
            "question_count": len(copilot_report.get("chat_results") or []),
        }

    metrics["retrieval"] = _run_retrieval_eval()
    metrics["strategy_engine"] = _run_strategy_engine_sample()
    metrics["feedback"] = _feedback_summary()

    composite = _compute_composite_score(metrics)
    duration_ms = int((time.perf_counter() - t0) * 1000)

    previous = fetch_latest_eval_run() if persist else None
    payload = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "host": socket.gethostname(),
        "git_ref": _git_ref(),
        "trigger_source": trigger_source,
        "composite_score": composite,
        "metrics": metrics,
        "gates": gates,
        "duration_ms": duration_ms,
    }
    payload["regressions"] = _detect_regressions(payload, previous)
    payload["status"] = _resolve_status(metrics=metrics, gates=gates, regressions=payload["regressions"])

    artifacts = {
        "search_qa_path": str(ROOT / "tests" / "search_qa_last_run.json"),
        "copilot_eval_path": str(ROOT / "tests" / "search_qa_ai_last_run.json"),
    }
    payload["artifacts"] = artifacts

    if persist:
        save_eval_run(payload)

    # Refresh JSON artifacts for operators
    (ROOT / "tests" / "quality_eval_last_run.json").write_text(
        json.dumps(payload, indent=2, default=str),
        encoding="utf-8",
    )
    return payload


def save_eval_run(payload: dict[str, Any]) -> str | None:
    try:
        with psycopg.connect(_db_conn(), connect_timeout=10) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO platform.quality_eval_run (
                      host, git_ref, trigger_source, status, composite_score,
                      metrics, gates, regressions, artifacts, duration_ms, notes
                    )
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s)
                    RETURNING run_id::text;
                    """,
                    (
                        payload.get("host") or "",
                        payload.get("git_ref"),
                        payload.get("trigger_source") or "manual",
                        payload.get("status") or "warn",
                        payload.get("composite_score"),
                        json.dumps(payload.get("metrics") or {}),
                        json.dumps(payload.get("gates") or {}),
                        json.dumps(payload.get("regressions") or []),
                        json.dumps(payload.get("artifacts") or {}),
                        int(payload.get("duration_ms") or 0),
                        None,
                    ),
                )
                row = cur.fetchone()
                conn.commit()
                return row[0] if row else None
    except Exception as exc:
        LOGGER.warning("quality_eval_run persist failed: %s", exc)
        return None


def fetch_latest_eval_run() -> dict[str, Any] | None:
    try:
        with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT run_id::text, run_at, status, composite_score, metrics, gates, regressions
                    FROM platform.quality_eval_run
                    ORDER BY run_at DESC
                    LIMIT 1;
                    """
                )
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "run_id": row[0],
                    "run_at": row[1].isoformat() if row[1] else None,
                    "status": row[2],
                    "composite_score": float(row[3]) if row[3] is not None else None,
                    "metrics": row[4] or {},
                    "gates": row[5] or {},
                    "regressions": row[6] or [],
                }
    except Exception:
        return None


def fetch_eval_history(*, limit: int = 30) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 200))
    try:
        with psycopg.connect(_db_conn(), connect_timeout=8) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT run_id::text, run_at, trigger_source, status, composite_score,
                           duration_ms, regressions, gates
                    FROM platform.quality_eval_run
                    ORDER BY run_at DESC
                    LIMIT %s;
                    """,
                    (limit,),
                )
                rows = []
                for r in cur.fetchall():
                    rows.append({
                        "run_id": r[0],
                        "run_at": r[1].isoformat() if r[1] else None,
                        "trigger_source": r[2],
                        "status": r[3],
                        "composite_score": float(r[4]) if r[4] is not None else None,
                        "duration_ms": r[5],
                        "regression_count": len(r[6] or []),
                        "overall_gate_pass": (r[7] or {}).get("overall_gate_pass"),
                    })
                return rows
    except Exception as exc:
        LOGGER.debug("eval history unavailable: %s", exc)
        return []
