import re
import os
import json
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from app_skeleton.api.llm_client import LLMClient

class PrivacyGuardrailAgent:
    """Detects and redacts potential direct patient identifiers (PII) from user queries."""
    
    # Regular expressions for common identifiers
    PATTERNS = {
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "mrn": r"\b(mrn|id|record)\s*#?\s*\d{6,10}\b",
        "dob": r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone": r"\b\+?\d{1,3}?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
    }

    @classmethod
    def audit_query(cls, text: str) -> Dict[str, Any]:
        redacted = text
        violations = []
        
        for name, pattern in cls.PATTERNS.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                violations.append(name.upper())
                redacted = re.sub(pattern, f"[REDACTED_{name.upper()}]", redacted)
                
        # Simple name lookup (heuristic for demo)
        name_matches = re.findall(r"\b(patient|subject)\s+([A-Z][a-z]+)\s+([A-Z][a-z]+)\b", text)
        if name_matches:
            violations.append("NAME")
            redacted = re.sub(r"\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b", "[REDACTED_NAME]", redacted)

        return {
            "is_safe": len(violations) == 0,
            "violations": violations,
            "redacted_text": redacted
        }


class RAGAgent:
    """Queries Qdrant collections to retrieve relevant documentation and script chunks."""
    
    def __init__(self, qdrant_client: QdrantClient, llm_client: LLMClient):
        self.qdrant = qdrant_client
        self.llm = llm_client

    def retrieve(self, query: str, project_codes: List[str], limit: int = 4) -> List[Dict[str, Any]]:
        query_vec = self.llm.embed(query)
        sources = []

        # Project-specific filter for scripts
        script_filter = None
        if project_codes:
            script_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="project_code",
                        match=models.MatchAny(any=project_codes)
                    )
                ]
            )

        # 1. Query doc_chunks (general documentation is queried without strict project exclusion)
        try:
            doc_res = self.qdrant.query_points(
                collection_name="doc_chunks",
                query=query_vec,
                using="text",
                limit=limit
            )
            for point in doc_res.points:
                sources.append({
                    "title": point.payload.get("title", "Doc Chunk"),
                    "source_type": "documentation",
                    "source_uuid": point.payload.get("document_id", "unknown"),
                    "chunk_id": point.payload.get("chunk_id"),
                    "text_preview": point.payload.get("text_preview", ""),
                    "score": point.score
                })
        except Exception as exc:
            print(f"RAGAgent: Error querying doc_chunks: {exc}")

        # 2. Query script_chunks (scripts are filtered strictly to selected projects)
        try:
            script_res = self.qdrant.query_points(
                collection_name="script_chunks",
                query=query_vec,
                using="text",
                query_filter=script_filter,
                limit=limit
            )
            for point in script_res.points:
                sources.append({
                    "title": point.payload.get("title", point.payload.get("file_path", "Script")),
                    "source_type": "script",
                    "source_uuid": point.payload.get("repo", "unknown"),
                    "chunk_id": point.payload.get("file_path"),
                    "text_preview": point.payload.get("text_preview", ""),
                    "score": point.score
                })
        except Exception as exc:
            print(f"RAGAgent: Error querying script_chunks: {exc}")

        # 3. Query PostgreSQL relational ROP tables for decisions, notebooks, and research wiki pages
        try:
            import psycopg
            DB_CONN = os.getenv("POSTGRES_CONN", "postgresql://farkki:farkki_dev_password@localhost:5432/farkki_ai")
            query_words = [w.lower() for w in re.findall(r'\w+', query) if len(w) > 3]
            if not query_words:
                query_words = [""]

            with psycopg.connect(DB_CONN) as conn:
                with conn.cursor() as cur:
                    # Decisions registry search
                    dec_query = """
                        SELECT d.title, d.decision_details, d.rationale, p.project_code
                        FROM platform.decision_registry d
                        JOIN core.project p ON d.project_id = p.project_id
                    """
                    params = []
                    if project_codes:
                        dec_query += " WHERE p.project_code = ANY(%s)"
                        params.append(project_codes)
                    cur.execute(dec_query, tuple(params))
                    for r in cur.fetchall():
                        title, details, rationale, pcode = r
                        text_to_search = f"{title} {details} {rationale}".lower()
                        if not query_words[0] or any(w in text_to_search for w in query_words):
                            sources.append({
                                "title": f"Decision: {title} ({pcode})",
                                "source_type": "decision_registry",
                                "source_uuid": pcode,
                                "chunk_id": "decision",
                                "text_preview": f"Details: {details}\nRationale: {rationale}",
                                "score": 0.95
                            })

                    # Notebook entry search
                    note_query = """
                        SELECT ne.title, ne.content, ne.conclusions, p.project_code, ne.entry_type
                        FROM platform.notebook_entry ne
                        JOIN core.project p ON ne.project_id = p.project_id
                    """
                    params = []
                    if project_codes:
                        note_query += " WHERE p.project_code = ANY(%s)"
                        params.append(project_codes)
                    cur.execute(note_query, tuple(params))
                    for r in cur.fetchall():
                        title, content, conclusions, pcode, etype = r
                        text_to_search = f"{title} {content} {conclusions or ''}".lower()
                        if not query_words[0] or any(w in text_to_search for w in query_words):
                            sources.append({
                                "title": f"Notebook Note: {title} ({pcode})",
                                "source_type": "notebook_entry",
                                "source_uuid": pcode,
                                "chunk_id": "notebook",
                                "text_preview": f"Type: {etype}\nContent: {content}\nConclusions: {conclusions or ''}",
                                "score": 0.90
                            })

                    # Research Wiki search
                    wiki_query = """
                        SELECT w.title, w.content, w.wiki_type, p.project_code
                        FROM platform.research_wiki w
                        LEFT JOIN core.project p ON w.project_id = p.project_id
                    """
                    cur.execute(wiki_query)
                    for r in cur.fetchall():
                        title, content, wtype, pcode = r
                        text_to_search = f"{title} {content}".lower()
                        if not query_words[0] or any(w in text_to_search for w in query_words):
                            sources.append({
                                "title": f"Wiki [{wtype}]: {title}",
                                "source_type": "research_wiki",
                                "source_uuid": pcode or "global",
                                "chunk_id": "wiki",
                                "text_preview": content,
                                "score": 0.92
                            })
        except Exception as exc:
            print(f"RAGAgent: Error querying PostgreSQL relational context: {exc}")

        # Sort and limit
        return sorted(sources, key=lambda s: s["score"], reverse=True)[:limit * 2]


class InstallationSpecialist:
    """Generates detailed, verified instructions for installing toolchains across OS profiles."""

    RECIPES = {
        "napari": {
            "macos": {
                "commands": "curl -L -O https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-arm64.sh\nbash Miniforge3-MacOSX-arm64.sh -b\nsource ~/miniforge3/bin/activate\nmamba create -n napari_env python=3.10 -y\nconda activate napari_env\nmamba install -c conda-forge napari pyqt -y",
                "verification": "napari",
                "expected": "Miniforge shell starts; packages resolve; napari opens GUI window.",
                "fix": "On Apple Silicon, ensure miniforge arm64 build is used. If PyQt fails, run: pip install pyqt5"
            },
            "linux": {
                "commands": "mamba create -n napari_env python=3.10 -y\nconda activate napari_env\nmamba install -c conda-forge napari pyqt -y",
                "verification": "napari",
                "expected": "Qt application resolves; GUI loads successfully.",
                "fix": "OpenGL issues: Run `export QT_DEBUG_PLUGINS=1`. Install system libs: `sudo apt install libxcb-xinerama0`"
            },
            "windows": {
                "commands": "conda create -n napari_env python=3.10 -y\nconda activate napari_env\nconda install -c conda-forge napari pyqt -y",
                "verification": "napari",
                "expected": "Napari window launches.",
                "fix": "In WSL2, configure VcXsrv or running GUI with WSLG. If OpenGL driver missing, force: export LIBGL_ALWAYS_SOFTWARE=1"
            }
        },
        "cylinter": {
            "linux": {
                "commands": "mamba create -n cylinter_env python=3.9 -y\nconda activate cylinter_env\nmamba install -c conda-forge openjdk -y\npip install cylinter==0.1.5",
                "verification": "cylinter --help",
                "expected": "Pip completes; Java dependency registered.",
                "fix": "Java runtime conflicts: ensure openjdk from conda-forge is registered first."
            }
        },
        "stardist": {
            "linux": {
                "commands": "mamba create -n stardist_env python=3.10 -y\nconda activate stardist_env\nmamba install -c conda-forge cudatoolkit=11.8 cudnn=8.6 -y\npip install tensorflow==2.12.0\npip install stardist csbdeep",
                "verification": "python -c \"from stardist.models import StarDist2D; print('StarDist OK')\"",
                "expected": "StarDist OK",
                "fix": "CUDA device registration errors: Verify CUDA path is exported: export LD_LIBRARY_PATH=$CONDA_PREFIX/lib"
            }
        }
    }

    def get_instructions(self, tool: str, os_platform: str) -> Dict[str, Any]:
        tool = tool.lower().strip()
        os_platform = os_platform.lower().strip()
        
        recipe = self.RECIPES.get(tool, {}).get(os_platform)
        if recipe:
            return {
                "status": "success",
                "tool": tool,
                "os": os_platform,
                "commands": recipe["commands"],
                "verification": recipe["verification"],
                "expected_output": recipe["expected"],
                "troubleshooting": recipe["fix"]
            }
            
        return {
            "status": "error",
            "message": f"No default recipe matching {tool} on {os_platform}. Please use general chat."
        }


class LumiHpcAgent:
    """Generates production Slurm run templates and environment wrappers for LUMI HPC."""

    SLURM_TEMPLATE = """#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --account={project_account}
#SBATCH --partition={partition}
#SBATCH --nodes=1
#SBATCH --gpus-per-node={gpus}
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task={cpus}
#SBATCH --mem={memory}
#SBATCH --time={walltime}
#SBATCH --output={log_dir}/{job_name}_%j.log
#SBATCH --error={log_dir}/{job_name}_%j.err

set -euo pipefail

# Print runtime metadata
echo "Starting job on $(hostname) at $(date)"
echo "CUDA Devices: ${{CUDA_VISIBLE_DEVICES:-None}}"

# Load module dependencies
module load Container-Tools/1.0

# Define Apptainer caching
export APPTAINER_CACHEDIR={scratch_path}/apptainer_cache
mkdir -p "$APPTAINER_CACHEDIR"

# Dynamic folder/input verification
if [ ! -d "{input_path}" ]; then
    echo "ERROR: Input path {input_path} does not exist!" >&2
    exit 1
fi

# Run Apptainer container
apptainer exec --nv \\
    -B {scratch_path}:{scratch_path} \\
    {container_sif} \\
    {execution_command}

echo "Job completed successfully at $(date)"
"""

    def generate_job(self, params: Dict[str, Any]) -> str:
        job_name = params.get("job_name", "lumi_spatial_job")
        project_account = params.get("project_account", "project_462001415")
        partition = params.get("partition", "small-g" if params.get("use_gpu") else "small")
        gpus = 1 if params.get("use_gpu") else 0
        cpus = params.get("cpus", 8)
        memory = params.get("memory", "32G")
        walltime = params.get("walltime", "02:00:00")
        scratch_path = params.get("scratch_path", "/scratch/project_462001415")
        log_dir = params.get("log_dir", "logs/pipeline")
        input_path = params.get("input_path", "/scratch/project_462001415/image_processing/ada/stitched")
        container_sif = params.get("container_sif", "/scratch/project_462001415/containers/deepcell-mesmer_latest.sif")
        execution_command = params.get("execution_command", "python /scratch/project_462001415/scripts/segment.py --input-dir " + input_path)

        return self.SLURM_TEMPLATE.format(
            job_name=job_name,
            project_account=project_account,
            partition=partition,
            gpus=gpus,
            cpus=cpus,
            memory=memory,
            walltime=walltime,
            scratch_path=scratch_path,
            log_dir=log_dir,
            input_path=input_path,
            container_sif=container_sif,
            execution_command=execution_command
        )


class ImagePipelineSpecialist:
    """Guides researchers through the multi-stage multiplex tCyCIF pipeline."""
    
    STAGES = {
        "basic": {
            "inputs": "Raw, multi-channel mosaic microscopy TIFF files (tiled format).",
            "outputs": "Shading/flatfield and darkfield calibration TIFF matrices.",
            "command": "python scripts/run_basic.py --input-dir /path/to/raw --output-dir /path/to/basic_calib",
            "troubleshoot": "Memory errors if loading high-resolution images globally. Fix: tile input streams."
        },
        "ashlar": {
            "inputs": "Raw microscopy tiles + flatfield/darkfield matrices from BaSiC.",
            "outputs": "Registered, stitched OME-TIFF mosaic pyramid file.",
            "command": "ashlar \"/path/to/tiles/*.tif\" --output /path/to/stitched.tif --ffp flatfield.tif --dfp darkfield.tif --align-channel 0",
            "troubleshoot": "Channel overlap errors. Fix: verify overlap parameters (default is 10%)."
        },
        "mesmer": {
            "inputs": "Stitched OME-TIFF mosaic containing nuclear and membrane marker channels.",
            "outputs": "Cell and nuclear integer boundary masks (TIFF format).",
            "command": "python segment.py --image /path/to/stitched.tif --nuclear-channel 0 --membrane-channel 1 --output /path/to/mask.tif",
            "troubleshoot": "CUDA out of memory during inference pass. Fix: reduce batch-size or use `--tile-size 256`."
        }
    }

    def get_stage_guidelines(self, stage: str) -> Dict[str, Any]:
        stage = stage.lower().strip()
        data = self.STAGES.get(stage)
        if data:
            return {
                "status": "success",
                "stage": stage,
                "expected_inputs": data["inputs"],
                "expected_outputs": data["outputs"],
                "command_template": data["command"],
                "troubleshooting": data["troubleshoot"]
            }
        return {
            "status": "error",
            "message": f"Stage {stage} is unknown. Supported: basic, ashlar, mesmer."
        }


class TroubleshootingAgent:
    """Analyzes tracebacks, environment issues, or stdout execution errors to suggest fixes."""

    @classmethod
    def diagnose_log(cls, log_text: str) -> Dict[str, Any]:
        lower_log = log_text.lower()
        
        # 1. Out Of Memory
        if "out of memory" in lower_log or "oom-killer" in lower_log or "exit code 137" in lower_log:
            return {
                "cause": "Slurm / System Out-Of-Memory (OOM) termination.",
                "fix": "Increase memory limits inside Slurm parameters (e.g. #SBATCH --mem=64G or --mem=128G). Reduce image segmentation batch-size configurations.",
                "prevention": "Ensure large spatial image layers are processed in tiles rather than loaded into host memory at once."
            }
            
        # 2. OpenGL / Qt platform plugin load failures
        if "opengl" in lower_log or "qt" in lower_log or "xcb" in lower_log:
            return {
                "cause": "Napari Qt platform display bindings or headless X11 server missing.",
                "fix": "Export screen variables: `export QT_QPA_PLATFORM=offscreen`. If running locally, install Qt xcb libraries: `sudo apt install libxcb-xinerama0`.",
                "prevention": "Use container wrappers or run in virtual framebuffers (e.g. xvfb-run napari)."
            }

        # 3. Conda environment conflicts
        if "unsatisfiable" in lower_log or "conflict" in lower_log:
            return {
                "cause": "Conda/Mamba environment package dependency version mismatch.",
                "fix": "Use a fresh conda environment with Python 3.10 and avoid mixing conda and pip channels. Use conda-forge prioritizing: `mamba create -n new_env -c conda-forge python=3.10 python-packages`.",
                "prevention": "Lock environment layouts using environment.yml locks."
            }

        # Generic default diagnostic
        return {
            "cause": "General execution error or file layout issues.",
            "fix": "Verify that all file paths exist, check that target directory output paths are writable, and check that required library channels match.",
            "prevention": "Incorporate safety checking before running scripts."
        }


class ScriptGeneratorAgent:
    """Generates robust Python, R, and Bash scripts with embedded safety headers."""

    def generate_bash(self, commands: str) -> str:
        return (
            "#!/bin/bash\n"
            "# Strict bash flags for debugging stability\n"
            "set -euo pipefail\n\n"
            "# 1. Setup logs\n"
            "LOG_FILE=\"pipeline_run_$(date +%Y%m%d_%H%M%S).log\"\n"
            "exec > >(tee -a \"$LOG_FILE\") 2>&1\n\n"
            "# 2. Print environment info\n"
            "echo \"Running script as $(whoami) on $(hostname)\"\n"
            "echo \"Date: $(date)\"\n"
            "echo \"Python: $(which python || echo 'Not Found')\"\n"
            "echo \"------------------------------------\"\n\n"
            "# 3. Execute commands\n" + commands + "\n\n"
            "echo \"Process completed successfully.\"\n"
        )

    def generate_python(self, body: str) -> str:
        return (
            "import os\n"
            "import sys\n"
            "import logging\n"
            "from datetime import datetime\n\n"
            "# Configure standard logging\n"
            "logging.basicConfig(\n"
            "    level=logging.INFO,\n"
            "    format='%(asctime)s [%(levelname)s] %(message)s',\n"
            "    handlers=[\n"
            "        logging.FileHandler(f\"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log\"),\n"
            "        logging.StreamHandler(sys.stdout)\n"
            "    ]\n"
            ")\n\n"
            "def main():\n"
            "    logging.info(\"Initializing script execution\")\n"
            "    # User commands execution\n" + 
            "\n".join("    " + line for line in body.split("\n")) + "\n\n"
            "if __name__ == '__main__':\n"
            "    try:\n"
            "        main()\n"
            "    except Exception as e:\n"
            "        logging.exception(f\"FATAL: Script execution failed: {e}\")\n"
            "        sys.exit(1)\n"
        )


class ClinicalSpatialSpecialist:
    """Generates R and Python scripts for clinical spatial cell calculations."""

    NEIGHBORHOOD_SCRIPT = """import pandas as pd
import numpy as np
from scipy.spatial import KDTree

def compute_spatial_neighborhoods(cell_table_path, target_cell_type, neighborhood_radius=30.0):
    \"\"\"Calculates neighboring cell counts within a specific micron radius.\"\"\"
    print(f"Loading cell features from {cell_table_path}...")
    df = pd.read_csv(cell_table_path)
    
    # Check coords presence
    if 'x' not in df.columns or 'y' not in df.columns or 'cell_type' not in df.columns:
        raise ValueError("Cell table must contain coords ('x', 'y') and cell type labels ('cell_type').")
        
    coords = df[['x', 'y']].values
    tree = KDTree(coords)
    
    # Query coordinates of target cell types
    target_idx = df[df['cell_type'] == target_cell_type].index
    target_coords = coords[target_idx]
    
    # Query ball radius
    neighbors_list = tree.query_ball_point(target_coords, r=neighborhood_radius)
    
    # Get density counts
    density = [len(n) - 1 for n in neighbors_list]  # Subtract query cell itself
    df.loc[target_idx, 'neighborhood_density'] = density
    
    print(f"Completed neighborhood calculations for {len(target_idx)} cells.")
    return df
"""

    def get_analysis_recipe(self, analysis_type: str) -> str:
        analysis_type = analysis_type.lower().strip()
        if "neighborhood" in analysis_type:
            return self.NEIGHBORHOOD_SCRIPT
        
        # Default fallback analysis guide (Kaplan-Meier survival plotter)
        return (
            "import pandas as pd\n"
            "from lifelines import KaplanMeierFitter\n"
            "import matplotlib.pyplot as plt\n\n"
            "def run_survival_analysis(df, duration_col='pfs_months', event_col='pfs_event', group_col='brca_mut'):\n"
            "    kmf = KaplanMeierFitter()\n"
            "    for name, grouped in df.groupby(group_col):\n"
            "        kmf.fit(grouped[duration_col], event_col=grouped[event_col], label=name)\n"
            "        kmf.plot_survival_function()\n"
            "    plt.title('PFS Kaplan-Meier Curve by BRCA status')\n"
            "    plt.xlabel('Months')\n"
            "    plt.ylabel('PFS Probability')\n"
            "    plt.show()\n"
        )
