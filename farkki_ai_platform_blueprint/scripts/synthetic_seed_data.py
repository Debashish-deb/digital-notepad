#!/usr/bin/env python3
from pathlib import Path
import csv
import random

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "synthetic_data"
OUT.mkdir(exist_ok=True)
random.seed(42)

with (OUT / "synthetic_patients.csv").open("w", newline="") as f:
    wr = csv.writer(f)
    wr.writerow(["patient_code", "histology", "hrd_status", "brca_status", "platinum_response", "pfs_months", "os_months"])
    for i in range(1, 21):
        wr.writerow([
            f"SYNTH_PATIENT_{i:03d}", "HGSC",
            random.choice(["HRD", "HRP", "unknown"]),
            random.choice(["mutated", "wildtype", "unknown"]),
            random.choice(["sensitive", "resistant", "unknown"]),
            round(random.uniform(4, 48), 1),
            round(random.uniform(12, 90), 1),
        ])

with (OUT / "synthetic_samples.csv").open("w", newline="") as f:
    wr = csv.writer(f)
    wr.writerow(["sample_code", "patient_code", "project_code", "site", "modality"])
    for i in range(1, 41):
        wr.writerow([
            f"SYNTH_SAMPLE_{i:03d}",
            f"SYNTH_PATIENT_{((i - 1) % 20) + 1:03d}",
            random.choice(["SPACE", "EyeMT", "KRAS"]),
            random.choice(["pOme", "iOme", "pOva", "IDS", "PDS"]),
            random.choice(["tcycif", "geomx", "wes"]),
        ])
print(f"Wrote synthetic data to {OUT}")
