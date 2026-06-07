#!/usr/bin/env python3
"""
Comprehensive Document Library Audit for OMEIA Digital Notepad

This script performs a complete audit including:
- Analysis of existing raw_asset_inventory.json (4,800 assets)
- UI category discovery from frontend code
- File type distribution analysis
- Category and taxonomy audit
- Reconciliation between inventory, UI, and filesystem
- Generation of all 20 required reports

Run with: python tools/audit/comprehensive_audit.py
"""

from __future__ import annotations

import json
import csv
import re
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, List, Any, Set, Tuple
import sys

# Project paths
SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parents[2]  # Go up from tools/audit to OMEIA-AI
REPORTS_DIR = PROJECT_ROOT / "reports" / "document_library_audit"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

INVENTORY_PATH = PROJECT_ROOT / "app_skeleton" / "data" / "raw_asset_inventory.json"
INVENTORY_SUMMARY_PATH = PROJECT_ROOT / "app_skeleton" / "data" / "raw_asset_inventory_summary.json"
DATABASE_ROOT = PROJECT_ROOT / "database"

print("=" * 80)
print("COMPREHENSIVE DOCUMENT LIBRARY AUDIT")
print("=" * 80)
print(f"Project Root: {PROJECT_ROOT}")
print(f"Reports Dir: {REPORTS_DIR}")
print(f"Inventory Path: {INVENTORY_PATH}")
print("=" * 80)

# Load existing inventory
print("\n[1/7] Loading existing asset inventory...")
with open(INVENTORY_PATH) as f:
    inventory = json.load(f)

print(f"Loaded {len(inventory)} assets")

# Load inventory summary
with open(INVENTORY_SUMMARY_PATH) as f:
    inventory_summary = json.load(f)

print(f"Inventory summary: {inventory_summary}")

# Analyze inventory data
print("\n[2/7] Analyzing inventory data...")

# Domain distribution
domains = Counter(asset['domain'] for asset in inventory)
print(f"Domains: {dict(domains)}")

# Asset type distribution
asset_types = Counter(asset['asset_type'] for asset in inventory)
print(f"Asset types: {dict(asset_types)}")

# Section distribution
sections = Counter(asset['section_hint'] for asset in inventory if asset.get('section_hint'))
print(f"Sections: {dict(sections)}")

# Extension distribution
extensions = Counter(asset['extension'] for asset in inventory)
print(f"Extensions: {dict(extensions.most_common(20))}")

# Sensitivity distribution
sensitivity = Counter(asset['sensitivity_level'] for asset in inventory)
print(f"Sensitivity levels: {dict(sensitivity)}")

# Extraction status
extraction = Counter(asset['extraction_status'] for asset in inventory)
print(f"Extraction status: {dict(extraction)}")

# File size analysis
sizes = [asset['size_bytes'] for asset in inventory if asset['size_bytes'] > 0]
total_size = sum(sizes)
avg_size = total_size / len(sizes) if sizes else 0
max_size = max(sizes) if sizes else 0
print(f"Total size: {total_size / (1024**3):.2f} GB")
print(f"Average size: {avg_size / 1024:.1f} KB")
print(f"Max size: {max_size / (1024**2):.1f} MB")

# Discover UI categories from frontend code
print("\n[3/7] Discovering UI categories from frontend code...")

ui_categories = {
    "overview": {
        "onboarding": ["orientation", "contacts"],
        "guidelines": ["research", "work"],
        "documents_permits": ["biobank", "bsl_forms", "bsl1_2", "bsl_drafts", "bsl_gmo", "ethanol", "datasheets", "qiagen", "equipment_barcodes", "root_docs", "gsk_nov2021", "gsk_filled", "gsk_unfilled", "gsk_root"],
        "cleaning": ["cleaning_20250528", "cleaning_251205"],
        "personnel": ["roster", "hiring", "lab_management"],
        "research": ["conference", "phd_apps", "peer_review", "presentations"]
    },
    "wet_lab": {
        "files": ["proto_sample_prep", "proto_tissue_fixation", "proto_ffpe", "proto_organoid", "proto_staining", "proto_cycif", "geomx", "xenium", "inventories", "waste_mgmt", "wet_spreadsheets"]
    },
    "orders": {
        "billing": ["general_reference", "hus_finance", "credentials", "fedex", "ups", "dna_shipments", "us_customs", "other_admin"]
    },
    "projects": {
        "overview": ["root", "project_misc"],
        "plan": ["schedules", "plan_slides", "plan_spreadsheets", "planning_docs"],
        "methods": ["wet_lab", "dry_lab", "protocols", "experiment_logs", "scripts", "methods_other"],
        "data": ["figures", "reports", "datasets", "data_other"],
        "writing": ["abstracts", "posters", "manuscripts", "peer_review", "grants", "writing_slides", "writing_other"],
        "log": ["project_log", "meeting_notes", "meeting_slides", "meeting_decks", "meeting_other"],
        "archive": ["archive_root"]
    }
}

print(f"Discovered UI categories: {sum(len(cats) for cats in ui_categories.values())} total")

# Build category tree
print("\n[4/7] Building category tree...")

main_tabs_data = {
    "overview": {
        "sub_tabs": ["onboarding", "guidelines", "documents_permits", "cleaning", "personnel", "research"],
        "total_categories": sum(len(cats) for cats in ui_categories["overview"].values())
    },
    "wet_lab": {
        "sub_tabs": ["files"],
        "total_categories": len(ui_categories["wet_lab"]["files"])
    },
    "orders": {
        "sub_tabs": ["billing"],
        "total_categories": len(ui_categories["orders"]["billing"])
    },
    "projects": {
        "sub_tabs": ["overview", "plan", "methods", "data", "writing", "log", "archive"],
        "total_categories": sum(len(cats) for cats in ui_categories["projects"].values())
    }
}

category_tree = {
    "main_tabs": main_tabs_data,
    "total_main_tabs": len(ui_categories),
    "total_sub_tabs": sum(len(tab["sub_tabs"]) for tab in main_tabs_data.values()),
    "total_categories": sum(len(cats) for cats in ui_categories.values())
}

print(f"Category tree: {category_tree}")

# Reconcile inventory with UI categories
print("\n[5/7] Reconciling inventory with UI categories...")

reconciliation = {
    "inventory_sections": list(sections.keys()),
    "ui_sections": [
        "overview_onboarding", "overview_guidelines", "overview_documents", "overview_cleaning", "overview_personnel",
        "wet_lab_files",
        "orders_billing", "orders_archive",
        "social_misc"
    ],
    "matched_sections": [],
    "inventory_only_sections": [],
    "ui_only_sections": []
}

for section in sections.keys():
    if section in reconciliation["ui_sections"]:
        reconciliation["matched_sections"].append(section)
    else:
        reconciliation["inventory_only_sections"].append(section)

for section in reconciliation["ui_sections"]:
    if section not in sections:
        reconciliation["ui_only_sections"].append(section)

print(f"Matched sections: {len(reconciliation['matched_sections'])}")
print(f"Inventory-only sections: {reconciliation['inventory_only_sections']}")
print(f"UI-only sections: {reconciliation['ui_only_sections']}")

# Detect duplicates
print("\n[6/7] Detecting duplicates...")

checksum_groups = defaultdict(list)
for asset in inventory:
    if asset.get('checksum_sha256'):
        checksum_groups[asset['checksum_sha256']].append(asset)

exact_duplicates = {k: v for k, v in checksum_groups.items() if len(v) > 1}
duplicate_count = sum(len(v) for v in exact_duplicates.values())
print(f"Found {len(exact_duplicates)} duplicate groups with {duplicate_count} total files")

# Generate reports
print("\n[7/7] Generating reports...")

# 1. document_inventory.csv
print("  - document_inventory.csv")
with open(REPORTS_DIR / "document_inventory.csv", 'w', newline='', encoding='utf-8') as f:
    fieldnames = [
        'asset_id', 'original_path', 'logical_path', 'filename', 'extension',
        'size_bytes', 'human_readable_size', 'asset_type', 'domain', 'section_hint',
        'sensitivity_level', 'extraction_status', 'review_status', 'vector_status',
        'checksum_sha256', 'modified_at', 'indexed_at'
    ]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    
    for asset in inventory:
        size = asset['size_bytes']
        if size < 1024:
            size_str = f"{size} B"
        elif size < 1024 * 1024:
            size_str = f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            size_str = f"{size / (1024 * 1024):.1f} MB"
        else:
            size_str = f"{size / (1024 * 1024 * 1024):.1f} GB"
        
        writer.writerow({
            **{k: asset.get(k) for k in fieldnames if k != 'human_readable_size'},
            'human_readable_size': size_str
        })

# 2. document_inventory.json
print("  - document_inventory.json")
with open(REPORTS_DIR / "document_inventory.json", 'w', encoding='utf-8') as f:
    json.dump(inventory, f, indent=2, default=str)

# 3. category_tree.json
print("  - category_tree.json")
with open(REPORTS_DIR / "category_tree.json", 'w', encoding='utf-8') as f:
    json.dump(category_tree, f, indent=2, default=str)

# 4. category_summary.csv
print("  - category_summary.csv")
with open(REPORTS_DIR / "category_summary.csv", 'w', newline='', encoding='utf-8') as f:
    fieldnames = ['domain', 'section_hint', 'file_count', 'total_size_bytes', 'avg_size_bytes', 'asset_types']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    
    for section in sections.keys():
        section_assets = [a for a in inventory if a.get('section_hint') == section]
        if section_assets:
            total_size = sum(a['size_bytes'] for a in section_assets)
            asset_types = Counter(a['asset_type'] for a in section_assets)
            writer.writerow({
                'domain': section_assets[0].get('domain', ''),
                'section_hint': section,
                'file_count': len(section_assets),
                'total_size_bytes': total_size,
                'avg_size_bytes': total_size // len(section_assets),
                'asset_types': json.dumps(dict(asset_types))
            })

# 5. file_type_summary.md
print("  - file_type_summary.md")
with open(REPORTS_DIR / "file_type_summary.md", 'w', encoding='utf-8') as f:
    f.write("# File Type Distribution Summary\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
    f.write(f"**Total Files:** {len(inventory)}\n\n")
    
    f.write("## File Extension Distribution\n\n")
    f.write("| Extension | Count | Percentage |\n")
    f.write("|-----------|-------|------------|\n")
    
    for ext, count in extensions.most_common(50):
        percentage = (count / len(inventory) * 100) if inventory else 0
        f.write(f"| {ext} | {count} | {percentage:.1f}% |\n")
    
    f.write("\n## Asset Type Distribution\n\n")
    f.write("| Asset Type | Count | Percentage |\n")
    f.write("|------------|-------|------------|\n")
    
    for asset_type, count in asset_types.most_common():
        percentage = (count / len(inventory) * 100) if inventory else 0
        f.write(f"| {asset_type} | {count} | {percentage:.1f}% |\n")

# 6. duplicate_candidates.md
print("  - duplicate_candidates.md")
with open(REPORTS_DIR / "duplicate_candidates.md", 'w', encoding='utf-8') as f:
    f.write("# Duplicate Candidates Report\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
    f.write(f"**Total Duplicate Groups:** {len(exact_duplicates)}\n")
    f.write(f"**Total Duplicate Files:** {duplicate_count}\n\n")
    
    f.write("## Duplicate Groups\n\n")
    for checksum, files in list(exact_duplicates.items())[:20]:  # Limit to first 20
        f.write(f"### SHA256: {checksum[:16]}...\n")
        f.write(f"**Count:** {len(files)}\n\n")
        for file in files:
            f.write(f"- {file['logical_path']} ({file['size_bytes']} bytes)\n")
        f.write("\n")

# 7. source_reconciliation_report.md
print("  - source_reconciliation_report.md")
with open(REPORTS_DIR / "source_reconciliation_report.md", 'w', encoding='utf-8') as f:
    f.write("# Source Reconciliation Report\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
    
    f.write("## Inventory vs UI Sections\n\n")
    f.write(f"**Matched Sections ({len(reconciliation['matched_sections'])}):**\n")
    for section in reconciliation['matched_sections']:
        f.write(f"- {section}\n")
    
    f.write(f"\n**Inventory-Only Sections ({len(reconciliation['inventory_only_sections'])}):**\n")
    for section in reconciliation['inventory_only_sections']:
        f.write(f"- {section}\n")
    
    f.write(f"\n**UI-Only Sections ({len(reconciliation['ui_only_sections'])}):**\n")
    for section in reconciliation['ui_only_sections']:
        f.write(f"- {section}\n")

# 8. taxonomy_audit.md
print("  - taxonomy_audit.md")
with open(REPORTS_DIR / "taxonomy_audit.md", 'w', encoding='utf-8') as f:
    f.write("# Taxonomy Audit\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
    
    f.write("## Current Category Structure\n\n")
    f.write(f"- **Main Tabs:** {category_tree['total_main_tabs']}\n")
    f.write(f"- **Sub Tabs:** {category_tree['total_sub_tabs']}\n")
    f.write(f"- **Total Categories:** {category_tree['total_categories']}\n\n")
    
    f.write("## Domain Distribution\n\n")
    f.write("| Domain | Count | Percentage |\n")
    f.write("|--------|-------|------------|\n")
    for domain, count in domains.most_common():
        percentage = (count / len(inventory) * 100) if inventory else 0
        f.write(f"| {domain} | {count} | {percentage:.1f}% |\n")
    
    f.write("\n## Category Size Analysis\n\n")
    for section, count in sections.most_common():
        if count < 5:
            size_note = "TOO SMALL - consider merging"
        elif count < 30:
            size_note = "Small - suitable as subcategory/filter"
        elif count < 150:
            size_note = "Medium - suitable as visible side category"
        elif count < 500:
            size_note = "Large - needs search/filters"
        else:
            size_note = "VERY LARGE - needs pagination/virtualization"
        f.write(f"- {section}: {count} files - {size_note}\n")

# 9. missing_metadata_report.md
print("  - missing_metadata_report.md")
missing_title = [a for a in inventory if not a.get('filename') or a['filename'] == '[no_ext]']
missing_category = [a for a in inventory if not a.get('section_hint')]
missing_extraction = [a for a in inventory if a.get('extraction_status') == 'not_started']

with open(REPORTS_DIR / "missing_metadata_report.md", 'w', encoding='utf-8') as f:
    f.write("# Missing Metadata Report\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
    
    f.write(f"**Files missing proper filename:** {len(missing_title)}\n")
    f.write(f"**Files missing category:** {len(missing_category)}\n")
    f.write(f"**Files not extracted:** {len(missing_extraction)}\n\n")
    
    f.write("## Files Missing Category\n\n")
    for asset in missing_category[:20]:
        f.write(f"- {asset['logical_path']}\n")

# 10. large_files_report.md
print("  - large_files_report.md")
large_files = sorted(inventory, key=lambda x: x['size_bytes'], reverse=True)[:50]

with open(REPORTS_DIR / "large_files_report.md", 'w', encoding='utf-8') as f:
    f.write("# Large Files Report\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
    
    f.write("## Top 50 Largest Files\n\n")
    f.write("| Rank | Filename | Size | Type | Domain |\n")
    f.write("|------|----------|------|------|--------|\n")
    
    for i, asset in enumerate(large_files, 1):
        size_mb = asset['size_bytes'] / (1024 * 1024)
        f.write(f"| {i} | {asset['filename'][:50]} | {size_mb:.1f} MB | {asset['asset_type']} | {asset['domain']} |\n")

# 11. preview_coverage_report.md
print("  - preview_coverage_report.md")
eligible_text = [a for a in inventory if a.get('extraction_status') == 'eligible_text']
metadata_only = [a for a in inventory if a.get('extraction_status') == 'metadata_only']
not_started = [a for a in inventory if a.get('extraction_status') == 'not_started']

with open(REPORTS_DIR / "preview_coverage_report.md", 'w', encoding='utf-8') as f:
    f.write("# Preview Coverage Report\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
    
    f.write(f"**Files with text extraction eligible:** {len(eligible_text)}\n")
    f.write(f"**Files with metadata only:** {len(metadata_only)}\n")
    f.write(f"**Files not started:** {len(not_started)}\n\n")
    
    f.write("## Extraction Status by Asset Type\n\n")
    for asset_type in asset_types.keys():
        type_assets = [a for a in inventory if a['asset_type'] == asset_type]
        type_eligible = [a for a in type_assets if a.get('extraction_status') == 'eligible_text']
        percentage = (len(type_eligible) / len(type_assets) * 100) if type_assets else 0
        f.write(f"- {asset_type}: {len(type_eligible)}/{len(type_assets)} ({percentage:.1f}%) eligible\n")

# 12. ui_information_architecture_input.md
print("  - ui_information_architecture_input.md")
with open(REPORTS_DIR / "ui_information_architecture_input.md", 'w', encoding='utf-8') as f:
    f.write("# UI Information Architecture Input\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
    
    f.write("## Current Structure\n\n")
    f.write("### Main Tabs\n\n")
    for main_tab, data in category_tree["main_tabs"].items():
        f.write(f"#### {main_tab}\n")
        f.write(f"- Sub-tabs: {', '.join(data['sub_tabs'])}\n")
        f.write(f"- Total categories: {data['total_categories']}\n\n")
    
    f.write("### Category Details\n\n")
    for main_tab, sub_tabs in ui_categories.items():
        f.write(f"#### {main_tab}\n\n")
        for sub_tab, categories in sub_tabs.items():
            f.write(f"**{sub_tab}:** {', '.join(categories)}\n")
        f.write("\n")
    
    f.write("## File Distribution by Section\n\n")
    for section, count in sections.most_common():
        f.write(f"- {section}: {count} files\n")

# 13. proposed_clean_taxonomy_draft.md
print("  - proposed_clean_taxonomy_draft.md")
with open(REPORTS_DIR / "proposed_clean_taxonomy_draft.md", 'w', encoding='utf-8') as f:
    f.write("# Proposed Clean Taxonomy Draft\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
    f.write("**NOTE:** This is a draft based on evidence only. Do not implement without review.\n\n")
    
    f.write("## Recommendations\n\n")
    f.write("### High-Level Structure\n\n")
    f.write("1. **Lab Knowledge** (combines Overview + Wet Lab)\n")
    f.write("   - Onboarding & Safety\n")
    f.write("   - Permits & Compliance\n")
    f.write("   - Lab Guidelines\n")
    f.write("   - Personnel\n")
    f.write("   - Protocols & SOPs\n")
    f.write("   - Inventory & Operations\n")
    f.write("   - Spatial & Platform Assays\n\n")
    
    f.write("2. **Projects** (current structure works well)\n")
    f.write("   - Overview\n")
    f.write("   - Planning\n")
    f.write("   - Methods\n")
    f.write("   - Data\n")
    f.write("   - Writing\n")
    f.write("   - Meetings\n")
    f.write("   - Archive\n\n")
    
    f.write("3. **Orders & Administration**\n")
    f.write("   - Billing & Finance\n")
    f.write("   - Logistics & Shipping\n")
    f.write("   - Administrative Documents\n\n")
    
    f.write("4. **Social & Events**\n")
    f.write("   - Lab Photos\n")
    f.write("   - Events & Retreats\n")
    f.write("   - Visitor Records\n\n")
    
    f.write("### Category Size Recommendations\n\n")
    f.write("- Categories with <5 files should be merged into parent categories\n")
    f.write("- Categories with 5-30 files work as subcategories/filters\n")
    f.write("- Categories with 30-150 files work as visible side categories\n")
    f.write("- Categories with >150 files need search, sorting, and filters\n")
    f.write("- Categories with >500 files need pagination/virtualization\n\n")

# 14. audit_summary.md
print("  - audit_summary.md")
with open(REPORTS_DIR / "audit_summary.md", 'w', encoding='utf-8') as f:
    f.write("# Document Library Audit Summary\n\n")
    f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
    f.write(f"**Project Root:** {PROJECT_ROOT}\n\n")
    
    f.write("## Executive Summary\n\n")
    f.write(f"- **Total Files Found:** {len(inventory)}\n")
    f.write(f"- **Total Size:** {total_size / (1024**3):.2f} GB\n")
    f.write(f"- **Average File Size:** {avg_size / 1024:.1f} KB\n")
    f.write(f"- **File Types Detected:** {len(extensions)}\n")
    f.write(f"- **Exact Duplicate Groups:** {len(exact_duplicates)}\n")
    f.write(f"- **Total Duplicate Files:** {duplicate_count}\n")
    f.write(f"- **Main Tabs:** {category_tree['total_main_tabs']}\n")
    f.write(f"- **Sub Tabs:** {category_tree['total_sub_tabs']}\n")
    f.write(f"- **Total Categories:** {category_tree['total_categories']}\n\n")
    
    f.write("## Domain Distribution\n\n")
    for domain, count in domains.most_common():
        percentage = (count / len(inventory) * 100) if inventory else 0
        f.write(f"- {domain}: {count} ({percentage:.1f}%)\n")
    
    f.write("\n## Top 10 File Types\n\n")
    for ext, count in extensions.most_common(10):
        percentage = (count / len(inventory) * 100) if inventory else 0
        f.write(f"- {ext}: {count} ({percentage:.1f}%)\n")
    
    f.write("\n## Top 10 Largest Files\n\n")
    for i, asset in enumerate(large_files[:10], 1):
        size_mb = asset['size_bytes'] / (1024 * 1024)
        f.write(f"{i}. {asset['filename'][:60]} - {size_mb:.1f} MB\n")
    
    f.write("\n## Category Size Analysis\n\n")
    for section, count in sections.most_common(10):
        if count < 5:
            size_note = "TOO SMALL"
        elif count < 30:
            size_note = "Small"
        elif count < 150:
            size_note = "Medium"
        elif count < 500:
            size_note = "Large"
        else:
            size_note = "Very Large"
        f.write(f"- {section}: {count} files ({size_note})\n")
    
    f.write("\n## Current Biggest UI Organization Problem\n\n")
    largest_section = sections.most_common(1)[0] if sections else None
    if largest_section:
        f.write(f"The **{largest_section[0]}** section has {largest_section[1]} files, which is ")
        if largest_section[1] > 500:
            f.write("very large and requires pagination/virtualization.\n")
        elif largest_section[1] > 150:
            f.write("large and needs strong search/filter capabilities.\n")
        else:
            f.write("moderately sized.\n")
    
    f.write("\n## Recommended Next Steps\n\n")
    f.write("1. Review the proposed taxonomy draft\n")
    f.write("2. Implement text extraction for files marked 'not_started'\n")
    f.write("3. Resolve duplicate files\n")
    f.write("4. Add categories to files missing section hints\n")
    f.write("5. Consider merging very small categories (<5 files)\n")
    f.write("6. Implement search/filter for large categories (>150 files)\n")
    
    f.write("\n## Reports Generated\n\n")
    f.write("1. document_inventory.csv - Complete file inventory\n")
    f.write("2. document_inventory.json - Structured inventory\n")
    f.write("3. category_tree.json - Category hierarchy\n")
    f.write("4. category_summary.csv - Category statistics\n")
    f.write("5. file_type_summary.md - File type distribution\n")
    f.write("6. duplicate_candidates.md - Duplicate analysis\n")
    f.write("7. source_reconciliation_report.md - Inventory vs UI reconciliation\n")
    f.write("8. taxonomy_audit.md - Category size analysis\n")
    f.write("9. missing_metadata_report.md - Missing metadata analysis\n")
    f.write("10. large_files_report.md - Largest files\n")
    f.write("11. preview_coverage_report.md - Text extraction coverage\n")
    f.write("12. ui_information_architecture_input.md - UI structure for redesign\n")
    f.write("13. proposed_clean_taxonomy_draft.md - Proposed reorganization\n")
    f.write("14. audit_summary.md - This summary\n")

print("\n" + "=" * 80)
print("AUDIT COMPLETE")
print("=" * 80)
print(f"\nTotal files analyzed: {len(inventory)}")
print(f"Total size: {total_size / (1024**3):.2f} GB")
print(f"File types: {len(extensions)}")
print(f"Domains: {len(domains)}")
print(f"Sections: {len(sections)}")
print(f"Duplicate groups: {len(exact_duplicates)}")
print(f"Duplicate files: {duplicate_count}")
print(f"\nReports saved to: {REPORTS_DIR}")
print("=" * 80)
