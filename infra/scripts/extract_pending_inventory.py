#!/usr/bin/env python3
"""Backward-compat wrapper — use scripts/digitalization/extract_pending_inventory.py"""
from pathlib import Path
import runpy

runpy.run_path(
    str(Path(__file__).resolve().parent / "digitalization" / "extract_pending_inventory.py"),
    run_name="__main__",
)
