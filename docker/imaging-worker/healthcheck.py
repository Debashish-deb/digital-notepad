#!/usr/bin/env python3
"""Verify imaging Docker image and print capability report."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "app_skeleton" / "api"))

from imaging_capabilities import probe_imaging_stack  # noqa: E402

if __name__ == "__main__":
    report = probe_imaging_stack()
    print(json.dumps(report, indent=2))
    sys.exit(0 if report.get("streaming_ready") else 1)
