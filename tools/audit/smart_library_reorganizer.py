#!/usr/bin/env python3
"""
OMEIA Smart Library Reorganizer — safe dry-run-first taxonomy migration.

Default (no destructive changes):
  python tools/audit/smart_library_reorganizer.py --root . --dry-run --hash

Review outputs under reports/smart_reorganization/, then:
  python tools/audit/smart_library_reorganizer.py --root . --apply --hash --include-docs --include-reports

Rollback:
  python tools/audit/smart_library_reorganizer.py --root . --rollback reports/smart_reorganization/rollback_manifest.json
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

# ---------------------------------------------------------------------------
# Category taxonomy (UI + folder targets)
# ---------------------------------------------------------------------------

CATEGORY_INDEX: list[dict[str, Any]] = [
    {
        "id": "registry",
        "label": "Project Registry",
        "folder": "omeia/data/00_registry",
        "description": "Core catalogs, personnel roster, processor state",
        "search_tags": ["catalog", "projects", "roster", "processor", "registry"],
        "aliases": ["projects_catalog.json", "lab_personnel_roster.json"],
        "display_priority": 1,
        "document_lifecycle": "config",
    },
    {
        "id": "source_inventory",
        "label": "Source Inventory",
        "folder": "omeia/data/01_source_inventory",
        "description": "Raw file inventory and source asset maps",
        "search_tags": ["inventory", "raw", "assets", "vault", "manifest"],
        "aliases": ["raw_asset_inventory.json", "raw_asset_inventory.csv"],
        "display_priority": 2,
        "document_lifecycle": "source",
    },
    {
        "id": "processed_knowledge",
        "label": "Processed Knowledge Base",
        "folder": "omeia/data/02_processed_projects",
        "description": "Project JSON twins, chunk indexes, search-ready exports",
        "search_tags": ["processed", "chunks", "jsonl", "digitalization", "twins"],
        "aliases": ["processed_projects"],
        "display_priority": 3,
        "document_lifecycle": "processed",
    },
    {
        "id": "ingestion_audit",
        "label": "Import & Processing History",
        "folder": "omeia/data/03_ingestion_audit",
        "description": "Ingestion reports, failed imports, processing history",
        "search_tags": ["ingestion", "import", "sync", "audit", "pipeline"],
        "aliases": ["ingestion_reports"],
        "display_priority": 4,
        "document_lifecycle": "generated_report",
    },
    {
        "id": "runtime_logs",
        "label": "Runtime Logs",
        "folder": "omeia/data/04_runtime_logs",
        "description": "Application and operational logs",
        "search_tags": ["log", "runtime", "processor", "errors"],
        "aliases": ["logs"],
        "display_priority": 5,
        "document_lifecycle": "runtime_log",
    },
    {
        "id": "storage_providers",
        "label": "Storage Connectors",
        "folder": "omeia/storage/01_providers",
        "description": "WebDAV, SMB, R2, and cloud/local storage adapters",
        "search_tags": ["webdav", "smb", "r2", "storage", "connector"],
        "aliases": ["datacloud_webdav.py", "pdrive_smb.py", "r2_preview.py"],
        "display_priority": 10,
        "document_lifecycle": "code",
    },
    {
        "id": "ingestion_engine",
        "label": "Ingestion Engine",
        "folder": "omeia/storage/02_ingestion_runtime",
        "description": "Code that pulls files into the system",
        "search_tags": ["ingestion", "runtime", "vault"],
        "aliases": ["ingestion.py"],
        "display_priority": 11,
        "document_lifecycle": "code",
    },
    {
        "id": "storage_environment",
        "label": "Storage Environment",
        "folder": "omeia/storage/03_environment",
        "description": "Environment helpers and runtime path configuration",
        "search_tags": ["env", "paths", "configuration"],
        "aliases": ["env.py"],
        "display_priority": 12,
        "document_lifecycle": "code",
    },
    {
        "id": "lab_operations",
        "label": "Lab Operations",
        "folder": "docs/01_lab_operations",
        "description": "Equipment manuals, maintenance, gas ordering",
        "search_tags": ["manual", "maintenance", "gas", "equipment", "sterilization"],
        "aliases": ["Välinehuolto", "Gas_ordering"],
        "display_priority": 20,
        "document_lifecycle": "source",
    },
    {
        "id": "procurement",
        "label": "Orders & Procurement",
        "folder": "docs/02_procurement_and_orders",
        "description": "Orders, quotes, offers, yearly spreadsheets, lab coats",
        "search_tags": ["order", "quote", "offer", "procurement", "excel"],
        "aliases": ["ORDERS & RELATED INFORMATION", "OFFERS_QUOTES"],
        "display_priority": 21,
        "document_lifecycle": "source",
    },
    {
        "id": "shipping_billing",
        "label": "Shipping, Billing & Accounts",
        "folder": "docs/03_shipping_billing_and_accounts",
        "description": "FedEx, billing, supplier contacts, account instructions",
        "search_tags": ["billing", "shipping", "fedex", "invoice", "account"],
        "aliases": ["Credit card purchase", "Sensire account"],
        "display_priority": 22,
        "document_lifecycle": "source",
    },
    {
        "id": "research_reference",
        "label": "Research Reference Library",
        "folder": "docs/04_research_reference",
        "description": "Protocols, papers, project notes, scientific references",
        "search_tags": ["protocol", "publication", "research", "methods"],
        "aliases": [],
        "display_priority": 23,
        "document_lifecycle": "source",
    },
    {
        "id": "current_summary",
        "label": "Current Reports",
        "folder": "reports/00_current_summary",
        "description": "Latest human-readable summaries",
        "search_tags": ["summary", "latest", "report"],
        "aliases": [],
        "display_priority": 30,
        "document_lifecycle": "generated_report",
    },
    {
        "id": "current_machine",
        "label": "Current Report Data",
        "folder": "reports/01_current_machine_readable",
        "description": "Latest JSON/CSV outputs used by the app",
        "search_tags": ["metadata", "inventory", "csv", "json", "enriched"],
        "aliases": ["metadata_v2"],
        "display_priority": 31,
        "document_lifecycle": "generated_report",
    },
    {
        "id": "historical_audits",
        "label": "Historical Audit Trail",
        "folder": "reports/02_historical_audits",
        "description": "Superseded first-pass, second-pass, and corrected audits",
        "search_tags": ["audit", "historical", "first_pass", "second_pass"],
        "aliases": ["document_library_audit/first_pass", "document_library_audit/second_pass"],
        "display_priority": 32,
        "document_lifecycle": "archive",
    },
    {
        "id": "structure_analysis",
        "label": "Structure Analysis",
        "folder": "reports/03_structure_analysis",
        "description": "Repository structure analyzer outputs",
        "search_tags": ["structure", "analysis", "metadata"],
        "aliases": ["structure_analysis"],
        "display_priority": 33,
        "document_lifecycle": "generated_report",
    },
    {
        "id": "quarantine",
        "label": "Review Before Deleting",
        "folder": "99_quarantine_review",
        "description": "Duplicates, obsolete generated files, and risky candidates",
        "search_tags": ["quarantine", "duplicate", "review", "obsolete"],
        "aliases": [],
        "display_priority": 99,
        "document_lifecycle": "quarantine_candidate",
    },
]

SKIP_DIR_NAMES = {
    ".git", ".hg", ".svn", ".cache", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    ".qodo", ".venv", "venv", "env", "__pycache__", "node_modules", "dist", "build",
    ".next", ".nuxt", ".turbo", ".expo", ".dart_tool", ".idea", ".vscode",
    "99_quarantine_review", "smart_reorganization",
}

LAB_OPERATION_KEYWORDS = re.compile(
    r"manual|maintenance|steriliz|välinehuolto|instrument|gas.order|kaasutilaus|herafreeze|minus80|revco|sensire",
    re.I,
)
PROCUREMENT_KEYWORDS = re.compile(
    r"order|quote|offer|quartzy|lab.coat|työvaate|eppendorf|centrifuge|catalog|varastokirjanpito|fican|archive",
    re.I,
)
SHIPPING_BILLING_KEYWORDS = re.compile(
    r"bill|invoice|billing|credit.card|fedex|shipping|account|vahvistus|customs|supplier",
    re.I,
)
RESEARCH_KEYWORDS = re.compile(r"protocol|publication|paper|research|methods|notes", re.I)

RESEARCH_PROJECTS = {
    "NKI", "CellCycle", "Fanconi", "iPDC_1.0", "iPDC_2.0", "KRAS", "SPACE", "SPACEstat",
    "SPACEjoint", "EyeMT", "FINPROVE", "Tribus", "Proteomics", "ADC", "DCIS", "EMT",
    "TLS", "CIN2", "HGSC_scRNAseq", "Sequencing", "Organoids", "Myelonets", "Pixel_AI",
    "TMA_Cohorts", "vTMA", "ovaHRDscar", "Mesenchymal_Ovca", "Endometrial_HRD", "Ovca_VTE",
    "Auria", "sciSet", "SC_Integration", "SideProjects", "VanharantaCollab", "SaloCollab",
    "LeppaCollab", "HaikalaCollab",
}

LAB_PROCESSED_PREFIXES = {
    "lab__wet_lab_files": "lab_operations/wet_lab_files",
    "lab__overview_documents": "lab_operations/overview_documents",
    "lab__overview_research_materials": "lab_operations/overview_research_materials",
    "lab__overview_cleaning": "lab_operations/overview_documents",
    "lab__overview_personnel": "lab_operations/overview_documents",
    "lab__social_misc": "lab_operations/overview_documents",
    "lab__orders_archive": "lab_operations/overview_documents",
    "lab__orders_billing": "lab_operations/overview_documents",
}

STORAGE_PROVIDER_FILES = {"datacloud_webdav.py", "pdrive_smb.py", "r2_preview.py"}
STORAGE_RUNTIME_FILES = {"ingestion.py"}
STORAGE_ENV_FILES = {"env.py"}

EXPORT_PAIRS = {
    "raw_asset_inventory.json": "raw_asset_inventory.csv",
    "metadata_enriched_inventory.json": "metadata_enriched_inventory.csv",
}

TINY_FILE_BYTES = 16
RETENTION_DEFAULT_DAYS = 30


@dataclass
class MoveProposal:
    current_path: str
    proposed_path: str
    action: str
    confidence: float
    reason: str
    risk_level: str
    duplicate_group_id: str | None = None
    canonical_path: str | None = None
    document_lifecycle: str = "source"
    usefulness_score: int = 50
    sha256: str | None = None
    size_bytes: int = 0

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScanStats:
    files_scanned: int = 0
    moves_proposed: int = 0
    duplicates_found: int = 0
    quarantine_candidates: int = 0
    high_risk_skipped: int = 0
    already_in_place: int = 0
    space_recoverable_bytes: int = 0


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def sha256_file(path: Path, max_bytes: int | None = None) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
            if max_bytes is not None and h.digest_size:  # noqa: SIM114 — stream only
                pass
    return h.hexdigest()


def usefulness_score_for(
    lifecycle: str,
    risk: str,
    *,
    is_canonical: bool,
    size_bytes: int,
) -> int:
    base = {
        "source": 90,
        "processed": 85,
        "config": 88,
        "generated_report": 60,
        "runtime_log": 35,
        "code": 95,
        "archive": 40,
        "quarantine_candidate": 10,
    }.get(lifecycle, 50)
    if is_canonical:
        base = min(100, base + 5)
    if risk == "never_auto_delete":
        base = max(base, 92)
    if risk == "high":
        base = min(base, 70)
    if size_bytes < TINY_FILE_BYTES:
        base = max(5, base - 40)
    return base


def classify_path(root: Path, path: Path) -> MoveProposal | None:
    """Return a move proposal for path, or None to skip scanning this path entirely."""
    rp = rel(root, path)
    name = path.name
    lower = rp.lower()
    size = path.stat().st_size if path.is_file() else 0

    def proposal(
        target: str,
        *,
        action: str = "move",
        confidence: float = 0.9,
        reason: str,
        risk: str = "low",
        lifecycle: str = "source",
        canonical: str | None = None,
        dup_id: str | None = None,
    ) -> MoveProposal:
        if rp == target:
            return MoveProposal(
                current_path=rp,
                proposed_path=target,
                action="keep",
                confidence=1.0,
                reason="Already in target location",
                risk_level="low",
                document_lifecycle=lifecycle,
                usefulness_score=usefulness_score_for(lifecycle, "low", is_canonical=True, size_bytes=size),
                size_bytes=size,
            )
        return MoveProposal(
            current_path=rp,
            proposed_path=target,
            action=action,
            confidence=confidence,
            reason=reason,
            risk_level=risk,
            canonical_path=canonical,
            duplicate_group_id=dup_id,
            document_lifecycle=lifecycle,
            usefulness_score=usefulness_score_for(lifecycle, risk, is_canonical=canonical == rp, size_bytes=size),
            size_bytes=size,
        )

    # --- omeia/data ---
    if name in {"projects_catalog.json", "lab_personnel_roster.json", "processor_state.json", "processor.pid"}:
        return proposal(
            f"omeia/data/00_registry/{name}",
            reason="Core registry catalog (requires --allow-data-moves + API path update)",
            lifecycle="config",
            risk="high",
        )

    if name in {"raw_asset_inventory.json", "raw_asset_inventory.csv", "raw_asset_inventory_summary.json", "inventory_manifest.json"}:
        return proposal(
            f"omeia/data/01_source_inventory/{name}",
            reason="Canonical source inventory (requires --allow-data-moves + API path update)",
            lifecycle="source",
            risk="high",
        )

    if rp.startswith("omeia/data/processed_projects/"):
        stem = name.replace(".chunks.jsonl", "").replace(".json", "")
        if stem in LAB_PROCESSED_PREFIXES:
            sub = LAB_PROCESSED_PREFIXES[stem]
        elif stem.startswith("lab__"):
            sub = "lab_operations/overview_documents"
        else:
            sub = "research_projects/" + stem.replace(".", "_")
        return proposal(
            f"omeia/data/02_processed_projects/{sub}/{name}",
            reason=f"Processed twin ({stem})",
            lifecycle="processed",
            confidence=0.92,
            risk="high",
        )

    if rp.startswith("omeia/data/ingestion_reports/"):
        if name == "sync_run_report.json":
            sub = "latest"
        elif "fail" in lower or "partial" in lower or "error" in lower:
            sub = "failed_or_partial"
        else:
            sub = "history"
        return proposal(
            f"omeia/data/03_ingestion_audit/{sub}/{name}",
            reason="Ingestion audit report (requires --allow-data-moves + API path update)",
            lifecycle="generated_report",
            confidence=0.85,
            risk="high",
        )

    if rp.startswith("omeia/data/logs/"):
        if name == "autonomous_processor.log":
            target = "omeia/data/04_runtime_logs/latest.log"
        else:
            target = f"omeia/data/04_runtime_logs/archived/{name}"
        return proposal(
            target,
            reason="Runtime operational log",
            lifecycle="runtime_log",
            confidence=0.88,
        )

    # --- omeia/storage (high risk) ---
    if rp.startswith("omeia/storage/"):
        if name in STORAGE_PROVIDER_FILES:
            return proposal(
                f"omeia/storage/01_providers/{name}",
                reason="Storage connector module",
                lifecycle="code",
                risk="high",
                confidence=0.7,
            )
        if name in STORAGE_RUNTIME_FILES:
            return proposal(
                f"omeia/storage/02_ingestion_runtime/{name}",
                reason="Ingestion runtime module",
                lifecycle="code",
                risk="high",
                confidence=0.7,
            )
        if name in STORAGE_ENV_FILES:
            return proposal(
                f"omeia/storage/03_environment/{name}",
                reason="Storage environment helper",
                lifecycle="code",
                risk="high",
                confidence=0.7,
            )
        if name == "__init__.py":
            return None
        return proposal(
            rp,
            action="skip",
            reason="Unclassified storage file — manual review",
            lifecycle="code",
            risk="high",
            confidence=0.3,
        )

    # --- docs: lab content under ORDERS & RELATED INFORMATION ---
    if rp.startswith("docs/ORDERS & RELATED INFORMATION/"):
        subpath = rp.split("ORDERS & RELATED INFORMATION/", 1)[1]
        if "Gas_ordering" in subpath or LAB_OPERATION_KEYWORDS.search(subpath):
            if "gas" in subpath.lower() or "kaasun" in subpath.lower() or "woikoski" in subpath.lower():
                bucket = "docs/01_lab_operations/gas_ordering"
            else:
                bucket = "docs/01_lab_operations/maintenance_and_service"
        elif "Lab_coats" in subpath:
            bucket = "docs/02_procurement_and_orders/lab_coats"
        elif "OFFERS_QUOTES" in subpath or "QUOTES" in subpath:
            bucket = "docs/02_procurement_and_orders/offers_and_quotes"
        elif "ORDERS_Excels" in subpath or re.search(r"ORDERS\s+20\d{2}", subpath):
            bucket = "docs/02_procurement_and_orders/yearly_order_excels"
        elif "Order_confirmations" in subpath or "manual" in subpath.lower():
            bucket = "docs/02_procurement_and_orders/order_confirmations"
        elif SHIPPING_BILLING_KEYWORDS.search(subpath) or "Credit card" in subpath or "Sensire" in subpath:
            bucket = "docs/03_shipping_billing_and_accounts/billing_instructions"
        elif "Archive" in subpath:
            bucket = "docs/99_archive_review/old_computer_orders"
        else:
            bucket = "docs/02_procurement_and_orders/order_confirmations"
        return proposal(
            f"{bucket}/{Path(subpath).name}",
            reason="Lab procurement / operations document",
            lifecycle="source",
            risk="medium",
            confidence=0.8,
        )

    if rp.startswith("docs/") and re.match(r"docs/\d{2}_", rp):
        return proposal(
            rp,
            action="keep",
            reason="Developer documentation — keep in place",
            lifecycle="config",
            risk="never_auto_delete",
            confidence=1.0,
        )

    # --- reports ---
    if rp.startswith("reports/structure_analysis/"):
        return proposal(
            f"reports/03_structure_analysis/{name}",
            reason="Structure analyzer output",
            lifecycle="generated_report",
            confidence=0.95,
        )

    if rp.startswith("reports/document_library_audit/metadata_v2/"):
        if name.endswith((".json", ".csv")) and "inventory" in name.lower():
            return proposal(
                f"reports/01_current_machine_readable/{name}",
                reason="Latest machine-readable enriched inventory",
                lifecycle="generated_report",
                confidence=0.9,
            )
        if name.endswith(".md") and "summary" in name.lower():
            return proposal(
                f"reports/00_current_summary/{name}",
                reason="Latest readable audit summary",
                lifecycle="generated_report",
                confidence=0.88,
            )
        return proposal(
            f"reports/01_current_machine_readable/{name}",
            reason="Current metadata_v2 audit artifact",
            lifecycle="generated_report",
            confidence=0.75,
        )

    if rp.startswith("reports/document_library_audit/first_pass/"):
        return proposal(
            f"reports/02_historical_audits/first_pass/{name}",
            reason="Superseded first-pass audit",
            lifecycle="archive",
            confidence=0.9,
        )

    if rp.startswith("reports/document_library_audit/second_pass/"):
        return proposal(
            f"reports/02_historical_audits/second_pass/{name}",
            reason="Superseded second-pass audit",
            lifecycle="archive",
            confidence=0.9,
        )

    if rp.startswith("reports/document_library_audit/final_corrected/"):
        return proposal(
            f"reports/02_historical_audits/final_corrected/{name}",
            reason="Final corrected historical audit",
            lifecycle="archive",
            confidence=0.88,
        )

    if rp.startswith("reports/document_library_audit/"):
        return proposal(
            f"reports/02_historical_audits/first_pass/{name}",
            reason="Legacy document_library_audit artifact",
            lifecycle="archive",
            confidence=0.7,
        )

    return None


def iter_scan_paths(root: Path, *, include_docs: bool, include_reports: bool) -> Iterable[Path]:
    roots = [root / "omeia" / "data"]
    if include_docs:
        roots.append(root / "docs")
    if include_reports:
        roots.append(root / "reports")
    roots.append(root / "omeia" / "storage")

    for base in roots:
        if not base.exists():
            continue
        for dirpath, dirnames, filenames in os_walk_safe(base):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES]
            for fn in filenames:
                yield Path(dirpath) / fn


def os_walk_safe(path: Path) -> Iterable[tuple[str, list[str], list[str]]]:
    import os

    for entry in os.walk(path, followlinks=False):
        yield entry


def scan_library(
    root: Path,
    *,
    do_hash: bool,
    include_docs: bool,
    include_reports: bool,
    min_confidence: float,
    retention_days: int,
    quarantine_only: bool,
) -> tuple[list[MoveProposal], ScanStats, dict[str, list[str]]]:
    proposals: list[MoveProposal] = []
    stats = ScanStats()
    hash_groups: dict[str, list[str]] = defaultdict(list)
    basename_groups: dict[str, list[str]] = defaultdict(list)

    for path in iter_scan_paths(root, include_docs=include_docs, include_reports=include_reports):
        if not path.is_file():
            continue
        stats.files_scanned += 1
        prop = classify_path(root, path)
        if prop is None:
            continue
        if prop.action == "keep":
            stats.already_in_place += 1
            continue
        if prop.confidence < min_confidence:
            prop.action = "skip"
            prop.reason += f" (below min confidence {min_confidence})"
            stats.high_risk_skipped += 1
        if do_hash and path.stat().st_size > 0:
            try:
                digest = sha256_file(path)
                prop.sha256 = digest
                hash_groups[digest].append(prop.current_path)
                basename_groups[path.name.lower()].append(prop.current_path)
            except OSError:
                pass
        if path.stat().st_size < TINY_FILE_BYTES:
            prop.action = "quarantine"
            prop.reason = "Empty or tiny placeholder file"
            prop.risk_level = "medium"
            prop.document_lifecycle = "quarantine_candidate"
            stats.quarantine_candidates += 1
        proposals.append(prop)

    # Exact duplicate quarantine (level 1)
    for digest, paths in hash_groups.items():
        if len(paths) < 2:
            continue
        stats.duplicates_found += len(paths) - 1
        canonical = _pick_canonical(paths)
        dup_id = digest[:16]
        for p in paths:
            for prop in proposals:
                if prop.current_path != p:
                    continue
                if p == canonical:
                    prop.canonical_path = canonical
                    prop.duplicate_group_id = dup_id
                    prop.reason += " — canonical copy preserved"
                else:
                    quarantine_root = _quarantine_target(root, prop)
                    prop.proposed_path = quarantine_root
                    prop.action = "quarantine"
                    prop.canonical_path = canonical
                    prop.duplicate_group_id = dup_id
                    prop.reason = f"Exact SHA-256 duplicate of {canonical}"
                    prop.document_lifecycle = "quarantine_candidate"
                    prop.risk_level = "medium"
                    stats.quarantine_candidates += 1
                    stats.space_recoverable_bytes += prop.size_bytes

    # Level 3 — superseded report families (older first_pass inventory when metadata_v2 exists)
    enriched = {p.current_path for p in proposals if "metadata_enriched_inventory" in p.current_path}
    if enriched:
        for prop in proposals:
            if "first_pass/document_inventory" in prop.current_path:
                prop.action = "quarantine"
                prop.proposed_path = "reports/99_quarantine_review/obsolete_reports/" + Path(prop.current_path).name
                prop.reason = "Superseded by metadata_v2 enriched inventory"
                prop.document_lifecycle = "quarantine_candidate"
                stats.quarantine_candidates += 1

    if quarantine_only:
        proposals = [p for p in proposals if p.action == "quarantine"]

    stats.moves_proposed = sum(1 for p in proposals if p.action in {"move", "quarantine"})
    return proposals, stats, dict(hash_groups)


def _pick_canonical(paths: list[str]) -> str:
    def score(p: str) -> tuple[int, int, str]:
        priority = 0
        if "01_source_inventory/raw_asset_inventory.json" in p or p.endswith("raw_asset_inventory.json"):
            priority += 100
        if "00_registry/" in p:
            priority += 80
        if "metadata_v2/" in p or "01_current_machine_readable/" in p:
            priority += 60
        if "first_pass/" in p or "second_pass/" in p:
            priority -= 20
        if "(1)" in p or " copy" in p.lower():
            priority -= 30
        return (priority, -len(p), p)

    return sorted(paths, key=score, reverse=True)[0]


def _quarantine_target(root: Path, prop: MoveProposal) -> str:
    name = Path(prop.current_path).name
    if prop.duplicate_group_id:
        return f"omeia/data/99_quarantine_review/duplicates/{prop.duplicate_group_id[:8]}_{name}"
    if prop.document_lifecycle == "generated_report":
        return f"reports/99_quarantine_review/obsolete_reports/{name}"
    return f"omeia/data/99_quarantine_review/unknown_category/{name}"


def write_manifests(root: Path, proposals: list[MoveProposal], stats: ScanStats, hash_groups: dict[str, list[str]]) -> Path:
    out = root / "reports" / "smart_reorganization"
    out.mkdir(parents=True, exist_ok=True)

    rows = [p.to_row() for p in proposals]
    with (out / "move_manifest.json").open("w", encoding="utf-8") as f:
        json.dump({"generated_at": utc_now(), "stats": asdict(stats), "moves": rows}, f, indent=2)

    with (out / "move_manifest.csv").open("w", encoding="utf-8", newline="") as f:
        if rows:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    _write_reorganization_plan(out, proposals, stats)
    _write_duplicate_report(out, hash_groups, proposals)
    _write_quarantine_review(out, proposals)
    _write_category_index(out, proposals)
    _write_readmes(root, proposals, apply=False)
    (root / "DOCUMENT_LIBRARY_README.md").write_text(_landing_readme(), encoding="utf-8")
    return out


def _write_reorganization_plan(out: Path, proposals: list[MoveProposal], stats: ScanStats) -> None:
    lines = [
        "# OMEIA Smart Library Reorganization Plan",
        "",
        f"Generated: {utc_now()}",
        "",
        "## Summary",
        "",
        f"- Files scanned: **{stats.files_scanned}**",
        f"- Moves / quarantine proposed: **{stats.moves_proposed}**",
        f"- Exact duplicates found: **{stats.duplicates_found}**",
        f"- Quarantine candidates: **{stats.quarantine_candidates}**",
        f"- High-risk skipped: **{stats.high_risk_skipped}**",
        f"- Already in target layout: **{stats.already_in_place}**",
        f"- Space recoverable after review: **{stats.space_recoverable_bytes / 1024 / 1024:.2f} MB**",
        "",
        "## Target taxonomy",
        "",
        "See `category_index.json` for UI labels, search tags, and folder paths.",
        "",
        "## Safety policy",
        "",
        "1. Default run is dry-run only — no files moved.",
        "2. Quarantine before delete — duplicates go to `99_quarantine_review/`.",
        "3. Source lab documents, configs, and code are never auto-deleted.",
        "4. Storage Python modules are high-risk — require `--allow-code-moves` on apply.",
        "",
        "## Top proposed actions",
        "",
    ]
    by_action: dict[str, list[MoveProposal]] = defaultdict(list)
    for p in proposals:
        by_action[p.action].append(p)
    for action in ("move", "quarantine", "skip", "keep"):
        items = by_action.get(action, [])[:15]
        if not items:
            continue
        lines.append(f"### {action.title()} ({len(by_action[action])})")
        lines.append("")
        for p in items:
            lines.append(f"- `{p.current_path}` → `{p.proposed_path}` — {p.reason}")
        lines.append("")
    (out / "reorganization_plan.md").write_text("\n".join(lines), encoding="utf-8")


def _write_duplicate_report(out: Path, hash_groups: dict[str, list[str]], proposals: list[MoveProposal]) -> None:
    lines = ["# Duplicate Report", "", f"Generated: {utc_now()}", ""]
    lines.append("## Level 1 — Exact duplicates (SHA-256)")
    lines.append("")
    exact = {k: v for k, v in hash_groups.items() if len(v) > 1}
    if not exact:
        lines.append("No exact duplicates detected.")
    else:
        for digest, paths in sorted(exact.items(), key=lambda x: -len(x[1])):
            canonical = _pick_canonical(paths)
            lines.append(f"### Group `{digest[:16]}` ({len(paths)} files)")
            lines.append(f"- **Canonical:** `{canonical}`")
            for p in paths:
                mark = " (canonical)" if p == canonical else " → quarantine candidate"
                lines.append(f"- `{p}`{mark}")
            lines.append("")

    lines.append("## Level 2 — Export pairs (not duplicates)")
    lines.append("")
    for a, b in EXPORT_PAIRS.items():
        lines.append(f"- `{a}` ↔ `{b}` — keep both unless content equivalence proven")

    lines.append("")
    lines.append("## Level 3 — Same report family (older versions)")
    lines.append("")
    superseded = [p for p in proposals if "Superseded" in p.reason]
    if superseded:
        for p in superseded[:20]:
            lines.append(f"- `{p.current_path}` — {p.reason}")
    else:
        lines.append("No superseded report moves proposed.")

    lines.append("")
    lines.append("## Near duplicates (filename similarity)")
    lines.append("")
    basename_groups: dict[str, list[str]] = defaultdict(list)
    for p in proposals:
        basename_groups[Path(p.current_path).name.lower()].append(p.current_path)
    conflicts = {k: v for k, v in basename_groups.items() if len(v) > 1}
    for name, paths in list(conflicts.items())[:25]:
        lines.append(f"- `{name}`: {len(paths)} paths — review for naming collision")

    (out / "duplicate_report.md").write_text("\n".join(lines), encoding="utf-8")


def _write_quarantine_review(out: Path, proposals: list[MoveProposal]) -> None:
    lines = [
        "# Quarantine Review",
        "",
        f"Generated: {utc_now()}",
        "",
        "Do **not** delete these files until a human confirms the canonical copy is preserved.",
        "",
    ]
    q = [p for p in proposals if p.action == "quarantine"]
    if not q:
        lines.append("No quarantine candidates in this plan.")
    else:
        for p in q:
            lines.append(f"## `{p.current_path}`")
            lines.append(f"- Proposed: `{p.proposed_path}`")
            lines.append(f"- Reason: {p.reason}")
            lines.append(f"- Canonical: `{p.canonical_path or 'n/a'}`")
            lines.append(f"- Risk: {p.risk_level}")
            lines.append("")
    (out / "quarantine_review.md").write_text("\n".join(lines), encoding="utf-8")


def _write_category_index(out: Path, proposals: list[MoveProposal]) -> None:
    counts: dict[str, int] = defaultdict(int)
    for p in proposals:
        for cat in CATEGORY_INDEX:
            folder = cat["folder"]
            if p.proposed_path.startswith(folder) or folder in p.proposed_path:
                counts[cat["id"]] += 1
                break

    enriched = []
    for cat in CATEGORY_INDEX:
        item = dict(cat)
        item["file_count"] = counts.get(cat["id"], 0)
        enriched.append(item)

    payload = {"generated_at": utc_now(), "categories": enriched}
    (out / "category_index.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _readme_for_folder(folder: str) -> str:
    cat = next((c for c in CATEGORY_INDEX if c["folder"] in folder or folder.endswith(c["folder"].split("/")[-1])), None)
    label = cat["label"] if cat else folder
    desc = cat["description"] if cat else "OMEIA library category"
    tags = ", ".join(cat["search_tags"]) if cat else ""
    return (
        f"# {label}\n\n"
        f"{desc}\n\n"
        f"**Search tags:** {tags}\n\n"
        "This folder is part of the OMEIA Smart Library taxonomy. "
        "See `DOCUMENT_LIBRARY_README.md` at the repository root and "
        "`reports/smart_reorganization/reorganization_plan.md` for migration details.\n"
    )


def _write_readmes(root: Path, proposals: list[MoveProposal], *, apply: bool) -> None:
    folders = {p.proposed_path.rsplit("/", 1)[0] for p in proposals if p.action in {"move", "quarantine"}}
    for cat in CATEGORY_INDEX:
        folders.add(cat["folder"])
    stubs: list[dict[str, str]] = []
    for folder in sorted(folders):
        stubs.append({"folder": folder, "content": _readme_for_folder(folder)})
    out = root / "reports" / "smart_reorganization" / "readme_stubs.json"
    out.write_text(json.dumps({"folders": stubs}, indent=2), encoding="utf-8")
    if not apply:
        return
    for item in stubs:
        readme = root / item["folder"] / "README.md"
        if readme.exists():
            continue
        readme.parent.mkdir(parents=True, exist_ok=True)
        readme.write_text(item["content"], encoding="utf-8")


def _landing_readme() -> str:
    lines = [
        "# OMEIA Document Library Guide",
        "",
        "This repository organizes scientific, lab, and platform knowledge into a **task-first** layout.",
        "",
        "## Where to look",
        "",
        "| You need… | Go to… | Label |",
        "|-----------|--------|-------|",
    ]
    for cat in sorted(CATEGORY_INDEX, key=lambda c: c["display_priority"]):
        lines.append(f"| {cat['description']} | `{cat['folder']}/` | {cat['label']} |")
    lines.extend([
        "",
        "## Safety",
        "",
        "- Generated reports and duplicates go to `99_quarantine_review/` — review before deleting.",
        "- Run `tools/audit/smart_library_reorganizer.py --dry-run` before any `--apply`.",
        "- Roll back with `--rollback reports/smart_reorganization/rollback_manifest.json`.",
        "",
        "## App integration",
        "",
        "The UI reads `reports/smart_reorganization/category_index.json` for human-friendly category labels.",
        "",
    ])
    return "\n".join(lines)


def apply_moves(
    root: Path,
    proposals: list[MoveProposal],
    *,
    allow_code_moves: bool,
    allow_data_moves: bool,
    min_confidence: float,
) -> list[dict[str, Any]]:
    rollback: list[dict[str, Any]] = []
    for prop in proposals:
        if prop.action not in {"move", "quarantine"}:
            continue
        if prop.confidence < min_confidence:
            continue
        if prop.current_path.startswith("omeia/data/") and not allow_data_moves:
            continue
        if prop.document_lifecycle == "code" and prop.risk_level == "high" and not allow_code_moves:
            continue
        src = root / prop.current_path
        dst = root / prop.proposed_path
        if not src.is_file():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        rollback.append({
            "from": prop.proposed_path,
            "to": prop.current_path,
            "moved_at": utc_now(),
        })
    out = root / "reports" / "smart_reorganization" / "rollback_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"generated_at": utc_now(), "moves": rollback}, indent=2), encoding="utf-8")
    return rollback


def rollback_moves(root: Path, manifest_path: Path) -> int:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    count = 0
    for entry in reversed(data.get("moves", [])):
        src = root / entry["from"]
        dst = root / entry["to"]
        if not src.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        count += 1
    return count


def print_summary(stats: ScanStats, out_dir: Path, *, dry_run: bool) -> None:
    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"\n=== OMEIA Smart Library Reorganizer ({mode}) ===")
    print(f"Files scanned:              {stats.files_scanned}")
    print(f"Moves proposed:             {stats.moves_proposed}")
    print(f"Duplicates found:           {stats.duplicates_found}")
    print(f"Quarantine candidates:      {stats.quarantine_candidates}")
    print(f"High-risk skipped:          {stats.high_risk_skipped}")
    print(f"Already in place:           {stats.already_in_place}")
    print(f"Space recoverable (review): {stats.space_recoverable_bytes / 1024 / 1024:.2f} MB")
    print(f"Manifests written to:       {out_dir}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="OMEIA Smart Library Reorganizer (safe, dry-run first)")
    p.add_argument("--root", type=Path, default=Path("."), help="Repository root")
    p.add_argument("--dry-run", action="store_true", help="Plan only (default)")
    p.add_argument("--apply", action="store_true", help="Execute moves from latest plan")
    p.add_argument("--hash", action="store_true", help="Compute SHA-256 for duplicate detection")
    p.add_argument("--retention-days", type=int, default=RETENTION_DEFAULT_DAYS)
    p.add_argument("--min-confidence", type=float, default=0.5)
    p.add_argument("--include-reports", action="store_true", default=True)
    p.add_argument("--include-docs", action="store_true", default=True)
    p.add_argument("--no-include-reports", action="store_false", dest="include_reports")
    p.add_argument("--no-include-docs", action="store_false", dest="include_docs")
    p.add_argument("--quarantine-only", action="store_true", help="Only output quarantine actions")
    p.add_argument("--allow-code-moves", action="store_true", help="Allow moving omeia/storage Python modules")
    p.add_argument("--allow-data-moves", action="store_true", help="Allow moving omeia/data (breaks API until paths updated)")
    p.add_argument("--rollback", type=Path, metavar="MANIFEST", help="Rollback a prior apply using rollback_manifest.json")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve()

    if args.rollback:
        n = rollback_moves(root, args.rollback.resolve())
        print(f"Rolled back {n} moves from {args.rollback}")
        return 0

    dry_run = not args.apply
    if not args.apply:
        args.dry_run = True

    proposals, stats, hash_groups = scan_library(
        root,
        do_hash=args.hash,
        include_docs=args.include_docs,
        include_reports=args.include_reports,
        min_confidence=args.min_confidence,
        retention_days=args.retention_days,
        quarantine_only=args.quarantine_only,
    )
    out_dir = write_manifests(root, proposals, stats, hash_groups)
    print_summary(stats, out_dir, dry_run=dry_run)

    if args.apply:
        _write_readmes(root, proposals, apply=True)
        applied = apply_moves(
            root,
            proposals,
            allow_code_moves=args.allow_code_moves,
            allow_data_moves=args.allow_data_moves,
            min_confidence=args.min_confidence,
        )
        print(f"Applied {len(applied)} moves. Rollback manifest updated.")
        if not args.allow_data_moves:
            print("Note: omeia/data moves were skipped (use --allow-data-moves after updating API paths).")
    else:
        print("\nDry-run complete. Review manifests before running with --apply.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
