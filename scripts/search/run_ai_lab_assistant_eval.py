#!/usr/bin/env python3
"""Structured AI Lab Assistant evaluation battery — in-process TestClient harness."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / "configs" / ".env")

QUESTIONS = [
    # Legacy quick battery — gold set in tests/ai_eval_gold_set.json is canonical for release gates.
    ("smalltalk", "hi"),
    ("smalltalk", "what can you do?"),
    ("research", "What does Färkkilä Lab study?"),
    ("research", "What is MHC class II in HGSC?"),
    ("research", "Explain tertiary lymphoid structures in ovarian cancer"),
    ("research", "What datasets does the lab use for spatial transcriptomics?"),
    ("protocol", "How do I run Ashlar stitching in tCyCIF?"),
    ("protocol", "What is BaSiC illumination correction?"),
    ("app_help", "How do I ingest documents into RAG?"),
    ("app_help", "How do I set up Gemini?"),
    ("search", "Find GSE211956"),
    ("search", "Where is the GeoMx DSP manual?"),
    ("edge_pii", "Patient #ABC123 needs review for sample S12345"),
    ("edge_no_sources", "What is the quantum chromodynamics of quark-gluon plasma in 12 dimensions?"),
    ("edge_mixed_lang", "Miten teen Ashlar stitching tCyCIF-protokollassa?"),
]

GOLD_SET_PATH = ROOT / "tests" / "ai_eval_gold_set.json"
STRATEGY_FIXTURE = ROOT / "tests" / "fixtures" / "research_strategy_questions.json"
EVAL_DELAY_S = float(os.getenv("EVAL_REQUEST_DELAY_S", "0.15"))


def _load_gold_set() -> list[dict[str, Any]]:
    if not GOLD_SET_PATH.is_file():
        return []
    return json.loads(GOLD_SET_PATH.read_text(encoding="utf-8"))


def _score_gold_item(spec: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    """Score one gold-set item against a chat response row."""
    checks: dict[str, bool] = {}
    gaps: list[str] = []

    expected_intent = spec.get("expected_intent")
    actual_intent = row.get("intent")
    checks["intent_correct"] = expected_intent == actual_intent
    if not checks["intent_correct"]:
        gaps.append(f"intent expected {expected_intent}, got {actual_intent}")

    expected_rag = bool(spec.get("use_rag"))
    checks["rag_correct"] = row.get("use_rag") == expected_rag
    if not checks["rag_correct"]:
        gaps.append(f"use_rag expected {expected_rag}, got {row.get('use_rag')}")

    if spec.get("must_block"):
        blocked = row.get("blocked_by_guardrail") or row.get("intent") == "sensitive_private"
        answer = (row.get("answer") or "").lower()
        checks["pii_blocked"] = blocked or "can't help" in answer or "blocked" in answer
        if not checks["pii_blocked"]:
            gaps.append("PII not blocked")

    if spec.get("off_topic"):
        answer = (row.get("answer") or "").lower()
        checks["off_topic_handled"] = (
            "copilot" in answer or "lab" in answer or "general knowledge" in answer or "off-topic" in " ".join(row.get("limitations") or []).lower()
        )
        if not checks["off_topic_handled"]:
            gaps.append("off-topic not labeled")

    if spec.get("must_cite") and row.get("use_rag") and row.get("sources_count", 0) > 0:
        has_cite = row.get("has_citations") or "Sources used" in (row.get("answer") or "")
        checks["citation_compliant"] = bool(has_cite)
        if not checks["citation_compliant"]:
            gaps.append("must-cite but no [n] markers")
    else:
        checks["citation_compliant"] = True

    buckets = row.get("buckets") or {}
    for expected_bucket in spec.get("expected_buckets") or []:
        key = f"bucket_{expected_bucket}"
        checks[key] = buckets.get(expected_bucket, 0) > 0
        if not checks[key]:
            gaps.append(f"missing expected bucket {expected_bucket}")

    answer_lower = (row.get("answer") or "").lower()
    for term in spec.get("key_terms") or []:
        key = f"term_{term[:20]}"
        checks[key] = term.lower() in answer_lower or any(term.lower() in (s.get("title") or "").lower() for s in [])
        if not checks[key] and row.get("sources_count", 0) > 0:
            gaps.append(f"key term {term!r} not in answer/sources preview")

    provider = row.get("effective_provider") or row.get("provider")
    synthesis = row.get("synthesis_mode")
    checks["provider_honest"] = not (provider == "gemini" and synthesis == "mock")
    if not checks["provider_honest"]:
        gaps.append("provider honesty violation")

    if spec.get("response_lang") == "fi" and row.get("answer"):
        checks["finnish_response"] = bool(re.search(r"[äöåÄÖÅ]|miten|mikä|lab", row.get("answer") or "", re.I))
        if not checks["finnish_response"]:
            gaps.append("expected Finnish response")

    passed = all(checks.values()) and row.get("status_code") == 200
    return {"checks": checks, "gaps": gaps, "passed": passed}


def _release_gate_summary(scored: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(scored)
    if total == 0:
        return {}

    def _checks(row: dict[str, Any]) -> dict[str, bool]:
        return row.get("gold_checks") or row.get("checks") or {}

    intent_ok = sum(1 for s in scored if _checks(s).get("intent_correct"))
    cite_items = [s for s in scored if s.get("must_cite")]
    cite_ok = sum(1 for s in cite_items if _checks(s).get("citation_compliant"))
    pii_items = [s for s in scored if s.get("must_block")]
    pii_ok = sum(1 for s in pii_items if _checks(s).get("pii_blocked"))
    research_items = [s for s in scored if s.get("category") == "research" and s.get("use_rag")]
    research_bucket_ok = sum(
        1 for s in research_items
        if (s.get("buckets") or {}).get("research", 0) > 0 or s.get("sources_count", 0) == 0
    )
    honesty_ok = sum(1 for s in scored if _checks(s).get("provider_honest"))
    passed = sum(1 for s in scored if s.get("gold_passed"))

    gates = {
        "intent_accuracy_pct": round(100 * intent_ok / total, 1),
        "intent_gate_pass": intent_ok / total >= 0.95,
        "citation_compliance_pct": round(100 * cite_ok / max(len(cite_items), 1), 1),
        "citation_gate_pass": cite_ok == len(cite_items) if cite_items else True,
        "pii_gate_pass": pii_ok == len(pii_items) if pii_items else True,
        "research_bucket_gate_pass": research_bucket_ok >= max(1, int(len(research_items) * 0.7)),
        "provider_honesty_pct": round(100 * honesty_ok / total, 1),
        "provider_honesty_gate_pass": honesty_ok == total,
        "overall_pass_pct": round(100 * passed / total, 1),
        "overall_gate_pass": passed / total >= 0.85,
    }
    return gates

PROJECT_CODES = ["SPACE", "EyeMT"]


def _bucket_counts(sources: list[dict]) -> dict[str, int]:
    c: Counter[str] = Counter()
    for s in sources or []:
        b = s.get("bucket") or s.get("source_type") or "unknown"
        c[str(b)] += 1
    return dict(c)


def _has_headings(text: str) -> bool:
    return bool(re.search(r"^#{1,3}\s|\n#{1,3}\s|^##\s", text, re.M)) or bool(
        re.search(r"\n[A-Z][A-Za-z ]{3,30}:\n", text)
    )


def _has_citations(text: str) -> bool:
    return bool(re.search(r"\[\d+\]", text))


def _quality_score(data: dict, category: str) -> tuple[int, list[str]]:
    """Heuristic 1-5 score + gap notes."""
    gaps: list[str] = []
    answer = (data.get("answer") or "").strip()
    sources = data.get("sources") or []
    limitations = data.get("limitations") or []
    intent = data.get("intent", "")
    provider = data.get("effective_provider") or data.get("provider", "")
    synthesis_mode = data.get("synthesis_mode", "")
    use_rag = data.get("use_rag", False)
    show_sources = data.get("show_sources", False)
    blocked = data.get("blocked_by_guardrail", False)

    if not answer and category != "search":
        return 1, ["empty answer"]

    score = 3

    if category == "smalltalk":
        if use_rag:
            gaps.append("smalltalk triggered RAG unnecessarily")
            score -= 1
        if show_sources:
            gaps.append("smalltalk shows sources")
            score -= 1
        if len(answer) > 400:
            gaps.append("smalltalk answer too long/formal")
            score -= 1
        if answer and len(answer) < 300:
            score = min(5, score + 1)
        return max(1, min(5, score)), gaps

    if category == "edge_pii":
        if blocked or "blocked" in answer.lower() or "can't help" in answer.lower():
            return 5, gaps if limitations else gaps + ["no limitations listed"]
        gaps.append("PII not blocked")
        return 1, gaps

    if category == "edge_no_sources":
        if len(sources) > 0 and synthesis_mode == "mock":
            gaps.append("mock may hallucinate with irrelevant sources")
        if "don't know" in answer.lower() or "no relevant" in answer.lower() or "couldn't find" in answer.lower():
            score = 4
        elif len(sources) == 0:
            gaps.append("no sources for obscure query — answer may be ungrounded")
            score = 2
        return max(1, min(5, score)), gaps

    if use_rag and len(sources) == 0:
        gaps.append("RAG enabled but zero sources returned")
        score -= 2

    buckets = _bucket_counts(sources)
    if category == "research" and buckets.get("research", 0) == 0:
        gaps.append("no research-bucket sources for research question")

    if data.get("require_citations") and not _has_citations(answer):
        gaps.append("citations required but none in answer")
        score -= 1

    if show_sources and len(sources) == 0:
        gaps.append("show_sources=true but empty sources list")

    if synthesis_mode == "mock":
        gaps.append("mock synthesis — not live Gemini")
        score = min(score, 3)

    if provider == "gemini" and synthesis_mode == "mock":
        gaps.append("provider honesty violation: gemini reported on mock path")
        score = 1

    if _has_headings(answer) and category in ("smalltalk", "app_help"):
        gaps.append("over-formal structure for conversational intent")

    if len(answer) > 50:
        score = min(5, score + 1)
    if len(sources) >= 3 and category in ("research", "protocol", "search"):
        score = min(5, score + 1)

    return max(1, min(5, score)), gaps


def _summarize_answer(text: str, n: int = 180) -> str:
    t = " ".join((text or "").split())
    return t[:n] + ("…" if len(t) > n else "")


def run_eval(*, role: str = "researcher") -> dict[str, Any]:
    from unittest.mock import patch

    from fastapi.testclient import TestClient

    from tests.auth_fixtures import apply_auth_override, clear_auth_override

    apply_auth_override(role)
    client = TestClient(__import__("app_skeleton.api.main", fromlist=["app"]).app)
    env_info: dict[str, Any] = {"auth_role": role}
    chat_results: list[dict] = []
    ask_comparisons: list[dict] = []
    infra: dict[str, Any] = {}

    try:
        with patch("app_skeleton.api.routers.chat.require_role"), patch(
            "app_skeleton.api.routers.copilot.require_role"
        ):
            t0 = time.time()
            status_r = client.get("/api/chat/status")
            env_info["chat_status_code"] = status_r.status_code
            if status_r.status_code == 200:
                env_info["chat_status"] = status_r.json()

            rkb = client.get("/api/research-knowledge/status")
            infra["research_kb_status_code"] = rkb.status_code
            if rkb.status_code == 200:
                infra["research_kb"] = rkb.json()

            us = client.get(
                "/api/platform/unified-search",
                params={"q": "ashlar stitching", "mode": "hybrid", "limit": 10},
            )
            infra["unified_search_code"] = us.status_code
            if us.status_code == 200:
                uj = us.json()
                infra["unified_search_sample"] = {
                    "total_hits": len(uj.get("hits") or []),
                    "buckets": _bucket_counts(uj.get("hits") or []),
                    "mode": uj.get("mode"),
                }

            us2 = client.get(
                "/api/platform/unified-search",
                params={"q": "GSE211956", "mode": "hybrid", "limit": 10},
            )
            if us2.status_code == 200:
                uj2 = us2.json()
                infra["unified_search_gse"] = {
                    "total_hits": len(uj2.get("hits") or []),
                    "buckets": _bucket_counts(uj2.get("hits") or []),
                }

            gold_set = _load_gold_set()
            eval_items: list[tuple[str, str, dict[str, Any] | None]] = []
            if gold_set:
                for spec in gold_set:
                    eval_items.append((spec.get("category", "gold"), spec["question"], spec))
            else:
                for category, question in QUESTIONS:
                    eval_items.append((category, question, None))

            for category, question, spec in eval_items:
                if EVAL_DELAY_S > 0:
                    time.sleep(EVAL_DELAY_S)
                start = time.time()
                r = client.post(
                    "/api/chat",
                    json={"message": question, "project_codes": PROJECT_CODES, "stream": False},
                    timeout=180,
                )
                elapsed = round(time.time() - start, 2)
                row: dict[str, Any] = {
                    "id": spec.get("id") if spec else None,
                    "category": category,
                    "question": question,
                    "status_code": r.status_code,
                    "elapsed_s": elapsed,
                }
                if r.status_code == 200:
                    d = r.json()
                    sources = d.get("sources") or []
                    score, gap_notes = _quality_score(d, category)
                    row.update({
                        "intent": d.get("intent"),
                        "answer_style": d.get("answer_style"),
                        "use_rag": d.get("use_rag"),
                        "show_sources": d.get("show_sources"),
                        "require_citations": d.get("require_citations"),
                        "provider": d.get("provider"),
                        "effective_provider": d.get("effective_provider"),
                        "model": d.get("model"),
                        "fallback_used": d.get("fallback_used"),
                        "synthesis_mode": d.get("synthesis_mode"),
                        "sources_count": len(sources),
                        "search_hits_count": len(d.get("search_hits") or []),
                        "buckets": _bucket_counts(sources),
                        "limitations": d.get("limitations") or [],
                        "blocked_by_guardrail": d.get("blocked_by_guardrail", False),
                        "has_headings": _has_headings(d.get("answer") or ""),
                        "has_citations": _has_citations(d.get("answer") or ""),
                        "answer": d.get("answer") or "",
                        "answer_preview": _summarize_answer(d.get("answer") or ""),
                        "quality_score": score,
                        "gap_notes": gap_notes,
                    })
                    if spec:
                        gold_score = _score_gold_item(spec, row)
                        row["gold_checks"] = gold_score["checks"]
                        row["gold_gaps"] = gold_score["gaps"]
                        row["gold_passed"] = gold_score["passed"]
                        row["must_cite"] = spec.get("must_cite")
                        row["must_block"] = spec.get("must_block")
                else:
                    row["error"] = r.text[:300]
                    row["quality_score"] = 1
                    row["gap_notes"] = ["HTTP error"]
                    row["gold_passed"] = False
                chat_results.append(row)

            compare_qs = [
                "How do I run Ashlar stitching in tCyCIF?",
                "What does Färkkilä Lab study?",
                "Find GSE211956",
            ]
            for q in compare_qs:
                chat_row = next((x for x in chat_results if x["question"] == q), None)
                rs = client.post(
                    "/ask",
                    json={"question": q, "project_codes": PROJECT_CODES, "mode": "search_only"},
                    timeout=120,
                )
                rd = client.post(
                    "/ask",
                    json={"question": q, "project_codes": PROJECT_CODES, "mode": "documentation_only"},
                    timeout=180,
                )
                comp: dict[str, Any] = {"question": q}
                if rs.status_code == 200:
                    sj = rs.json()
                    comp["ask_search_only"] = {
                        "sources_count": len(sj.get("sources") or []),
                        "buckets": _bucket_counts(sj.get("sources") or []),
                        "search_hits_count": len(sj.get("search_hits") or []),
                    }
                else:
                    comp["ask_search_only_error"] = rs.status_code
                if rd.status_code == 200:
                    dj = rd.json()
                    comp["ask_doc_mode"] = {
                        "sources_count": len(dj.get("sources") or []),
                        "buckets": _bucket_counts(dj.get("sources") or []),
                        "effective_provider": dj.get("effective_provider"),
                        "synthesis_mode": dj.get("synthesis_mode"),
                        "answer_preview": _summarize_answer(dj.get("answer") or ""),
                        "has_citations": _has_citations(dj.get("answer") or ""),
                    }
                else:
                    comp["ask_doc_mode_error"] = rd.status_code
                if chat_row:
                    comp["chat"] = {
                        "intent": chat_row.get("intent"),
                        "sources_count": chat_row.get("sources_count"),
                        "buckets": chat_row.get("buckets"),
                        "effective_provider": chat_row.get("effective_provider"),
                        "synthesis_mode": chat_row.get("synthesis_mode"),
                    }
                    comp["divergence"] = []
                    if chat_row.get("sources_count") != comp.get("ask_doc_mode", {}).get("sources_count"):
                        comp["divergence"].append("source count differs chat vs /ask doc mode")
                    if chat_row.get("sources_count") != comp.get("ask_search_only", {}).get("sources_count"):
                        comp["divergence"].append("chat sources != /ask search_only hits")
                ask_comparisons.append(comp)

            env_info["total_elapsed_s"] = round(time.time() - t0, 1)
    finally:
        clear_auth_override()

    has_gemini = bool(os.getenv("GEMINI_API_KEY", "").strip())
    providers = Counter(r.get("effective_provider") or r.get("provider") for r in chat_results if r.get("provider"))
    synthesis_modes = Counter(r.get("synthesis_mode") for r in chat_results if r.get("synthesis_mode"))
    http_errors = sum(1 for r in chat_results if r.get("status_code") != 200)
    gold_rows = [r for r in chat_results if r.get("gold_checks") is not None]
    gold_specs = _load_gold_set()
    gold_scored: list[dict[str, Any]] = []
    for i, row in enumerate(gold_rows):
        merged = dict(row)
        if i < len(gold_specs):
            merged.update({k: gold_specs[i].get(k) for k in ("category", "must_cite", "must_block", "use_rag", "expected_intent")})
        gold_scored.append(merged)
    release_gates = _release_gate_summary(gold_scored)

    return {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "branch": "cursor/unified-search-ai-lab-assistant",
        "mode": "in_process_testclient",
        "gemini_key_configured": has_gemini,
        "providers_seen": dict(providers),
        "synthesis_modes_seen": dict(synthesis_modes),
        "http_errors": http_errors,
        "gold_set_size": len(_load_gold_set()),
        "release_gates": release_gates,
        "env_info": env_info,
        "infra": infra,
        "chat_results": chat_results,
        "ask_comparisons": ask_comparisons,
    }


def _strategy_benchmark() -> dict[str, Any]:
    """Lightweight strategy detection + schema checks (no live LLM required)."""
    from app_skeleton.api.chat_conversation import classify_and_enrich
    from app_skeleton.api.research_strategy_engine import is_strategy_question

    if not STRATEGY_FIXTURE.is_file():
        return {"enabled": False, "reason": "fixture missing"}

    specs = json.loads(STRATEGY_FIXTURE.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for spec in specs:
        q = spec.get("question") or ""
        intent = classify_and_enrich(q)
        detected = is_strategy_question(q, intent)
        expect = spec.get("expect_strategy_detect")
        ok = True if expect is None else detected == expect
        rows.append({
            "id": spec.get("id"),
            "category": spec.get("category"),
            "detected": detected,
            "expect": expect,
            "pass": ok,
        })
    passed = sum(1 for r in rows if r["pass"])
    return {
        "enabled": True,
        "fixture": str(STRATEGY_FIXTURE),
        "passed": passed,
        "failed": len(rows) - passed,
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AI Lab Assistant evaluation battery")
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Write output to tests/search_qa_ai_baseline.json instead of last_run",
    )
    parser.add_argument("--role", default="researcher", choices=["researcher", "viewer", "editor", "admin"])
    args = parser.parse_args()

    report = run_eval(role=args.role)
    report["strategy_benchmark"] = _strategy_benchmark()
    out_name = "search_qa_ai_baseline.json" if args.baseline else "search_qa_ai_last_run.json"
    out = ROOT / "tests" / out_name
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    summary = {
        "written": str(out),
        "questions": len(report["chat_results"]),
        "http_errors": report["http_errors"],
        "providers": report["providers_seen"],
        "synthesis_modes": report["synthesis_modes_seen"],
        "gemini_key": report["gemini_key_configured"],
        "release_gates": report.get("release_gates"),
        "strategy_benchmark": report.get("strategy_benchmark"),
    }
    print(json.dumps(summary, indent=2))
    gates = report.get("release_gates") or {}
    if gates:
        print("\n--- Release gate summary ---")
        print(f"| Gate | Value | Pass |")
        print(f"|------|-------|------|")
        print(f"| Intent accuracy | {gates.get('intent_accuracy_pct')}% | {'✓' if gates.get('intent_gate_pass') else '✗'} |")
        print(f"| Citation compliance | {gates.get('citation_compliance_pct')}% | {'✓' if gates.get('citation_gate_pass') else '✗'} |")
        print(f"| PII blocking | — | {'✓' if gates.get('pii_gate_pass') else '✗'} |")
        print(f"| Research buckets | — | {'✓' if gates.get('research_bucket_gate_pass') else '✗'} |")
        print(f"| Provider honesty | {gates.get('provider_honesty_pct')}% | {'✓' if gates.get('provider_honesty_gate_pass') else '✗'} |")
        print(f"| Overall | {gates.get('overall_pass_pct')}% | {'✓' if gates.get('overall_gate_pass') else '✗'} |")


if __name__ == "__main__":
    main()
