import streamlit as st
import requests
import pandas as pd
import difflib
from datetime import date, datetime

# Set page configuration
st.set_page_config(
    page_title="Farkki-AI Clinical-Spatial ROP Platform",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for premium styling (sleek dark mode, curated HSL colors)
st.markdown("""
<style>
    .stApp {
        background-color: #0d1117;
        color: #e6edf3;
    }
    .main-header {
        font-family: 'Outfit', 'Inter', sans-serif;
        background: linear-gradient(90deg, #818cf8, #34d399, #38bdf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.8rem;
        margin-bottom: 0.1rem;
    }
    .metric-card {
        background-color: #161b22;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #30363d;
        border-left: 5px solid #818cf8;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.15);
        margin-bottom: 1rem;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #8b949e;
        text-transform: uppercase;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #ffffff;
    }
    .card-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #58a6ff;
        margin-bottom: 0.8rem;
    }
    .audit-log-item {
        background-color: #161b22;
        padding: 0.8rem;
        border-radius: 8px;
        border: 1px solid #21262d;
        margin-bottom: 0.5rem;
    }
    .diff-added {
        background-color: #1f3a2b;
        color: #3fdb84;
        padding: 0.2rem;
        font-family: monospace;
    }
    .diff-removed {
        background-color: #441c22;
        color: #ff6b7d;
        padding: 0.2rem;
        font-family: monospace;
    }
    .diff-context {
        color: #8b949e;
        padding: 0.2rem;
        font-family: monospace;
    }
</style>
""", unsafe_allow_html=True)

API_URL = "http://localhost:8000"

import os
import pathlib

def get_project_folder_path(project_code):
    projects_dir = "/Users/debashishdeb/Downloads/OMEIA-AI/projects"
    if not os.path.exists(projects_dir):
        return None
    for folder in os.listdir(projects_dir):
        folder_path = os.path.join(projects_dir, folder)
        if not os.path.isdir(folder_path):
            continue
        clean_folder = folder.lower().replace("_", "").replace("-", "")
        clean_code = project_code.lower().replace("_", "").replace("-", "")
        if clean_code in clean_folder or clean_folder in clean_code:
            return folder_path
    return None

def scan_project_text_files(folder_path):
    text_files = []
    if not folder_path or not os.path.exists(folder_path):
        return text_files
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            if any(part in file_path for part in [".git", "node_modules", ".venv", ".dart_tool", "build"]):
                continue
            ext = pathlib.Path(file).suffix.lower()
            if ext in [".txt", ".md", ".py", ".r", ".sh", ".json", ".yaml", ".yml", ".sql"]:
                rel_path = os.path.relpath(file_path, folder_path)
                text_files.append({"name": rel_path, "path": file_path})
    return text_files

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.image("https://img.icons8.com/nolan/96/dna.png", width=70)
    st.markdown("### **CS-ROP Platform**")
    st.caption("Clinical-Spatial Research Operating Platform")
    st.markdown("---")
    
    st.markdown("#### **Scope Settings**")
    try:
        proj_resp = requests.get(f"{API_URL}/projects", timeout=3)
        db_projects = [p["project_code"] for p in proj_resp.json()]
    except Exception:
        db_projects = ["SPACE", "EyeMT", "KRAS"]

    project_codes = st.multiselect(
        "Scoping Projects",
        options=db_projects,
        default=["SPACE", "EyeMT", "KRAS"] if "SPACE" in db_projects else db_projects[:3],
        help="Filters RAG documents and database metrics to selected projects."
    )
    
    mode = st.selectbox(
        "Inquiry Mode",
        options=["documentation_only", "deidentified_research"],
        help="Choose between looking up documentation/scripts only or querying cohort metrics."
    )

    st.markdown("⚠️ **Privacy Warning**:\nDo not paste identifiable patient data (SSNs, DOBs, MRNs). Use de-identified research IDs only.")

    st.markdown("---")
    with st.expander("🔑 **LLM Provider Settings**", expanded=False):
        llm_provider = st.selectbox(
            "Provider Selection",
            options=["mock", "groq", "openai", "openrouter", "together", "ollama"],
            index=0,
            help="Select the active LLM provider. 'mock' runs local dynamic synthesis."
        )
        llm_model = st.text_input(
            "Model Name",
            value="llama-3.1-70b-versatile" if llm_provider == "groq" else ("gpt-4o-mini" if llm_provider == "openai" else "mock-model"),
            help="Target model identifier."
        )
        llm_api_key = st.text_input(
            "API Key (Optional)",
            type="password",
            placeholder="Enter API Key...",
            help="Credentials are processed in-memory."
        )
        llm_base_url = st.text_input(
            "Base URL (Optional)",
            placeholder="Default API endpoint",
            help="Override standard URL."
        )

# Dynamic stats loading based on sidebar filters
def fetch_stats(projects):
    try:
        params = {"project_code": projects} if projects else {}
        r = requests.get(f"{API_URL}/stats", params=params, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"error": str(exc), "patient_count": 0, "sample_count": 0, "project_samples": {}, "modality_samples": {}}

stats = fetch_stats(project_codes)

with st.sidebar:
    st.markdown("---")
    st.markdown("#### **Database Status**")
    if "error" in stats:
        st.error("❌ Postgres Connection Offline")
    else:
        st.success("⚡ Postgres Connected")
        st.info("⚡ Qdrant Index Live")

# ----------------- MAIN CONTENT -----------------
st.markdown('<p class="main-header">Clinical-Spatial Operating Platform</p>', unsafe_allow_html=True)
st.caption("Lab notebook, project tracker, protocol wiki, and AI copilot for spatial biology laboratories.")

tabs = st.tabs([
    "🏠 Lab Dashboard",
    "📁 Projects & Data Catalog",
    "📓 Living Notebook & Wiki",
    "⚖️ Research Decisions",
    "✅ Tasks Planner",
    "💬 Chat Copilot", 
    "🛠️ Install Software", 
    "🚀 Run Pipeline", 
    "💻 Generate LUMI Job",
    "🩺 Env Checker",
    "🔍 Troubleshoot Error",
    "✨ Knowledge Onboarding Wizard",
    "🤖 AI Model Registry",
    "🏢 Infrastructure Registry",
    "📊 Gap Analysis & Readiness"
])

# --- TAB 0: LAB DASHBOARD ---
with tabs[0]:
    # Key stats cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Patients</div>
            <div class="metric-value">{stats.get('patient_count', 0)}</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Samples</div>
            <div class="metric-value">{stats.get('sample_count', 0)}</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Active Projects</div>
            <div class="metric-value">{len(stats.get('project_samples', {}))}</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        # Load team count dynamically
        team_size = 0
        try:
            r_team = requests.get(f"{API_URL}/team", timeout=3)
            if r_team.status_code == 200:
                team_size = len(r_team.json())
        except Exception:
            pass
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Lab Team Members</div>
            <div class="metric-value">{team_size or 3}</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("---")
    
    col_dash1, col_dash2 = st.columns(2)
    with col_dash1:
        st.markdown("### 👥 **Lab Members & Roles**")
        try:
            r_team = requests.get(f"{API_URL}/team", timeout=3)
            if r_team.status_code == 200:
                df_team = pd.DataFrame(r_team.json())
                st.dataframe(df_team, use_container_width=True)
            else:
                st.info("No lab member profiles found.")
        except Exception as exc:
            st.error(f"Failed to fetch team data: {exc}")
            
    with col_dash2:
        st.markdown("### 📜 **System Audit logs (Notebook-traceable)**")
        try:
            r_logs = requests.get(f"{API_URL}/auto_logs", timeout=3)
            if r_logs.status_code == 200:
                logs = r_logs.json()
                for log in logs[:10]:
                    st.markdown(f"""
                    <div class="audit-log-item">
                        <div style="display:flex; justify-content:space-between; font-size:0.8rem; color:#8b949e;">
                            <span>👤 <b>{log['actor']}</b> | Event: <i>{log['event_type']}</i></span>
                            <span>🕒 {log['created_at'].replace('T', ' ')}</span>
                        </div>
                        <div style="margin-top: 0.3rem; font-size:0.9rem;">{log['description']}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No audit logs recorded.")
        except Exception as exc:
            st.error(f"Failed to load audit logs: {exc}")

# --- TAB 1: PROJECTS & DATA CATALOG ---
with tabs[1]:
    import math
    st.markdown("### 📁 **Project Portfolio & Clinical-Spatial Workspaces**")
    
    # Initialize session state for project selection
    if "selected_project" not in st.session_state:
        st.session_state.selected_project = None
        
    try:
        r_proj = requests.get(f"{API_URL}/projects", timeout=5)
        if r_proj.status_code == 200:
            projects = r_proj.json()
            proj_dict = {p["project_code"]: p for p in projects}
            
            # --- PORTFOLIO VIEW (NO SELECTED PROJECT) ---
            if st.session_state.selected_project is None:
                st.markdown("Select an active clinical-spatial research project to access its workspace, documentation checklists, notebooks, and folder logs.")
                
                # Search and filter projects
                col_search, col_type = st.columns([2, 1])
                p_search_query = col_search.text_input("🔍 Search project portfolio...", placeholder="Search code, title, lead, PI...")
                p_type_filter = col_type.selectbox("Filter by Type", ["All Types", "spatial_profiling", "clinical_trial", "pilot_study"])
                
                filtered_projects = projects
                if p_search_query:
                    filtered_projects = [p for p in filtered_projects if (
                        p_search_query.lower() in p["project_code"].lower() or
                        p_search_query.lower() in p["project_name"].lower() or
                        p_search_query.lower() in p["project_lead"].lower() or
                        p_search_query.lower() in p["principal_investigator"].lower() or
                        p_search_query.lower() in (p.get("disease_focus") or "").lower()
                    )]
                if p_type_filter != "All Types":
                    filtered_projects = [p for p in filtered_projects if p.get("project_type") == p_type_filter]
                
                if filtered_projects:
                    # Render grid cards
                    cols_per_row = 3
                    num_filtered = len(filtered_projects)
                    num_rows = math.ceil(num_filtered / cols_per_row)
                    
                    for r_idx in range(num_rows):
                        grid_cols = st.columns(cols_per_row)
                        for c_idx in range(cols_per_row):
                            p_idx = r_idx * cols_per_row + c_idx
                            if p_idx < num_filtered:
                                p = filtered_projects[p_idx]
                                with grid_cols[c_idx]:
                                    st.markdown(f"""
                                    <div class="metric-card" style="min-height: 250px; display: flex; flex-direction: column; justify-content: space-between; border-left: 5px solid #38bdf8;">
                                        <div>
                                            <div style="font-weight: 700; color: #58a6ff; font-size: 1.25rem;">🧬 {p['project_code']}</div>
                                            <div style="font-size: 0.95rem; font-weight: 600; margin-top: 0.2rem; color: #ffffff; height: 50px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">{p['project_name']}</div>
                                            <div style="font-size: 0.85rem; color: #8b949e; margin-top: 0.4rem; height: 50px; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;">
                                                {p.get('project_summary') or p.get('short_description') or 'No summary provided.'}
                                            </div>
                                        </div>
                                        <div style="font-size: 0.8rem; color: #8b949e; margin-top: 0.5rem; border-top: 1px solid #21262d; padding-top: 0.5rem;">
                                            👤 PI: <b>{p['principal_investigator']}</b><br>
                                            👤 Lead: <b>{p['project_lead']}</b><br>
                                            ⚡ Status: <span style="color: #34d399;">{p['status']}</span>
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    if st.button(f"📂 Open Workspace: {p['project_code']}", key=f"btn_open_{p['project_code']}", type="secondary", use_container_width=True):
                                        st.session_state.selected_project = p['project_code']
                                        st.rerun()
                else:
                    st.info("No research projects found matching the criteria.")
                    
            # --- DETAILED WORKSPACE VIEW ---
            else:
                p_code = st.session_state.selected_project
                p_data = proj_dict[p_code]
                
                # Header with Back button
                col_back, col_title = st.columns([1, 8])
                with col_back:
                    if st.button("← Portfolio", key="btn_back_to_portfolio", type="primary", use_container_width=True):
                        st.session_state.selected_project = None
                        st.rerun()
                with col_title:
                    st.markdown(f"<h3 style='margin:0; color:#58a6ff;'>🧬 Project Workspace: {p_data['project_name']} ({p_code})</h3>", unsafe_allow_html=True)
                    st.caption(f"Principal Investigator: {p_data['principal_investigator']} | Project Lead: {p_data['project_lead']} | Status: `{p_data['status']}`")
                
                st.markdown("---")
                
                col_w1, col_w2 = st.columns([3, 2])
                with col_w1:
                    st.markdown("#### **Research Overview & Question**")
                    st.markdown(f"**Research Question:** {p_data['research_question'] or 'Not defined.'}")
                    st.markdown(f"**Detailed Summary:**\n{p_data['project_summary'] or 'No summary recorded.'}")
                    st.markdown(f"**Disease Focus:** `{p_data['disease_focus']}`")
                    st.markdown(f"**Project Type:** `{p_data.get('project_type', 'spatial_profiling')}`")
                    st.markdown(f"**Ethics Reference:** `{p_data['ethics_approval_reference'] or 'N/A'}`")
                with col_w2:
                    st.markdown("#### **Onboarding & Status**")
                    # Checklists fetch for progress
                    try:
                        chk_r = requests.get(f"{API_URL}/checklists/{p_code}", timeout=3)
                        checklists = chk_r.json() if chk_r.status_code == 200 else []
                    except Exception:
                        checklists = []
                        
                    if checklists:
                        completed_items = sum(1 for c in checklists if c["status"] == "completed")
                        total_items = len(checklists)
                        score = int((completed_items / total_items) * 100) if total_items > 0 else 0
                        st.metric("Milestone Completion Score", f"{score}%", f"{completed_items} of {total_items} items")
                        st.progress(score / 100.0)
                        
                        pending_items = [c for c in checklists if c["status"] != "completed"]
                        if pending_items:
                            st.warning("⚠️ **Pending Milestones:**")
                            for item in pending_items[:2]:
                                st.markdown(f"- **{item['item_name']}** ({item['category']})")
                        else:
                            st.success("🎉 All onboarding checklists completed!")
                    else:
                        st.info("No milestone checklist registered for this project.")
                        
                    st.markdown(f"**Priority:** `{p_data.get('priority', 'medium').upper()}`")
                    st.markdown(f"**Collaborators:** {', '.join(p_data.get('collaborators', [])) or 'None'}")
                    st.markdown(f"**Latest Activity:** {p_data.get('latest_update', 'N/A')}")
                    
                st.markdown("---")
                
                # Workspace sub-tabs
                p_tabs = st.tabs([
                    "📄 Folder Documentation & Notepad",
                    "✅ Onboarding Milestones",
                    "📓 Notebook Logs",
                    "⚖️ Decisions Ledger",
                    "📊 Data & Pipelines Catalog",
                    "📝 Edit Metadata"
                ])
                
                # --- Tab 1a: Folder Documentation Notepad ---
                with p_tabs[0]:
                    st.markdown("### 📁 **Folder Documentation & Interactive Notepad**")
                    st.caption("Access and edit documentation, experimental notes, and logs directly from your project directory.")
                    
                    folder_path = get_project_folder_path(p_code)
                    if folder_path:
                        st.markdown(f"📂 **Project Folder Path:** `{folder_path}`")
                        files = scan_project_text_files(folder_path)
                        
                        if files:
                            file_names = [f["name"] for f in files]
                            
                            col_sel_file, col_edit_toggle = st.columns([3, 1])
                            with col_sel_file:
                                selected_file_name = st.selectbox("Select Documentation File to View/Edit", file_names, key=f"sel_file_{p_code}")
                            selected_file = next(f for f in files if f["name"] == selected_file_name)
                            
                            # Read file
                            try:
                                with open(selected_file["path"], "r", encoding="utf-8", errors="ignore") as f:
                                    file_content = f.read()
                            except Exception as exc:
                                file_content = f"Error reading file: {exc}"
                                
                            file_ext = os.path.splitext(selected_file["name"])[1].lower()
                            
                            with col_edit_toggle:
                                edit_mode = st.toggle("✍️ Enable Notepad Edit", value=False, key=f"edit_mode_toggle_{selected_file_name}")
                                
                            if edit_mode:
                                with st.form(f"edit_file_form_{p_code}_{selected_file_name.replace('.', '_').replace('/', '_')}"):
                                    new_content = st.text_area("Edit Content (Notepad)", value=file_content, height=450)
                                    submit_save = st.form_submit_button("💾 Save Revisions to Disk", type="primary")
                                    if submit_save:
                                        try:
                                            with open(selected_file["path"], "w", encoding="utf-8") as f:
                                                f.write(new_content)
                                            st.success(f"Successfully saved revisions to `{selected_file_name}`!")
                                            st.rerun()
                                        except Exception as exc:
                                            st.error(f"Failed to write to file: {exc}")
                            else:
                                if file_ext == ".md":
                                    st.markdown(f"<div style='background-color:#161b22; padding:1.5rem; border-radius:8px; border:1px solid #30363d;'>{file_content}</div>", unsafe_allow_html=True)
                                else:
                                    st.code(file_content, language=file_ext[1:] if file_ext[1:] else "text")
                        else:
                            st.info("No text or markdown documentation files found in this folder.")
                            
                            # Allow creating a new note file
                            with st.form(f"create_new_doc_form_{p_code}"):
                                new_doc_name = st.text_input("New File Name", "README.md")
                                new_doc_content = st.text_area("File Content (Notepad)", "# Project Notes\n\nWrite your observations...")
                                submit_create = st.form_submit_button("🆕 Create Documentation File", type="primary")
                                if submit_create:
                                    try:
                                        new_file_path = os.path.join(folder_path, new_doc_name)
                                        with open(new_file_path, "w", encoding="utf-8") as f:
                                            f.write(new_doc_content)
                                        st.success(f"Successfully created `{new_doc_name}` in the project folder!")
                                        st.rerun()
                                    except Exception as exc:
                                        st.error(f"Failed to create file: {exc}")
                    else:
                        st.warning("⚠️ **Project Folder Not Found on Disk.**")
                        st.info(f"Could not map project code '{p_code}' to a folder in `/Users/debashishdeb/Downloads/OMEIA-AI/projects`. Make sure the folder is named appropriately.")
                        
                # --- Tab 1b: Onboarding Milestones Checklists ---
                with p_tabs[1]:
                    st.markdown("### Onboarding Milestone Checklists")
                    if checklists:
                        categories = list(set([c["category"] for c in checklists]))
                        categories.sort()
                        for cat in categories:
                            st.markdown(f"**{cat.upper()} Checklists**")
                            cat_items = [c for c in checklists if c["category"] == cat]
                            for item in cat_items:
                                checked = (item["status"] == "completed")
                                chk_key = f"chk_workspace_{item['checklist_id']}"
                                col_chk, col_info = st.columns([0.1, 0.9])
                                with col_chk:
                                    is_checked = st.checkbox("", value=checked, key=chk_key)
                                with col_info:
                                    st.markdown(f"**{item['item_name']}** — {item['description']}")
                                    if item["checked_at"]:
                                        st.caption(f"✓ Checked off on {item['checked_at'][:10]}")
                                if is_checked != checked:
                                    new_status = 'completed' if is_checked else 'pending'
                                    try:
                                        requests.post(f"{API_URL}/checklists/toggle", json={
                                            "checklist_id": item["checklist_id"],
                                            "status": new_status,
                                            "username": "debdeba"
                                        })
                                        st.success("Checklist milestone updated!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error: {e}")
                    else:
                        st.info("No milestone checklists registered for this project.")
                        
                # --- Tab 1c: Notebook Logs ---
                with p_tabs[2]:
                    st.markdown("### Project Notebook Logs")
                    try:
                        r_note = requests.get(f"{API_URL}/notebook", params={"project_code": p_code}, timeout=5)
                        if r_note.status_code == 200 and r_note.json():
                            for e in r_note.json():
                                with st.expander(f"📓 {e['title']} (v{e['version']}) — {e['created_at'].replace('T', ' ')[:16]}"):
                                    st.markdown(e["content"])
                                    if e["conclusions"]:
                                        st.markdown(f"**Conclusions:** {e['conclusions']}")
                                    if e["issues_found"]:
                                        st.warning(f"⚠️ **Issues Found:** {e['issues_found']}")
                                    if e["next_steps"]:
                                        st.info(f"💡 **Next Steps:** {e['next_steps']}")
                        else:
                            st.info("No notebook entries logged for this project.")
                    except Exception as e:
                        st.error(f"Failed to load notebook logs: {e}")
                        
                # --- Tab 1d: Decisions Ledger ---
                with p_tabs[3]:
                    st.markdown("### Project Decisions Registry")
                    try:
                        r_dec = requests.get(f"{API_URL}/decisions", timeout=5)
                        if r_dec.status_code == 200:
                            proj_decs = [d for d in r_dec.json() if d["project_code"] == p_code]
                            if proj_decs:
                                for d in proj_decs:
                                    st.markdown(f"""
                                    <div class="audit-log-item" style="border-left: 5px solid #34d399;">
                                        <h5 style="color:#58a6ff; margin:0;">🎯 {d['title']}</h5>
                                        <div style="font-size:0.8rem; color:#8b949e; margin-bottom:0.4rem;">Decided By: {d['decider_name']} | Date: {d['decision_date']}</div>
                                        <div style="font-size:0.9rem;">{d['decision_details']}</div>
                                        <div style="font-size:0.85rem; color:#8b949e; margin-top:0.3rem;"><i>Rationale:</i> {d['rationale']}</div>
                                    </div>
                                    """, unsafe_allow_html=True)
                            else:
                                st.info("No formal decisions logged for this project.")
                        else:
                            st.error("Failed to load decisions registry.")
                    except Exception as e:
                        st.error(f"Failed to load decisions ledger: {e}")
                        
                # --- Tab 1e: Data & Pipelines Catalog ---
                with p_tabs[4]:
                    sub_col1, sub_col2, sub_col3 = st.columns(3)
                    with sub_col1:
                        st.markdown("##### 📁 **Folders Catalog**")
                        r_fold = requests.get(f"{API_URL}/folders", params={"project_code": p_code}, timeout=5)
                        if r_fold.status_code == 200 and r_fold.json():
                            st.dataframe(pd.DataFrame(r_fold.json()), use_container_width=True)
                        else:
                            st.info("No registered folders for this project.")
                    with sub_col2:
                        st.markdown("##### 🧪 **Datasets Inventory**")
                        r_data = requests.get(f"{API_URL}/datasets", params={"project_code": p_code}, timeout=5)
                        if r_data.status_code == 200 and r_data.json():
                            st.dataframe(pd.DataFrame(r_data.json()), use_container_width=True)
                        else:
                            st.info("No registered datasets for this project.")
                    with sub_col3:
                        st.markdown("##### 🚀 **Pipeline Runs**")
                        r_runs = requests.get(f"{API_URL}/pipeline_runs", params={"project_code": p_code}, timeout=5)
                        if r_runs.status_code == 200 and r_runs.json():
                            st.dataframe(pd.DataFrame(r_runs.json()), use_container_width=True)
                        else:
                            st.info("No pipeline runs logged for this project.")
                            
                # --- Tab 1f: Edit Metadata Form ---
                with p_tabs[5]:
                    st.markdown("### Edit Project Registry Fields")
                    with st.form(f"edit_project_form_{p_code}"):
                        up_short_title = st.text_input("Short Title", p_data.get("project_short_title", p_code))
                        up_question = st.text_area("Research Question", p_data.get("research_question", ""))
                        p_types = ["spatial_profiling", "clinical_trial", "pilot_study"]
                        curr_type = p_data.get("project_type", "spatial_profiling")
                        if curr_type not in p_types:
                            p_types.append(curr_type)
                        up_type = st.selectbox("Project Type", p_types, index=p_types.index(curr_type))

                        p_priorities = ["low", "medium", "high", "critical"]
                        curr_priority = p_data.get("priority", "medium")
                        if curr_priority not in p_priorities:
                            p_priorities.append(curr_priority)
                        up_priority = st.selectbox("Priority", p_priorities, index=p_priorities.index(curr_priority))
                        up_ethics = st.text_input("Ethics Reference", p_data.get("ethics_approval_reference", ""))
                        up_blockers = st.text_area("Current Blockers", p_data.get("current_blockers", ""))
                        up_next_actions = st.text_area("Next Actions", p_data.get("next_actions", ""))
                        up_summary = st.text_area("Project Summary", p_data.get("project_summary", ""))
                        up_update = st.text_input("Latest Activity Update", p_data.get("latest_update", ""))
                        
                        submit_up = st.form_submit_button("Update Project & Log Action", type="primary")
                        if submit_up:
                            payload = {
                                "project_short_title": up_short_title,
                                "research_question": up_question,
                                "project_type": up_type,
                                "priority": up_priority,
                                "ethics_approval_reference": up_ethics,
                                "current_blockers": up_blockers,
                                "next_actions": up_next_actions,
                                "project_summary": up_summary,
                                "latest_update": up_update
                            }
                            r_put = requests.put(f"{API_URL}/projects/{p_code}", json=payload)
                            if r_put.status_code == 200:
                                st.success("Project updated successfully and logged in notebook system of record!")
                                st.rerun()
                            else:
                                st.error(f"Failed to update project: {r_put.text}")
        else:
            st.error("Failed to load projects list.")
    except Exception as exc:
        st.error(f"Error fetching projects: {exc}")

# --- TAB 2: LIVING NOTEBOOK & WIKI ---
with tabs[2]:
    st.markdown("### 📓 **Living Notebook & Lab Wiki Protocol Center**")
    
    subtab1, subtab2 = st.tabs(["📓 Lab Notebook Logs", "📚 Protocols Wiki SOPs"])
    
    with subtab1:
        st.markdown("#### **Research Notebook System of Record**")
        
        # Two-column notebook view
        col_n1, col_n2 = st.columns([1, 2])
        
        with col_n1:
            st.markdown("##### **Select/Filter Entry**")
            p_filter = st.selectbox("Filter by Project", ["All"] + ["SPACE", "EyeMT", "KRAS"])
            p_param = {"project_code": p_filter} if p_filter != "All" else {}
            
            try:
                r_note = requests.get(f"{API_URL}/notebook", params=p_param)
                if r_note.status_code == 200:
                    entries = r_note.json()
                    if entries:
                        entry_titles = [f"{e['title']} (v{e['version']})" for e in entries]
                        selected_title = st.radio("Choose Notebook Entry", entry_titles)
                        selected_entry = entries[entry_titles.index(selected_title)]
                    else:
                        st.info("No notebook entries match the filter.")
                        selected_entry = None
                else:
                    st.error("Failed to fetch notebook entries.")
                    selected_entry = None
            except Exception as exc:
                st.error(f"Error: {exc}")
                selected_entry = None
                
            st.markdown("---")
            # Create new entry form
            with st.expander("🆕 Create New Notebook Log"):
                with st.form("create_notebook_form"):
                    n_proj = st.selectbox("Project Code", ["SPACE", "EyeMT", "KRAS"])
                    n_sample = st.text_input("Sample Code (Optional)", "")
                    n_title = st.text_input("Log Title", "")
                    n_content = st.text_area("Observations/Content", "")
                    n_conclusions = st.text_area("Conclusions (Optional)", "")
                    n_issues = st.text_area("Issues Found (Optional)", "")
                    n_next = st.text_area("Next Steps (Optional)", "")
                    n_tags = st.text_input("Tags (comma separated)", "QC, mesm_run")
                    n_type = st.selectbox("Entry Type", ["general_note", "decision_note", "run_failure_note", "protocol_deviation_note"])
                    
                    submit_n = st.form_submit_button("Record Entry in Logbook", type="primary")
                    if submit_n:
                        payload = {
                            "project_code": n_proj,
                            "sample_code": n_sample if n_sample else None,
                            "title": n_title,
                            "content": n_content,
                            "conclusions": n_conclusions if n_conclusions else None,
                            "issues_found": n_issues if n_issues else None,
                            "next_steps": n_next if n_next else None,
                            "tags": [t.strip() for t in n_tags.split(",") if t.strip()],
                            "entry_type": n_type
                        }
                        r_post = requests.post(f"{API_URL}/notebook", json=payload)
                        if r_post.status_code == 200:
                            st.success("Entry added to primary system of record!")
                            st.rerun()
                        else:
                            st.error(f"Failed to create notebook log: {r_post.text}")

        with col_n2:
            if selected_entry:
                st.markdown(f"### **{selected_entry['title']}**")
                st.caption(f"📅 Registered: {selected_entry['created_at']} | 👤 Author: {selected_entry['author_name']} | 📦 Version: v{selected_entry['version']}")
                
                # Tags display
                if selected_entry['tags']:
                    tags_html = " ".join([f"<span style='background-color:#21262d; border:1px solid #30363d; border-radius:15px; padding:0.2rem 0.6rem; margin-right:0.3rem; font-size:0.8rem;'>#{t}</span>" for t in selected_entry['tags']])
                    st.markdown(tags_html, unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)
                
                st.markdown(f"**Observations & Process Details:**\n{selected_entry['content']}")
                if selected_entry['conclusions']:
                    st.markdown(f"**Conclusions:**\n{selected_entry['conclusions']}")
                if selected_entry['issues_found']:
                    st.warning(f"⚠️ **Issues Found:**\n{selected_entry['issues_found']}")
                if selected_entry['next_steps']:
                    st.info(f"💡 **Next Steps:**\n{selected_entry['next_steps']}")
                
                st.markdown("---")
                
                # Revision History and Rollbacks
                st.markdown("#### ⏳ **Notebook Revision History & Diff Comparison**")
                try:
                    r_revs = requests.get(f"{API_URL}/notebook/{selected_entry['entry_id']}/revisions")
                    if r_revs.status_code == 200:
                        revisions = r_revs.json()
                        rev_options = {f"Version {rv['revision_number']} (Compiled {rv['created_at'].replace('T', ' ')})": rv for rv in revisions}
                        
                        # Selection columns
                        c_rev1, c_rev2 = st.columns(2)
                        v_selected_1 = c_rev1.selectbox("Select Revision A", list(rev_options.keys()), index=0)
                        v_selected_2 = c_rev2.selectbox("Select Revision B", list(rev_options.keys()), index=min(1, len(revisions)-1))
                        
                        rev_a = rev_options[v_selected_1]
                        rev_b = rev_options[v_selected_2]
                        
                        # Show Diff Comparison
                        if st.button("Compare Revisions A & B"):
                            st.markdown(f"**Comparing: {v_selected_1} vs {v_selected_2}**")
                            diff = difflib.ndiff(rev_b["content"].splitlines(), rev_a["content"].splitlines())
                            diff_output = []
                            for line in diff:
                                if line.startswith('+ '):
                                    diff_output.append(f"<div class='diff-added'>+ {line[2:]}</div>")
                                elif line.startswith('- '):
                                    diff_output.append(f"<div class='diff-removed'>- {line[2:]}</div>")
                                elif line.startswith('  '):
                                    diff_output.append(f"<div class='diff-context'>  {line[2:]}</div>")
                            st.markdown(f"<div style='background-color:#0d1117; padding:1rem; border-radius:8px;'>{''.join(diff_output)}</div>", unsafe_allow_html=True)
                            
                        st.markdown("---")
                        # Rollback widget
                        st.markdown("##### 🚨 Rollback to Previous Version")
                        target_rollback_version = st.selectbox("Rollback Target Revision", [rv["revision_number"] for rv in revisions])
                        if st.button("Execute Version Rollback"):
                            r_rb = requests.post(f"{API_URL}/notebook/{selected_entry['entry_id']}/rollback", params={"revision_number": target_rollback_version})
                            if r_rb.status_code == 200:
                                st.success(f"Notebook successfully rolled back to Version {target_rollback_version}!")
                                st.rerun()
                            else:
                                st.error(f"Failed to rollback notebook version: {r_rb.text}")
                    else:
                        st.error("Failed to load revision metrics.")
                except Exception as exc:
                    st.error(f"Error fetching notebook revisions: {exc}")
                    
                st.markdown("---")
                
                # Edit Entry inline
                with st.expander("📝 Edit Selected Log (Creates new revision)"):
                    with st.form("edit_notebook_form"):
                        ed_title = st.text_input("Log Title", selected_entry["title"])
                        ed_content = st.text_area("Observations/Content", selected_entry["content"])
                        ed_conclusions = st.text_area("Conclusions (Optional)", selected_entry["conclusions"] or "")
                        ed_issues = st.text_area("Issues Found (Optional)", selected_entry["issues_found"] or "")
                        ed_next = st.text_area("Next Steps (Optional)", selected_entry["next_steps"] or "")
                        ed_tags = st.text_input("Tags (comma separated)", ",".join(selected_entry["tags"]))
                        entry_types = ["general_note", "decision_note", "run_failure_note", "protocol_deviation_note"]
                        if selected_entry["entry_type"] not in entry_types:
                            entry_types.append(selected_entry["entry_type"])
                        ed_type = st.selectbox("Entry Type", entry_types, index=entry_types.index(selected_entry["entry_type"]))
                        
                        submit_ed = st.form_submit_button("Record Revision", type="primary")
                        if submit_ed:
                            payload_ed = {
                                "title": ed_title,
                                "content": ed_content,
                                "conclusions": ed_conclusions if ed_conclusions else None,
                                "issues_found": ed_issues if ed_issues else None,
                                "next_steps": ed_next if ed_next else None,
                                "tags": [t.strip() for t in ed_tags.split(",") if t.strip()],
                                "entry_type": ed_type
                            }
                            r_put = requests.put(f"{API_URL}/notebook/{selected_entry['entry_id']}", json=payload_ed)
                            if r_put.status_code == 200:
                                st.success("Revision written to platform ledger!")
                                st.rerun()
                            else:
                                st.error(f"Failed to write revision: {r_put.text}")
            else:
                st.info("Select or create a notebook entry to begin review.")

    with subtab2:
        st.markdown("#### **Research Wikis & Standard Operating Procedures (SOPs)**")
        col_w1, col_w2 = st.columns([1, 2])
        
        with col_w1:
            st.markdown("##### **Select Wiki Page**")
            try:
                r_wiki = requests.get(f"{API_URL}/wiki")
                if r_wiki.status_code == 200:
                    wiki_pages = r_wiki.json()
                    if wiki_pages:
                        wiki_titles = [f"{w['title']} [{w['wiki_type']}]" for w in wiki_pages]
                        selected_w_title = st.radio("Choose Wiki Page", wiki_titles)
                        selected_wiki = wiki_pages[wiki_titles.index(selected_w_title)]
                    else:
                        st.info("No wiki pages registered.")
                        selected_wiki = None
                else:
                    st.error("Failed to load wiki registry.")
                    selected_wiki = None
            except Exception as exc:
                st.error(f"Error: {exc}")
                selected_wiki = None
                
            st.markdown("---")
            # Create wiki form
            with st.expander("🆕 Create Wiki SOP Page"):
                with st.form("create_wiki_form"):
                    w_title = st.text_input("Wiki Title", "")
                    w_slug = st.text_input("Slug URL path", "")
                    w_type = st.selectbox("Wiki Type", ["SOP", "Installation", "Troubleshooting", "Experiment"])
                    w_project = st.selectbox("Linked Project (Optional)", ["None", "SPACE", "EyeMT", "KRAS"])
                    w_content = st.text_area("Markdown SOP Body", "")
                    
                    submit_w = st.form_submit_button("Record Wiki Document")
                    if submit_w:
                        payload_w = {
                            "title": w_title,
                            "slug": w_slug,
                            "content": w_content,
                            "wiki_type": w_type,
                            "project_code": w_project if w_project != "None" else None
                        }
                        r_wp = requests.post(f"{API_URL}/wiki", json=payload_w)
                        if r_wp.status_code == 200:
                            st.success("Wiki SOP compiled successfully!")
                            st.rerun()
                        else:
                            st.error(f"Failed to save wiki SOP: {r_wp.text}")

        with col_w2:
            if selected_wiki:
                st.markdown(f"### **{selected_wiki['title']}**")
                st.caption(f"Modality type: `{selected_wiki['wiki_type']}` | Project mapping: `{selected_wiki['project_code'] or 'global'}` | Author: {selected_wiki['author_name']} | Updated: {selected_wiki['updated_at']}")
                st.markdown("---")
                st.markdown(selected_wiki["content"])
                st.markdown("---")
                
                # Edit wiki form
                with st.expander("📝 Edit Wiki page content (Saves revision history)"):
                    with st.form("edit_wiki_form"):
                        ed_w_title = st.text_input("Wiki Title", selected_wiki["title"])
                        w_types = ["SOP", "Installation", "Troubleshooting", "Experiment"]
                        curr_w_type = selected_wiki.get("wiki_type", "SOP")
                        if curr_w_type not in w_types:
                            w_types.append(curr_w_type)
                        ed_w_type = st.selectbox("Wiki Type", w_types, index=w_types.index(curr_w_type))
                        ed_w_content = st.text_area("Markdown SOP Body", selected_wiki["content"])
                        
                        submit_ed_w = st.form_submit_button("Save SOP Changes")
                        if submit_ed_w:
                            payload_ed_w = {
                                "title": ed_w_title,
                                "content": ed_w_content,
                                "wiki_type": ed_w_type
                            }
                            r_put_w = requests.put(f"{API_URL}/wiki/{selected_wiki['wiki_id']}", json=payload_ed_w)
                            if r_put_w.status_code == 200:
                                st.success("Wiki page revisions updated!")
                                st.rerun()
                            else:
                                st.error(f"Failed to update wiki page: {r_put_w.text}")
            else:
                st.info("Select a Wiki Page or create one to proceed.")

# --- TAB 3: RESEARCH DECISIONS ---
with tabs[3]:
    st.markdown("### ⚖️ **Lab Research Decisions Registry & Audit Trail**")
    
    col_d1, col_d2 = st.columns([2, 1])
    
    with col_d1:
        st.markdown("##### **Logged Research Decisions**")
        try:
            r_dec = requests.get(f"{API_URL}/decisions")
            if r_dec.status_code == 200:
                decisions = r_dec.json()
                if decisions:
                    for d in decisions:
                        st.markdown(f"""
                        <div class="audit-log-item" style="border-left: 5px solid #34d399;">
                            <h5 style="color:#58a6ff; margin:0;">🎯 {d['title']}</h5>
                            <div style="font-size:0.8rem; color:#8b949e; margin-bottom:0.4rem;">
                                Project: <b>{d['project_code']}</b> | Decided By: {d['decider_name']} | Date: {d['decision_date']}
                            </div>
                            <div style="font-size:0.95rem; margin-bottom:0.3rem;"><b>Decision Details:</b> {d['decision_details']}</div>
                            <div style="font-size:0.9rem; color:#c9d1d9;"><i>Rationale:</i> {d['rationale']}</div>
                            {f"<div style='font-size:0.85rem; color:#8b949e; margin-top:0.3rem;'><i>Alternatives Considered:</i> {d['alternatives_considered']}</div>" if d['alternatives_considered'] else ""}
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No decisions logged in the registry.")
            else:
                st.error("Failed to load decisions registry.")
        except Exception as exc:
            st.error(f"Error fetching decisions: {exc}")
            
    with col_d2:
        st.markdown("##### **Log a New Research Decision**")
        st.caption("Decisions are recorded in the registry and automatically appended to the Living Notebook!")
        
        with st.form("create_decision_form"):
            d_proj = st.selectbox("Project Code Context", ["SPACE", "EyeMT", "KRAS"])
            d_title = st.text_input("Decision Title", placeholder="e.g. Set Mesmer Whole-Cell Segmentation as standard")
            d_details = st.text_area("Decision Details", placeholder="What was decided...")
            d_rationale = st.text_area("Rationale & Logic", placeholder="Why this path was chosen...")
            d_alt = st.text_area("Alternatives Considered (Optional)", placeholder="What else we thought of...")
            
            submit_d = st.form_submit_button("Record Formal Decision", type="primary")
            if submit_d:
                payload_d = {
                    "project_code": d_proj,
                    "title": d_title,
                    "decision_details": d_details,
                    "rationale": d_rationale,
                    "alternatives_considered": d_alt if d_alt else None,
                    "decided_by_username": "debdeba"
                }
                r_post_d = requests.post(f"{API_URL}/decisions", json=payload_d)
                if r_post_d.status_code == 200:
                    st.success("Decision recorded and notebook trail created!")
                    st.rerun()
                else:
                    st.error(f"Failed to record decision: {r_post_d.text}")

# --- TAB 4: TASKS PLANNER ---
with tabs[4]:
    st.markdown("### ✅ **Actionable Lab Tasks Planner & Progress Checklist**")
    
    col_t1, col_t2 = st.columns([2, 1])
    
    with col_t1:
        st.markdown("##### **Active Lab Checklist**")
        try:
            r_tasks = requests.get(f"{API_URL}/tasks")
            if r_tasks.status_code == 200:
                tasks = r_tasks.json()
                if tasks:
                    # Render as dataframe with action buttons
                    df_tasks = pd.DataFrame(tasks)
                    st.dataframe(df_tasks, use_container_width=True)
                    
                    st.markdown("##### **Quick Update Task Status/Priority**")
                    with st.form("update_task_form"):
                        task_opts = {f"{t['title']} (Project {t['project_code']})": t for t in tasks}
                        target_task_title = st.selectbox("Select Task to Update", list(task_opts.keys()))
                        target_task = task_opts[target_task_title]
                        
                        t_statuses = ["todo", "in_progress", "completed"]
                        curr_t_status = target_task.get("status", "todo")
                        if curr_t_status not in t_statuses:
                            t_statuses.append(curr_t_status)
                        up_t_status = st.selectbox("Status", t_statuses, index=t_statuses.index(curr_t_status))

                        t_priorities = ["low", "medium", "high", "critical"]
                        curr_t_priority = target_task.get("priority", "medium")
                        if curr_t_priority not in t_priorities:
                            t_priorities.append(curr_t_priority)
                        up_t_priority = st.selectbox("Priority", t_priorities, index=t_priorities.index(curr_t_priority))
                        up_t_due = st.date_input("Due Date", datetime.strptime(target_task["due_date"], "%Y-%m-%d").date() if target_task["due_date"] else date.today())
                        
                        submit_up_t = st.form_submit_button("Commit Task Updates & Log")
                        if submit_up_t:
                            payload_up_t = {
                                "title": target_task["title"],
                                "description": target_task["description"],
                                "status": up_t_status,
                                "priority": up_t_priority,
                                "due_date": str(up_t_due)
                            }
                            r_put_t = requests.put(f"{API_URL}/tasks/{target_task['task_id']}", json=payload_up_t)
                            if r_put_t.status_code == 200:
                                st.success("Task details modified and logged in notebook trail!")
                                st.rerun()
                            else:
                                st.error(f"Failed to update task: {r_put_t.text}")
                else:
                    st.info("No active tasks found in the planner.")
            else:
                st.error("Failed to load tasks checklist.")
        except Exception as exc:
            st.error(f"Error loading tasks: {exc}")
            
    with col_t2:
        st.markdown("##### **Assign a New Task**")
        st.caption("Tasks are assigned to team members and log notebook audit entries automatically.")
        
        with st.form("create_task_form"):
            t_proj = st.selectbox("Linked Project", ["SPACE", "EyeMT", "KRAS"])
            t_sample = st.text_input("Sample Code (Optional)", "")
            t_title = st.text_input("Task Title", placeholder="e.g. Check stitch quality batch 3")
            t_desc = st.text_area("Task Description", placeholder="What needs to be done...")
            t_priority = st.selectbox("Task Priority", ["low", "medium", "high", "critical"], index=1)
            t_due = st.date_input("Due Date Target", date.today())
            
            submit_t = st.form_submit_button("Create Task & Log Entry", type="primary")
            if submit_t:
                payload_t = {
                    "project_code": t_proj,
                    "sample_code": t_sample if t_sample else None,
                    "title": t_title,
                    "description": t_desc if t_desc else None,
                    "status": "todo",
                    "priority": t_priority,
                    "due_date": str(t_due)
                }
                r_post_t = requests.post(f"{API_URL}/tasks", json=payload_t)
                if r_post_t.status_code == 200:
                    st.success("Task assigned successfully!")
                    st.rerun()
                else:
                    st.error(f"Failed to create task: {r_post_t.text}")

# --- TAB 5: CHAT COPILOT ---
with tabs[5]:
    st.markdown("#### Ask research questions about protocols, stitching, segmentation, and sample features:")
    
    # Initialize message history
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    # Pre-canned prompt buttons
    col1, col2, col3 = st.columns(3)
    p1 = col1.button("📌 How does the tCyCIF pipeline run?")
    p2 = col2.button("Tell me about the KRAS project notebooks.")
    p3 = col3.button("Show database sample counts.")
    
    clicked_question = None
    if p1:
        clicked_question = "What is the end-to-end tCyCIF image-processing pipeline?"
    elif p2:
        clicked_question = "Which scripts are used for KRAS gating, thresholding, and spatial count?"
    elif p3:
        clicked_question = "How many samples and patients are registered in the database?"
        
    # Render message history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander("References"):
                    for i, src in enumerate(msg["sources"]):
                        st.markdown(f"**[{i+1}] {src['title']}** (Score: {src['score']:.3f})")
                        st.code(src["text_preview"])

    # Handle input
    input_question = st.chat_input("Enter your research question here...")
    
    active_question = clicked_question or input_question
    
    if active_question:
        # Save user message
        st.session_state.messages.append({"role": "user", "content": active_question})
        with st.chat_message("user"):
            st.markdown(active_question)
            
        # Get assistant response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing registries and vector context..."):
                payload = {
                    "question": active_question,
                    "project_codes": project_codes,
                    "mode": "deidentified_research" if "deidentified" in mode else "documentation_only",
                    "llm_provider": llm_provider,
                    "llm_model": llm_model,
                    "llm_api_key": llm_api_key if llm_api_key else None,
                    "llm_base_url": llm_base_url if llm_base_url else None
                }
                try:
                    r = requests.post(f"{API_URL}/ask", json=payload, timeout=30)
                    r.raise_for_status()
                    res = r.json()
                    
                    st.markdown(res["answer"])
                    
                    if res.get("limitations"):
                        for limit in res["limitations"]:
                            st.warning(f"⚠️ {limit}")
                            
                    if res.get("sources"):
                        with st.expander("References"):
                            for i, src in enumerate(res["sources"]):
                                st.markdown(f"**[{i+1}] {src['title']}** (Score: {src['score']:.3f})")
                                st.code(src["text_preview"])
                                
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": res["answer"],
                        "sources": res.get("sources", [])
                    })
                except Exception as exc:
                    st.error(f"API request failed: {exc}")

# --- TAB 6: INSTALL SOFTWARE ---
with tabs[6]:
    st.markdown("#### Package Installation Recipe Generator")
    st.caption("Generate step-by-step verified terminal commands for tool setups")
    
    col_inst1, col_inst2 = st.columns(2)
    selected_tool = col_inst1.selectbox("Select Software Package", ["napari", "cylinter", "stardist"])
    selected_os = col_inst2.selectbox("Target OS Platform", ["linux", "macos", "windows"])
    
    if st.button("Generate Installation Recipe", type="primary"):
        with st.spinner("Fetching installation scripts..."):
            payload = {"tool_name": selected_tool, "os_platform": selected_os}
            try:
                r = requests.post(f"{API_URL}/install_guide", json=payload)
                r.raise_for_status()
                res = r.json()
                
                st.success(f"Successfully generated recipe for {selected_tool.upper()} on {selected_os.upper()}!")
                
                # Render script
                st.markdown("##### 💻 Installation Commands")
                st.code(res["script"], language="bash" if selected_os != "windows" else "powershell")
                
                # Expected Output / Verification
                st.markdown(f"**🔍 Verification Command:** `{res['verification']}`")
                st.markdown(f"**📈 Expected Outcome:** {res['expected_output']}")
                
                # Troubleshooting
                st.warning(f"⚠️ **Common Caveats & Recovery:** {res['troubleshooting']}")
            except Exception as exc:
                st.error(f"Failed to generate installation guide: {exc}")

# --- TAB 7: RUN PIPELINE ---
with tabs[7]:
    st.markdown("#### Image Processing Pipeline stage assistant")
    st.caption("Detailed parameters and staging layouts for microscopy pipelines")
    
    selected_stage = st.selectbox("Pipeline Phase", ["basic", "ashlar", "mesmer"])
    
    st.markdown("---")
    
    if selected_stage == "basic":
        st.markdown("### Stage 1: BaSiC (Illumination correction)")
        st.markdown("**Expected Input Files:** Raw TIFF single-tile cycles.")
        st.markdown("**Expected Output Files:** Flatfield/darkfield correction matrices.")
        st.markdown("**Run Command Template:**")
        st.code("python scripts/run_basic.py --input-dir /path/to/raw --output-dir /path/to/basic_calib", language="bash")
        st.info("💡 **Validation:** Ensure matrices don't contain NaN or zero values. Visual validation inside ImageJ/Napari.")
    elif selected_stage == "ashlar":
        st.markdown("### Stage 2: Ashlar (Stitching & Registration)")
        st.markdown("**Expected Input Files:** Raw cycle files + BaSiC calibration matrices.")
        st.markdown("**Expected Output Files:** Seamless pyramids OME-TIFF mosaic.")
        st.markdown("**Run Command Template:**")
        st.code("ashlar \"/path/to/tiles/*.tif\" --output /path/to/stitched.tif --ffp flatfield.tif --dfp darkfield.tif --align-channel 0", language="bash")
        st.info("💡 **Validation:** Inspect overlap seams inside Napari visual quality check panels.")
    elif selected_stage == "mesmer":
        st.markdown("### Stage 3: Mesmer (Nuclear & Membrane Segmentation)")
        st.markdown("**Expected Input Files:** Stitched OME-TIFF files.")
        st.markdown("**Expected Output Files:** Cell border boundary integer masks.")
        st.markdown("**Run Command Template:**")
        st.code("python segment.py --image /path/to/stitched.tif --nuclear-channel 0 --membrane-channel 1 --output /path/to/mask.tif", language="bash")
        st.info("💡 **Validation:** Check mask overlap matching rates. Inspect for segmented area metrics outliers.")

# --- TAB 8: GENERATE LUMI JOB ---
with tabs[8]:
    st.markdown("#### Slurm Job Script Builder for LUMI / HPC")
    st.caption("Configure resources and generate a cluster-ready batch Slurm script")
    
    col_l1, col_l2 = st.columns(2)
    job_name = col_l1.text_input("Slurm Job Name", "lumi_mesmer_segmentation")
    project_account = col_l2.text_input("Billing Project Account", "project_462001415")
    
    col_l3, col_l4 = st.columns(2)
    cpus = col_l3.slider("CPUs Per Task", 4, 32, 8)
    memory = col_l4.text_input("Memory allocation", "32G")
    
    col_l5, col_l6 = st.columns(2)
    walltime = col_l5.text_input("Walltime limit", "02:00:00")
    use_gpu = col_l6.checkbox("Require GPU Allocation", value=True)
    
    input_path = st.text_input("Input directory path (scratch)", "/scratch/project_462001415/image_processing/ada/stitched")
    container_sif = st.text_input("Apptainer SIF container path", "/scratch/project_462001415/containers/deepcell-mesmer_latest.sif")
    exec_command = st.text_input("Execution command", "python /scratch/project_462001415/scripts/segment.py --compartment cell")
    
    if st.button("Generate Slurm Script", type="primary"):
        payload = {
            "job_name": job_name,
            "project_account": project_account,
            "use_gpu": use_gpu,
            "cpus": cpus,
            "memory": memory,
            "walltime": walltime,
            "scratch_path": "/scratch/" + project_account,
            "log_dir": "logs/pipeline",
            "input_path": input_path,
            "container_sif": container_sif,
            "execution_command": exec_command
        }
        try:
            r = requests.post(f"{API_URL}/lumi_job", json=payload)
            r.raise_for_status()
            res = r.json()
            
            st.success("Successfully compiled Slurm file! Checked with static safety checks.")
            st.code(res["script"], language="bash")
            st.info("💡 **HPC Warning:** Always write scripts to scratch or project partitions. Avoid placing datasets in home directory scopes.")
        except Exception as exc:
            st.error(f"Failed to generate Slurm script: {exc}")

# --- TAB 9: ENV CHECKER ---
with tabs[9]:
    st.markdown("#### Workstation & HPC Environment Checker")
    st.caption("Run dynamic localized verification tests directly on the host server")
    
    checker_choice = st.selectbox("Verify Environment Parameter", [
        ("Python Environment", "python_env"),
        ("NVIDIA GPU & CUDA Availability", "gpu"),
        ("Napari Visuals & Display Server", "napari"),
        ("Docker Client & Daemon Permissions", "docker"),
        ("LUMI Module loads & /scratch", "lumi_modules"),
        ("Cylinter Input manifest metadata files", "cylinter_inputs"),
        ("Workspace structure compliance", "project_structure")
    ], format_func=lambda x: x[0])
    
    if st.button("Execute Health Check", type="primary"):
        with st.spinner("Executing health tests..."):
            payload = {"checker_name": checker_choice[1]}
            try:
                r = requests.post(f"{API_URL}/run_checker", json=payload)
                r.raise_for_status()
                res = r.json()
                
                # Check status
                if res["status"] == "PASS":
                    st.success("💚 Environment Check Passed!")
                else:
                    st.warning("💛 Warnings/Failures Detected in configurations!")
                    
                st.markdown("##### 📜 Health Logs output")
                st.code(res["stdout"] + "\n" + res["stderr"], language="bash")
            except Exception as exc:
                st.error(f"Failed to run environment checker: {exc}")

# --- TAB 10: TROUBLESHOOT ERROR ---
with tabs[10]:
    st.markdown("#### Troubleshooting log parser Agent")
    st.caption("Paste execution errors, Python tracebacks, or Slurm logs to diagnose root cause and exact recovery steps")
    
    log_input = st.text_area("Paste Traceback Logs Here", placeholder="Error: PyQt5.QtCore platform plugin load failed...\nOr Slurm exit code 137...")
    
    if st.button("Diagnose Error Log", type="primary") and log_input:
        with st.spinner("Analyzing error structures..."):
            payload = {"log_text": log_input}
            try:
                r = requests.post(f"{API_URL}/parse_log", json=payload)
                r.raise_for_status()
                res = r.json()
                
                st.success("Traceback evaluated successfully!")
                
                st.markdown("### 🩺 Diagnostic Report")
                st.markdown(f"**Likely Root Cause:** {res['cause']}")
                st.markdown(f"**🛠️ Exact Fix Instructions:**")
                st.code(res["recommended_fix"], language="bash")
                st.markdown(f"**💡 Long-term Prevention:** {res['prevention']}")
            except Exception as exc:
                st.error(f"Log parsing request failed: {exc}")


# --- TAB 11: KNOWLEDGE ONBOARDING WIZARD ---
with tabs[11]:
    st.markdown("### ✨ Laboratory Knowledge Onboarding Wizard")
    st.caption("Systematic entry point to ingest projects, documents, staining protocols, and check off milestone compliance checklists.")

    w_subtab1, w_subtab2, w_subtab3 = st.tabs([
        "📁 Onboard New Project",
        "📄 Document Ingestion Pipeline",
        "✅ Project Checklist Tracker"
    ])

    with w_subtab1:
        st.markdown("##### 1. Register Core Project Information")
        with st.form("onboard_project_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_code = st.text_input("Project Code (e.g. Myelonets, HaikalaCollab)", placeholder="Myelonets")
                new_name = st.text_input("Full Project Title", placeholder="3D spatial profiling of myeloid cell networks")
                new_lead = st.text_input("Project Lead Name", placeholder="Pablo Siliceo")
            with col2:
                new_focus = st.text_input("Disease Focus", value="Ovarian Cancer")
                new_priority = st.selectbox("Project Priority", ["low", "medium", "high"])
                new_ethics = st.text_input("Ethics Board Reference", value="ETHICS-2026-Farkki")

            new_desc = st.text_area("Short Scientific Question / Description", placeholder="Characterizing myeloid cell subtypes and their functional heterogeneity in 3D ovarian tumor TME...")
            new_summary = st.text_area("Detailed Project Summary & Status", placeholder="Write current status, blockers, and next actions here...")

            submit_proj = st.form_submit_button("Create Project & Seed Checklists", type="primary")

            if submit_proj:
                if not new_code or not new_name or not new_lead:
                    st.error("Please fill in all required fields (Code, Title, Lead).")
                else:
                    payload = {
                        "project_code": new_code.strip(),
                        "project_name": new_name.strip(),
                        "project_lead": new_lead.strip(),
                        "short_description": new_desc.strip(),
                        "disease_focus": new_focus.strip(),
                        "priority": new_priority,
                        "ethics_approval_reference": new_ethics.strip(),
                        "project_summary": new_summary.strip()
                    }
                    try:
                        r = requests.post(f"{API_URL}/projects", json=payload)
                        r.raise_for_status()
                        st.success(f"🎉 Project '{new_code}' successfully onboarded! Milestone checklists initialized.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to onboard project: {e}")

    with w_subtab2:
        st.markdown("##### 2. File & Script Upload Ingestion Pipeline")
        st.caption("Supported formats: PDF, DOCX, TXT, MD, HTML, Jupyter Notebooks (.ipynb), R/Python scripts, YAML/JSON, and CSV.")

        # Get projects list
        try:
            p_resp = requests.get(f"{API_URL}/projects")
            p_resp.raise_for_status()
            project_list = [p["project_code"] for p in p_resp.json()]
        except Exception:
            project_list = ["SPACE", "EyeMT", "KRAS"]

        assoc_proj = st.selectbox("Associate with Project", options=project_list)
        doc_tags = st.text_input("Tags (comma separated)", placeholder="protocol, staining, mesmer-config")
        
        col_s, col_p = st.columns(2)
        with col_s:
            soft_assoc = st.multiselect("Software Associations", ["napari", "Cylinter", "Mesmer", "StarDist", "Ashlar", "BaSiC", "Docker", "Conda", "Apptainer"])
        with col_p:
            pipe_assoc = st.multiselect("Pipeline Stage Associations", ["illumination_correction", "stitching", "segmentation", "quantification", "cell_calling", "spatial_analysis"])

        uploaded_file = st.file_uploader("Upload File to Ingestion Pipeline", type=["pdf", "docx", "txt", "md", "html", "ipynb", "py", "r", "yaml", "yml", "json", "csv"])

        if uploaded_file is not None:
            filename = uploaded_file.name
            file_size = uploaded_file.size
            file_ext = filename.split(".")[-1].lower()

            st.info(f"File uploaded: `{filename}` ({file_size} bytes)")

            # Parse content
            extracted_text = ""
            metadata_dict = {"file_size": file_size, "ingested_at": datetime.now().isoformat()}

            try:
                content_bytes = uploaded_file.read()
                if file_ext in ["txt", "md", "py", "r", "yaml", "yml", "json", "csv", "html"]:
                    extracted_text = content_bytes.decode("utf-8")
                elif file_ext == "ipynb":
                    import json
                    notebook_data = json.loads(content_bytes.decode("utf-8"))
                    cells_text = []
                    for cell in notebook_data.get("cells", []):
                        cell_type = cell.get("cell_type", "")
                        source = cell.get("source", [])
                        if isinstance(source, list):
                            source = "".join(source)
                        cells_text.append(f"[{cell_type.upper()}]\n{source}")
                    extracted_text = "\n\n".join(cells_text)
                else:
                    # PDF/DOCX Mock parsing fallback
                    extracted_text = f"[Ingested Binary / Document File: {filename}]\nThis file was processed through the CS-ROP onboarding pipeline. Structural information, layout and metadata extracted."
                    metadata_dict["mock_parser"] = True

                # Show preview
                st.text_area("Extracted Text Preview", value=extracted_text[:1000] + "\n...", height=200, disabled=True)

                if st.button("Confirm Ingestion to Database", type="primary"):
                    tags_list = [t.strip() for t in doc_tags.split(",") if t.strip()]
                    payload = {
                        "filename": filename,
                        "file_type": file_ext,
                        "extracted_text": extracted_text,
                        "tags": tags_list,
                        "project_code": assoc_proj,
                        "software_associations": soft_assoc,
                        "pipeline_stage_associations": pipe_assoc,
                        "metadata_dict": metadata_dict
                    }
                    r = requests.post(f"{API_URL}/ingest-document", json=payload)
                    r.raise_for_status()
                    st.success(f"🎉 Document '{filename}' successfully ingested and logged into notebook records!")
            except Exception as e:
                st.error(f"Error parsing file: {e}")

    with w_subtab3:
        st.markdown("##### 3. Project Milestone Compliance Checklists")
        st.caption("Select a project to review and toggle onboarding milestones.")

        sel_chk_proj = st.selectbox("Project Checklist Scope", options=project_list, key="chk_proj_scope")

        try:
            r = requests.get(f"{API_URL}/checklists/{sel_chk_proj}")
            r.raise_for_status()
            checklists = r.json()
        except Exception as e:
            checklists = []
            st.error(f"Failed to fetch checklists: {e}")

        if checklists:
            # Group by category
            categories = list(set([c["category"] for c in checklists]))
            categories.sort()

            for cat in categories:
                st.markdown(f"**{cat.upper()} Checklists**")
                cat_items = [c for c in checklists if c["category"] == cat]
                for item in cat_items:
                    checked = (item["status"] == "completed")
                    chk_key = f"chk_{item['checklist_id']}"
                    
                    col_chk, col_info = st.columns([0.1, 0.9])
                    with col_chk:
                        is_checked = st.checkbox("", value=checked, key=chk_key)
                    with col_info:
                        st.markdown(f"**{item['item_name']}** — {item['description']}")
                        if item["checked_at"]:
                            st.caption(f"✓ Checked off on {item['checked_at'][:10]}")

                    # Toggle status if modified
                    if is_checked != checked:
                        new_status = 'completed' if is_checked else 'pending'
                        try:
                            t_r = requests.post(f"{API_URL}/checklists/toggle", json={
                                "checklist_id": item["checklist_id"],
                                "status": new_status,
                                "username": "debdeba"
                            })
                            t_r.raise_for_status()
                            st.success(f"Checklist item status updated to {new_status}!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to update checklist item: {e}")
        else:
            st.info("No checklist items configured for this project.")

# --- TAB 12: AI MODEL REGISTRY ---
with tabs[12]:
    st.markdown("### 🤖 Ovarian Cancer & Spatial Biology AI Model Registry")
    st.caption("Registry of recommended LLMs, embeddings, computer vision, segmentation, and downstream spatial bioinformatics algorithms.")

    try:
        mr_r = requests.get(f"{API_URL}/ai-models")
        mr_r.raise_for_status()
        all_models = mr_r.json()
    except Exception as e:
        all_models = []
        st.error(f"Failed to load AI model registry: {e}")

    # Search bar & Filters
    col_search, col_filter = st.columns([0.6, 0.4])
    with col_search:
        m_query = st.text_input("Search Models by name or keyword...", placeholder="Mesmer, Llama, BiomedCLIP...")
    with col_filter:
        m_types = ["All"] + list(set([m["model_type"] for m in all_models]))
        sel_type = st.selectbox("Filter by Category", options=m_types)

    # Filter logic
    filtered_models = all_models
    if m_query:
        filtered_models = [m for m in filtered_models if m_query.lower() in m["name"].lower() or m_query.lower() in m["use_cases"].lower()]
    if sel_type != "All":
        filtered_models = [m for m in filtered_models if m["model_type"] == sel_type]

    for model in filtered_models:
        with st.expander(f"⚙️ {model['name']} — {model['model_type'].replace('_', ' ').upper()}", expanded=False):
            st.markdown(f"**🔍 Use Cases:** {model['use_cases']}")
            st.markdown(f"**📦 Model Source:** {model['source']} | **📜 License:** {model['license']}")
            st.markdown(f"**⚡ GPU Specs:** {model['gpu_requirements']} | **🧠 Memory:** {model['memory_requirements']}")
            st.markdown(f"**🛠️ Installation & Setup:**")
            st.code(model["installation_instructions"], language="bash")
            
            c_str, c_weak = st.columns(2)
            with c_str:
                st.markdown(f"💚 **Strengths:** {model['strengths']}")
            with c_weak:
                st.markdown(f"💔 **Weaknesses:** {model['weaknesses']}")

# --- TAB 13: INFRASTRUCTURE REGISTRY ---
with tabs[13]:
    st.markdown("### 🏢 Laboratory Compute & Storage Infrastructure Registry")
    st.caption("Registry of workstations, HPC accounts (LUMI), database connections, and Hostinger object storage buckets.")

    try:
        infra_r = requests.get(f"{API_URL}/infrastructure")
        infra_r.raise_for_status()
        all_infra = infra_r.json()
    except Exception as e:
        all_infra = []
        st.error(f"Failed to load infrastructure registry: {e}")

    for resource in all_infra:
        with st.expander(f"🖥️ {resource['name']} — {resource['resource_type'].upper()}", expanded=False):
            st.markdown(f"**🌐 Operating System:** {resource['operating_system']}")
            st.markdown(f"**🔌 CPU:** {resource['cpu_specs']} | **⚡ GPU:** {resource['gpu_specs']} | **🧠 RAM:** {resource['ram_specs']}")
            st.markdown(f"**💾 Storage Layout:** {resource['storage_specs']}")
            st.markdown(f"**📦 Installed Software:** {', '.join(resource['installed_software']) or 'None'}")
            st.markdown(f"**🔑 Access Notes:** {resource['access_notes']}")
            st.markdown(f"**🔧 Maintenance Schedule:** {resource['maintenance_notes']}")

# --- TAB 14: GAP ANALYSIS & READINESS ---
with tabs[14]:
    st.markdown("### 📊 Operational Gap Analysis & Lab Readiness Audit")
    st.caption("Quantitative audit of missing datasets, unlinked document configurations, and checklist completion metrics.")

    try:
        gap_r = requests.get(f"{API_URL}/gap-analysis")
        gap_r.raise_for_status()
        gap_data = gap_r.json()
    except Exception as e:
        gap_data = {}
        st.error(f"Failed to fetch gap analysis metrics: {e}")

    if gap_data:
        # Score header
        col_s1, col_s2 = st.columns([0.4, 0.6])
        with col_s1:
            st.markdown("##### 🧬 Overall Lab Onboarding Readiness Score")
            r_score = gap_data["readiness_score"]
            st.metric(label="Readiness Level", value=f"{r_score}%", delta=f"{r_score - 100}% to Complete")
            st.progress(r_score / 100.0)
        with col_s2:
            st.markdown("##### 📦 Inventory Summaries")
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                st.metric("AI Models Registered", gap_data["ai_models_count"])
                st.metric("Compute Resources", gap_data["infrastructure_count"])
            with col_m2:
                st.metric("Publications Linked", gap_data["publications_count"])
                st.metric("Ingested Documents", gap_data["documents_count"])
            with col_m3:
                st.metric("Cataloged Folders", gap_data["folders_count"])
                st.metric("Cataloged Datasets", gap_data["datasets_count"])

        # Project Breakdowns
        st.markdown("---")
        st.markdown("##### 📁 Readiness Score per Project")
        p_df = pd.DataFrame(gap_data["project_breakdown"])
        if not p_df.empty:
            st.dataframe(p_df, column_config={
                "project_code": "Project Code",
                "project_name": "Project Name",
                "total_items": "Total Checklists",
                "completed_items": "Completed Milestones",
                "score": st.column_config.ProgressColumn("Readiness Score (%)", format="%f%%", min_value=0, max_value=100)
            }, use_container_width=True)

        # Gap list
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("##### ⚠️ Missing Critical Information (Pending Checklist Items)")
            missing_items = gap_data["missing_checklist_items"]
            if missing_items:
                for idx, item in enumerate(missing_items):
                    st.warning(f"**{item['project_code']}**: Pending '{item['item_name']}' under category *{item['category']}*")
            else:
                st.success("All checklists completed for all active projects.")

        with col_g2:
            st.markdown("##### 💡 Action Plan & Onboarding Recommendations")
            for rec in gap_data["recommendations"]:
                st.markdown(f"- {rec}")

        # Toggles for Architecture and Storage Planning
        st.markdown("---")
        st.markdown("### 🗺️ Storage Layout & Deployment Strategy Plan")
        
        with st.expander("☁️ Hostinger Production Deployment Blueprint", expanded=False):
            st.markdown("""
            ### Production deployment architecture for shared scientific platforms
            
            ```mermaid
            graph TD
                A[Streamlit Web UI] -->|Direct API| B[FastAPI Backend Services]
                B -->|SQL Queries| C[(PostgreSQL Metadata Registry)]
                B -->|Vector Search| D[(Qdrant Search Index)]
                B -->|File Fetch| E[Hostinger Object Storage MinIO]
                E -->|OME-TIFF slides| F[File System / HPC Mount]
            ```
            
            1. **Metadata Database**: PostgreSQL hosted on a Linux VPS. Needs `pgvector` enabled for indexing document chunks.
            2. **Object Storage**: S3-compatible cloud bucket (MinIO) to handle high-resolution stitched TIFF slides and segmentation cell masks.
            3. **Vector Index**: Qdrant running in a dockerized container on VPS to handle real-time SOP and protocol lookups.
            4. **Computing Compute Pipeline**: Compute nodes (LUMI or local GPU cluster) map to Postgres for status updates on Snakemake pipeline triggers.
            """)

        with st.expander("💾 Future Storage Directory Design Layout", expanded=False):
            st.markdown("""
            ### Scalable lab storage division mapping
            
            - `/data/metadata/`: Core clinical tables, patients, specimens, and notebook entry logs (System of record).
            - `/data/documents/`: Ingested wet-lab protocols, SOPs, and troubleshooting guides (.pdf, .docx, .md).
            - `/data/embeddings/`: Vector indices for parsed document chunks and embeddings.
            - `/data/raw_images/`: Raw multiplexed slides (OME-TIFF format) stored in read-only object storage.
            - `/data/segmented_masks/`: StarDist/Mesmer output masks (.tiff).
            - `/data/quantification_tables/`: Decoded single-cell expression tables (.csv, .h5ad) for spatial statistics analysis.
            - `/data/logs/`: Snakemake workflow traces and Slurm compute job histories.
            - `/data/generated_reports/`: PDF gap audits and readiness summaries.
            """)

