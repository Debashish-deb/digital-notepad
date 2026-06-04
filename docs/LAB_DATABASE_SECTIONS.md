# Lab database folder → section → navigation

Top-level folders under `database/` (sibling to `projects/`):

| Disk folder | `section_id` | Main nav · sub-tab |
|-------------|--------------|-------------------|
| `Overview/Onboarding and Outboarding` | `overview_onboarding` | Overview · Onboarding & Outboarding |
| `Overview/Guidelines` | `overview_guidelines` | Overview · Guidelines |
| `Overview/Documents - permits, forms, datasheets, handbooks etc.` | `overview_documents` | Overview · Documents & Permits |
| `Overview/PERSONNEL` | `overview_personnel` | Overview · Personnel |
| `Overview/LAB CLEANING` | `overview_cleaning` | Overview · Lab cleaning |
| `ORDERS & RELATED INFORMATION/Billing and ordering instructions` | `orders_billing` | Orders · Billing & ordering instructions |
| `ORDERS & RELATED INFORMATION/Archive` | `orders_archive` | Orders · Archive |
| `SOCIAL & MISCELLANEOUS` | `social_misc` | Social · Browse |
| `WET_LAB` | `wet_lab_files` | Wet-lab · Lab database files |

Skipped on bulk `database_processor --all` (processed via project pipeline):

| Disk path | `section_id` | Nav |
|-----------|--------------|-----|
| `projects/RESEARCH MATERIALS` | `overview_research_materials` | Overview · Research materials |

Config sources: `database_sections.py`, `databaseSections.js`, `navigation.js`.
