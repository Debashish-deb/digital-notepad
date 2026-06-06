"""Map search hits to in-app navigation actions (no server disk paths)."""
from __future__ import annotations

from typing import Any

from app_skeleton.api.search_models import SearchBucket, SearchNavAction

# section_id → { main, sub } for LabDocumentsBrowser-backed tabs
SECTION_NAV: dict[str, dict[str, str]] = {
    "overview_onboarding": {"main": "overview", "sub": "onboarding"},
    "overview_guidelines": {"main": "overview", "sub": "guidelines"},
    "overview_documents": {"main": "overview", "sub": "documents_permits"},
    "overview_personnel": {"main": "overview", "sub": "personnel"},
    "overview_cleaning": {"main": "overview", "sub": "cleaning"},
    "overview_research_materials": {"main": "overview", "sub": "research_materials"},
    "orders_billing": {"main": "orders", "sub": "billing"},
    "orders_archive": {"main": "orders", "sub": "archive"},
    "social_misc": {"main": "overview", "sub": "social"},
    "meetings": {"main": "data_storage", "sub": "meetings"},
    "wet_lab_files": {"main": "wet_lab", "sub": "files"},
}

PAGE_DOMAIN_TO_VAULT: dict[str, str] = {
    "projects": "projects",
    "research_hub": "research_hub",
    "computational": "computational",
    "cycif": "cycif",
    "wet_lab": "wet_lab",
    "orders": "orders",
    "overview": "overview",
    "social": "social",
    "knowledge_base": "knowledge_base",
    "notebook": "notebook",
    "tasks_decisions": "tasks_decisions",
    "administration": "administration",
}


def vault_domain_for_page(page_domain_id: str | None) -> str | None:
    if not page_domain_id:
        return None
    return PAGE_DOMAIN_TO_VAULT.get(page_domain_id.strip().lower())


def nav_for_section(section_id: str | None, *, relative_path: str | None = None) -> SearchNavAction | None:
    if not section_id:
        return None
    base = SECTION_NAV.get(section_id)
    if not base:
        return SearchNavAction(main="data_storage", sub="documents", section_id=section_id, relative_path=relative_path)
    return SearchNavAction(
        main=base["main"],
        sub=base["sub"],
        section_id=section_id,
        relative_path=relative_path,
    )


def nav_for_bucket(
    bucket: SearchBucket,
    *,
    project_code: str | None = None,
    section_id: str | None = None,
    relative_path: str | None = None,
    entry_id: str | None = None,
    wiki_id: str | None = None,
    decision_id: str | None = None,
    task_id: str | None = None,
    document_id: str | None = None,
) -> SearchNavAction | None:
    if bucket in ("lab", "file"):
        return nav_for_section(section_id, relative_path=relative_path)
    if bucket == "vault":
        return SearchNavAction(main="data_storage", sub="documents", relative_path=relative_path, query=relative_path)
    if bucket == "notebook":
        return SearchNavAction(main="projects_data", sub="notebook", entry_id=entry_id, project_code=project_code)
    if bucket == "wiki":
        return SearchNavAction(main="projects_data", sub="notebook", wiki_id=wiki_id, project_code=project_code)
    if bucket == "decision":
        return SearchNavAction(main="projects_data", sub="decisions", decision_id=decision_id, project_code=project_code)
    if bucket == "task":
        return SearchNavAction(main="wet_lab", sub="tasks", task_id=task_id, project_code=project_code)
    if bucket == "project":
        return SearchNavAction(main="projects_data", sub="portfolio", project_code=project_code)
    if bucket == "research":
        return SearchNavAction(main="ai_assistant", sub="research_kb", query=relative_path)
    return None


def hit_source_label(bucket: SearchBucket, *, section_label: str | None = None) -> str:
    labels = {
        "lab": "Lab knowledge corpus",
        "file": "Lab document index",
        "vault": "Vault metadata",
        "notebook": "Notebook entry",
        "wiki": "Research wiki",
        "decision": "Decision registry",
        "task": "Lab task",
        "project": "Project workspace",
        "research": "Research knowledge base",
    }
    if section_label and bucket in ("lab", "file"):
        return f"{labels.get(bucket, bucket)} · {section_label}"
    return labels.get(bucket, bucket.replace("_", " ").title())
