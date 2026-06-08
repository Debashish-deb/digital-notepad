"""README auto-create for project workspaces."""
from __future__ import annotations

from pathlib import Path

import pytest

from app_skeleton.api import paths
from app_skeleton.api.project_processor import (
    _readme_template,
    _twin_has_readme,
    ensure_project_readme,
)


def test_readme_template_includes_catalog_fields():
    text = _readme_template(
        {
            "project_name": "EMT",
            "project_lead": "Zhihan Liang",
            "principal_investigator": "Anniina Färkkilä",
            "project_summary": "EMT profiling study",
            "status": "discontinued",
            "disease_focus": "Ovarian cancer",
        }
    )
    assert "# EMT" in text
    assert "Zhihan Liang" in text
    assert "EMT profiling study" in text
    assert "Discontinued" in text


def test_twin_has_readme_checks_content_library():
    twin = {
        "document_index": [],
        "content_library": {
            "sections": [
                {
                    "text_files": [{"path": "README.md"}],
                }
            ]
        },
    }
    assert _twin_has_readme(twin) is True


@pytest.fixture()
def project_with_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "projects" / "SampleProj"
    root.mkdir(parents=True)
    monkeypatch.setattr(paths, "PROJECTS_ROOT", tmp_path / "projects")
    monkeypatch.setenv("PROJECTS_ROOT", str(tmp_path / "projects"))
    monkeypatch.setattr(
        "app_skeleton.api.project_processor._load_catalog",
        lambda: {
            "SampleProj": {
                "project_code": "SampleProj",
                "project_name": "Sample Project",
                "folder_path": "SampleProj",
            }
        },
    )
    monkeypatch.setattr(
        "app_skeleton.api.project_processor.get_content_root",
        lambda code: root if code == "SampleProj" else None,
    )
    monkeypatch.setattr(
        "app_skeleton.api.project_processor.load_processed",
        lambda code: None,
    )
    monkeypatch.setattr(
        "app_skeleton.api.project_processor.get_digital_twin",
        lambda code, refresh=False: {"project_code": code, "document_index": [{"path": "README.md"}]},
    )
    monkeypatch.setattr(
        "app_skeleton.api.project_processor.save_processed",
        lambda code, data: None,
    )
    return root


def test_ensure_project_readme_creates_sample_file(project_with_root: Path):
    result = ensure_project_readme("SampleProj")
    assert result["created"] is True
    readme = project_with_root / "README.md"
    assert readme.is_file()
    assert "# Sample Project" in readme.read_text(encoding="utf-8")
