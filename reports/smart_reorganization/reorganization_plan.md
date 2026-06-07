# OMEIA Smart Library Reorganization Plan

Generated: 2026-06-06T23:50:26Z

## Summary

- Files scanned: **327**
- Moves / quarantine proposed: **240**
- Exact duplicates found: **3**
- Quarantine candidates: **13**
- High-risk skipped: **0**
- Already in target layout: **54**
- Space recoverable after review: **47.12 MB**

## Target taxonomy

See `category_index.json` for UI labels, search tags, and folder paths.

## Safety policy

1. Default run is dry-run only — no files moved.
2. Quarantine before delete — duplicates go to `99_quarantine_review/`.
3. Source lab documents, configs, and code are never auto-deleted.
4. Storage Python modules are high-risk — require `--allow-code-moves` on apply.

## Top proposed actions

### Move (228)

- `app_skeleton/data/raw_asset_inventory_summary.json` → `app_skeleton/data/01_source_inventory/raw_asset_inventory_summary.json` — Canonical source inventory (requires --allow-data-moves + API path update)
- `app_skeleton/data/projects_catalog.json` → `app_skeleton/data/00_registry/projects_catalog.json` — Core registry catalog (requires --allow-data-moves + API path update)
- `app_skeleton/data/processor_state.json` → `app_skeleton/data/00_registry/processor_state.json` — Core registry catalog (requires --allow-data-moves + API path update)
- `app_skeleton/data/raw_asset_inventory.csv` → `app_skeleton/data/01_source_inventory/raw_asset_inventory.csv` — Canonical source inventory (requires --allow-data-moves + API path update)
- `app_skeleton/data/lab_personnel_roster.json` → `app_skeleton/data/00_registry/lab_personnel_roster.json` — Core registry catalog (requires --allow-data-moves + API path update)
- `app_skeleton/data/raw_asset_inventory.json` → `app_skeleton/data/01_source_inventory/raw_asset_inventory.json` — Canonical source inventory (requires --allow-data-moves + API path update) — canonical copy preserved
- `app_skeleton/data/processed_projects/iPDC_1.0.json` → `app_skeleton/data/02_processed_projects/research_projects/iPDC_1_0/iPDC_1.0.json` — Processed twin (iPDC_1.0)
- `app_skeleton/data/processed_projects/HaikalaCollab.json` → `app_skeleton/data/02_processed_projects/research_projects/HaikalaCollab/HaikalaCollab.json` — Processed twin (HaikalaCollab)
- `app_skeleton/data/processed_projects/Sequencing.json` → `app_skeleton/data/02_processed_projects/research_projects/Sequencing/Sequencing.json` — Processed twin (Sequencing)
- `app_skeleton/data/processed_projects/lab__wet_lab_files.chunks.jsonl` → `app_skeleton/data/02_processed_projects/lab_operations/wet_lab_files/lab__wet_lab_files.chunks.jsonl` — Processed twin (lab__wet_lab_files)
- `app_skeleton/data/processed_projects/SPACE.json` → `app_skeleton/data/02_processed_projects/research_projects/SPACE/SPACE.json` — Processed twin (SPACE)
- `app_skeleton/data/processed_projects/lab__orders_billing.chunks.jsonl` → `app_skeleton/data/02_processed_projects/lab_operations/overview_documents/lab__orders_billing.chunks.jsonl` — Processed twin (lab__orders_billing)
- `app_skeleton/data/processed_projects/DCIS.chunks.jsonl` → `app_skeleton/data/02_processed_projects/research_projects/DCIS/DCIS.chunks.jsonl` — Processed twin (DCIS)
- `app_skeleton/data/processed_projects/ovaHRDscar.json` → `app_skeleton/data/02_processed_projects/research_projects/ovaHRDscar/ovaHRDscar.json` — Processed twin (ovaHRDscar)
- `app_skeleton/data/processed_projects/TLS.json` → `app_skeleton/data/02_processed_projects/research_projects/TLS/TLS.json` — Processed twin (TLS)

### Quarantine (12)

- `app_skeleton/data/processed_projects/Ovca_VTE.chunks.jsonl` → `app_skeleton/data/02_processed_projects/research_projects/Ovca_VTE/Ovca_VTE.chunks.jsonl` — Empty or tiny placeholder file
- `app_skeleton/data/processed_projects/Proteomics.chunks.jsonl` → `app_skeleton/data/99_quarantine_review/unknown_category/Proteomics.chunks.jsonl` — Exact SHA-256 duplicate of app_skeleton/data/processed_projects/SaloCollab.chunks.jsonl
- `app_skeleton/data/processed_projects/Organoids.chunks.jsonl` → `app_skeleton/data/02_processed_projects/research_projects/Organoids/Organoids.chunks.jsonl` — Empty or tiny placeholder file
- `app_skeleton/data/processed_projects/LeppaCollab.chunks.jsonl` → `app_skeleton/data/02_processed_projects/research_projects/LeppaCollab/LeppaCollab.chunks.jsonl` — Empty or tiny placeholder file
- `app_skeleton/data/processed_projects/VanharantaCollab.chunks.jsonl` → `app_skeleton/data/02_processed_projects/research_projects/VanharantaCollab/VanharantaCollab.chunks.jsonl` — Empty or tiny placeholder file
- `app_skeleton/data/processed_projects/Mesenchymal_Ovca.chunks.jsonl` → `app_skeleton/data/02_processed_projects/research_projects/Mesenchymal_Ovca/Mesenchymal_Ovca.chunks.jsonl` — Empty or tiny placeholder file
- `app_skeleton/data/processed_projects/SideProjects.chunks.jsonl` → `app_skeleton/data/02_processed_projects/research_projects/SideProjects/SideProjects.chunks.jsonl` — Empty or tiny placeholder file
- `app_skeleton/data/processed_projects/Endometrial_HRD.chunks.jsonl` → `app_skeleton/data/02_processed_projects/research_projects/Endometrial_HRD/Endometrial_HRD.chunks.jsonl` — Empty or tiny placeholder file
- `app_skeleton/data/processed_projects/sciSet.chunks.jsonl` → `app_skeleton/data/02_processed_projects/research_projects/sciSet/sciSet.chunks.jsonl` — Empty or tiny placeholder file
- `reports/document_library_audit/metadata_v2/low_confidence_metadata_queue.csv` → `reports/99_quarantine_review/obsolete_reports/low_confidence_metadata_queue.csv` — Exact SHA-256 duplicate of reports/document_library_audit/metadata_v2/unknown_type_review_queue.csv
- `reports/document_library_audit/first_pass/document_inventory.csv` → `reports/99_quarantine_review/obsolete_reports/document_inventory.csv` — Superseded by metadata_v2 enriched inventory
- `reports/document_library_audit/first_pass/document_inventory.json` → `reports/99_quarantine_review/obsolete_reports/document_inventory.json` — Superseded by metadata_v2 enriched inventory
