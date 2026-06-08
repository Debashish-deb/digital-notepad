from __future__ import annotations

from typing import Any

SEED_DATASETS = [
    {
        "accession": "GSE211956",
        "source_database": "GEO",
        "title": "HGSOC Visium spatial RNA-seq and 10x scRNA-seq experiments",
        "disease": "High-grade serous ovarian carcinoma",
        "modality": ["spatial transcriptomics", "single-cell RNA-seq"],
        "technology": ["10x Genomics Visium", "10x Genomics Chromium"],
        "url": "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE211956",
        "usable_for": ["spatial transcriptomics evaluation", "HGSOC TME analysis", "dataset registry seed"],
        "limitations": ["Check sample count, access files, and preprocessing status from GEO before analysis."],
    },
    {
        "accession": "phs002262",
        "source_database": "EGA",
        "title": "HGSOC single-cell RNA-seq study metadata",
        "disease": "High-grade serous ovarian carcinoma",
        "modality": ["single-cell RNA-seq"],
        "technology": ["10x Genomics"],
        "url": "https://ega-archive.org/studies/phs002262",
        "usable_for": ["HGSOC cell type composition", "single-cell reference mapping"],
        "limitations": ["Access may require controlled data approval."],
    },
    {
        "accession": "TCGA-OV",
        "source_database": "GDC/TCGA",
        "title": "TCGA Ovarian Serous Cystadenocarcinoma",
        "disease": "Ovarian serous carcinoma",
        "modality": ["genomics", "transcriptomics", "clinical"],
        "url": "https://portal.gdc.cancer.gov/projects/TCGA-OV",
        "usable_for": ["background cohort", "omics validation", "clinical-genomic context"],
        "limitations": ["Not a spatial dataset."],
    },
]


def seed_dataset_registry() -> list[dict[str, Any]]:
    return SEED_DATASETS.copy()


def normalize_dataset_record(record: dict[str, Any]) -> dict[str, Any]:
    out = dict(record)
    for field in ("modality", "technology", "usable_for", "limitations"):
        value = out.get(field)
        if value is None:
            out[field] = []
        elif isinstance(value, str):
            out[field] = [value]
    return out
