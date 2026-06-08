#!/usr/bin/env python3
"""Extract lab folders from disk, then assimilate into canonical rag.* + Qdrant index."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = os.environ.get("OMEIA_REPO_ROOT", str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("OMEIA_REPO_ROOT", ROOT)

from app_skeleton.api.lab_knowledge_store import _cli  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.argv = [sys.argv[0], "--all", "--refresh-extract"]
    raise SystemExit(_cli())
