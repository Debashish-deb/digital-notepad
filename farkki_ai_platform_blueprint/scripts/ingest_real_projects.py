#!/usr/bin/env python3
import os
import re
import psycopg
from pathlib import Path

DB_CONN = os.getenv("POSTGRES_CONN", "postgresql://farkki:farkki_dev_password@localhost:5432/farkki_ai")
MASTER_FILE = Path("/home/debdeba/Documents/scripts/projects/Projects_Master_File.md")

# Mapping of names to usernames
NAME_TO_USER = {
    "Pablo Siliceo": "psiliceo",
    "Anastasia Kachalova": "akachalova",
    "Ada Junquera": "ajunquera",
    "Ada junquera": "ajunquera",
    "Zhihan Liang": "zliang",
    "Aleksandra Shabanova": "ashabanova",
    "Saundaryah Shah": "sshah",
    "Saundarya Shah": "sshah",
    "Saun": "sshah",
    "Ilja Nystrand": "inystrand",
    "Matilda Salko": "msalko",
    "Ashwini Nagaraj": "anagaraj",
    "Iga Niemiec": "iniemiec",
    "Martina Giacomini": "mgiacomini",
    "Ziqi Kang": "zkang",
    "Sara Palomino": "spalomino",
    "Wenqing Chen": "wchen",
    "Wenging Chen": "wchen",
    "Inga Maria Launonen": "ilaunonen",
    "Inga-Maria Launonen": "ilaunonen",
    "Ella Anttila": "eanttila",
    "Naipunya Guruprasad": "nguruprasad",
    "Anni Virtanen": "avirtanen",
    "Oskari Lehtonen": "olehtonen",
    "Kaiyang Zhang": "kzhang",
    "Kaiyan Zhang": "kzhang",
    "Anniina Färkkilä": "afarkkila",
    "María Hincapié-Otero": "mhincapie",
    "María Hincapié Otero": "mhincapie",
    "Joonas Jukonen": "jjukonen",
    "Antti Toivanen": "atoivanen",
    "Fernando Perez": "fperez",
    "Jun Dai": "jdai",
    "Julia Casado": "jcasado",
    "Jacopo": "jacopo",
    "Salvatore": "salvatore",
    "Lilyan": "lilyan",
    "Ulla-Maija Haltia": "uhaltia",
    "Anni Suoknuuti": "asuoknuuti",
    "Elias Ruuska": "eruuska",
    "Mariike": "mariike",
    "Tuomas": "tuomas",
    "Mari": "mari",
    "Hanna Elomaa": "helomaa",
    "Andreas Hainari": "ahainari",
    "Anni Lindfors": "alindfors",
    "Nika Mikhailava": "nmikhailava",
    "Angela Szabo": "aszabo",
    "Teodora Farago": "tfarago",
    "Kevin Elias": "kelias",
    "Matias": "matias",
    "Olavi": "olavi",
    "Esa": "esa",
    "Venla Kaislo": "vkaislo",
    "Debashish Deb": "debdeba"
}

# Determine project code from index/title
def get_project_code(index, title):
    title_clean = re.sub(r'[^a-zA-Z0-9]', '', title).lower()
    if "myelonets" in title_clean: return "Myelonets"
    if "haikala" in title_clean: return "HaikalaCollab"
    if "fanconi" in title_clean or "alfredo" in title_clean: return "Fanconi"
    if "cellcycle" in title_clean or "cell cycle" in title.lower(): return "CellCycle"
    if "emt" in title_clean: return "EMT"
    if "lepp" in title_clean: return "LeppaCollab"
    if "tls" in title_clean: return "TLS"
    if "ipdc1" in title_clean or "ipdc_1" in title.lower(): return "iPDC_1.0"
    if "eyemt" in title_clean: return "EyeMT"
    if "salo" in title_clean: return "SaloCollab"
    if "vanharanta" in title_clean: return "VanharantaCollab"
    if "spacejoint" in title_clean: return "SPACEjoint"
    if "spacestat" in title_clean: return "SPACEstat"
    if "space" in title_clean: return "SPACE"
    if "sciset" in title_clean: return "sciSet"
    if "cin2" in title_clean: return "CIN2"
    if "ipdc2" in title_clean or "ipdc_2" in title.lower(): return "iPDC_2.0"
    if "vte" in title_clean: return "Ovca_VTE"
    if "auria" in title_clean: return "Auria"
    if "singlecell" in title_clean or "single cell" in title.lower(): return "SC_Integration"
    if "organoid" in title_clean: return "Organoids"
    if "vtma" in title_clean: return "vTMA"
    if "kras" in title_clean: return "KRAS"
    if "nki" in title_clean: return "NKI"
    if "ovahrdscar" in title_clean: return "ovaHRDscar"
    if "scrnaseq" in title_clean: return "HGSC_scRNAseq"
    if "sequencing" in title_clean: return "Sequencing"
    if "endometrial" in title_clean: return "Endometrial_HRD"
    if "mesenchymal" in title_clean: return "Mesenchymal_Ovca"
    if "dcis" in title_clean: return "DCIS"
    if "tribus" in title_clean: return "Tribus"
    if "pixel" in title_clean: return "Pixel_AI"
    if "proteomics" in title_clean: return "Proteomics"
    if "finprove" in title_clean: return "FINPROVE"
    if "tma" in title_clean: return "TMA_Cohorts"
    if "adc" in title_clean: return "ADC"
    return f"PROJ_{index}"

def parse_projects():
    if not MASTER_FILE.exists():
        print(f"Error: Master file not found at {MASTER_FILE}")
        return []

    content = MASTER_FILE.read_text()
    # Split by headers
    sections = re.split(r'\n###\s+', content)
    
    parsed = []
    # Skip the index section
    for section in sections[1:]:
        lines = section.strip().split('\n')
        if not lines:
            continue
        
        # Parse title: e.g. "1. 3D Myelonets"
        title_line = lines[0].strip()
        match = re.match(r'^(\d+)\.\s*(.*)', title_line)
        if match:
            idx = int(match.group(1))
            title = match.group(2).strip()
        else:
            idx = 99
            title = title_line
        
        responsible = "TBD"
        desc_lines = []
        in_desc = False
        
        for line in lines[1:]:
            line_str = line.strip()
            # Match responsible line
            resp_match = re.match(r'^\*\*Responsible:\s*(.*?)\*\*$', line_str, re.IGNORECASE)
            if not resp_match:
                resp_match = re.match(r'^\*\*Responsible:\s*(.*)$', line_str, re.IGNORECASE)
            
            if resp_match:
                responsible = resp_match.group(1).replace("**", "").strip()
                continue
            
            desc_match = re.match(r'^\*\*Description:?\*\*?(.*)$', line_str, re.IGNORECASE)
            if desc_match:
                in_desc = True
                desc_lines.append(desc_match.group(1).strip())
                continue
            
            if line_str.startswith("###"):
                break
                
            if in_desc or line_str:
                # Accumulate description
                desc_lines.append(line.strip())
        
        description = "\n".join([d for d in desc_lines if d]).strip()
        code = get_project_code(idx, title)
        parsed.append({
            "index": idx,
            "title": title,
            "code": code,
            "responsible": responsible,
            "description": description
        })
    return parsed

def main():
    projects = parse_projects()
    print(f"Parsed {len(projects)} projects from master file.")
    
    with psycopg.connect(DB_CONN) as conn:
        with conn.cursor() as cur:
            # 1. Register all researchers in platform.researcher first
            for name, username in NAME_TO_USER.items():
                role = 'PI' if username == 'afarkkila' else 'researcher'
                if username == 'debdeba':
                    role = 'IT Specialist'
                cur.execute("""
                    INSERT INTO platform.researcher (username, full_name, role, allowed_project_codes)
                    VALUES (%s, %s, %s, '{}')
                    ON CONFLICT (username) DO UPDATE 
                    SET full_name = EXCLUDED.full_name, role = EXCLUDED.role;
                """, (username, name, role))
            print("Successfully registered/updated all researchers.")
            
            # Fetch researcher map
            cur.execute("SELECT researcher_id, username FROM platform.researcher;")
            researcher_map = {uname: rid for rid, uname in cur.fetchall()}
            
            # 2. Insert projects into core.project and platform.project_extension
            for p in projects:
                code = p["code"]
                name = p["title"]
                desc = p["description"]
                resp_str = p["responsible"]
                
                # Determine project lead based on responsible persons list
                lead_name = resp_str.split('(')[0].split(',')[0].strip()
                lead_username = NAME_TO_USER.get(lead_name, "debdeba")
                lead_id = researcher_map.get(lead_username, researcher_map["debdeba"])
                
                # Clean up responsible string to extract potential members
                clean_names = re.findall(r'\b[A-Z][a-zA-ZäöåÄÖÅ-]+\s+[A-Z][a-zA-ZäöåÄÖÅ-]+\b', resp_str)
                members_usernames = [NAME_TO_USER.get(n) for n in clean_names if n in NAME_TO_USER]
                members_usernames = list(set([u for u in members_usernames if u]))
                
                # Add project lead to allowed project codes
                allowed_users = [lead_username] + members_usernames + ["afarkkila"]
                for u in allowed_users:
                    cur.execute("""
                        UPDATE platform.researcher
                        SET allowed_project_codes = array_append(allowed_project_codes, %s)
                        WHERE username = %s AND NOT (%s = ANY(allowed_project_codes));
                    """, (code, u, code))
                
                # Insert core project
                cur.execute("""
                    INSERT INTO core.project (project_code, project_name, project_lead, principal_investigator, disease_focus, short_description, default_sensitivity, status)
                    VALUES (%s, %s, %s, 'Anniina Färkkilä, MD, PhD', 'Ovarian Cancer', %s, 'restricted', 'active')
                    ON CONFLICT (project_code) DO UPDATE
                    SET project_name = EXCLUDED.project_name,
                        short_description = EXCLUDED.short_description
                    RETURNING project_id;
                """, (code, name, lead_name, desc[:300]))
                pid = cur.fetchone()[0]
                
                # Insert project extension
                priority = "medium"
                if code in ["SPACE", "EyeMT", "ADC"]:
                    priority = "high"
                cur.execute("""
                    INSERT INTO platform.project_extension (project_id, project_short_title, research_question, project_type, priority, collaborators, ethics_approval_reference, current_blockers, next_actions, project_summary, latest_update)
                    VALUES (%s, %s, %s, 'translational_research', %s, '{}', 'ETHICS-2026-GEN', 'None', 'Continue data analysis', %s, 'Project imported from Master File.')
                    ON CONFLICT (project_id) DO UPDATE
                    SET project_short_title = EXCLUDED.project_short_title,
                        project_summary = EXCLUDED.project_summary;
                """, (pid, name[:50], name, priority, desc))
                
                # Add members to project_member
                # Lead
                cur.execute("""
                    INSERT INTO platform.project_member (project_id, researcher_id, role, project_access_level, notes)
                    VALUES (%s, %s, 'project_lead', 'read_write', 'Lead researcher on project')
                    ON CONFLICT (project_id, researcher_id) DO NOTHING;
                """, (pid, lead_id))
                
                # PI Anniina Färkkilä
                cur.execute("""
                    INSERT INTO platform.project_member (project_id, researcher_id, role, project_access_level, notes)
                    VALUES (%s, %s, 'PI', 'admin', 'Principal Investigator oversight')
                    ON CONFLICT (project_id, researcher_id) DO NOTHING;
                """, (pid, researcher_map["afarkkila"]))
                
                # Other members
                for u in members_usernames:
                    rid = researcher_map.get(u)
                    if rid and rid != lead_id:
                        cur.execute("""
                            INSERT INTO platform.project_member (project_id, researcher_id, role, project_access_level, notes)
                            VALUES (%s, %s, 'collaborator', 'read_write', 'Collaborating researcher')
                            ON CONFLICT (project_id, researcher_id) DO NOTHING;
                        """, (pid, rid))
            
            print("Successfully registered all real projects, extensions and members mapping.")
            
        conn.commit()
    print("Database sync completed.")

if __name__ == "__main__":
    main()
