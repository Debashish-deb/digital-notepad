#!/usr/bin/env python3
"""Debug RAG wiring while the API is running (in-process or HTTP)."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _print_report(report: dict) -> None:
    print(f"\n=== RAG diagnostic: {report.get('query', '')!r} ===")
    print(f"OK: {report.get('ok')} | total: {report.get('total_ms')} ms\n")
    for step in report.get("steps") or []:
        status = "OK" if step.get("ok") else "FAIL"
        print(f"[{status}] {step.get('name')} — {step.get('elapsed_ms')} ms")
        if step.get("detail"):
            print(f"       {step['detail']}")
        data = step.get("data") or {}
        if data:
            print(f"       {json.dumps(data, ensure_ascii=False)[:500]}")


def run_in_process(query: str, *, category: str, mode: str, probe_llm: bool) -> dict:
    from app_skeleton.api.chat_model_catalog import make_chat_llm
    from app_skeleton.api.common import DB_CONN, qdrant_client, rag_agent
    from app_skeleton.api.rag_diagnostics import run_rag_diagnostics
    from app_skeleton.api.search_service import SearchService

    llm = make_chat_llm(None, None)
    search_svc = SearchService(db_conn=DB_CONN, qdrant=qdrant_client, llm=llm)
    report = run_rag_diagnostics(
        query,
        search_svc=search_svc,
        llm=llm,
        rag_agent=rag_agent,
        category_id=category,
        mode=mode,
        probe_llm=probe_llm,
    )
    return report.to_dict()


def run_http(query: str, *, base_url: str, category: str, mode: str) -> None:
    import urllib.error
    import urllib.request

    payload = json.dumps(
        {
            "query": query,
            "category": category,
            "mode": mode,
            "probe_llm": True,
            "project_codes": [],
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/chat/rag-debug",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')[:800]}")
        return
    except Exception as exc:
        print(f"Request failed after {(time.monotonic() - started) * 1000:.0f} ms: {exc}")
        return
    _print_report(body)


def run_category_timing(query: str, *, base_url: str, category: str, mode: str) -> None:
    import urllib.error
    import urllib.request

    payload = json.dumps(
        {
            "message": query,
            "category": category,
            "mode": mode,
            "project_codes": [],
            "use_rag": True,
            "use_local_models": True,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/chat/category",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.monotonic()
    print(f"\n=== Category chat timing ({category}/{mode}) ===")
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        elapsed = (time.monotonic() - started) * 1000.0
        print(f"Completed in {elapsed:.0f} ms")
        print(f"agents_used: {body.get('agents_used')}")
        print(f"synthesis_mode: {body.get('synthesis_mode')}")
        print(f"answer_chars: {len(body.get('answer') or '')}")
        if body.get("warnings"):
            print(f"warnings: {body.get('warnings')}")
        print((body.get("answer") or "")[:400])
    except urllib.error.HTTPError as exc:
        elapsed = (time.monotonic() - started) * 1000.0
        print(f"HTTP {exc.code} after {elapsed:.0f} ms")
        print(exc.read().decode("utf-8", errors="replace")[:800])
    except Exception as exc:
        elapsed = (time.monotonic() - started) * 1000.0
        print(f"Failed after {elapsed:.0f} ms: {exc}")


def _print_infra_hint() -> None:
    docker_local = os.getenv("DOCKER_LOCAL", "true").strip().lower()
    ts_ip = os.getenv("TAILSCALE_LINUX_IP", "").strip()
    if docker_local not in {"false", "0"} and not ts_ip:
        print(
            "\nNOTE: DOCKER_LOCAL is true and TAILSCALE_LINUX_IP is unset.\n"
            "If Docker runs on Linux (not this Mac), set in configs/.env:\n"
            "  TAILSCALE_LINUX_IP=<linux-tailscale-ip>\n"
            "  DOCKER_LOCAL=false\n"
            "  OLLAMA_BASE_URL=http://<linux-ip>:11434/v1\n"
            "  QDRANT_URL=http://<linux-ip>:6333\n"
            "Then restart the API. See docs/MAC_STARTUP.md\n"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Debug OMEIA RAG wiring")
    parser.add_argument(
        "query",
        nargs="?",
        default="Explain TLS in HGSC immunotherapy",
        help="Test query",
    )
    parser.add_argument("--category", default="cancer_oncology")
    parser.add_argument("--mode", default="balanced", choices=["fast", "balanced", "deep"])
    parser.add_argument("--api", default=os.getenv("OMEIA_API_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--in-process", action="store_true", help="Run diagnostics in-process (no HTTP)")
    parser.add_argument("--skip-llm-probe", action="store_true")
    parser.add_argument("--category-chat", action="store_true", help="Also time full /api/chat/category")
    args = parser.parse_args()

    os.environ.setdefault("PLATFORM_AUTH_DISABLED", "true")
    _print_infra_hint()

    if args.in_process:
        report = run_in_process(
            args.query,
            category=args.category,
            mode=args.mode,
            probe_llm=not args.skip_llm_probe,
        )
        _print_report(report)
    else:
        run_http(args.query, base_url=args.api, category=args.category, mode=args.mode)

    if args.category_chat and not args.in_process:
        run_category_timing(
            args.query,
            base_url=args.api,
            category=args.category,
            mode=args.mode,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
