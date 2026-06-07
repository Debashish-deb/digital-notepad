#!/usr/bin/env python3
"""Backward-compat wrapper — use scripts/digitalization/process_inventory_pipeline.py"""
from pathlib import Path
import runpy

runpy.run_path(
    str(Path(__file__).resolve().parent / "digitalization" / "process_inventory_pipeline.py"),
    run_name="__main__",
)
