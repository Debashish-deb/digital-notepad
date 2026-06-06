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

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / "configs" / ".env")

QUESTIONS = [
    # category, question
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

            for category, question in QUESTIONS:
                start = time.time()
                r = client.post(
                    "/api/chat",
                    json={"message": question, "project_codes": PROJECT_CODES, "stream": False},
                    timeout=180,
                )
                elapsed = round(time.time() - start, 2)
                row: dict[str, Any] = {
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
                else:
                    row["error"] = r.text[:300]
                    row["quality_score"] = 1
                    row["gap_notes"] = ["HTTP error"]
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

    return {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "branch": "cursor/unified-search-ai-lab-assistant",
        "mode": "in_process_testclient",
        "gemini_key_configured": has_gemini,
        "providers_seen": dict(providers),
        "synthesis_modes_seen": dict(synthesis_modes),
        "http_errors": http_errors,
        "env_info": env_info,
        "infra": infra,
        "chat_results": chat_results,
        "ask_comparisons": ask_comparisons,
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
    out_name = "search_qa_ai_baseline.json" if args.baseline else "search_qa_ai_last_run.json"
    out = ROOT / "tests" / out_name
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({
        "written": str(out),
        "questions": len(report["chat_results"]),
        "http_errors": report["http_errors"],
        "providers": report["providers_seen"],
        "synthesis_modes": report["synthesis_modes_seen"],
        "gemini_key": report["gemini_key_configured"],
    }, indent=2))


if __name__ == "__main__":
    main()
