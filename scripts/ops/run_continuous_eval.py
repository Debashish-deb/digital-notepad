#!/usr/bin/env python3
"""Run continuous quality evaluation battery (search, copilot, strategy, feedback).

Usage:
  python scripts/ops/run_continuous_eval.py
  python scripts/ops/run_continuous_eval.py --skip-copilot --no-persist
  python scripts/ops/run_continuous_eval.py --json-only

Writes: tests/quality_eval_last_run.json
Requires: sql/149_quality_eval_runs.sql applied when --persist is used.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="OMEIA continuous quality evaluation")
    parser.add_argument("--skip-copilot", action="store_true", help="Skip slow copilot HTTP eval")
    parser.add_argument("--no-persist", action="store_true", help="Do not write to platform.quality_eval_run")
    parser.add_argument("--role", default="researcher", help="Copilot eval role (researcher|admin)")
    parser.add_argument("--json-only", action="store_true", help="Print full JSON report to stdout")
    parser.add_argument("--force", action="store_true", help="Run even when OMEIA_CONTINUOUS_EVAL_ENABLED=false")
    args = parser.parse_args()

    from app_skeleton.api.platform_flags import continuous_eval_enabled
    from app_skeleton.api.quality_eval_service import run_continuous_eval

    if not args.force and not continuous_eval_enabled():
        print("Continuous eval disabled (OMEIA_CONTINUOUS_EVAL_ENABLED=false). Use --force to override.")
        return 2

    report = run_continuous_eval(
        trigger_source="cli",
        copilot_role=args.role,
        skip_copilot=args.skip_copilot,
        persist=not args.no_persist,
    )

    if args.json_only:
        print(json.dumps(report, indent=2, default=str))
    else:
        status = report.get("status")
        score = report.get("composite_score")
        regressions = report.get("regressions") or []
        print(f"\n=== OMEIA Continuous Quality Eval ===")
        print(f"Status: {status}")
        print(f"Composite score: {score}")
        metrics = report.get("metrics") or {}
        sq = metrics.get("search_qa") or {}
        print(f"Search QA: {sq.get('passed')}/{sq.get('total')} passed")
        if metrics.get("copilot", {}).get("skipped"):
            print("Copilot eval: skipped")
        else:
            gates = (metrics.get("copilot") or {}).get("release_gates") or {}
            print(f"Copilot gates: overall_pass={gates.get('overall_gate_pass')}")
        print(f"Regressions: {len(regressions)}")
        print(f"Wrote {ROOT / 'tests' / 'quality_eval_last_run.json'}\n")

    status = report.get("status")
    if status == "fail":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
