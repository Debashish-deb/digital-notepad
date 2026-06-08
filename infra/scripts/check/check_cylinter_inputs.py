#!/usr/bin/env python3
import os
import sys

def check_cylinter_inputs(markers_path="markers.csv", config_path="config.yml", mask_path="mask.tif"):
    print("🔬 Checking Cylinter Input Quality & Structure...")
    print("-------------------------------------------------")
    
    issues = 0
    
    # 1. Markers check
    if not os.path.exists(markers_path):
        print(f"[FAIL] Missing marker antibodies configuration at: {markers_path}")
        issues += 1
    else:
        print(f"[PASS] Marker configuration file exists: {markers_path}")
        
    # 2. Config check
    if not os.path.exists(config_path):
        print(f"[WARNING] Cylinter runtime settings missing: {config_path}")
        print("Recommended Fix: Create standard config.yml mapping paths.")
        issues += 1
    else:
        print(f"[PASS] Runtime configurations: {config_path}")

    # 3. Segmentation Mask check
    if not os.path.exists(mask_path):
        print(f"[FAIL] Missing cell segmentation boundary masks: {mask_path}")
        issues += 1
    else:
        print(f"[PASS] Segmentation boundary mask: {mask_path}")
        
    if issues == 0:
        print("\n[RESULT] Input checks passed! Files are safe to process inside Cylinter pipeline.")
        return 0
    else:
        print(f"\n[RESULT] Verification failed with {issues} issue(s). Resolve warnings before starting QC.")
        return 1

if __name__ == "__main__":
    sys.exit(check_cylinter_inputs())
