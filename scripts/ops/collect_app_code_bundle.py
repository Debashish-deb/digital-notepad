#!/usr/bin/env python3
"""Collect OMEIA application source into one indexed markdown bundle.

Focus: runnable app code (API, React UI, configs, tests, sql) with a full
numbered index of everything under scripts/.

Usage:
  python scripts/ops/collect_app_code_bundle.py
  python scripts/ops/collect_app_code_bundle.py -o docs/OMEIA_app_code_bundle.md
  python scripts/ops/collect_app_code_bundle.py --include-pipelines --max-file-kb 256

Output is suitable for LLM architecture review (single file, navigable index).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# --- Collect roots (relative to repo root) ---
APP_CODE_ROOTS: tuple[str, ...] = (
    "app_skeleton/api",
    "app_skeleton/security",
    "app_skeleton/ui/react_frontend/src",
    "app_skeleton/ui/react_frontend/scripts",
    "app_skeleton/ui/streamlit_app.py",
    "configs",
    "sql",
    "tests",
)

SCRIPT_ROOT = ROOT / "scripts"

# Optional roots (--include-pipelines)
PIPELINE_ROOTS: tuple[str, ...] = (
    "app_skeleton/pipelines",
)

# Root-level launcher / infra files
ROOT_FILES: tuple[str, ...] = (
    "start.sh",
    "start_portable.sh",
    "docker-compose.yml",
    "docker-compose.linux.yml",
    "pyproject.toml",
    "requirements.txt",
)

CODE_EXTENSIONS: frozenset[str] = frozenset({
    ".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
    ".css", ".scss", ".sql", ".sh", ".bash", ".zsh",
    ".yaml", ".yml", ".json", ".toml", ".md",
    ".html", ".xml",
})

# Paths always skipped (globs as path segments)
EXCLUDE_DIR_NAMES: frozenset[str] = frozenset({
    "__pycache__", ".git", ".venv", "venv", "node_modules", "dist", "build",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "deepcell-tf",  # vendored container library
    "farkki_ai_platform_blueprint",
    "OMEIA_Farkkila_Research_KB_AI_Brain_Package",
    "labMember",
    "CSC",
    "reports",
    "docs",  # avoid bundling prior bundles
})

EXCLUDE_PATH_PREFIXES: tuple[str, ...] = (
    "app_skeleton/data/",
    "app_skeleton/ui/react_frontend/public/processed/",
    "app_skeleton/ui/react_frontend/public/database/",
    "app_skeleton/ui/react_frontend/node_modules/",
    "configs/.env",
    "configs/secrets/",
)

EXCLUDE_FILE_NAMES: frozenset[str] = frozenset({
    ".env", ".env.local", ".DS_Store",
})

LANG_BY_EXT: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "jsx",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".css": "css",
    ".scss": "scss",
    ".sql": "sql",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "zsh",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".md": "markdown",
    ".html": "html",
    ".xml": "xml",
}


@dataclass(frozen=True)
class IndexedFile:
    index: int
    rel_path: str
    category: str
    lines: int
    size_bytes: int
    summary: str
    abs_path: Path


def _git_info() -> tuple[str, str]:
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=ROOT, text=True, stderr=subprocess.DEVNULL,
        ).strip()
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT, text=True, stderr=subprocess.DEVNULL,
        ).strip()
        return branch, commit
    except Exception:
        return "unknown", "unknown"


def _should_skip(rel: str, path: Path) -> bool:
    if path.name in EXCLUDE_FILE_NAMES:
        return True
    if path.suffix and path.suffix.lower() not in CODE_EXTENSIONS:
        return True
    norm = rel.replace("\\", "/")
    for prefix in EXCLUDE_PATH_PREFIXES:
        if norm.startswith(prefix):
            return True
    parts = Path(norm).parts
    if any(p in EXCLUDE_DIR_NAMES for p in parts):
        return True
    return False


def _categorize(rel: str) -> str:
    norm = rel.replace("\\", "/")
    if norm.startswith("scripts/"):
        sub = norm[len("scripts/") :].split("/")[0]
        return f"scripts/{sub}" if sub else "scripts"
    if norm.startswith("app_skeleton/api/"):
        return "api"
    if norm.startswith("app_skeleton/security/"):
        return "security"
    if "react_frontend/src" in norm:
        return "frontend"
    if norm.startswith("configs/"):
        return "config"
    if norm.startswith("sql/"):
        return "sql"
    if norm.startswith("tests/"):
        return "tests"
    if norm.startswith("app_skeleton/pipelines/"):
        return "pipelines"
    return "other"


def _one_line_summary(path: Path, text: str) -> str:
    lines = text.splitlines()
    for line in lines[:25]:
        s = line.strip()
        if not s or s.startswith("#!"):
            continue
        if path.suffix == ".py" and (s.startswith('"""') or s.startswith("'''")):
            inner = s.strip("\"'")
            if inner:
                return inner[:120]
            continue
        if s.startswith("#") or s.startswith("//"):
            return s.lstrip("#/ ").strip()[:120]
        if s.startswith("/*"):
            return s.lstrip("/* ").rstrip("*/").strip()[:120]
        break
    return "(no summary)"


def _collect_files(
    *,
    include_pipelines: bool,
    max_file_bytes: int,
) -> list[Path]:
    found: list[Path] = []

    def add_path(p: Path) -> None:
        if not p.is_file():
            return
        rel = str(p.relative_to(ROOT))
        if _should_skip(rel, p):
            return
        if p.stat().st_size > max_file_bytes:
            return
        found.append(p)

    for rel_root in APP_CODE_ROOTS:
        base = ROOT / rel_root
        if base.is_file():
            add_path(base)
            continue
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            add_path(path)

    if include_pipelines:
        for rel_root in PIPELINE_ROOTS:
            base = ROOT / rel_root
            if not base.is_dir():
                continue
            for path in sorted(base.rglob("*")):
                add_path(path)

    for name in ROOT_FILES:
        add_path(ROOT / name)

    if SCRIPT_ROOT.is_dir():
        for path in sorted(SCRIPT_ROOT.rglob("*")):
            add_path(path)

    # Stable sort: scripts first (for index), then category, then path
    def sort_key(p: Path) -> tuple:
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        script_first = 0 if rel.startswith("scripts/") else 1
        return (script_first, _categorize(rel), rel)

    return sorted(set(found), key=sort_key)


def _build_index(files: list[Path]) -> list[IndexedFile]:
    indexed: list[IndexedFile] = []
    for i, path in enumerate(files, start=1):
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        indexed.append(
            IndexedFile(
                index=i,
                rel_path=rel,
                category=_categorize(rel),
                lines=text.count("\n") + (1 if text else 0),
                size_bytes=path.stat().st_size,
                summary=_one_line_summary(path, text),
                abs_path=path,
            )
        )
    return indexed


def _fence_lang(path: Path) -> str:
    ext = path.suffix.lower()
    return LANG_BY_EXT.get(ext, "")


def _render_script_index(script_files: list[IndexedFile]) -> str:
    lines = [
        "## Script index (numbered)",
        "",
        "All files under `scripts/` — primary operational entry points.",
        "",
        "| # | Path | Subfolder | Lines | Summary |",
        "|---|------|-----------|------:|---------|",
    ]
    for f in script_files:
        sub = f.rel_path[len("scripts/") :].split("/")[0] if "/" in f.rel_path[len("scripts/") :] else "(root)"
        lines.append(
            f"| {f.index:03d} | `{f.rel_path}` | {sub} | {f.lines} | {f.summary.replace('|', '/')} |"
        )
    return "\n".join(lines) + "\n"


def _render_master_toc(files: list[IndexedFile]) -> str:
    by_cat: dict[str, list[IndexedFile]] = {}
    for f in files:
        by_cat.setdefault(f.category, []).append(f)

    lines = [
        "## Master file index (by category)",
        "",
        "| # | Category | Path | Lines |",
        "|---|----------|------|------:|",
    ]
    for f in files:
        lines.append(f"| {f.index:03d} | {f.category} | `{f.rel_path}` | {f.lines} |")

    lines.extend(["", "### Category totals", ""])
    for cat in sorted(by_cat):
        items = by_cat[cat]
        total_lines = sum(x.lines for x in items)
        lines.append(f"- **{cat}**: {len(items)} files, {total_lines:,} lines")

    return "\n".join(lines) + "\n"


def _render_contents(files: list[IndexedFile]) -> str:
    parts = ["## Source files", ""]
    for f in files:
        try:
            body = f.abs_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            body = f"# unreadable: {exc}"
        lang = _fence_lang(f.abs_path)
        parts.append(f"### [{f.index:03d}] `{f.rel_path}`")
        parts.append(f"*Category: {f.category} · {f.lines} lines · {f.size_bytes:,} bytes*")
        parts.append("")
        parts.append(f"```{lang}")
        parts.append(body.rstrip())
        parts.append("```")
        parts.append("")
    return "\n".join(parts)


def build_bundle(
    *,
    output: Path,
    include_pipelines: bool,
    max_file_kb: int,
) -> dict[str, int]:
    max_bytes = max_file_kb * 1024
    paths = _collect_files(include_pipelines=include_pipelines, max_file_bytes=max_bytes)
    indexed = _build_index(paths)
    script_files = [f for f in indexed if f.rel_path.startswith("scripts/")]
    branch, commit = _git_info()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    header = [
        "# OMEIA Application Code Bundle",
        "",
        f"Generated: {now}",
        f"Repository: `{ROOT.name}` · branch `{branch}` · commit `{commit}`",
        "",
        "Automated export for architecture / code review. Each file has a stable index `[NNN]`.",
        "",
        f"- **Files included:** {len(indexed)}",
        f"- **Scripts indexed:** {len(script_files)}",
        f"- **Max file size:** {max_file_kb} KB (larger files skipped)",
        f"- **Pipelines included:** {'yes' if include_pipelines else 'no'}",
        "",
        "---",
        "",
    ]

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as fh:
        fh.write("\n".join(header))
        fh.write(_render_script_index(script_files))
        fh.write("\n---\n\n")
        fh.write(_render_master_toc(indexed))
        fh.write("\n---\n\n")
        fh.write(_render_contents(indexed))

    return {
        "files": len(indexed),
        "scripts": len(script_files),
        "lines": sum(f.lines for f in indexed),
        "bytes": output.stat().st_size,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=ROOT / "docs" / "OMEIA_app_code_bundle.md",
        help="Output markdown path (default: docs/OMEIA_app_code_bundle.md)",
    )
    parser.add_argument(
        "--include-pipelines",
        action="store_true",
        help="Include app_skeleton/pipelines (excludes vendored deepcell-tf)",
    )
    parser.add_argument(
        "--max-file-kb",
        type=int,
        default=512,
        help="Skip individual files larger than this (default: 512)",
    )
    args = parser.parse_args()
    out = args.output if args.output.is_absolute() else ROOT / args.output

    stats = build_bundle(
        output=out,
        include_pipelines=args.include_pipelines,
        max_file_kb=args.max_file_kb,
    )
    print(f"Wrote {out}")
    print(f"  files: {stats['files']}  scripts: {stats['scripts']}  lines: {stats['lines']:,}  size: {stats['bytes']:,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
