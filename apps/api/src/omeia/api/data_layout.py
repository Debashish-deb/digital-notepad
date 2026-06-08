"""Smart library data layout — new taxonomy paths with legacy fallback.

Research project twins stay flat under ``processed_projects/`` (Project Portfolio unchanged).
Lab section twins migrate under ``02_processed_projects/lab_operations/<category>/``.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

_PKG_ROOT = Path(__file__).resolve().parents[1]

DATA_ROOT = Path(os.environ.get("OMEIA_DATA_ROOT", str(_PKG_ROOT / "data"))).expanduser().resolve()

REGISTRY_DIR = DATA_ROOT / "00_registry"
SOURCE_INVENTORY_DIR = DATA_ROOT / "01_source_inventory"
LAB_PROCESSED_ROOT = DATA_ROOT / "02_processed_projects" / "lab_operations"
INGESTION_AUDIT_DIR = DATA_ROOT / "03_ingestion_audit"
RUNTIME_LOGS_DIR = DATA_ROOT / "04_runtime_logs"

# Flat research + legacy lab twins (Project Portfolio)
LEGACY_PROCESSED_DIR = DATA_ROOT / "processed_projects"
LEGACY_INGESTION_DIR = DATA_ROOT / "ingestion_reports"
LEGACY_LOGS_DIR = DATA_ROOT / "logs"

LAB_SECTION_SUBDIRS: dict[str, str] = {
    "wet_lab_files": "wet_lab_files",
    "overview_documents": "overview_documents",
    "overview_research_materials": "overview_research_materials",
    "overview_cleaning": "overview_documents",
    "overview_personnel": "overview_documents",
    "overview_onboarding": "overview_documents",
    "overview_guidelines": "overview_documents",
    "social_misc": "overview_documents",
    "orders_archive": "overview_documents",
    "orders_billing": "overview_documents",
}


def _first_existing(*paths: Path) -> Path:
    for path in paths:
        if path.exists():
            return path
    return paths[0]


def resolve_data_file(new_path: Path, legacy_path: Path) -> Path:
    return _first_existing(new_path, legacy_path)


def registry_path(name: str) -> Path:
    return resolve_data_file(REGISTRY_DIR / name, DATA_ROOT / name)


def inventory_dir() -> Path:
    if SOURCE_INVENTORY_DIR.is_dir() and any(SOURCE_INVENTORY_DIR.iterdir()):
        return SOURCE_INVENTORY_DIR
    if (SOURCE_INVENTORY_DIR / "raw_asset_inventory.json").is_file():
        return SOURCE_INVENTORY_DIR
    return DATA_ROOT


def inventory_json() -> Path:
    return resolve_data_file(
        SOURCE_INVENTORY_DIR / "raw_asset_inventory.json",
        DATA_ROOT / "raw_asset_inventory.json",
    )


def inventory_csv() -> Path:
    return resolve_data_file(
        SOURCE_INVENTORY_DIR / "raw_asset_inventory.csv",
        DATA_ROOT / "raw_asset_inventory.csv",
    )


def inventory_summary_json() -> Path:
    return resolve_data_file(
        SOURCE_INVENTORY_DIR / "raw_asset_inventory_summary.json",
        DATA_ROOT / "raw_asset_inventory_summary.json",
    )


def ingestion_reports_dir() -> Path:
    if INGESTION_AUDIT_DIR.is_dir():
        for sub in ("latest", "history", "failed_or_partial"):
            if any((INGESTION_AUDIT_DIR / sub).glob("*.json")):
                return INGESTION_AUDIT_DIR
    return LEGACY_INGESTION_DIR if LEGACY_INGESTION_DIR.is_dir() else INGESTION_AUDIT_DIR


def iter_ingestion_report_files() -> Iterable[Path]:
    base = ingestion_reports_dir()
    if base == INGESTION_AUDIT_DIR:
        for sub in ("latest", "history", "failed_or_partial"):
            subdir = base / sub
            if subdir.is_dir():
                yield from sorted(subdir.glob("*.json"))
        return
    if base.is_dir():
        yield from sorted(base.glob("*.json"))


def ingestion_report_write_dir(*, failed: bool = False) -> Path:
    if failed:
        dest = INGESTION_AUDIT_DIR / "failed_or_partial"
    else:
        dest = INGESTION_AUDIT_DIR / "latest"
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def processor_state_path() -> Path:
    return resolve_data_file(REGISTRY_DIR / "processor_state.json", DATA_ROOT / "processor_state.json")


def processor_pid_path() -> Path:
    return resolve_data_file(REGISTRY_DIR / "processor.pid", DATA_ROOT / "processor.pid")


def runtime_log_path(name: str = "autonomous_processor.log") -> Path:
    if name == "autonomous_processor.log":
        latest = RUNTIME_LOGS_DIR / "latest.log"
        if latest.is_file():
            return latest
    archived = RUNTIME_LOGS_DIR / "archived" / name
    if archived.is_file():
        return archived
    return LEGACY_LOGS_DIR / name


def runtime_log_write_path(name: str = "autonomous_processor.log") -> Path:
    if name == "autonomous_processor.log":
        RUNTIME_LOGS_DIR.mkdir(parents=True, exist_ok=True)
        return RUNTIME_LOGS_DIR / "latest.log"
    archived = RUNTIME_LOGS_DIR / "archived"
    archived.mkdir(parents=True, exist_ok=True)
    return archived / name


def lab_twin_filename(section_id: str) -> str:
    return f"lab__{section_id}.json"


def lab_chunks_filename(section_id: str) -> str:
    return f"lab__{section_id}.chunks.jsonl"


def lab_processed_read_path(section_id: str, *, chunks: bool = False) -> Path:
    name = lab_chunks_filename(section_id) if chunks else lab_twin_filename(section_id)
    sub = LAB_SECTION_SUBDIRS.get(section_id, "overview_documents")
    candidates = [
        LAB_PROCESSED_ROOT / sub / name,
        LEGACY_PROCESSED_DIR / name,
    ]
    if LAB_PROCESSED_ROOT.is_dir():
        candidates = list(LAB_PROCESSED_ROOT.rglob(name)) + candidates
    return _first_existing(*candidates)


def lab_processed_write_path(section_id: str, *, chunks: bool = False) -> Path:
    name = lab_chunks_filename(section_id) if chunks else lab_twin_filename(section_id)
    sub = LAB_SECTION_SUBDIRS.get(section_id, "overview_documents")
    dest = LAB_PROCESSED_ROOT / sub
    dest.mkdir(parents=True, exist_ok=True)
    return dest / name


def iter_lab_processed_files(*, chunks: bool = False) -> Iterable[Path]:
    pattern = "lab__*.chunks.jsonl" if chunks else "lab__*.json"
    seen: set[str] = set()
    if LAB_PROCESSED_ROOT.is_dir():
        for path in sorted(LAB_PROCESSED_ROOT.rglob(pattern)):
            if path.name == "lab__manifest.json":
                continue
            if path.name not in seen:
                seen.add(path.name)
                yield path
    if LEGACY_PROCESSED_DIR.is_dir():
        for path in sorted(LEGACY_PROCESSED_DIR.glob(pattern)):
            if path.name == "lab__manifest.json":
                continue
            if path.name not in seen:
                seen.add(path.name)
                yield path


def inventory_write_dir() -> Path:
    SOURCE_INVENTORY_DIR.mkdir(parents=True, exist_ok=True)
    return SOURCE_INVENTORY_DIR


def registry_write_dir() -> Path:
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    return REGISTRY_DIR
