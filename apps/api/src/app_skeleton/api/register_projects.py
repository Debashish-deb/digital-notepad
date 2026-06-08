import os
import psycopg
from app_skeleton.api.paths import PROJECTS_ROOT
from app_skeleton.api.supabase_config import postgres_conn

def register_missing_projects():
    conn_uri = postgres_conn()
    with psycopg.connect(conn_uri) as conn:
        with conn.cursor() as cur:
            # Get existing project codes
            cur.execute("SELECT project_code FROM core.project;")
            existing_codes = {row[0] for row in cur.fetchall()}
            
            new_count = 0
            for child in PROJECTS_ROOT.iterdir():
                if child.is_dir() and child.name not in ["compiled_scripts", "project_scripts"]:
                    code = child.name
                    if code not in existing_codes:
                        print(f"Registering missing project to core.project: {code}")
                        
                        # 1. Insert into core.project
                        cur.execute("""
                            INSERT INTO core.project (
                                project_code, project_name, project_lead, 
                                principal_investigator, disease_focus, 
                                short_description, default_sensitivity, status
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, 'internal', 'active'
                            ) RETURNING project_id;
                        """, (
                            code, 
                            code.replace('_', ' '), 
                            "Auto Imported", 
                            "afarkkila", 
                            "Other", 
                            "Automatically registered from database folder"
                        ))
                        pid = cur.fetchone()[0]
                        
                        # 2. Insert into platform.project_extension
                        cur.execute("""
                            INSERT INTO platform.project_extension (
                                project_id, project_short_title, research_question, 
                                project_type, priority, collaborators, 
                                ethics_approval_reference, current_blockers, 
                                next_actions, project_summary, latest_update
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s::text[], %s, %s, %s, %s, %s
                            ) ON CONFLICT DO NOTHING;
                        """, (
                            pid, 
                            code, 
                            "TBD", 
                            "Exploratory", 
                            "Medium", 
                            [], 
                            "N/A", 
                            "None", 
                            "Review imported data", 
                            "Project folders synced from disk.", 
                            "Auto imported into platform"
                        ))
                        new_count += 1
                        
            conn.commit()
            print(f"Registered {new_count} new projects to the GUI database.")

if __name__ == "__main__":
    register_missing_projects()
