#!/usr/bin/env python3
"""Build document library category verification JSONs from audit data."""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "tools" / "audit"))

from document_library_audit import FileCategory  # noqa: E402

AUDIT_DIR = PROJECT_ROOT / "reports" / "document_library_audit" / "first_pass"
OUT_DIR = PROJECT_ROOT / "configs" / "document_library"

INVENTORY_PATH = AUDIT_DIR / "document_inventory.json"
CATEGORY_TREE_PATH = AUDIT_DIR / "category_tree.json"
CATEGORY_SUMMARY_PATH = AUDIT_DIR / "category_summary.csv"


def _load_inventory() -> list[dict]:
    if not INVENTORY_PATH.is_file():
        raise FileNotFoundError(f"Missing inventory: {INVENTORY_PATH}")
    data = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def _folder_segments(logical_path: str) -> list[str]:
    parts = [p.strip() for p in (logical_path or "").split("/") if p.strip()]
    return parts


def build_official_tree(inventory: list[dict], category_tree: dict) -> dict:
    """Official UI taxonomy from audit category_tree.json."""
    out = {
        "source": "category_tree.json",
        "generated_from": str(CATEGORY_TREE_PATH),
        "main_tabs": category_tree.get("main_tabs", {}),
        "total_main_tabs": category_tree.get("total_main_tabs", 0),
        "total_sub_tabs": category_tree.get("total_sub_tabs", 0),
        "total_categories": category_tree.get("total_categories", 0),
    }
    domain_counts: dict[str, int] = defaultdict(int)
    section_counts: dict[str, int] = defaultdict(int)
    for row in inventory:
        domain_counts[row.get("domain") or "unknown"] += 1
        section_counts[row.get("section_hint") or "unknown"] += 1
    out["domain_file_counts"] = dict(sorted(domain_counts.items(), key=lambda x: -x[1]))
    out["section_file_counts"] = dict(sorted(section_counts.items(), key=lambda x: -x[1]))
    return out


def build_folder_derived_tree(inventory: list[dict]) -> dict:
    """Hierarchy derived from top-level folder paths."""
    root: dict = {"children": {}, "file_count": 0}

    def insert(node: dict, segments: list[str]) -> None:
        node["file_count"] = node.get("file_count", 0) + 1
        if not segments:
            return
        head, *tail = segments
        children = node.setdefault("children", {})
        if head not in children:
            children[head] = {"label": head, "children": {}, "file_count": 0}
        insert(children[head], tail)

    for row in inventory:
        segs = _folder_segments(row.get("logical_path") or "")
        if segs:
            insert(root, segs[:-1] if len(segs) > 1 else segs[:1])

    def flatten(node: dict, path: list[str] | None = None) -> list[dict]:
        path = path or []
        items: list[dict] = []
        for name, child in sorted((node.get("children") or {}).items()):
            full = path + [name]
            items.append({
                "path": "/".join(full),
                "label": name,
                "file_count": child.get("file_count", 0),
                "depth": len(full),
            })
            items.extend(flatten(child, full))
        return items

    return {
        "source": "folder_path",
        "root_folders": [
            {"path": k, "label": k, "file_count": v.get("file_count", 0)}
            for k, v in sorted((root.get("children") or {}).items())
        ],
        "nodes": flatten(root),
        "total_files": len(inventory),
    }


def build_tag_derived_tree(inventory: list[dict]) -> dict:
    """Tags from domain + section_hint + asset_type."""
    tags: dict[str, int] = defaultdict(int)
    combos: dict[str, int] = defaultdict(int)
    for row in inventory:
        domain = row.get("domain") or "unknown"
        section = row.get("section_hint") or "unknown"
        asset_type = row.get("asset_type") or "unknown"
        tags[f"domain:{domain}"] += 1
        tags[f"section:{section}"] += 1
        tags[f"type:{asset_type}"] += 1
        combos[f"{domain}/{section}"] += 1
    return {
        "source": "derived_tags",
        "tags": dict(sorted(tags.items(), key=lambda x: -x[1])),
        "domain_section_combos": dict(sorted(combos.items(), key=lambda x: -x[1])),
    }


def build_scientific_terms_tree(inventory: list[dict]) -> dict:
    """Scientific categories from FileCategory enum + path heuristics."""
    enum_terms = {c.value: {"label": c.value.replace("_", " ").title(), "file_count": 0} for c in FileCategory}

    keyword_map = {
        "protocol": ["protocol", "sop"],
        "sop": ["sop", "standard operating"],
        "wet_lab_operation": ["wet lab", "wet_lab"],
        "inventory": ["inventory", "reagent"],
        "antibody_panel": ["antibody", "panel"],
        "marker_panel": ["marker"],
        "cycif": ["cycif"],
        "tcycif": ["tcycif", "t-cycif"],
        "order_forms": ["order", "purchase", "billing"],
        "scrna_seq": ["scrna", "single cell"],
        "sequencing": ["sequencing", "seq"],
        "spreadsheet_tracker": [".xlsx", ".xls", "tracker"],
        "ffpe": ["ffpe"],
        "frozen_tissue": ["frozen"],
        "patient_sample": ["patient", "sample id"],
    }

    for row in inventory:
        blob = " ".join(
            str(row.get(k, ""))
            for k in ("logical_path", "filename", "section_hint", "asset_type", "domain")
        ).lower()
        matched = False
        for term, keywords in keyword_map.items():
            if any(kw in blob for kw in keywords):
                enum_terms.setdefault(term, {"label": term, "file_count": 0})
                enum_terms[term]["file_count"] += 1
                matched = True
        if not matched:
            enum_terms["unknown"]["file_count"] += 1

    return {
        "source": "scientific_terms",
        "categories": enum_terms,
        "enum_values": [c.value for c in FileCategory],
    }


def build_combined_tree(
    official: dict,
    folder: dict,
    tags: dict,
    scientific: dict,
    summary_rows: list[dict],
) -> dict:
    return {
        "source": "combined",
        "official": {
            "main_tabs": official.get("main_tabs"),
            "domain_file_counts": official.get("domain_file_counts"),
        },
        "folder_roots": folder.get("root_folders"),
        "top_tags": dict(list(tags.get("tags", {}).items())[:40]),
        "scientific_categories": {
            k: v for k, v in scientific.get("categories", {}).items() if v.get("file_count", 0) > 0
        },
        "category_summary": summary_rows,
        "totals": {
            "files": folder.get("total_files", 0),
            "domains": len(official.get("domain_file_counts", {})),
            "sections": len(official.get("section_file_counts", {})),
        },
    }


def _load_summary_csv() -> list[dict]:
    if not CATEGORY_SUMMARY_PATH.is_file():
        return []
    rows: list[dict] = []
    with CATEGORY_SUMMARY_PATH.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            rows.append(dict(row))
    return rows


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    inventory = _load_inventory()
    category_tree = json.loads(CATEGORY_TREE_PATH.read_text(encoding="utf-8")) if CATEGORY_TREE_PATH.is_file() else {}
    summary_rows = _load_summary_csv()

    official = build_official_tree(inventory, category_tree)
    folder = build_folder_derived_tree(inventory)
    tags = build_tag_derived_tree(inventory)
    scientific = build_scientific_terms_tree(inventory)
    combined = build_combined_tree(official, folder, tags, scientific, summary_rows)

    outputs = {
        "category_tree_official.json": official,
        "category_tree_folder_derived.json": folder,
        "category_tree_tag_derived.json": tags,
        "category_tree_scientific_terms.json": scientific,
        "category_tree_combined.json": combined,
    }
    for name, payload in outputs.items():
        path = OUT_DIR / name
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote {path} ({len(json.dumps(payload))} bytes)")


if __name__ == "__main__":
    main()
