# OMEIA Document Library Guide

This repository organizes scientific, lab, and platform knowledge into a **task-first** layout.

## Where to look

| You need… | Go to… | Label |
|-----------|--------|-------|
| Core catalogs, personnel roster, processor state | `app_skeleton/data/00_registry/` | Project Registry |
| Raw file inventory and source asset maps | `app_skeleton/data/01_source_inventory/` | Source Inventory |
| Project JSON twins, chunk indexes, search-ready exports | `app_skeleton/data/02_processed_projects/` | Processed Knowledge Base |
| Ingestion reports, failed imports, processing history | `app_skeleton/data/03_ingestion_audit/` | Import & Processing History |
| Application and operational logs | `app_skeleton/data/04_runtime_logs/` | Runtime Logs |
| WebDAV, SMB, R2, and cloud/local storage adapters | `app_skeleton/storage/01_providers/` | Storage Connectors |
| Code that pulls files into the system | `app_skeleton/storage/02_ingestion_runtime/` | Ingestion Engine |
| Environment helpers and runtime path configuration | `app_skeleton/storage/03_environment/` | Storage Environment |
| Equipment manuals, maintenance, gas ordering | `docs/01_lab_operations/` | Lab Operations |
| Orders, quotes, offers, yearly spreadsheets, lab coats | `docs/02_procurement_and_orders/` | Orders & Procurement |
| FedEx, billing, supplier contacts, account instructions | `docs/03_shipping_billing_and_accounts/` | Shipping, Billing & Accounts |
| Protocols, papers, project notes, scientific references | `docs/04_research_reference/` | Research Reference Library |
| Latest human-readable summaries | `reports/00_current_summary/` | Current Reports |
| Latest JSON/CSV outputs used by the app | `reports/01_current_machine_readable/` | Current Report Data |
| Superseded first-pass, second-pass, and corrected audits | `reports/02_historical_audits/` | Historical Audit Trail |
| Repository structure analyzer outputs | `reports/03_structure_analysis/` | Structure Analysis |
| Duplicates, obsolete generated files, and risky candidates | `99_quarantine_review/` | Review Before Deleting |

## Safety

- Generated reports and duplicates go to `99_quarantine_review/` — review before deleting.
- Run `tools/audit/smart_library_reorganizer.py --dry-run` before any `--apply`.
- Roll back with `--rollback reports/smart_reorganization/rollback_manifest.json`.

## App integration

The UI reads `reports/smart_reorganization/category_index.json` for human-friendly category labels.
