#!/usr/bin/env python3
"""Platform validation orchestrator — Phases 4–8 readiness checks.

Usage:
  python scripts/ops/validate_platform.py [API_URL]
  python scripts/ops/validate_platform.py --json-only

Writes: tests/platform_validation_last_run.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT_JSON = ROOT / "tests" / "platform_validation_last_run.json"
VENV_PY = ROOT / ".test-venv" / "bin" / "python"
PYTHON = str(VENV_PY if VENV_PY.is_file() else sys.executable)


def _run(cmd: list[str], *, timeout: int = 300, cwd: Path | None = None) -> dict[str, Any]:
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd or ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "cmd": cmd,
            "exit_code": proc.returncode,
            "stdout_tail": proc.stdout[-4000:] if proc.stdout else "",
            "stderr_tail": proc.stderr[-2000:] if proc.stderr else "",
            "elapsed_s": round(time.monotonic() - t0, 1),
            "ok": proc.returncode == 0,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "cmd": cmd,
            "exit_code": -1,
            "ok": False,
            "error": f"timeout after {timeout}s",
            "stdout_tail": (exc.stdout or "")[-2000:] if exc.stdout else "",
            "stderr_tail": (exc.stderr or "")[-2000:] if exc.stderr else "",
            "elapsed_s": round(time.monotonic() - t0, 1),
        }
    except Exception as exc:
        return {"cmd": cmd, "exit_code": -1, "ok": False, "error": str(exc)}


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _api_smoke(api: str) -> dict[str, Any]:
    import requests

    results: list[dict[str, Any]] = []
    try:
        r = requests.get(f"{api}/health", timeout=10)
        results.append({"check": "/health", "ok": r.status_code == 200, "status": r.status_code})
        if r.status_code == 200:
            body = r.json()
            results.append({"check": "database_connected", "ok": bool(body.get("database_connected"))})
    except Exception as exc:
        return {"ok": False, "reachable": False, "error": str(exc), "checks": results}

    try:
        r = requests.get(f"{api}/metrics", timeout=5)
        results.append({"check": "/metrics", "ok": r.status_code == 200, "status": r.status_code})
    except Exception as exc:
        results.append({"check": "/metrics", "ok": False, "error": str(exc)})

    return {"ok": all(c.get("ok") for c in results if c["check"] in ("/health",)), "reachable": True, "checks": results}


def main() -> int:
    parser = argparse.ArgumentParser(description="OMEIA platform validation")
    parser.add_argument("api", nargs="?", default="http://127.0.0.1:8000")
    parser.add_argument("--json-only", action="store_true")
    parser.add_argument("--skip-pytest", action="store_true")
    parser.add_argument("--skip-search-qa", action="store_true")
    parser.add_argument("--skip-continuous-eval", action="store_true")
    args = parser.parse_args()

    report: dict[str, Any] = {
        "run_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "api_url": args.api,
        "sections": {},
    }
    failures: list[str] = []

    print(f"\n=== OMEIA Platform Validation (Phases 4–8) ===\n")

    # 1. Backend pytest
    if not args.skip_pytest:
        print("[1] Backend test suite")
        phase_tests = _run(
            [PYTHON, "-m", "pytest", "tests/", "-q", "--tb=no"],
            timeout=240,
        )
        report["sections"]["pytest_full"] = phase_tests
        print(f"  {'✓' if phase_tests['ok'] else '✗'} pytest full (exit {phase_tests['exit_code']})")
        if not phase_tests["ok"]:
            failures.append("pytest_full")

        focused = _run(
            [
                PYTHON,
                "-m",
                "pytest",
                "tests/test_researcher_resolver.py",
                "tests/test_project_permissions.py",
                "tests/test_ocr_queue.py",
                "tests/test_ocr_adapter.py",
                "tests/test_ocr_queue_flag.py",
                "tests/test_vault_semantic_search.py",
                "tests/test_vault_json_fallback.py",
                "tests/test_deployment_ops.py",
                "tests/test_security_authentication.py",
                "tests/test_security_authorization.py",
                "-q",
                "--tb=no",
            ],
            timeout=120,
        )
        report["sections"]["pytest_phases_4_8"] = focused
        print(f"  {'✓' if focused['ok'] else '✗'} phases 4–8 focused tests")
        if not focused["ok"]:
            failures.append("pytest_phases_4_8")

    # 2. Search QA
    if not args.skip_search_qa:
        print("\n[2] Search QA")
        sq = _run([PYTHON, "scripts/search/run_search_qa.py"], timeout=120)
        report["sections"]["search_qa"] = sq
        sq_data = _load_json(ROOT / "tests" / "search_qa_last_run.json")
        if sq_data:
            report["sections"]["search_qa_summary"] = {
                "passed": sq_data.get("passed"),
                "failed": sq_data.get("failed"),
            }
        print(f"  {'✓' if sq['ok'] else '✗'} run_search_qa.py")
        if not sq["ok"]:
            failures.append("search_qa")

    # 3. Copilot eval (use last run if present; fresh run is slow)
    print("\n[3] RAG / copilot evaluation")
    eval_data = _load_json(ROOT / "tests" / "search_qa_ai_last_run.json")
    if eval_data:
        gates = eval_data.get("release_gates") or {}
        report["sections"]["copilot_eval"] = {
            "source": "tests/search_qa_ai_last_run.json",
            "http_errors": eval_data.get("http_errors"),
            "release_gates": gates,
            "ok": eval_data.get("http_errors", 1) == 0,
        }
        print(f"  ✓ last eval loaded (http_errors={eval_data.get('http_errors')}, overall_gate={gates.get('overall_gate_pass')})")
    else:
        report["sections"]["copilot_eval"] = {"ok": False, "error": "no search_qa_ai_last_run.json"}
        failures.append("copilot_eval")
        print("  ✗ no copilot eval artifact")

    # 4. Linux sync health
    print("\n[4] Linux sync health")
    sync = _run([PYTHON, "scripts/ops/check_linux_sync_health.py"], timeout=60)
    sync_data: dict[str, Any] | None = None
    raw = subprocess.run(
        [PYTHON, "scripts/ops/check_linux_sync_health.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    try:
        sync_data = json.loads(raw.stdout)
    except Exception:
        sync_data = {"ok": False, "parse_error": True, "stdout": raw.stdout[:500]}
    report["sections"]["sync_health"] = {"run": sync, "report": sync_data}
    sync_ok = bool(sync_data and sync_data.get("ok"))
    print(f"  {'✓' if sync_ok else '⚠'} sync health (failed={sync_data.get('failed') if sync_data else '?'})")
    if not sync_ok:
        failures.append("sync_health")

    # 5. Backup dry-run
    print("\n[5] Backup dry-run")
    backup = _run(["bash", "scripts/ops/backup_linux.sh", "--dry-run"], timeout=60)
    report["sections"]["backup_dry_run"] = backup
    print(f"  {'✓' if backup['ok'] else '✗'} backup_linux.sh --dry-run")
    if not backup["ok"]:
        failures.append("backup_dry_run")

    # 6. Frontend build artifact
    print("\n[6] Frontend production build")
    dist = ROOT / "omeia" / "ui" / "react_frontend" / "dist" / "index.html"
    build_ok = dist.is_file()
    report["sections"]["frontend_build"] = {"dist_index_exists": build_ok, "path": str(dist)}
    if not build_ok:
        build = _run(["npm", "run", "build"], cwd=ROOT / "omeia" / "ui" / "react_frontend", timeout=180)
        report["sections"]["frontend_build"]["build_run"] = build
        build_ok = dist.is_file() and build.get("ok", False)
    print(f"  {'✓' if build_ok else '✗'} dist/index.html")
    if not build_ok:
        failures.append("frontend_build")

    # 7. Continuous quality eval
    if not args.skip_continuous_eval:
        print("\n[7] Continuous quality eval")
        ce = _run(
            [
                PYTHON,
                "scripts/ops/run_continuous_eval.py",
                "--force",
                "--skip-copilot",
                "--no-persist",
            ],
            timeout=180,
        )
        report["sections"]["continuous_eval"] = ce
        ce_data = _load_json(ROOT / "tests" / "quality_eval_last_run.json")
        if ce_data:
            report["sections"]["continuous_eval_summary"] = {
                "status": ce_data.get("status"),
                "composite_score": ce_data.get("composite_score"),
                "search_qa": (ce_data.get("metrics") or {}).get("search_qa"),
            }
        print(f"  {'✓' if ce['ok'] else '✗'} run_continuous_eval.py")
        if not ce["ok"]:
            failures.append("continuous_eval")

    # 8. Live API (optional)
    print(f"\n[8] Live API smoke ({args.api})")
    api = _api_smoke(args.api)
    report["sections"]["api_smoke"] = api
    if api.get("reachable"):
        print(f"  {'✓' if api.get('ok') else '⚠'} API reachable")
    else:
        print(f"  ⚠ API not reachable (dev/TestClient validations still valid)")
        report["sections"]["api_smoke"]["note"] = "skipped_live_requirements"

    report["failures"] = failures
    report["ok"] = len(failures) == 0

    OUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n=== Summary: {len(failures)} blocking section(s) ===")
    for f in failures:
        print(f"  - {f}")
    print(f"\nWrote {OUT_JSON}\n")

    if args.json_only:
        print(json.dumps(report, indent=2))

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
