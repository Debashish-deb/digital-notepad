#!/usr/bin/env python3
"""Extract lab folders to processed twins. For full canonical index use ingest_lab_knowledge.py."""
from __future__ import annotations

import os
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve()
ROOT = os.environ.get("OMEIA_REPO_ROOT", str(_SCRIPT.parents[2]))
sys.path.insert(0, str(_SCRIPT.parents[2]))
os.environ.setdefault("OMEIA_REPO_ROOT", ROOT)

from app_skeleton.api.database_processor import _cli  # noqa: E402

if __name__ == "__main__":
    sys.argv = [sys.argv[0], "--all", "--refresh", *sys.argv[1:]]
    raise SystemExit(_cli())
