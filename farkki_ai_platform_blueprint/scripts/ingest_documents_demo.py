#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import math
import os
import re
from pathlib import Path
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http import models

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
COMPILED_SCRIPTS_DIR = Path("/home/debdeba/Documents/scripts/projects/compiled_scripts")

def pseudo_semantic_embed(text: str, dim: int = 384) -> List[float]:
    """
    Zero-dependency term-frequency (bag-of-words) unit vectorizer.
    Yields cosine similarities corresponding to word overlap,
    making exact-word queries match documents containing those words.
    """
    vec = [0.0] * dim
    # Clean text and extract alphanumeric words
    words = re.findall(r'[a-zA-Z0-9_\-]+', text.lower())
    for w in words:
        # Simple stop words filtering
        if w in {'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were',
                 'to', 'in', 'of', 'for', 'on', 'with', 'at', 'by', 'from', 'this',
                 'that', 'these', 'those', 'it', 'its', 'as', 'we', 'you', 'i', 'our'}:
            continue
        # Use SHA-256 to hash the word into an index
        h = int(hashlib.sha256(w.encode('utf-8')).hexdigest(), 16)
        idx = h % dim
        vec[idx] += 1.0
        
    # Normalize to unit length
    norm = math.sqrt(sum(v*v for v in vec))
    if norm < 0.0001:
        # Fallback to deterministic hash of the entire text if empty
        h_all = hashlib.sha256(text.encode('utf-8')).digest()
        vec = [((h_all[i % len(h_all)] / 255.0) * 2 - 1) for i in range(dim)]
        norm = math.sqrt(sum(v*v for v in vec)) or 1.0
    return [v / norm for v in vec]

def chunk_markdown(filepath: Path) -> List[Dict[str, str]]:
    """Splits a markdown file into sections based on headers."""
    content = filepath.read_text(encoding='utf-8', errors='ignore')
    sections = []
    current_header = "Header"
    current_lines = []
    
    for line in content.splitlines():
        if line.startswith('#'):
            if current_lines:
                sections.append({
                    "header": current_header,
                    "text": "\n".join(current_lines).strip()
                })
            current_header = line.strip('# ')
            current_lines = [line]
        else:
            current_lines.append(line)
            
    if current_lines:
        sections.append({
            "header": current_header,
            "text": "\n".join(current_lines).strip()
        })
        
    return sections

def main():
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    client = QdrantClient(url=qdrant_url)
    
    # --- 1. Ingest Documentation in doc_chunks ---
    doc_points = []
    print("Reading documentation files from docs/...")
    
    for doc_file in sorted(DOCS_DIR.glob("*.md")):
        print(f"  Processing {doc_file.name}")
        chunks = chunk_markdown(doc_file)
        for i, chunk in enumerate(chunks):
            title = f"{doc_file.name}: {chunk['header']}"
            text = chunk['text']
            if not text:
                continue
                
            point_id = hashlib.md5(f"doc_{doc_file.name}_{i}".encode('utf-8')).hexdigest()
            payload = {
                "schema_version": 1,
                "source_type": "documentation",
                "document_id": doc_file.name,
                "source_file_id": doc_file.name,
                "chunk_id": str(i),
                "title": title,
                "text_preview": text[:1000],
                "project_code": "SPACE", # Default scope
                "modality": ["documentation"],
                "sensitivity_level": "internal",
                "allowed_project_codes": ["SPACE", "EyeMT", "KRAS"],
                "contains_patient_level_data": False,
                "contains_direct_identifier": False,
                "embedding_model": "pseudo_semantic_bag_of_words",
                "embedding_dimension": 384,
                "created_at": "2026-06-02T12:00:00Z",
                "status": "active"
            }
            doc_points.append(models.PointStruct(
                id=point_id,
                vector={"text": pseudo_semantic_embed(text)},
                payload=payload
            ))
            
    if doc_points:
        client.upsert(collection_name="doc_chunks", points=doc_points)
        print(f"Upserted {len(doc_points)} points into doc_chunks.")

    # --- 2. Ingest Consolidated Script Files in script_chunks ---
    script_points = []
    # Map consolidated file names to project codes
    project_mapping = {
        "image_processing_scripts.md": "SPACE",
        "cefiira_scripts.md": "EyeMT",
        "kras_scripts.md": "KRAS",
        "geomx_processing_scripts.md": "EyeMT",
        "spacestat_scripts.md": "SPACE",
        "space_scripts.md": "SPACE",
        "cellcycle_scripts.md": "EyeMT",
        "tribus_scripts.md": "EyeMT",
        "eyemt_scripts.md": "EyeMT",
        "clinical_data_curation_scripts.md": "EyeMT",
        "finprove_scripts.md": "SPACE"
    }
    
    if COMPILED_SCRIPTS_DIR.exists():
        print("Reading compiled script files...")
        for script_file in sorted(COMPILED_SCRIPTS_DIR.glob("*.md")):
            proj_code = project_mapping.get(script_file.name, "SPACE")
            print(f"  Processing script file {script_file.name} for project {proj_code}")
            
            chunks = chunk_markdown(script_file)
            for i, chunk in enumerate(chunks):
                title = f"{script_file.name}: {chunk['header']}"
                text = chunk['text']
                if not text:
                    continue
                    
                # Determine language inside this chunk
                lang = "python"
                if "```bash" in text:
                    lang = "bash"
                elif "```r" in text:
                    lang = "r"
                
                point_id = hashlib.md5(f"script_{script_file.name}_{i}".encode('utf-8')).hexdigest()
                payload = {
                    "schema_version": 1,
                    "repo": script_file.name.replace("_scripts.md", ""),
                    "file_path": chunk['header'],
                    "language": lang,
                    "pipeline_stage": "analysis" if "analysis" in chunk['header'].lower() else "processing",
                    "project_code": proj_code,
                    "sensitivity_level": "internal",
                    "title": title,
                    "text_preview": text[:1000],
                    "created_at": "2026-06-02T12:00:00Z"
                }
                script_points.append(models.PointStruct(
                    id=point_id,
                    vector={"text": pseudo_semantic_embed(text)},
                    payload=payload
                ))
                
        if script_points:
            client.upsert(collection_name="script_chunks", points=script_points)
            print(f"Upserted {len(script_points)} points into script_chunks.")
            
    print("Qdrant document and script ingestion complete.")

if __name__ == "__main__":
    main()
