#!/usr/bin/env python3
"""Build a comprehensive projects catalog from Projects_Master_File.md and folder structure."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECTS_DIR = ROOT / "projects"
MASTER_FILE = PROJECTS_DIR / "Projects_Master_File.md"
OUTPUT_JSON = Path(__file__).resolve().parents[2] / "app_skeleton" / "data" / "projects_catalog.json"
OUTPUT_JS = (
    Path(__file__).resolve().parents[2]
    / "app_skeleton"
    / "ui"
    / "react_frontend"
    / "src"
    / "data"
    / "projectsCatalog.js"
)

PI = "Anniina Färkkilä, MD, PhD"

# Enriched metadata keyed by project index (from combined_projects_summary.md)
ENRICHMENT: dict[int, dict] = {
    4: {
        "modalities": ["tCycIF", "Xenium", "GeoMx", "RareCyte Proteopicking"],
        "repository": "https://github.com/farkkilab/cellcycle",
        "cohort_size": "28 patient samples (tCycIF discovery cohort)",
        "priority": "high",
        "category": "spatial_omics",
    },
    7: {
        "modalities": ["H&E WSI", "Bulk RNA-seq", "tCycIF", "GeoMx", "BCR profiling"],
        "cohort_size": "Multi-histology ovarian cancer cohort",
        "priority": "high",
        "category": "spatial_omics",
    },
    8: {
        "modalities": ["iPDC functional assays", "Flow cytometry"],
        "publication": "https://www.biorxiv.org/content/10.1101/2024.02.15.579904v1",
        "category": "platform_model",
    },
    9: {
        "modalities": ["tCycIF", "GeoMx", "WES"],
        "repository": "https://github.com/farkkilab/eyeMT/tree/aleksandra",
        "cohort_size": "Batch 1: n=16, Batch 2: n=14, Batch 3: n=30",
        "priority": "high",
        "category": "spatial_omics",
    },
    12: {
        "modalities": ["tCycIF", "WES", "RNA-seq", "H&E WSI"],
        "repository": "https://github.com/farkkilab/SPACE",
        "cohort_size": "Batch 1: n=80, Batch 2: n=39 chemo-naive HGSC",
        "priority": "high",
        "category": "flagship",
        "timeline": "August 2024 – Present",
        "project_lead": "Ziqi Kang",
        "collaborators": [
            "Ulla-Maija Haltia", "Matilda Salko", "Anastasia Lundgren", "Andreas Hainari",
            "Venla Kaislo", "Saundaryah Shah", "Foteni", "Ksenia", "Lina", "Matias Aiskovich",
            "Olavi Goussev", "Angela Szabo",
        ],
    },
    14: {
        "modalities": ["t-CycIF", "GeoMx"],
        "cohort_size": "67 biopsies from 60 patients (ISRCTN91953024)",
        "priority": "high",
        "category": "clinical_collaboration",
        "disease_focus": "Cervical CIN2",
    },
    15: {
        "modalities": ["GeoMx", "tCycIF", "Flow cytometry", "3D ex vivo model"],
        "cohort_size": "GeoMx Batch 2: n=13",
        "priority": "high",
        "category": "platform_model",
        "timeline": "2023 – Present",
    },
    17: {
        "modalities": ["t-CycIF TMA", "scRNA-seq", "Visium"],
        "cohort_size": "186 TNBC patients, 345 TMA cores (3.68M cells)",
        "category": "external_collaboration",
        "disease_focus": "Triple-Negative Breast Cancer",
    },
    21: {
        "modalities": ["tCycIF", "scRNA-seq", "WES", "WGS", "CosMx"],
        "repository": "https://github.com/farkkilab/KRAS",
        "cohort_size": "WES n=23, WGS n=100, scRNA-seq n=102, CosMx n=30",
        "priority": "high",
        "category": "spatial_omics",
    },
    22: {
        "modalities": ["t-CycIF TMA", "GeoMx", "scRNA-seq", "Immunopeptidomics"],
        "repository": "https://github.com/farkkilab/devNKI-scripts",
        "publication": "Cancer Discovery 2026 (doi:10.1158/2159-8290.CD-25-1492)",
        "cohort_size": "265 HGSC tumors across 10 TMAs",
        "priority": "high",
        "category": "flagship",
        "status": "completed",
    },
    29: {
        "modalities": ["Multiplexed imaging (t-CycIF)"],
        "repository": "https://github.com/farkkilab/tribus",
        "publication": "Bioinformatics 2025 (doi:10.1093/bioinformatics/btaf082)",
        "category": "computational_tool",
        "status": "completed",
        "project_lead": "Ziqi Kang",
        "collaborators": ["Angela Szabo", "Teodora Farago", "Fernando Perez", "Ada Junquera", "Saundarya Shah", "Inga-Maria Launonen", "Ella Anttila", "Julia Casado", "Kevin Elias", "Anni Virtanen", "Ulla-Maija Haltia", "Anniina Färkkilä"],
    },
    30: {
        "modalities": ["Multiplex CycIF", "VAE/VQ-VAE deep learning"],
        "cohort_size": "NKI TMA + 92 SPACE WSI",
        "category": "computational_tool",
        "project_lead": "Ziqi Kang",
        "collaborators": ["Matias Aiskovich", "Olavi Goussev", "Angela Szabo", "Fernando Perez"],
    },
    31: {
        "modalities": ["Clinical data", "WES/CNA", "SPACEstat spatial metrics"],
        "repository": "https://github.com/farkkilab/SPACE",
        "category": "computational_tool",
        "timeline": "2025 – Present",
        "project_lead": "Venla Kaislo",
        "collaborators": ["Ziqi Kang", "Matilda Salko", "Angela Szabo", "Andreas Hainari"],
    },
    35: {
        "modalities": ["t-CycIF whole-slide spatial statistics"],
        "repository": "https://github.com/Kkkzq/SPACEstat/tree/main",
        "category": "computational_tool",
        "priority": "high",
        "timeline": "March 2025 – Present",
        "project_lead": "Ziqi Kang",
        "collaborators": ["Elias Ruuska", "Aleksandra Shabanova"],
    },
    13: {
        "modalities": ["tCycIF", "Spatial proteomics"],
        "publication": "Cancer Cell 2024 — Chemotherapy induces myeloid-driven spatially confined T cell exhaustion",
        "category": "flagship",
        "status": "completed",
        "project_lead": "Sara Palomino",
        "collaborators": ["Wenqing Chen", "Inga-Maria Launonen"],
    },
    38: {
        "modalities": ["t-CycIF", "GeoMx", "Bulk RNA-seq", "Xenium"],
        "cohort_size": "ONCOSYS-OVA Batch 1: n=39 + 58 GeoMx samples",
        "priority": "high",
        "category": "spatial_omics",
        "timeline": "May 2025 – Present",
        "project_lead": "Andreas Hainari",
        "collaborators": ["Anni Lindfors", "Ziqi Kang", "Ada Junquera", "Nika Mikhailava", "Iga Niemiec", "Sara Palomino", "Saundarya Shah", "Anni Virtanen", "Ulla-Maija Haltia", "Anniina Färkkilä"],
    },
}

CODE_MAP = {
    1: "Myelonets",
    2: "HaikalaCollab",
    3: "Fanconi",
    4: "CellCycle",
    5: "EMT",
    6: "LeppaCollab",
    7: "TLS",
    8: "iPDC_1.0",
    9: "EyeMT",
    10: "SaloCollab",
    11: "VanharantaCollab",
    12: "SPACE",
    13: "sciSet",
    14: "CIN2",
    15: "iPDC_2.0",
    16: "Ovca_VTE",
    17: "Auria",
    18: "SC_Integration",
    19: "Organoids",
    20: "vTMA",
    21: "KRAS",
    22: "NKI",
    23: "ovaHRDscar",
    24: "HGSC_scRNAseq",
    25: "Sequencing",
    26: "Endometrial_HRD",
    27: "Mesenchymal_Ovca",
    28: "DCIS",
    29: "Tribus",
    30: "Pixel_AI",
    31: "SPACEjoint",
    32: "Proteomics",
    33: "FINPROVE",
    35: "SPACEstat",
    36: "Metabolomics",
    37: "TMA_Cohorts",
    38: "ADC",
    39: "ADC_Mechanisms",
    66: "SideProjects",
}

CATEGORY_LABELS = {
    "flagship": "Flagship Research Programs",
    "spatial_omics": "Spatial & Multi-Omics Studies",
    "computational_tool": "Computational Tools & Software",
    "platform_model": "Patient-Derived Models & Platforms",
    "clinical_collaboration": "Clinical Trial Collaborations",
    "external_collaboration": "External Lab Collaborations",
    "genomics": "Genomics & Sequencing",
    "infrastructure": "Infrastructure & Cohorts",
    "support": "Support & Validation",
}

DISEASE_DEFAULTS = {
    "CIN2": "Cervical CIN2",
    "Auria": "Triple-Negative Breast Cancer",
    "DCIS": "Breast DCIS",
    "HaikalaCollab": "Lung Cancer",
    "Fanconi": "Fanconi Anemia / SCC",
    "LeppaCollab": "Lymphoma / Lymph Node",
    "SaloCollab": "Head & Neck SCC",
    "Endometrial_HRD": "Endometrial Cancer",
}


def parse_responsible(text: str) -> tuple[str, list[str]]:
    if not text:
        return "", []
    raw = re.sub(r"\*{1,2}", "", text).strip(" :")
    collaborators: list[str] = []
    lead_part = raw
    paren = re.search(r"\(([^)]+)\)", raw)
    if paren:
        collaborators = [c.strip() for c in re.split(r",|;", paren.group(1)) if c.strip() and len(c.strip()) > 2]
        lead_part = raw[: paren.start()].strip()
    leads = []
    for segment in re.split(r",|\band\b", lead_part):
        segment = segment.strip()
        if len(segment) > 2 and segment[0].isupper():
            leads.append(segment)
    lead = leads[0] if leads else ""
    for extra in leads[1:]:
        if extra not in collaborators:
            collaborators.append(extra)
    return lead, collaborators


def infer_category(title: str, idx: int) -> str:
    t = title.lower()
    if idx in (29, 30, 31, 35):
        return "computational_tool"
    if idx in (8, 15, 19):
        return "platform_model"
    if "collab" in t or "virtanen" in t or "englund" in t or "sorger" in t or "vähärautio" in t or "varjosalo" in t:
        return "external_collaboration"
    if idx in (23, 24, 25, 26):
        return "genomics"
    if idx in (37, 20):
        return "infrastructure"
    if idx == 66:
        return "support"
    if idx in (12, 22):
        return "flagship"
    return "spatial_omics"


def infer_status(title: str, idx: int) -> str:
    t = title.lower()
    if "discontinued" in t or idx in (5, 11):
        return "discontinued"
    if "finished" in t or idx in (13, 29, 22):
        return "completed"
    return "active"


def find_folder(idx: int, code: str) -> str | None:
    if not PROJECTS_DIR.exists():
        return None
    code_clean = code.lower().replace("_", "")
    best = None
    for folder in PROJECTS_DIR.iterdir():
        if not folder.is_dir():
            continue
        name = folder.name
        if name.startswith(f"{idx}_") or name.startswith(f"{idx}."):
            return name
        name_clean = name.lower().replace("_", "").replace("-", "").replace(" ", "")
        if code_clean in name_clean or name_clean.startswith(code_clean[:4]):
            best = name
    return best


def folder_subdirs(folder_name: str | None) -> list[str]:
    if not folder_name:
        return []
    fp = PROJECTS_DIR / folder_name
    if not fp.exists():
        return []
    return sorted(d.name for d in fp.iterdir() if d.is_dir())


def parse_master() -> list[dict]:
    content = MASTER_FILE.read_text(encoding="utf-8")
    sections = re.split(r"\n###\s+", content)
    projects = []

    for section in sections[1:]:
        lines = section.strip().split("\n")
        if not lines:
            continue
        title_line = lines[0].strip().lstrip("#").strip()
        # Fix malformed titles like "### 13. sciSet - Finished"
        title_line = re.sub(r'^#+\s*', '', title_line).strip()
        m = re.match(r"^(\d+)\.\s*(.*)", title_line)
        if m:
            idx, title = int(m.group(1)), m.group(2).strip()
        else:
            idx, title = 99, title_line

        responsible_raw = ""
        desc_lines: list[str] = []
        in_desc = False

        for line in lines[1:]:
            ls = line.strip()
            rm = re.match(r"^\*\*Responsible:?\s*(.*?)\*\*?$", ls, re.I)
            if not rm:
                rm = re.match(r"^\*\*Responsible:?\s*(.*)$", ls, re.I)
            if rm:
                responsible_raw = rm.group(1).replace("**", "").strip()
                continue
            if ls.lower().startswith("description:"):
                in_desc = True
                rest = re.sub(r"^description:?\*?\*?", "", ls, flags=re.I).strip()
                if rest:
                    desc_lines.append(rest)
                continue
            dm = re.match(r"^\*\*Description:?\*\*?(.*)$", ls, re.I)
            if dm:
                in_desc = True
                if dm.group(1).strip():
                    desc_lines.append(dm.group(1).strip())
                continue
        if ls.startswith("###"):
            break
        if ls.startswith("[**") and "projects" in ls.lower():
            break
        if in_desc or (ls and not ls.startswith("**Responsible")):
            if ls not in ("Description:", "Description"):
                desc_lines.append(line.strip())

        description = re.sub(r"\s+", " ", " ".join(d for d in desc_lines if d)).strip()
        description = description.replace("\\'", "'")
        description = re.sub(r"\[\[.*?\]\]\(.*?\)", "", description).strip()

        code = CODE_MAP.get(idx, f"PROJ_{idx}")
        enrich = ENRICHMENT.get(idx, {})
        lead, collaborators = parse_responsible(responsible_raw)
        if enrich.get("project_lead"):
            lead = enrich["project_lead"]
        if enrich.get("collaborators"):
            collaborators = enrich["collaborators"]
        status = enrich.get("status") or infer_status(title, idx)
        category = enrich.get("category") or infer_category(title, idx)
        folder = find_folder(idx, code)
        subdirs = folder_subdirs(folder)

        disease = enrich.get("disease_focus") or DISEASE_DEFAULTS.get(code, "Ovarian / Gynecologic Cancer")

        project = {
            "project_index": idx,
            "project_code": code,
            "project_name": re.sub(r"\s*-\s*(Discontinued|Finished)\s*$", "", title, flags=re.I).strip(),
            "project_short_title": title[:60],
            "project_lead": lead,
            "principal_investigator": PI,
            "disease_focus": disease,
            "status": status,
            "category": category,
            "category_label": CATEGORY_LABELS.get(category, category),
            "priority": enrich.get("priority", "medium" if status == "active" else "low"),
            "project_type": "computational_tool" if category == "computational_tool" else "spatial_profiling",
            "research_question": description[:300] if description else title,
            "project_summary": description,
            "collaborators": collaborators,
            "modalities": enrich.get("modalities", []),
            "cohort_size": enrich.get("cohort_size", ""),
            "repository": enrich.get("repository", ""),
            "publication": enrich.get("publication", ""),
            "timeline": enrich.get("timeline", ""),
            "folder_path": folder or "",
            "folder_structure": subdirs,
            "ethics_approval_reference": "ISRCTN91953024" if idx == 14 else "",
            "current_blockers": "",
            "next_actions": "",
            "latest_update": "",
            "members": [{"name": lead, "role": "project_lead"}]
            + [{"name": c, "role": "collaborator"} for c in collaborators],
        }
        projects.append(project)

    projects.sort(key=lambda p: (p["project_index"], p["project_code"]))
    return projects


def main() -> None:
    catalog = parse_master()
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")

    js_content = (
        "// Auto-generated from projects/Projects_Master_File.md — do not edit manually\n"
        f"export const projectsCatalog = {json.dumps(catalog, indent=2, ensure_ascii=False)};\n\n"
        "export const PROJECT_CATEGORIES = "
        + json.dumps(CATEGORY_LABELS, indent=2, ensure_ascii=False)
        + ";\n\n"
        "export const getProjectsByCategory = () => {\n"
        "  const grouped = {};\n"
        "  for (const p of projectsCatalog) {\n"
        "    const cat = p.category;\n"
        "    if (!grouped[cat]) grouped[cat] = [];\n"
        "    grouped[cat].push(p);\n"
        "  }\n"
        "  return grouped;\n"
        "};\n\n"
        "export const getProjectByCode = (code) => projectsCatalog.find(p => p.project_code === code);\n\n"
        "export default projectsCatalog;\n"
    )
    OUTPUT_JS.write_text(js_content, encoding="utf-8")
    print(f"Wrote {len(catalog)} projects to {OUTPUT_JSON}")
    print(f"Wrote JS module to {OUTPUT_JS}")


if __name__ == "__main__":
    main()
