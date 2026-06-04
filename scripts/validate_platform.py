#!/usr/bin/env python3
"""End-to-end platform validation — API, digital twins, catalog vs disk, checkers."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

API = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "app_skeleton" / "data" / "projects_catalog.json"
PROCESSED = ROOT / "app_skeleton" / "data" / "processed_projects"
PUBLIC = ROOT / "app_skeleton" / "ui" / "react_frontend" / "public" / "processed"

failures: list[str] = []
warnings: list[str] = []


def ok(msg: str) -> None:
    print(f"  ✓ {msg}")


def warn(msg: str) -> None:
    warnings.append(msg)
    print(f"  ⚠ {msg}")


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"  ✗ {msg}")


def main() -> int:
    print(f"\n=== OMEIA Platform Validation ({API}) ===\n")

    # Health
    print("[1] API health")
    try:
        r = requests.get(f"{API}/health", timeout=10)
        if r.status_code != 200:
            fail(f"/health → {r.status_code}")
        else:
            data = r.json()
            ok(f"API up · DB connected={data.get('database_connected')}")
            if not data.get("database_connected"):
                warn("Postgres not connected — run docker compose + ingest")
    except Exception as exc:
        fail(f"Cannot reach API: {exc}")
        print("\nStart backend: cd farkki_ai_platform_blueprint && uvicorn app_skeleton.api.main:app --port 8000")
        return 1

    # Core endpoints smoke test
    print("\n[2] Core endpoints")
    for path in [
        "/projects",
        "/stats",
        "/team",
        "/gap-analysis",
        "/ai-models",
        "/api/storage/roots",
        "/api/vault/summary",
        "/api/database/sections",
        "/api/knowledge/lab/stats",
        "/api/page-domains",
        "/api/documents/registry",
        "/api/search?q=protocol&mode=hybrid",
        "/api/admin/ingestion-jobs",
        "/api/admin/review-tasks",
    ]:
        try:
            r = requests.get(f"{API}{path}", timeout=15)
            if r.status_code == 200:
                ok(path)
            else:
                warn(f"{path} → {r.status_code}")
        except Exception as exc:
            warn(f"{path} → {exc}")

    # Digital twin pilots
    print("\n[3] Digital twins (pilot projects)")
    for code in ["SPACE", "CellCycle", "Tribus", "EyeMT", "Fanconi"]:
        try:
            r = requests.get(f"{API}/api/projects/{code}/digital-twin", timeout=30)
            if r.status_code != 200:
                fail(f"{code} twin → {r.status_code}")
                continue
            twin = r.json()
            assets = twin.get("total_assets_count") or twin.get("content_library", {}).get("totals", {}).get("all", 0)
            ok(f"{code}: {assets} assets, root={twin.get('content_root') or '—'}")
        except Exception as exc:
            fail(f"{code} twin → {exc}")

    # Static mounts
    print("\n[4] Static asset serving")
    try:
        r = requests.get(
            f"{API}/projects-static/29_Tribus/Figures/Fig1_v2.png",
            timeout=15,
        )
        if r.status_code == 200 and "image" in r.headers.get("content-type", ""):
            ok("projects-static image")
        else:
            warn(f"projects-static → {r.status_code}")
    except Exception as exc:
        warn(f"projects-static → {exc}")

    # Checker + parse_log
    print("\n[5] Diagnostics contracts")
    try:
        r = requests.post(f"{API}/run_checker", json={"checker_name": "python_env"}, timeout=30)
        if r.status_code == 200 and "stdout" in r.json():
            ok("run_checker (python_env)")
        else:
            fail(f"run_checker → {r.status_code}")
    except Exception as exc:
        fail(f"run_checker → {exc}")

    try:
        r = requests.post(
            f"{API}/parse_log",
            json={"log_text": "Out of memory (exit code 137)"},
            timeout=15,
        )
        if r.status_code == 200 and r.json().get("cause"):
            ok("parse_log")
        else:
            fail(f"parse_log → {r.status_code}")
    except Exception as exc:
        fail(f"parse_log → {exc}")

    # Catalog vs processed vs disk
    print("\n[6] Catalog / processed / disk alignment")
    if not CATALOG.exists():
        fail("projects_catalog.json missing")
    else:
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        codes = [p["project_code"] for p in catalog]
        ok(f"Catalog: {len(codes)} projects")

        processed_files = {p.stem for p in PROCESSED.glob("*.json")}
        missing_proc = [c for c in codes if c not in processed_files]
        if missing_proc:
            warn(f"Missing processed JSON: {', '.join(missing_proc[:8])}{'…' if len(missing_proc) > 8 else ''}")
        else:
            ok(f"Processed twins: {len(processed_files)}")

        public_files = {p.stem for p in PUBLIC.glob("*.json")} if PUBLIC.exists() else set()
        if len(public_files) < len(processed_files):
            warn(f"Public fallback stale: {len(public_files)}/{len(processed_files)} — run process-all")
        else:
            ok(f"Public fallback: {len(public_files)} files")

        no_folder = [p["project_code"] for p in catalog if not p.get("folder_path")]
        if no_folder:
            warn(f"Catalog-only (no disk folder): {', '.join(no_folder)}")

    print("\n[7] Lab section roots + vault")
    try:
        r = requests.get(f"{API}/api/database/sections", timeout=15)
        if r.status_code == 200:
            missing = r.json().get("missing_section_roots") or []
            if missing:
                fail(f"Missing lab section folders: {', '.join(missing)}")
            else:
                ok("All lab section roots exist on disk")
        else:
            warn(f"/api/database/sections → {r.status_code}")
        r = requests.get(f"{API}/api/vault/search", params={"q": "protocol", "limit": 3}, timeout=15)
        if r.status_code == 200:
            ok(f"Vault search ({r.json().get('count', 0)} hits)")
        else:
            warn(f"/api/vault/search → {r.status_code}")
        r = requests.get(f"{API}/api/vault/dedupe-report", params={"limit": 5}, timeout=15)
        if r.status_code == 200:
            ok(f"Dedupe groups: {r.json().get('duplicate_checksum_groups', 0)}")
        r = requests.get(f"{API}/api/knowledge/hybrid-search", params={"q": "onboarding", "limit": 5}, timeout=20)
        if r.status_code == 200:
            ok("Hybrid knowledge search")
        else:
            warn(f"/api/knowledge/hybrid-search → {r.status_code}")
        try:
            r = requests.post(f"{API}/api/vault/sync", timeout=120)
            if r.status_code == 200:
                ok(f"Vault Postgres sync ({r.json().get('upserted', 0)} rows)")
            else:
                warn(f"/api/vault/sync → {r.status_code}")
        except Exception as exc:
            warn(f"/api/vault/sync → {exc}")
    except Exception as exc:
        warn(f"vault/sections → {exc}")

    # Phase 3+ endpoints
    print("\n[8] Phase 3 — Feature warehouse")
    try:
        r = requests.get(f"{API}/features/definitions", timeout=10)
        if r.status_code == 200:
            ok(f"Feature definitions ({r.json().get('count', 0)})")
        else:
            warn(f"/features/definitions → {r.status_code}")
    except Exception as exc:
        warn(f"features → {exc}")

    print("\n[9] Phase 4 — Clinical stats")
    try:
        r = requests.post(f"{API}/clinical/survival", json={"project_code": "SPACE", "register_run": False}, timeout=15)
        if r.status_code == 200 and r.json().get("groups"):
            ok("Survival analysis")
        else:
            warn(f"/clinical/survival → {r.status_code}")
        r = requests.post(
            f"{API}/features/similarity",
            json={"sample_code": "SYNTH_SAMPLE_001", "project_code": "SPACE", "limit": 3},
            timeout=15,
        )
        if r.status_code == 200:
            ok(f"Feature similarity ({len(r.json().get('similar', []))} matches)")
        else:
            warn(f"/features/similarity → {r.status_code}")
    except Exception as exc:
        warn(f"clinical → {exc}")

    # Summary
    print("\n=== Summary ===")
    print(f"  Failures: {len(failures)}")
    print(f"  Warnings: {len(warnings)}")
    if failures:
        for f in failures:
            print(f"    - {f}")
    if warnings:
        for w in warnings:
            print(f"    - {w}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
