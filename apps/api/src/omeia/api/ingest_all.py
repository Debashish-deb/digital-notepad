import os
from omeia.api.paths import PROJECTS_ROOT
from omeia.api.project_knowledge_extractor import extract_and_ingest_project

def main():
    print(f"Scanning for projects in {PROJECTS_ROOT}")
    total_projects = 0
    total_docs = 0
    total_chunks = 0
    
    for child in PROJECTS_ROOT.iterdir():
        if child.is_dir() and child.name not in ["compiled_scripts", "project_scripts"]:
            print(f"Processing project: {child.name}")
            try:
                res = extract_and_ingest_project(child.name)
                docs = res.get("extracted_docs", 0)
                chunks = res.get("extracted_chunks", 0)
                print(f"  -> Success: {docs} documents, {chunks} chunks")
                total_projects += 1
                total_docs += docs
                total_chunks += chunks
            except Exception as e:
                print(f"  -> Error: {str(e)}")
                
    print("\n--- INGESTION COMPLETE ---")
    print(f"Total Projects Processed: {total_projects}")
    print(f"Total Documents Indexed:  {total_docs}")
    print(f"Total Chunks Vectorized:  {total_chunks}")

if __name__ == "__main__":
    main()
