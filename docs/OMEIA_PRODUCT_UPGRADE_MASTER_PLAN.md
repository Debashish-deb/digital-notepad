# OMEIA Product Upgrade Master Plan

Canonical step-by-step upgrade plan for the existing OMEIA digital notepad / research platform.

**Do not rewrite the app.** Improve incrementally with feature flags, tests, Linux validation, and rollback paths.

## Product goal

OMEIA is a lab-native digital notepad:

- Website / web app (now)
- Installable desktop shell (later)
- Linux-workstation-backed research platform

Success = researchers get **ranked directions, internal + external evidence, citations, confidence, risks, validation experiments** — not generic chat.

## Information flow

```
User / Lab Files / Projects / Publications / Images
  → Ingestion → Metadata → OCR (if needed) → Classification
  → Chunking → Embedding → Postgres + Qdrant
  → SearchService → EvidenceOrchestrator → ResearchStrategyEngine
  → AI Lab Assistant → Feedback / verified knowledge
```

**AI order:** Search first → Evidence second → Reasoning third → Answer last.

## Core rules

**Preserve:** existing APIs, frontend workflows, document library, project workspace, AI assistant, search UI, Linux deployment.

**Never:** embed Napari in React; fine-tune on private data early; expose filesystem paths to frontend; invent citations; answer research questions without retrieval.

**Always:** feature flags, tests, rollback plan, Linux validation, scientific references in docs.

## Phases (execution order)

| Phase | Focus | Status doc |
|-------|--------|------------|
| 1 | Indexing, search, storage consistency | [OMEIA_PHASE_STATUS.md](./OMEIA_PHASE_STATUS.md#phase-1) |
| 2 | Knowledge foundation pipeline | [OMEIA_PHASE_STATUS.md](./OMEIA_PHASE_STATUS.md#phase-2) |
| 3 | OCR and document completeness | [OMEIA_PHASE_STATUS.md](./OMEIA_PHASE_STATUS.md#phase-3) |
| 4 | AI three-layer strategy | [OMEIA_THREE_LAYER_AI_STRATEGY.md](./OMEIA_THREE_LAYER_AI_STRATEGY.md) |
| 5 | Research Strategy Assistant | [OMEIA_PHASE_STATUS.md](./OMEIA_PHASE_STATUS.md#phase-5) |
| 6 | Continuous learning (no early fine-tune) | [OMEIA_PHASE_STATUS.md](./OMEIA_PHASE_STATUS.md#phase-6) |
| 7 | Scientific image viewer (tile API) | [IMAGE_STREAMING_API.md](./IMAGE_STREAMING_API.md) |
| 8 | External scientific evidence | [OMEIA_PHASE_STATUS.md](./OMEIA_PHASE_STATUS.md#phase-8) |
| 9 | Security and permissions | [OMEIA_PHASE_STATUS.md](./OMEIA_PHASE_STATUS.md#phase-9) |
| 10 | Frontend UX polish | [OMEIA_PHASE_STATUS.md](./OMEIA_PHASE_STATUS.md#phase-10) |
| 11 | Linux deploy, sync, backup | [LINUX_PRIMARY_DEPLOYMENT.md](./LINUX_PRIMARY_DEPLOYMENT.md) |
| 12 | Evaluation framework | [OMEIA_PHASE_STATUS.md](./OMEIA_PHASE_STATUS.md#phase-12) |
| 13 | Scientific reference docs | [SCIENTIFIC_REFERENCE_REGISTRY.md](./SCIENTIFIC_REFERENCE_REGISTRY.md) |
| 14 | Missing features + adaptive compute | [ADAPTIVE_COMPUTE_PROFILES.md](./ADAPTIVE_COMPUTE_PROFILES.md) |

## After each phase

Return: files changed, tests, feature flags, Linux steps, validation commands, results, rollback, risks, next phase.

## Related plans

- [PLATFORM_REMEDIATION_MASTER_PLAN.md](./PLATFORM_REMEDIATION_MASTER_PLAN.md)
- [KNOWLEDGE_PLATFORM_REMEDIATION_PLAN.md](./KNOWLEDGE_PLATFORM_REMEDIATION_PLAN.md)
- [THREE_LAYER_IMPLEMENTATION_REPORT.md](./THREE_LAYER_IMPLEMENTATION_REPORT.md)
