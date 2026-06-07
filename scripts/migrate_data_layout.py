#!/usr/bin/env python3
# Backward-compat wrapper — use scripts/database/migrate_data_layout.py
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parent / "database" / "migrate_data_layout.py"), run_name="__main__")
