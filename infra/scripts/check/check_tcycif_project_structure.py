#!/usr/bin/env python3
import os
import sys

def check_project_structure(base_dir="."):
    print("📁 Checking tCyCIF Project Workspace layouts...")
    print("---------------------------------------------")
    
    expected_folders = [
        "configs",
        "scripts",
        "sql",
        "schemas",
        "docs",
        "omeia"
    ]
    
    missing = []
    for f in expected_folders:
        path = os.path.join(base_dir, f)
        if not os.path.isdir(path):
            missing.append(f)
            
    if missing:
        print(f"[FAIL] Missing directories in project layout: {missing}")
        print("Recommended Fix: Regenerate workspace using platform bootstrap template scripts.")
        return 1
        
    print("[PASS] Standard folders structure matches platform specifications.")
    return 0

if __name__ == "__main__":
    sys.exit(check_project_structure())
