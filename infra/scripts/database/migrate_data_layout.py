#!/usr/bin/env python3
"""Migrate omeia/data to smart taxonomy layout (skips research project twins)."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app_skeleton.api.data_layout import (  # noqa: E402
    DATA_ROOT,
    INGESTION_AUDIT_DIR,
    LAB_PROCESSED_ROOT,
    LAB_SECTION_SUBDIRS,
    LEGACY_INGESTION_DIR,
    LEGACY_LOGS_DIR,
    LEGACY_PROCESSED_DIR,
    REGISTRY_DIR,
    RUNTIME_LOGS_DIR,
    SOURCE_INVENTORY_DIR,
    lab_chunks_filename,
    lab_twin_filename,
)

REGISTRY_FILES = ("projects_catalog.json", "lab_personnel_roster.json", "processor_state.json", "processor.pid")
INVENTORY_FILES = (
    "raw_asset_inventory.json",
    "raw_asset_inventory.csv",
    "raw_asset_inventory_summary.json",
    "inventory_manifest.json",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def move_file(src: Path, dest: Path, *, dry_run: bool, log: list[dict]) -> None:
    if not src.is_file():
        return
    if dest.is_file():
        return
    log.append({"from": str(src.relative_to(ROOT)), "to": str(dest.relative_to(ROOT))})
    if dry_run:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dest))


def migrate(*, dry_run: bool) -> dict:
    log: list[dict] = []

    for name in REGISTRY_FILES:
        move_file(DATA_ROOT / name, REGISTRY_DIR / name, dry_run=dry_run, log=log)

    for name in INVENTORY_FILES:
        move_file(DATA_ROOT / name, SOURCE_INVENTORY_DIR / name, dry_run=dry_run, log=log)

    if LEGACY_INGESTION_DIR.is_dir():
        for path in sorted(LEGACY_INGESTION_DIR.glob("*.json")):
            sub = "latest" if path.name == "sync_run_report.json" else "history"
            move_file(path, INGESTION_AUDIT_DIR / sub / path.name, dry_run=dry_run, log=log)

    if LEGACY_LOGS_DIR.is_dir():
        for path in sorted(LEGACY_LOGS_DIR.glob("*.log")):
            dest = RUNTIME_LOGS_DIR / ("latest.log" if path.name == "autonomous_processor.log" else f"archived/{path.name}")
            move_file(path, dest, dry_run=dry_run, log=log)

    if LEGACY_PROCESSED_DIR.is_dir():
        for path in sorted(LEGACY_PROCESSED_DIR.glob("lab__*")):
            if path.suffix not in (".json", ".jsonl") and not path.name.endswith(".chunks.jsonl"):
                continue
            stem = path.name.replace(".chunks.jsonl", "").replace(".json", "")
            section_id = stem.replace("lab__", "", 1) if stem.startswith("lab__") else stem
            sub = LAB_SECTION_SUBDIRS.get(section_id, "overview_documents")
            move_file(path, LAB_PROCESSED_ROOT / sub / path.name, dry_run=dry_run, log=log)

    manifest = {"generated_at": utc_now(), "dry_run": dry_run, "moves": log}
    out = ROOT / "reports" / "smart_reorganization" / "data_layout_migration.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    if not dry_run:
        out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> int:
    p = argparse.ArgumentParser(description="Migrate data/ to smart taxonomy (no research project twins)")
    p.add_argument("--dry-run", action="store_true", help="Plan only")
    p.add_argument("--apply", action="store_true", help="Execute moves")
    args = p.parse_args()
    dry_run = not args.apply
    result = migrate(dry_run=dry_run)
    print(f"{'DRY-RUN' if dry_run else 'APPLIED'}: {len(result['moves'])} file moves")
    for row in result["moves"][:20]:
        print(f"  {row['from']} -> {row['to']}")
    if len(result["moves"]) > 20:
        print(f"  ... and {len(result['moves']) - 20} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
