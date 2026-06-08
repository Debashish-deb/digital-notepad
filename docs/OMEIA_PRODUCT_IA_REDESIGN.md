# OMEIA Product IA Redesign

Inspired by [SciNote](https://www.scinote.net/product/), [Benchling](https://www.benchling.com/platform), and [Labguru](https://www.labguru.com/) — adapted for the Färkkilä spatial oncology lab (not molecular-biology LIMS).

## Design principles borrowed

| Vendor | Pattern adopted in OMEIA |
|--------|--------------------------|
| **Labguru** | Three product pillars → sidebar **groups** (Work · Lab · Knowledge · Infra · Admin) |
| **SciNote** | Dashboard + tasks + protocol repository → **Workbench** + Wet Lab protocols-first |
| **Benchling** | Global searchable library + linked entities → **Document Library** hub + future Registry |
| **All** | Project-centric research → **Projects** (portfolio, notebook, decisions) stays central |

## Sidebar structure (implemented)

### Work
- **Workbench** — lab dashboard (default landing)
- **Projects** — portfolio, living notebook, decisions, feature warehouse

### Laboratory
- **Wet Lab** — protocols → inventory → tasks → files (operations before browsing)
- **CyCIF** — imaging pipeline + project resources (unchanged)

### Knowledge
- **Document Library** — unified browse/search (all files, lab ops, CyCIF, admin docs, orders)
- **AI Lab Assistant** — copilot, hybrid search, research KB

### Infrastructure
- **Data & Storage** — FAIR landscape, drives, Allas, transfer tools
- **Compute** — LUMI, cPouta, utilities, lab tools
- **Orders & Procurement** — billing, archive, registers

### Administration
- **Lab Administration** — onboarding, guidelines, permits (formerly “Get Started”)
- **Meetings** — booking calendar

## Legacy redirects

| Old route | New route |
|-----------|-----------|
| `data_storage:all_files` | `library:all_files` |
| `data_storage:documents` | `library:all_files` |
| `overview:dashboard` | `workbench:home` |
| `dashboard` (storage key) | `workbench:home` |

## Next phases (not yet built)

1. **Registry** — `core.sample` + structured reagent lots (Benchling Inventory / Labguru sample element)
2. **Experiment runner** — protocol steps with checkboxes + activity log (SciNote tasks)
3. **Smart @-links** — notebook ↔ inventory ↔ library assets
4. **Ops dashboard widgets** on Workbench — overdue tasks, low-stock alerts

## Validation

```bash
node --test web/src/config/navigation.test.mjs
cd web && npm run build
```
