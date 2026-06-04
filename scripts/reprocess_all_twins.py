#!/usr/bin/env python3
"""Reprocess all project digital twins and sync to React public/processed."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# OMEIA-AI repo root (parent of farkki_ai_platform_blueprint), not the blueprint folder.
ROOT = os.environ.get(
    "OMEIA_REPO_ROOT",
    str(Path(__file__).resolve().parents[2]),
)
BLUEPRINT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BLUEPRINT))
# Only set repo root when unset so paths.py resolves database/ under OMEIA-AI.
if not os.environ.get("OMEIA_REPO_ROOT"):
    os.environ["OMEIA_REPO_ROOT"] = ROOT

from app_skeleton.api.project_processor import _cli  # noqa: E402

if __name__ == "__main__":
    sys.argv = [sys.argv[0], "--all", "--refresh", *sys.argv[1:]]
    raise SystemExit(_cli())
