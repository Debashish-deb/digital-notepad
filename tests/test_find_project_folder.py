"""Project folder resolution across PROJECTS_ROOT and LAB_STORAGE_ROOT."""
from __future__ import annotations

from pathlib import Path

import pytest

from app_skeleton.api import paths
from app_skeleton.api.project_processor import find_project_folder


@pytest.fixture()
def emt_folders(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    projects_root = tmp_path / "projects"
    lab_root = tmp_path / "lab"
    stub = projects_root / "5_EMT-20260602T171604Z-3-001" / "5_EMT"
    stub.mkdir(parents=True)
    (stub / "5_Project_Log.docx").write_bytes(b"log")
    (stub / "README.md").write_text("stub\n", encoding="utf-8")

    rich = lab_root / "Data" / "5-EMT"
    rich.mkdir(parents=True)
    for i in range(5):
        (rich / f"file_{i}.pdf").write_bytes(b"x" * 10)

    monkeypatch.setattr(paths, "PROJECTS_ROOT", projects_root)
    monkeypatch.setattr(paths, "DATABASE_ROOT", projects_root.parent)
    monkeypatch.setenv("LAB_STORAGE_ROOT", str(lab_root))
    monkeypatch.setenv("PROJECTS_ROOT", str(projects_root))
    return {"stub": stub, "rich": rich}


def test_find_project_folder_prefers_richest_match(emt_folders, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "app_skeleton.api.project_processor._load_catalog",
        lambda: {
            "EMT": {
                "project_code": "EMT",
                "project_index": 5,
                "folder_path": "5_EMT-20260602T171604Z-3-001",
                "folder_aliases": ["5-EMT", "Data/5-EMT"],
                "folder_structure": ["5_EMT"],
            }
        },
    )
    found = find_project_folder("EMT")
    assert found is not None
    assert found.resolve() == emt_folders["rich"].resolve()
