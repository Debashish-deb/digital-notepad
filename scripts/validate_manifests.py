#!/usr/bin/env python3
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
required = {
    "project_registry_template.csv": ["project_code", "project_name", "status", "default_sensitivity"],
    "data_inventory_template.csv": ["project_code", "sample_code", "modality", "path_or_uri", "sensitivity_level"],
    "clinical_dictionary_template.csv": ["variable_name", "data_type", "definition", "curation_rule"],
    "assay_registry_template.csv": ["assay_run_code", "project_code", "sample_code", "assay_type"],
    "document_manifest_template.csv": ["document_code", "title", "source_type", "project_code", "sensitivity_level"],
    "pipeline_run_manifest_template.csv": ["pipeline_run_code", "pipeline_name", "project_code", "status"],
}
errors = []
for file_name, cols in required.items():
    path = SCHEMAS / file_name
    df = pd.read_csv(path)
    missing = [c for c in cols if c not in df.columns]
    if missing:
        errors.append(f"{file_name}: missing {missing}")
    else:
        print(f"OK: {file_name}")
if errors:
    raise SystemExit("\n".join(errors))
print("All manifest templates passed required-column validation.")
