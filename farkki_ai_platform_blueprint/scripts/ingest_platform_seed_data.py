#!/usr/bin/env python3
import os
import psycopg
from pathlib import Path
from datetime import datetime, date

ROOT = Path(__file__).resolve().parents[1]
DB_CONN = os.getenv("POSTGRES_CONN", "postgresql://farkki:farkki_dev_password@localhost:5432/farkki_ai")

def main():
    print(f"Seeding CS-ROP schemas at: {DB_CONN}")
    with psycopg.connect(DB_CONN) as conn:
        with conn.cursor() as cur:
            # 0. Clean platform tables to prevent duplicates
            cur.execute("""
                TRUNCATE platform.wiki_revision, platform.research_wiki, platform.decision_registry, 
                         platform.task, platform.pipeline_run, platform.dataset_catalog, 
                         platform.folder_catalog, platform.notebook_revision, platform.notebook_entry, 
                         platform.project_member, platform.project_extension CASCADE;
            """)

            # 1. Fetch project IDs
            cur.execute("SELECT project_id, project_code FROM core.project;")
            projects = {code: pid for pid, code in cur.fetchall()}
            
            # Update core.project to use Anniina Färkkilä, MD, PhD as PI and Debashish Deb, MSc as Lead
            cur.execute("""
                UPDATE core.project 
                SET principal_investigator = 'Anniina Färkkilä, MD, PhD', 
                    project_lead = 'Debashish Deb, MSc' 
                WHERE project_code IN ('SPACE', 'EyeMT', 'KRAS');
            """)

            # Update debdeba in platform.researcher
            cur.execute("""
                UPDATE platform.researcher 
                SET full_name = 'Debashish Deb, MSc', role = 'IT Specialist' 
                WHERE username = 'debdeba';
            """)

            # Fetch researcher ID (username = 'debdeba')
            cur.execute("SELECT researcher_id FROM platform.researcher WHERE username = 'debdeba';")
            debdeba_id = cur.fetchone()[0]

            # Register Anniina Färkkilä, MD, PhD (PI)
            cur.execute("""
                INSERT INTO platform.researcher (username, full_name, role, allowed_project_codes)
                VALUES ('afarkkila', 'Anniina Färkkilä, MD, PhD', 'PI', '{"SPACE", "EyeMT", "KRAS"}')
                ON CONFLICT (username) DO UPDATE SET full_name = EXCLUDED.full_name, role = EXCLUDED.role
                RETURNING researcher_id;
            """)
            pi_id = cur.fetchone()[0]

            # Register Anastasia Lundgren, MSc
            cur.execute("""
                INSERT INTO platform.researcher (username, full_name, role, allowed_project_codes)
                VALUES ('alundgren', 'Anastasia Lundgren, MSc', 'Lab Manager', '{"SPACE", "EyeMT", "KRAS"}')
                ON CONFLICT (username) DO UPDATE SET full_name = EXCLUDED.full_name, role = EXCLUDED.role
                RETURNING researcher_id;
            """)
            alundgren_id = cur.fetchone()[0]

            # Register Joonas Jukonen, PhD
            cur.execute("""
                INSERT INTO platform.researcher (username, full_name, role, allowed_project_codes)
                VALUES ('jjukonen', 'Joonas Jukonen, PhD', 'Research Coordinator', '{"SPACE", "EyeMT", "KRAS"}')
                ON CONFLICT (username) DO UPDATE SET full_name = EXCLUDED.full_name, role = EXCLUDED.role
                RETURNING researcher_id;
            """)
            jjukonen_id = cur.fetchone()[0]

            # Register Maija Vääriskoski, MSc Midwife
            cur.execute("""
                INSERT INTO platform.researcher (username, full_name, role, allowed_project_codes)
                VALUES ('mvaariskoski', 'Maija Vääriskoski, MSc Midwife', 'Clinical Research Coordinator', '{"SPACE", "EyeMT", "KRAS"}')
                ON CONFLICT (username) DO UPDATE SET full_name = EXCLUDED.full_name, role = EXCLUDED.role
                RETURNING researcher_id;
            """)
            mvaariskoski_id = cur.fetchone()[0]

            # Register Saundarya (Saun) Shah, MSc
            cur.execute("""
                INSERT INTO platform.researcher (username, full_name, role, allowed_project_codes)
                VALUES ('sshah', 'Saundarya (Saun) Shah, MSc', 'Doctoral Researcher', '{"SPACE", "EyeMT", "KRAS"}')
                ON CONFLICT (username) DO UPDATE SET full_name = EXCLUDED.full_name, role = EXCLUDED.role
                RETURNING researcher_id;
            """)
            sshah_id = cur.fetchone()[0]

            extensions = [
                ("SPACE", "SPACE - Spatial Escapes", "How do spatial immune escape configurations shape treatment responses in chemo-naive HGSC?", "spatial_profiling", "critical", ["Helsinki University Hospital", "Karolinska Institute"], "ETHICS-2025-X8", "Awaiting sample shipment for cohort 2", "Run Ashlar stitching on batch 3 tiles", "Comprehensive multiplex imaging and clinical metadata integration for ovarian cancer.", "Added 20 new high-resolution OME-TIFF slides."),
                ("EyeMT", "EyeMT - Multiomics", "Can we integrate single-cell transcriptomics (GeoMx) with high-plex spatial proteomics (tCyCIF)?", "clinical_trial", "high", ["Tampere University", "Stanford Medicine"], "ETHICS-2026-Y2", "Sequencing alignment bottlenecks", "Align GeoMx ROI coordinates with tCyCIF images", "Multi-omic spatial validation of ovarian tissue specimen cohorts.", "GeoMx sequencing run completed and fastq files processed."),
                ("KRAS", "KRAS - Gating", "What are the exact spatial marker threshold and cell cluster parameters across mutation models?", "spatial_profiling", "medium", [], "ETHICS-2024-Z9", "None", "Run Cylinter gating notebooks", "Quantification and validation of KRAS cell clusters in mouse tissue cohorts.", "Completed first-round cell-segmentation mask verification.")
            ]
            for code, short, question, ptype, priority, collab, ethics, blockers, next_act, summary, update in extensions:
                pid = projects[code]
                cur.execute("""
                    INSERT INTO platform.project_extension (project_id, project_short_title, research_question, project_type, priority, collaborators, ethics_approval_reference, current_blockers, next_actions, project_summary, latest_update)
                    VALUES (%s, %s, %s, %s, %s, %s::text[], %s, %s, %s, %s, %s)
                    ON CONFLICT (project_id) DO UPDATE
                    SET project_short_title = EXCLUDED.project_short_title,
                        research_question = EXCLUDED.research_question,
                        current_blockers = EXCLUDED.current_blockers,
                        next_actions = EXCLUDED.next_actions,
                        latest_update = EXCLUDED.latest_update;
                """, (pid, short, question, ptype, priority, collab, ethics, blockers, next_act, summary, update))
            print("Successfully seeded project extensions.")

            # 3. Seed project_member
            members = [
                ("SPACE", pi_id, "PI", "admin", "Principal Investigator oversight"),
                ("SPACE", debdeba_id, "project_lead", "read_write", "Lead Bioinformatician"),
                ("SPACE", alundgren_id, "Lab Manager", "read_write", "Sample collection coordinator"),
                ("SPACE", jjukonen_id, "Research Coordinator", "read_only", "Mentoring and financials"),
                ("SPACE", mvaariskoski_id, "Clinical Coordinator", "read_write", "Clinical data registry lead"),
                ("SPACE", sshah_id, "Doctoral Researcher", "read_write", "Spatial analysis researcher"),
                ("EyeMT", pi_id, "PI", "admin", "Co-Investigator"),
                ("EyeMT", debdeba_id, "bioinformatician", "read_write", "Primary integrator"),
                ("EyeMT", sshah_id, "Doctoral Researcher", "read_write", "Transcripts realigner"),
                ("KRAS", debdeba_id, "image_analyst", "read_write", "Lead analyst")
            ]
            for code, rid, role, access, notes in members:
                pid = projects[code]
                cur.execute("""
                    INSERT INTO platform.project_member (project_id, researcher_id, role, project_access_level, notes)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (project_id, researcher_id) DO UPDATE
                    SET role = EXCLUDED.role, project_access_level = EXCLUDED.project_access_level;
                """, (pid, rid, role, access, notes))
            print("Successfully seeded project members.")

            # 4. Fetch some sample IDs for notebook and files linkage
            cur.execute("SELECT sample_id, sample_code, project_id FROM core.sample LIMIT 10;")
            sample_rows = cur.fetchall()
            samples = {row[1]: (row[0], row[2]) for row in sample_rows}

            notes = [
                ("SPACE", "SYNTH_SAMPLE_001", "Batch 1 Ashlar Stitching Run", "Ashlar stitching/registration", "Completed raw TIFF registration for Batch 1. Encountered minor cycle overlap error on channel 4, solved by resetting tile overlap parameters to 15%. Stitched pyramid OME-TIFF shows crisp cell outlines.", "Successful registration", "Channel 4 cycle shift", "Stitch next batches with 15% overlap config", ["ashlar", "stitching", "batch_1"], "experiment_note"),
                ("SPACE", None, "Weekly Sync Meeting", None, "Discussed progress on SPACE cohort. Patient count is currently 20. Stitched slides are ready for segmentation using Mesmer. Dr. Anniina Färkkilä suggested comparing Mesmer and Cellpose models next week.", "Mesmer segmentation is prioritized", "None", "Run Mesmer on stitched batch 1 images", ["meeting", "space_sync"], "meeting_note"),
                ("EyeMT", "SYNTH_SAMPLE_002", "GeoMx Coordinate Realignment", "spatial feature extraction", "Attempted to align single-cell transcripts with high-plex tCyCIF slides. ROI coordinates resolved using custom python coordinate translation script. R-squared alignment value is 0.985.", "Realignment completed", "Slight rotation offset", "Apply alignment matrix to all remaining ROIs", ["geomx", "alignment", "multiomics"], "analysis_note"),
                ("KRAS", None, "Troubleshooting Cylinter Java Dependency", "Cylinter QC", "Cylinter failed with Java conflict error on WSL2 Linux workstation. Fixed by installing OpenJDK from conda-forge explicitly inside the active environment.", "OpenJDK path resolved", "Java environment crash", "Always pin openjdk=11 in the conda package lists", ["cylinter", "troubleshooting", "conda"], "troubleshooting_note")
            ]
            for p_code, s_code, title, stage, content, conclusions, issues, next_steps, tags, entry_type in notes:
                pid = projects[p_code]
                sid = samples[s_code][0] if s_code else None
                cur.execute("""
                    INSERT INTO platform.notebook_entry (project_id, sample_id, title, pipeline_stage, author_id, content, conclusions, issues_found, next_steps, tags, entry_type)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::text[], %s)
                    RETURNING entry_id;
                """, (pid, sid, title, stage, debdeba_id, content, conclusions, issues, next_steps, tags, entry_type))
            print("Successfully seeded notebook entries.")

            # 6. Seed folder_catalog
            folders = [
                ("SPACE", "SYNTH_SAMPLE_001", "raw_images", "/home/debdeba/Documents/scripts/projects/SPACE/raw", "raw images", "Ashlar stitching", 240, 48582910020),
                ("SPACE", "SYNTH_SAMPLE_001", "stitched_images", "/home/debdeba/Documents/scripts/projects/SPACE/stitched", "stitched images", "Mesmer segmentation", 20, 19283749000),
                ("SPACE", "SYNTH_SAMPLE_001", "segmentation_masks", "/home/debdeba/Documents/scripts/projects/SPACE/masks", "segmentation masks", "quantification", 40, 2910283000),
                ("EyeMT", "SYNTH_SAMPLE_002", "clinical_metadata", "/home/debdeba/Documents/scripts/projects/EyeMT/clinical", "clinical metadata", "clinical integration", 2, 5920392),
                ("KRAS", None, "analysis_scripts", "/home/debdeba/Documents/scripts/projects/KRAS/scripts", "analysis scripts", "spatial feature extraction", 8, 192033)
            ]
            for p_code, s_code, fname, path, dtype, stage, count, size in folders:
                pid = projects[p_code]
                sid = samples[s_code][0] if s_code else None
                cur.execute("""
                    INSERT INTO platform.folder_catalog (project_id, sample_id, folder_name, absolute_path, data_type, pipeline_stage, file_count, total_size_bytes, owner_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (absolute_path) DO NOTHING;
                """, (pid, sid, fname, path, dtype, stage, count, size, debdeba_id))
            print("Successfully seeded folders catalog.")

            # 7. Seed dataset_catalog
            datasets = [
                ("SPACE", "SYNTH_SAMPLE_001", "SYNTH_SAMPLE_001_stitched.ome.tif", "OME-TIFF", "ome.tiff", "/home/debdeba/Documents/scripts/projects/SPACE/stitched/SYNTH_SAMPLE_001_stitched.ome.tif", 9201928374, "Ashlar stitching", "ashlar", "1.17.0", "approved", "Stitched slide image ready for segmentation"),
                ("SPACE", "SYNTH_SAMPLE_001", "SYNTH_SAMPLE_001_cell_mask.tif", "segmentation mask", "tiff", "/home/debdeba/Documents/scripts/projects/SPACE/masks/SYNTH_SAMPLE_001_cell_mask.tif", 82910293, "Mesmer segmentation", "mesmer", "0.12.3", "approved", "Nuclear and whole-cell segmented mask"),
                ("SPACE", "SYNTH_SAMPLE_001", "SYNTH_SAMPLE_001_features.csv", "CSV", "csv", "/home/debdeba/Documents/scripts/projects/SPACE/masks/SYNTH_SAMPLE_001_features.csv", 4829100, "quantification", "python_script", "1.0", "approved", "Expression and spatial coordinates of 24,000 cells")
            ]
            for p_code, s_code, dname, dtype, format, path, size, stage, sw, ver, qc, notes in datasets:
                pid = projects[p_code]
                sid = samples[s_code][0] if s_code else None
                cur.execute("""
                    INSERT INTO platform.dataset_catalog (project_id, sample_id, dataset_name, data_type, format, file_path, file_size_bytes, pipeline_stage, software_used, version_used, quality_status, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (file_path) DO NOTHING;
                """, (pid, sid, dname, dtype, format, path, size, stage, sw, ver, qc, notes))
            print("Successfully seeded datasets catalog.")

            # 8. Seed pipeline_run
            runs = [
                ("SPACE", "SYNTH_SAMPLE_001", "Ashlar stitching/registration", "ashlar '/home/debdeba/Documents/scripts/projects/SPACE/raw/*.tif' --output '/home/debdeba/Documents/scripts/projects/SPACE/stitched/SYNTH_SAMPLE_001_stitched.ome.tif'", "/home/debdeba/Documents/scripts/projects/SPACE/scripts/stitch.sh", "[]", "completed", "Processed 12 channels in 480 seconds", "Pass"),
                ("SPACE", "SYNTH_SAMPLE_001", "Mesmer segmentation", "python segment.py --image '/home/debdeba/Documents/scripts/projects/SPACE/stitched/SYNTH_SAMPLE_001_stitched.ome.tif' --output '/home/debdeba/Documents/scripts/projects/SPACE/masks/SYNTH_SAMPLE_001_cell_mask.tif'", "/home/debdeba/Documents/scripts/projects/SPACE/scripts/segment.py", "[]", "completed", "Segmented 24,510 cells using nuclear model", "Pass"),
                ("KRAS", None, "Cylinter QC", "cylinter --config /home/debdeba/Documents/scripts/projects/KRAS/configs/cylinter_config.yaml", "/home/debdeba/Documents/scripts/projects/KRAS/scripts/run_cylinter.sh", "[]", "failed", "Environment dependency mismatch during startup (Java JDK error)", "Fail")
            ]
            for p_code, s_code, stage, cmd, script, err, status, desc, qc in runs:
                pid = projects[p_code]
                sid = samples[s_code][0] if s_code else None
                cur.execute("""
                    INSERT INTO platform.pipeline_run (project_id, sample_id, pipeline_stage, command_used, script_path, status, error_summary, qc_result)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                """, (pid, sid, stage, cmd, script, status, desc, qc))
            print("Successfully seeded pipeline runs.")

            # 9. Seed tasks
            tasks = [
                ("SPACE", "SYNTH_SAMPLE_001", "Run Mesmer on stitched slide", "Segment cells using whole-cell deepcell algorithm", "todo", "high", date(2026, 6, 10)),
                ("SPACE", None, "Review weekly sync slides", "Prepare slides for the PI sync with Dr. Anniina Färkkilä", "in_progress", "medium", date(2026, 6, 5)),
                ("KRAS", None, "Fix WSL2 Java JDK environment conflict", "Resolve Cylinter runtime failure", "blocked", "high", date(2026, 6, 3))
            ]
            for p_code, s_code, title, desc, status, priority, due in tasks:
                pid = projects[p_code]
                sid = samples[s_code][0] if s_code else None
                cur.execute("""
                    INSERT INTO platform.task (project_id, sample_id, title, description, status, priority, due_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                """, (pid, sid, title, desc, status, priority, due))
            print("Successfully seeded tasks.")

            # 10. Seed decisions registry
            decisions = [
                ("SPACE", "Use Mesmer instead of StarDist", "Dense chemo-naive ovarian cancer tissue produced better segmentation quality with deep learning whole-cell models relative to star-convex boundary approximations.", "Selected Mesmer model v0.12.3", "StarDist segmentation, Cellpose inference", pi_id, date(2026, 5, 10)),
                ("SPACE", "Tile overlap parameters adjusted to 15%", "Stitching raw cycles failed with alignment mismatches on edge tiles when using standard 10% overlap.", "Set overlap parameter to 15% in Ashlar command line configs", "10% default overlap", debdeba_id, date(2026, 5, 2))
            ]
            for p_code, title, rationale, details, alternatives, decider, d_date in decisions:
                pid = projects[p_code]
                cur.execute("""
                    INSERT INTO platform.decision_registry (project_id, title, decision_details, rationale, alternatives_considered, decided_by_id, decision_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                """, (pid, title, details, rationale, alternatives, decider, d_date))
            print("Successfully seeded decisions registry.")

            # 11. Seed research_wiki
            wikis = [
                ("tCyCIF Tissue Preparation and Staining Protocol", "tcycif-tissue-preparation", "Tissue prep protocol detailing cyclic immunofluorescence methods, fluorophore labeling, and thermal bleaching cycle controls.", "protocol", pi_id),
                ("Mesmer Segmentation Guide", "mesmer-segmentation-guide", "Run Mesmer whole-cell and nuclear boundary prediction. Address memory errors on high-resolution stitched TIFF files using tile-size constraints.", "software_guide", debdeba_id),
                ("LUMI Ashlar Stitching SOP", "lumi-ashlar-stitching-sop", "Step-by-step tutorial for stitching high-resolution cycles on LUMI computing modules. Configures VcXsrv virtual displays and Apptainer environments.", "SOP", debdeba_id)
            ]
            for w_title, slug, content, w_type, author in wikis:
                cur.execute("""
                    INSERT INTO platform.research_wiki (title, slug, content, wiki_type, created_by_id)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING wiki_id;
                """, (w_title, slug, content, w_type, author))
                w_id = cur.fetchone()[0]
                
                # Seed version 1 in wiki_revision
                cur.execute("""
                    INSERT INTO platform.wiki_revision (wiki_id, revision_number, title, content, author_id)
                    VALUES (%s, 1, %s, %s, %s);
                """, (w_id, w_title, content, author))
            print("Successfully seeded research wiki and revisions.")

            # 12. Seed auto logs
            cur.execute("""
                INSERT INTO platform.auto_log (actor, event_type, description)
                VALUES ('debdeba', 'schema_upgrade', 'Upgraded the research platform schemas to the Clinical-Spatial Research Operating Platform standard (CS-ROP) with Digital Notebook as the system of record.');
            """)

        conn.commit()
    print("CS-ROP schema database seeding completed successfully.")

if __name__ == "__main__":
    main()
