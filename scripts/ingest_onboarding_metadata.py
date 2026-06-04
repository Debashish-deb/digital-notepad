#!/usr/bin/env python3
import os
import psycopg
from datetime import datetime, date

DB_CONN = os.getenv("POSTGRES_CONN", "postgresql://farkki:farkki_dev_password@localhost:5432/farkki_ai")

def main():
    print(f"Connecting to database to seed onboarding metadata: {DB_CONN}")
    with psycopg.connect(DB_CONN) as conn:
        with conn.cursor() as cur:
            # 1. Seed AI Models
            models = [
                # TEXT / REASONING
                ("MedGemma", "biomedical_LLM", "Google / HuggingFace", "Gemma License", "7B / 2B", "L4 GPU / 24GB VRAM", "16GB RAM", True, True, 
                 "Clinical question answering, translation of patient notes", "Specifically tuned on medical datasets", "Not suitable for diagnostic decisions",
                 "pip install transformers; huggingface-cli download google/medgemma-7b"),
                
                ("BioMistral", "biomedical_LLM", "BioMistral", "Apache 2.0", "7B", "RTX 3090 / 4090", "16GB RAM", True, True,
                 "Medical documentation and literature summary", "Strong reasoning on biology and pharmacology", "Limited clinical safety guardrails relative to proprietary models",
                 "pip install transformers; huggingface-cli download BioMistral/BioMistral-7B"),
                
                ("Med42", "biomedical_LLM", "M42 Health", "Custom Non-commercial", "70B", "A100 GPU", "64GB RAM", False, True,
                 "Clinical decision support, diagnostic assistance suggestions", "State of the art medical benchmarking results", "Huge compute requirements to host locally",
                 "Use model API or deploy on LUMI using 4x A100 GPU cluster"),
                
                ("BioGPT", "biomedical_LLM", "Microsoft", "MIT", "1.5B", "T4 GPU", "12GB RAM", True, False,
                 "Biomedical text generation and mining", "Fine-tuned on PubMed papers", "Small context window, robotic outputs",
                 "pip install transformers; model = AutoModelForCausalLM.from_pretrained('microsoft/biogpt')"),
                
                ("Llama 3.1-8B", "LLM", "Meta", "Llama 3 License", "8B", "RTX 4080", "16GB RAM", True, True,
                 "General research assistance, code generation", "Highly versatile, excellent context size", "Not specifically tuned on medical domains",
                 "ollama run llama3.1"),

                # EMBEDDINGS
                ("PubMedBERT", "embedding", "Microsoft", "MIT", "110M", "CPU or T4", "8GB RAM", True, False,
                 "Semantic indexing of medical literature, search query embeddings", "Trained from scratch on PubMed abstracts", "Short maximum text length (512 tokens)",
                 "from transformers import AutoTokenizer, AutoModel; Tokenizer.from_pretrained('microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext')"),

                ("BioBERT", "embedding", "DMIS Lab", "Apache 2.0", "110M", "CPU or T4", "8GB RAM", True, False,
                 "Biomedical entity extraction, text classification", "Trained on PMC articles and PubMed abstracts", "Requires domain-specific fine-tuning for top results",
                 "AutoModel.from_pretrained('dmis-lab/biobert-v1.1')"),

                ("MedCPT", "embedding", "NCBI / NIH", "Public Domain", "110M", "CPU", "8GB RAM", True, True,
                 "Semantic search query-to-article mapping", "Trained on millions of PubMed search click logs", "Only handles biomedical literature searches",
                 "AutoModel.from_pretrained('ncbi/MedCPT-Query-Encoder')"),

                # VISION
                ("BiomedCLIP", "vision", "Microsoft", "MIT", "200M", "T4 GPU", "12GB RAM", True, False,
                 "Pathology image captioning, zero-shot classification", "Large training set of PubMed image-caption pairs", "Fails on highly out-of-distribution tissue structures",
                 "pip install open_clip_torch; open_clip.create_model_and_transforms('ViT-B-16', pretrained='pubmed')"),

                ("PLIP", "vision", "PathologyImage", "Apache 2.0", "200M", "T4 GPU", "12GB RAM", True, False,
                 "Computational pathology, image search", "Fine-tuned on social media pathology images with texts", "Best on H&E; less optimized for multi-channel multiplex imaging",
                 "from PIL import Image; import requests; # Load USRL/PLIP from HuggingFace"),

                # SEGMENTATION
                ("Mesmer", "segmentation", "DeepCell / Van Valen Lab", "DeepCell License", "20M", "RTX 3080", "16GB RAM", True, False,
                 "Cell segmentation (nuclear and whole-cell) in multiplex tCyCIF images", "Trained on TissueNet containing 1M+ hand-labeled cell boundaries", "Computationally heavy on whole slides; requires tiling",
                 "pip install deepcell; from deepcell.applications import Mesmer; app = Mesmer()"),

                ("StarDist", "segmentation", "MPI-CBG", "BSD-3-Clause", "5M", "CPU or T4", "8GB RAM", True, False,
                 "Nuclear boundary segmentation in dense fluorescent images", "Extremely fast, handles star-convex shapes beautifully", "Fails on overlapping cell bodies or membrane segmentation",
                 "pip install stardist; from stardist.models import StarDist2D"),

                ("Cellpose", "segmentation", "Stringer & Pachitariu", "BSD-3-Clause", "15M", "RTX 3080", "16GB RAM", True, False,
                 "General cell and nucleus segmentation across diverse modalities", "Excellent generalizability, interactive napari plugin", "Occasional oversegmentation in dense clusters",
                 "pip install cellpose; from cellpose import models; model = models.Cellpose(gpu=True, model_type='cyto')"),

                ("SAM2", "segmentation", "Meta", "Apache 2.0", "300M", "RTX 4090", "32GB RAM", True, True,
                 "Zero-shot interactive boundary tracking and masking", "Extremely powerful promptable segmentation (points, bounding boxes)", "Struggles with tiny cellular features without fine-tuning",
                 "pip install segment-anything-2; # Load sam2 checkpoint"),

                # SPATIAL BIOLOGY
                ("Scanpy", "spatial_biology", "Theislab", "BSD-3-Clause", "N/A", "CPU", "16GB RAM", True, False,
                 "Single-cell and spatial transcriptomics data preprocessing, clustering, visualization", "De facto python standard, integrates with AnnData", "No native deep spatial statistics",
                 "pip install scanpy"),

                ("Squidpy", "spatial_biology", "Theislab / Helmhotz", "BSD-3-Clause", "N/A", "CPU", "16GB RAM", True, False,
                 "Spatial neighborhood analysis, centrality, ligand-receptor inference", "Integrates Scanpy with network modeling tools (NetworkX, PySAL)", "Large coordinate sets consume significant RAM",
                 "pip install squidpy"),

                ("Giotto", "spatial_biology", "Dries Lab", "GPL-3", "N/A", "CPU", "32GB RAM", True, False,
                 "R-based comprehensive spatial analysis toolbox", "Great for cell-to-cell interaction grids and niche identification", "Requires R environment configuration",
                 "install.packages('Giotto')"),

                ("CellCharter", "spatial_biology", "Palla Lab", "MIT", "N/A", "CPU / GPU", "16GB RAM", True, False,
                 "Algorithmic cell microenvironment identification and clustering", "Accurate spatial niche detection across multiplex datasets", "Sensitive to segmentation noise",
                 "pip install cellcharter")
            ]

            for name, mtype, src, lic, params, gpu, mem, local_dep, api_dep, use, strength, weak, install in models:
                cur.execute("""
                    INSERT INTO platform.ai_model (name, model_type, source, license, parameters, gpu_requirements, memory_requirements, local_deployment, api_deployment, use_cases, strengths, weaknesses, installation_instructions)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (name) DO UPDATE
                    SET model_type = EXCLUDED.model_type,
                        use_cases = EXCLUDED.use_cases,
                        installation_instructions = EXCLUDED.installation_instructions;
                """, (name, mtype, src, lic, params, gpu, mem, local_dep, api_dep, use, strength, weak, install))
            print("Successfully seeded AI Model Registry.")

            # 2. Seed Infrastructure Registry
            infra = [
                ("LUMI Supercomputer", "lumi", "HPE Cray EX OS (SLES)", "64-core AMD EPYC", "512GB per node", "4x AMD Instinct MI250X GPUs per node", "Flash storage clusters (LUSTRE)",
                 ["Apptainer", "Singularity", "Conda", "Mamba", "Slurm", "Snakemake", "Ashlar", "Mesmer"],
                 "Requires SSH keys registered with CSC. Access through login.lumi.csc.fi.",
                 "Monthly service maintenance on Wednesdays."),

                ("CSC Puhti", "csc", "RedHat Enterprise Linux", "Intel Xeon Gold", "192GB / 384GB per node", "V100/A100 GPUs", "All-flash scratch and proj volumes",
                 ["Conda", "Slurm", "Apptainer", "R-env", "Jupyter", "Cellpose", "StarDist"],
                 "Direct login through CSC portal (puhti.csc.fi). Suitable for fast interactive analysis.",
                 "Check CSC service status alerts."),

                ("Lab Workstation 1 - WSL2", "workstation", "Ubuntu 22.04 on Windows WSL2", "Intel Core i9-13900K", "128GB", "NVIDIA RTX 4090 (24GB VRAM)", "4TB NVMe SSD",
                 ["Docker", "Conda", "napari", "Cylinter", "Ashlar", "Cellpose", "CUDA 12.1"],
                 "Local workstation located in lab room B429. User credentials managed locally.",
                 "Ensure WSL2 network interface bridge doesn't block Qdrant/Postgres endpoints."),

                ("Hostinger VPS Database", "database", "Ubuntu 24.04 LTS", "4 vCPU Virtualized", "16GB", "None", "200GB NVMe Storage",
                 ["PostgreSQL 16", "pgvector", "Qdrant", "Redis"],
                 "Houses metadata registry, search index, and user access records.",
                 "Weekly backup schedule runs on Sundays at 02:00."),

                ("Hostinger MinIO Object Storage", "storage", "Linux Cloud", "N/A", "N/A", "None", "5TB Cloud Storage",
                 ["MinIO", "S3-compatible API"],
                 "Stores pyramid OME-TIFF slides, segmented cell masks, and quantification features.",
                 "Replicated across multiple backup zones.")
            ]

            for name, rtype, os_specs, cpu, ram, gpu, storage, software, access, maint in infra:
                cur.execute("""
                    INSERT INTO platform.infrastructure (name, resource_type, operating_system, cpu_specs, ram_specs, gpu_specs, storage_specs, installed_software, access_notes, maintenance_notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::text[], %s, %s)
                    ON CONFLICT (name) DO UPDATE
                    SET operating_system = EXCLUDED.operating_system,
                        installed_software = EXCLUDED.installed_software,
                        access_notes = EXCLUDED.access_notes;
                """, (name, rtype, os_specs, cpu, ram, gpu, storage, software, access, maint))
            print("Successfully seeded Infrastructure Registry.")

            # 3. Seed Publications
            pubs = [
                ("MHC class II expression on cancer cells shaped by tumor-immune microenvironment interactions in HGSC",
                 "Perez F, Shabanova A, Casado J, Kachalova A, Färkkilä A, et al.",
                 "Cancer Discovery", 2026, "10.1158/2159-8290.CD-25-1492", "41661089",
                 "Analysis of a large cohort of 265 HGSC patients using 10 TMAs to profile HLA-class II expression on cancer cells and its association with survival and clinical outcomes.",
                 "NKI", None),

                ("Tribus: knowledge-based cell classification gating trees for multiplexed imaging datasets",
                 "Kang Z, Szabo A, Perez F, Junquera A, Shah S, Anttila E, Haltia UM, Färkkilä A, et al.",
                 "Bioinformatics", 2025, "10.1093/bioinformatics/btaf082", "39982403",
                 "Custom computational package featuring a knowledge-based, multi-stage single-cell classification algorithm that uses logical gating trees of marker expressions to annotate cell types in multiplexed imaging datasets without manual labeling.",
                 "Tribus", "https://github.com/farkkilab/tribus"),

                ("Chemotherapy induces myeloid-driven spatially confined T cell exhaustion in ovarian cancer",
                 "Palomino S, Chen W, Launonen IM, Färkkilä A, et al.",
                 "Cancer Cell", 2024, "10.1016/j.ccell.2024.11.002", "39658541",
                 "Spatially mapped cellular profiles showing post-chemotherapy changes in high-grade serous ovarian cancer, highlighting localized myeloid-T cell suppressive hubs.",
                 "sciSet", None)
            ]

            # Fetch project mapping
            cur.execute("SELECT project_id, project_code FROM core.project;")
            project_map = {code: pid for pid, code in cur.fetchall()}

            for title, authors, journal, year, doi, pmid, abstract, p_code, full_text in pubs:
                pid = project_map.get(p_code)
                cur.execute("""
                    INSERT INTO platform.publication (title, authors, journal, publication_year, doi, pmid, abstract, project_id, full_text_path)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (doi) DO UPDATE
                    SET abstract = EXCLUDED.abstract, pmid = EXCLUDED.pmid;
                """, (title, authors, journal, year, doi, pmid, abstract, pid, full_text))
            print("Successfully seeded Publications Registry.")

            # 4. Generate Onboarding Checklist Templates for all projects
            checklist_items = [
                # Project
                ("project", "Project Description & Goals", "Ensure project description, scientific questions, and goals are documented."),
                ("project", "Members & Collaborators", "Add responsible researchers and their clinical/computational roles."),
                
                # Document
                ("document", "Protocols & SOPs", "Link the wet-lab staining/imaging and dry-lab segmentation SOPs used."),
                ("document", "Ethics Approvals", "Record the ethics board registry reference number."),
                
                # Software
                ("software", "Software Versions", "Document package versions (Cylinter, Ashlar, Mesmer, Tribus) used."),
                
                # Pipeline
                ("pipeline", "Stitching Pipeline Run", "Execute and link Ashlar stitching logs/runs."),
                ("pipeline", "Cell Segmentation Quality Check", "Verify cell boundaries and mask outputs."),
                
                # Dataset
                ("dataset", "OME-TIFF Raw Slides", "Verify raw image folders are cataloged and size computed."),
                ("dataset", "Segmented Cell Masks", "Store and register cell masks (.tif) in object storage."),
                ("dataset", "Quantified Cell Features Table", "Verify single-cell expression tables (.csv/.h5ad) are cataloged."),
                
                # Sample
                ("sample", "Sample Code Verification", "Align clinical patient codes with imaging specimen codes."),
                
                # Publication
                ("publication", "Preprint/Publication Linkage", "Track linked publications or conference poster details.")
            ]

            for code, pid in project_map.items():
                for category, item, desc in checklist_items:
                    cur.execute("""
                        INSERT INTO platform.onboarding_checklist (project_id, category, item_name, description, status)
                        VALUES (%s, %s, %s, %s, 'pending')
                        ON CONFLICT (project_id, category, item_name) DO NOTHING;
                    """, (pid, category, item, desc))
            print("Successfully initialized Onboarding Checklists templates.")

        conn.commit()
    print("Ingestion script completed successfully!")

if __name__ == "__main__":
    main()
