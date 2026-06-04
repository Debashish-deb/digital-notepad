# 21 — Page / domain mapping rules

Maps storage paths → `platform.page_domain` / `page_section` (migration `112`).

## Prefix rules (proposal — confirm after DataCloud scan)

| Path prefix (under `/farkkila/LAB-ASSISTANT-PLATFORM`) | `page_domain_id` | Nav screen |
|--------------------------------------------------------|------------------|------------|
| `02_PROJECTS/` | `projects` | `projects` |
| `03_RESEARCH_HUB/` | `research_hub` | `lab_knowledge` |
| `04_COMPUTATIONAL/` | `computational` | `bioinformatics` |
| `05_CYCIF_IMAGING/` | `cycif` | `cycif_pipeline` |
| `06_WET_LAB/` | `wet_lab` | `lab_knowledge` |
| `07_ORDERS_PROCUREMENT/` | `orders` | `lab_knowledge` |
| `08_PERSONNEL/` | `overview` | `lab_knowledge` |
| `09_SOCIAL_MISC/` | `social` | `lab_knowledge` |
| `10_KNOWLEDGE_BASE/` | `knowledge_base` | `lab_knowledge` / `data_storage` |
| `11_NOTEBOOK_WIKI/` | `notebook` | `notebook` |
| `12_TASKS_DECISIONS/` | `tasks_decisions` | `tasks` / `decisions` |
| `00_ADMIN/`, `01_PLATFORM/` | `administration` | `administration` |
| `20_CLINICAL_RESTRICTED/` | `overview` | restricted lens |

## Confidence

- Exact prefix match → `assignment_confidence >= 0.85`
- Ambiguous (file in root or `99_ARCHIVE`) → `< 0.85` → review queue
- Conflict (two rules match) → `needs_user_decision = true`

## Worker algorithm (checklist item)

1. Normalize `logical_path`.
2. Longest-prefix match against table.
3. Write `page_domain_id` / `page_section_id` on vault row.
4. Never change DataCloud folders based on mapping alone.

See `docs/23_STORAGE_WORKER_CHECKLIST.md`.
