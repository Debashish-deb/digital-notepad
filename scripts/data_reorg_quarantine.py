#!/usr/bin/env python3
"""Quarantine-first data reorganization — dry-run by default, no deletes.

Reads reports/smart_reorganization/move_manifest.json and emits review artifacts.
Apply moves only with --confirm into a timestamped quarantine directory.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "reports" / "smart_reorganization" / "move_manifest.json"
DEFAULT_OUT = ROOT / "reports" / "smart_reorganization" / "quarantine_runs"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _is_canonical_preserved(entry: dict) -> bool:
    reason = (entry.get("reason") or "").lower()
    return "canonical copy preserved" in reason


def classify_entry(entry: dict) -> str:
    if _is_canonical_preserved(entry):
        return "skip_canonical"
    action = (entry.get("action") or "move").lower()
    if action == "quarantine" or entry.get("duplicate_group_id"):
        return "duplicate_or_quarantine"
    return "move"


def build_outputs(manifest: dict, run_dir: Path) -> dict:
    run_dir.mkdir(parents=True, exist_ok=True)
    moves = manifest.get("moves") or []

    files_to_move: list[dict] = []
    duplicates_to_review: list[dict] = []
    quarantine_manifest: list[dict] = []
    restore_plan: list[dict] = []

    for entry in moves:
        current = entry.get("current_path", "")
        proposed = entry.get("proposed_path", "")
        kind = classify_entry(entry)
        row = {
            "current_path": current,
            "proposed_path": proposed,
            "action": entry.get("action"),
            "reason": entry.get("reason"),
            "sha256": entry.get("sha256"),
            "size_bytes": entry.get("size_bytes"),
            "risk_level": entry.get("risk_level"),
            "duplicate_group_id": entry.get("duplicate_group_id"),
        }
        if kind == "skip_canonical":
            continue
        if kind == "duplicate_or_quarantine":
            duplicates_to_review.append(row)
            quarantine_manifest.append({**row, "quarantine_target": proposed})
        else:
            files_to_move.append(row)
        restore_plan.append(
            {
                "from_path": proposed,
                "restore_to": current,
                "sha256": entry.get("sha256"),
                "size_bytes": entry.get("size_bytes"),
            }
        )

    move_csv = run_dir / "files_to_move.csv"
    dup_csv = run_dir / "duplicates_to_review.csv"
    q_manifest = run_dir / "quarantine_manifest.json"
    restore_json = run_dir / "restore_plan.json"

    fieldnames = [
        "current_path",
        "proposed_path",
        "action",
        "reason",
        "sha256",
        "size_bytes",
        "risk_level",
        "duplicate_group_id",
    ]
    for path, rows in ((move_csv, files_to_move), (dup_csv, duplicates_to_review)):
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    with q_manifest.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source_manifest": str(DEFAULT_MANIFEST),
                "entries": quarantine_manifest,
            },
            f,
            indent=2,
        )

    with restore_json.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "restore_instructions": "Copy each from_path back to restore_to to undo apply.",
                "entries": restore_plan,
            },
            f,
            indent=2,
        )

    return {
        "run_dir": str(run_dir),
        "files_to_move": len(files_to_move),
        "duplicates_to_review": len(duplicates_to_review),
        "quarantine_manifest": str(q_manifest),
        "restore_plan": str(restore_json),
    }


def apply_quarantine(manifest: dict, run_dir: Path, quarantine_root: Path) -> dict:
    applied: list[dict] = []
    errors: list[dict] = []
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = quarantine_root / stamp
    base.mkdir(parents=True, exist_ok=True)

    for entry in manifest.get("moves") or []:
        kind = classify_entry(entry)
        if kind in ("skip_canonical", "move"):
            continue
        if kind != "duplicate_or_quarantine":
            continue
        src = ROOT / entry["current_path"]
        if not src.exists():
            errors.append({"path": str(src), "error": "missing"})
            continue
        digest = sha256_file(src)
        if entry.get("sha256") and digest != entry["sha256"]:
            errors.append({"path": str(src), "error": "checksum_mismatch", "expected": entry["sha256"], "actual": digest})
            continue
        rel = Path(entry["current_path"])
        dest = base / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        applied.append(
            {
                "from": str(src),
                "to": str(dest),
                "sha256": digest,
                "size_bytes": dest.stat().st_size,
                "reason": entry.get("reason"),
            }
        )

    log_path = run_dir / "apply_log.json"
    with log_path.open("w", encoding="utf-8") as f:
        json.dump({"quarantine_root": str(base), "applied": applied, "errors": errors}, f, indent=2)
    return {"applied": len(applied), "errors": len(errors), "quarantine_root": str(base), "log": str(log_path)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Quarantine-first smart reorganization workflow")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--apply", action="store_true", help="Move quarantine candidates (requires --confirm)")
    parser.add_argument("--confirm", action="store_true", help="Explicit confirmation for apply")
    args = parser.parse_args()

    if not args.manifest.exists():
        print(f"Manifest not found: {args.manifest}", file=sys.stderr)
        return 1

    manifest = load_manifest(args.manifest)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = args.out_dir / stamp
    summary = build_outputs(manifest, run_dir)
    print(json.dumps(summary, indent=2))

    if args.apply:
        if not args.confirm:
            print("Refusing apply without --confirm", file=sys.stderr)
            return 2
        apply_summary = apply_quarantine(manifest, run_dir, ROOT / "reports" / "99_quarantine_review")
        print(json.dumps(apply_summary, indent=2))
        return 0 if apply_summary["errors"] == 0 else 3

    print("Dry-run only. Re-run with --apply --confirm to quarantine duplicate/placeholder files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
