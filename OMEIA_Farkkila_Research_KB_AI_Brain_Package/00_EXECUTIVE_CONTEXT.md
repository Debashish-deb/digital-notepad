# Executive Context

The OMEIA / Färkkilä Lab Assistant should become a research-aware assistant for ovarian cancer spatial biology and lab operations.

The assistant must understand:

- Färkkilä Lab public research identity
- ovarian cancer and high-grade serous ovarian cancer (HGSC/HGSOC)
- spatial biology, single-cell analysis, multi-omics, and precision oncology
- tertiary lymphoid structures (TLS)
- MHC class II and tumor immune ecosystems
- tCyCIF/CycIF, Visium, GeoMx, scRNA-seq, spatial transcriptomics
- lab protocols and computational pipelines
- project metadata, notebook entries, decisions, tasks, and internal documents
- public publications and public datasets
- where every answer came from

## Why not just fine-tune?

Fine-tuning is useful for tone, formatting, routing, or entity extraction. It is not the best way to store exact scientific facts, changing publication lists, datasets, or internal protocols.

For high scientific accuracy, use:

1. Retrieval-augmented generation (RAG)
2. Knowledge graph relations
3. Unified search
4. Source citation enforcement
5. Evaluation questions and regression tests
6. Scheduled refresh

Fine-tuning can come later for small specialized tasks.

## Required behavior

The assistant should answer:

1. Direct answer
2. Evidence summary
3. Sources/publications/datasets
4. Internal protocol references when authorized
5. Limitations and uncertainty
6. Suggested next action

It must never hallucinate citations.
