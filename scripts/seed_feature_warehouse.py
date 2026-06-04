#!/usr/bin/env python3
"""Seed Phase 3 feature warehouse (Postgres + Qdrant spatial_feature_profiles)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app_skeleton.api.feature_warehouse import seed_feature_warehouse
from app_skeleton.api.clinical_tools import _load_patients
import os
import csv
import psycopg

DB_CONN = os.getenv("POSTGRES_CONN", "postgresql://farkki:farkki_dev_password@localhost:5432/farkki_ai")


def seed_clinical_dictionary() -> int:
    tpl = ROOT / "schemas" / "clinical_dictionary_template.csv"
    if not tpl.exists():
        return 0
    count = 0
    with psycopg.connect(DB_CONN) as conn:
        with conn.cursor() as cur:
            with tpl.open(encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    cur.execute(
                        """
                        INSERT INTO clinical.variable_dictionary
                          (variable_name, display_name, data_type, unit, definition, curation_rule, sensitivity_level)
                        VALUES (%s, %s, %s, %s, %s, %s, 'restricted')
                        ON CONFLICT (variable_name) DO NOTHING;
                        """,
                        (row["variable_name"], row["display_name"], row["data_type"], row.get("unit") or None, row.get("definition"), row.get("curation_rule")),
                    )
                    count += 1
            # Seed patient_clinical_summary from synthetic patients
            for p in _load_patients():
                cur.execute("SELECT patient_id FROM core.patient WHERE patient_code = %s;", (p["patient_code"],))
                row = cur.fetchone()
                if not row:
                    continue
                cur.execute(
                    """
                    INSERT INTO clinical.patient_clinical_summary
                      (patient_id, histology, hrd_status, brca_status, platinum_response, pfs_months, os_months, progression_event, qc_status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'passed')
                    ON CONFLICT (patient_id) DO UPDATE SET pfs_months = EXCLUDED.pfs_months, os_months = EXCLUDED.os_months;
                    """,
                    (row[0], p["histology"], p["hrd_status"], p["brca_status"], p["platinum_response"], p["pfs_months"], p["os_months"], bool(p["pfs_event"])),
                )
        conn.commit()
    return count


def apply_analysis_run_schema() -> None:
    sql = ROOT / "sql" / "060_analysis_run_schema.sql"
    if sql.exists():
        with psycopg.connect(DB_CONN) as conn:
            conn.execute(sql.read_text(encoding="utf-8"))
            conn.commit()


def main() -> None:
    print("Applying analysis_run schema…")
    try:
        apply_analysis_run_schema()
        print("  ✓ platform.analysis_run")
    except Exception as exc:
        print(f"  ⚠ schema: {exc}")

    print("Seeding clinical dictionary…")
    n = seed_clinical_dictionary()
    print(f"  ✓ {n} clinical variables")

    print("Seeding feature warehouse…")
    stats = seed_feature_warehouse()
    print(f"  features={stats['features']} values={stats['values']} vectors={stats['vectors']}")
    if stats["errors"]:
        for e in stats["errors"]:
            print(f"  ⚠ {e}")


if __name__ == "__main__":
    main()
