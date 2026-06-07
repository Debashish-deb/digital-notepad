#!/usr/bin/env python3
import os
import csv
from pathlib import Path
import psycopg

ROOT = Path(__file__).resolve().parents[2]
DB_CONN = os.getenv("POSTGRES_CONN", "postgresql://farkki:farkki_dev_password@localhost:5432/farkki_ai")

def main():
    print(f"Connecting to database at: {DB_CONN}")
    with psycopg.connect(DB_CONN) as conn:
        with conn.cursor() as cur:
            # 1. Ingest Projects
            projects = [
                ("SPACE", "Precision Oncology of Spatial Immune Escape Mechanisms in Ovarian Cancer", "TBD", "TBD", "HGSC", "Spatial immune escape in chemo-naive HGSC", "internal", "active"),
                ("EyeMT", "Immune escape multiomics integration", "TBD", "TBD", "HGSC", "tCyCIF + GeoMx + WES integration", "internal", "active"),
                ("KRAS", "KRAS Project Analysis", "TBD", "TBD", "HGSC", "Consolidated KRAS Spatial and thresholding analysis", "internal", "active")
            ]
            for code, name, lead, pi, focus, desc, sens, status in projects:
                cur.execute("""
                    INSERT INTO core.project (project_code, project_name, project_lead, principal_investigator, disease_focus, short_description, default_sensitivity, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::core.sensitivity_level, %s::core.record_status)
                    ON CONFLICT (project_code) DO UPDATE
                    SET project_name = EXCLUDED.project_name,
                        disease_focus = EXCLUDED.disease_focus,
                        short_description = EXCLUDED.short_description;
                """, (code, name, lead, pi, focus, desc, sens, status))
            print("Successfully registered projects.")

            # 2. Ingest Cohorts
            cohorts = [
                ("SPACE", "SPACE_COHORT", "SPACE Core Cohort"),
                ("EyeMT", "EyeMT_COHORT", "EyeMT Core Cohort"),
                ("KRAS", "KRAS_COHORT", "KRAS Core Cohort")
            ]
            for p_code, c_code, c_name in cohorts:
                cur.execute("SELECT project_id FROM core.project WHERE project_code = %s;", (p_code,))
                p_id = cur.fetchone()[0]
                cur.execute("""
                    INSERT INTO core.cohort (project_id, cohort_code, cohort_name, status)
                    VALUES (%s, %s, %s, 'active')
                    ON CONFLICT (project_id, cohort_code) DO NOTHING;
                """, (p_id, c_code, c_name))
            print("Successfully registered cohorts.")

            # 3. Ingest Synthetic Patients
            patients_csv = ROOT / "synthetic_data" / "synthetic_patients.csv"
            if patients_csv.exists():
                with open(patients_csv, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Map clinical info to metadata JSONB
                        metadata = {
                            "histology": row["histology"],
                            "hrd_status": row["hrd_status"],
                            "brca_status": row["brca_status"],
                            "platinum_response": row["platinum_response"],
                            "pfs_months": float(row["pfs_months"]),
                            "os_months": float(row["os_months"])
                        }
                        cur.execute("""
                            INSERT INTO core.patient (patient_code, disease_label, sensitivity_level, status, metadata)
                            VALUES (%s, %s, 'restricted', 'active', %s)
                            ON CONFLICT (patient_code) DO UPDATE
                            SET metadata = EXCLUDED.metadata;
                        """, (row["patient_code"], row["histology"], psycopg.types.json.Jsonb(metadata)))
                print("Successfully ingested synthetic patients.")

            # 4. Ingest Specimens & Samples
            samples_csv = ROOT / "synthetic_data" / "synthetic_samples.csv"
            if samples_csv.exists():
                with open(samples_csv, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        p_code = row["project_code"]
                        pat_code = row["patient_code"]
                        s_code = row["sample_code"]
                        site = row["site"]
                        modality = row["modality"]

                        # Get Project, Cohort and Patient IDs
                        cur.execute("SELECT project_id FROM core.project WHERE project_code = %s;", (p_code,))
                        p_id = cur.fetchone()[0]

                        cur.execute("SELECT cohort_id FROM core.cohort WHERE project_id = %s;", (p_id,))
                        c_id = cur.fetchone()[0]

                        cur.execute("SELECT patient_id FROM core.patient WHERE patient_code = %s;", (pat_code,))
                        pat_id = cur.fetchone()[0]

                        # Insert Specimen (assume 1-to-1 with sample for synthetic data)
                        spec_code = f"SPEC_{s_code}"
                        cur.execute("""
                            INSERT INTO core.specimen (patient_id, specimen_code, anatomical_site, sensitivity_level)
                            VALUES (%s, %s, %s, 'restricted')
                            ON CONFLICT (specimen_code) DO NOTHING;
                        """, (pat_id, spec_code, site))

                        cur.execute("SELECT specimen_id FROM core.specimen WHERE specimen_code = %s;", (spec_code,))
                        spec_id = cur.fetchone()[0]

                        # Insert Sample
                        metadata = {"modality": modality}
                        cur.execute("""
                            INSERT INTO core.sample (patient_id, specimen_id, project_id, cohort_id, sample_code, sample_name, sample_type, anatomical_site, qc_status, sensitivity_level, status, metadata)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pass', 'restricted', 'active', %s)
                            ON CONFLICT (sample_code) DO UPDATE
                            SET metadata = EXCLUDED.metadata, qc_status = 'pass';
                        """, (pat_id, spec_id, p_id, c_id, s_code, s_code, modality, site, psycopg.types.json.Jsonb(metadata)))
                print("Successfully ingested synthetic samples.")

        conn.commit()
    print("Database seeding completed.")

if __name__ == "__main__":
    main()
