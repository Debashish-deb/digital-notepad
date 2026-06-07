#!/usr/bin/env python3
"""
Premium Project Structure Analyzer

Analyzes selected project folders, collects file/folder metadata, generates:
  - PROJECT_STRUCTURE_ANALYSIS.md
  - PROJECT_STRUCTURE_METADATA.json
  - PROJECT_STRUCTURE_STATS.json

Default usage from a repository:
  python tools/audit/structure_analyzer.py

Useful examples:
  python tools/audit/structure_analyzer.py --root .
  python tools/audit/structure_analyzer.py --root . --max-depth 6 --hash
  python tools/audit/structure_analyzer.py --paths app_skeleton/data docs scripts

Why this version is safer than the original:
  - Valid Mermaid node IDs even for paths containing spaces/slashes.
  - CLI options instead of hard-coded-only behavior.
  - Permission/symlink/loop handling.
  - Recursive directory size calculation.
  - Markdown escaping for table safety.
  - JSON-serializable stats.
  - Optional SHA-256 hashing.
  - Limits Mermaid size so huge repos do not destroy the report viewer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import platform
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_ANALYSIS_PATHS = [
    "app_skeleton/data",
    "app_skeleton/storage",
    "docs",
    "scripts",
    "configs",
    "reports",
]

DEFAULT_SKIP_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".cache",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".qodo",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".nuxt",
    ".turbo",
    ".expo",
    ".dart_tool",
    ".idea",
    ".vscode",
}

TEXT_EXTENSIONS_FOR_LINE_COUNT = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".json",
    ".jsonl",
    ".md",
    ".txt",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".cfg",
    ".sql",
    ".sh",
    ".bash",
    ".zsh",
    ".html",
    ".css",
    ".scss",
    ".r",
    ".go",
    ".rs",
    ".java",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".dart",
}

FILE_ICON_MAP = {
    ".py": "🐍",
    ".js": "📜",
    ".jsx": "⚛️",
    ".ts": "📘",
    ".tsx": "⚛️",
    ".json": "📋",
    ".jsonl": "📋",
    ".md": "📝",
    ".csv": "📊",
    ".xlsx": "📊",
    ".xls": "📊",
    ".parquet": "🧱",
    ".pdf": "📕",
    ".docx": "📘",
    ".doc": "📘",
    ".pptx": "📙",
    ".png": "🖼️",
    ".jpg": "🖼️",
    ".jpeg": "🖼️",
    ".webp": "🖼️",
    ".svg": "🎨",
    ".txt": "📄",
    ".yml": "⚙️",
    ".yaml": "⚙️",
    ".toml": "⚙️",
    ".ini": "⚙️",
    ".sql": "🗄️",
    ".sh": "💻",
    ".html": "🌐",
    ".css": "🎨",
    ".scss": "🎨",
    ".ipynb": "📓",
    ".r": "📊",
    ".go": "🦫",
    ".rs": "🦀",
    ".java": "☕",
    ".c": "🔧",
    ".cpp": "🔧",
    ".h": "🔧",
    ".hpp": "🔧",
    ".dart": "🎯",
    ".tif": "🔬",
    ".tiff": "🔬",
    ".ome.tif": "🔬",
    ".ome.tiff": "🔬",
}


@dataclass
class WarningItem:
    level: str
    path: str
    message: str


@dataclass
class ScanContext:
    root: Path
    max_depth: int
    skip_names: set[str]
    include_hidden: bool
    follow_symlinks: bool
    hash_files: bool
    count_lines: bool
    output_dir: Path
    warnings: list[WarningItem] = field(default_factory=list)
    visited_dirs: set[tuple[int, int]] = field(default_factory=set)

    def warn(self, level: str, path: Path | str, message: str) -> None:
        self.warnings.append(WarningItem(level=level, path=str(path), message=message))


@dataclass
class Stats:
    total_directories: int = 0
    total_files: int = 0
    total_size_bytes: int = 0
    total_line_count: int = 0
    by_extension: Counter[str] = field(default_factory=Counter)
    by_directory: dict[str, dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: {"files": 0, "size_bytes": 0}))
    largest_files: list[dict[str, Any]] = field(default_factory=list)
    newest_files: list[dict[str, Any]] = field(default_factory=list)
    oldest_files: list[dict[str, Any]] = field(default_factory=list)
    error_count: int = 0
    skipped_count: int = 0
    symlink_count: int = 0

    def to_jsonable(self, top_n: int = 50) -> dict[str, Any]:
        largest = sorted(self.largest_files, key=lambda item: item["size_bytes"], reverse=True)[:top_n]
        newest = sorted(self.newest_files, key=lambda item: item["modified_epoch"], reverse=True)[:top_n]
        oldest = sorted(self.oldest_files, key=lambda item: item["modified_epoch"])[:top_n]
        return {
            "total_directories": self.total_directories,
            "total_files": self.total_files,
            "total_size_bytes": self.total_size_bytes,
            "total_size_human": format_size(self.total_size_bytes),
            "total_line_count": self.total_line_count,
            "by_extension": dict(sorted(self.by_extension.items(), key=lambda item: item[1], reverse=True)),
            "by_directory": dict(sorted(self.by_directory.items(), key=lambda item: item[1]["size_bytes"], reverse=True)),
            "largest_files": largest,
            "newest_files": newest,
            "oldest_files": oldest,
            "error_count": self.error_count,
            "skipped_count": self.skipped_count,
            "symlink_count": self.symlink_count,
        }


class MermaidBuilder:
    """Builds safe Mermaid graph diagrams with valid node IDs and size limits."""

    def __init__(self, max_nodes: int = 350) -> None:
        self.max_nodes = max_nodes
        self.counter = 0
        self.truncated = False
        self.lines: list[str] = ["```mermaid", "graph TD"]

    def add_box(self, label: str) -> str:
        node_id = f"n{self.counter}"
        self.counter += 1
        safe_label = escape_mermaid_label(label)
        self.lines.append(f'    {node_id}["{safe_label}"]')
        return node_id

    def add_edge(self, parent_id: str, child_id: str) -> None:
        self.lines.append(f"    {parent_id} --> {child_id}")

    def can_add(self) -> bool:
        return self.counter < self.max_nodes

    def finish(self) -> str:
        if self.truncated:
            note_id = self.add_box("Diagram truncated\\nIncrease --max-mermaid-nodes to show more")
            root_id = "n0"
            self.add_edge(root_id, note_id)
        self.lines.append("```")
        return "\n".join(self.lines)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def format_size(size_bytes: int | float | None) -> str:
    if size_bytes is None:
        return "N/A"
    value = float(size_bytes)
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    for unit in units:
        if abs(value) < 1024.0 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} PB"


def safe_relative(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except Exception:
        return str(path)


def safe_stat(path: Path, follow_symlinks: bool) -> os.stat_result | None:
    try:
        return path.stat() if follow_symlinks else path.lstat()
    except OSError:
        return None


def iso_from_epoch(epoch: float | int | None) -> str | None:
    if epoch is None:
        return None
    return datetime.fromtimestamp(epoch).astimezone().isoformat(timespec="seconds")


def get_extension(path: Path) -> str:
    lower_name = path.name.lower()
    if lower_name.endswith(".ome.tif"):
        return ".ome.tif"
    if lower_name.endswith(".ome.tiff"):
        return ".ome.tiff"
    return path.suffix.lower() or "no_ext"


def get_file_icon(extension: str) -> str:
    return FILE_ICON_MAP.get(extension.lower(), "📄")


def should_skip(path: Path, ctx: ScanContext) -> tuple[bool, str | None]:
    name = path.name
    if not ctx.include_hidden and name.startswith("."):
        return True, "hidden path"
    if name in ctx.skip_names:
        return True, "configured skip name"
    try:
        if path.resolve() == ctx.output_dir.resolve() or ctx.output_dir.resolve() in path.resolve().parents:
            return True, "output directory"
    except OSError:
        pass
    return False, None


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str | None:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(chunk_size)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def count_file_lines(path: Path) -> int | None:
    try:
        with path.open("rb") as handle:
            return sum(1 for _ in handle)
    except OSError:
        return None


def collect_metadata(path: Path, ctx: ScanContext, current_depth: int = 0) -> dict[str, Any] | None:
    """Recursively collect metadata for a path."""
    skip, reason = should_skip(path, ctx)
    if skip:
        ctx.warn("skip", safe_relative(path, ctx.root), reason or "skipped")
        return None

    if current_depth > ctx.max_depth:
        ctx.warn("skip", safe_relative(path, ctx.root), f"max depth exceeded ({ctx.max_depth})")
        return None

    stat = safe_stat(path, ctx.follow_symlinks)
    if stat is None:
        ctx.warn("error", safe_relative(path, ctx.root), "cannot stat path")
        return {
            "name": path.name,
            "path": safe_relative(path, ctx.root),
            "absolute_path": str(path),
            "type": "error",
            "error": "cannot stat path",
            "children": [],
        }

    is_symlink = path.is_symlink()
    if is_symlink and not ctx.follow_symlinks:
        target = None
        try:
            target = os.readlink(path)
        except OSError:
            target = "unreadable"
        return {
            "name": path.name,
            "path": safe_relative(path, ctx.root),
            "absolute_path": str(path),
            "type": "symlink",
            "target": target,
            "size_bytes": stat.st_size,
            "size_human": format_size(stat.st_size),
            "modified": iso_from_epoch(stat.st_mtime),
            "created": iso_from_epoch(stat.st_ctime),
            "is_symlink": True,
            "children": [],
        }

    try:
        is_dir = path.is_dir()
        is_file = path.is_file()
    except OSError as exc:
        ctx.warn("error", safe_relative(path, ctx.root), f"cannot determine path type: {exc}")
        return {
            "name": path.name,
            "path": safe_relative(path, ctx.root),
            "absolute_path": str(path),
            "type": "error",
            "error": str(exc),
            "children": [],
        }

    metadata: dict[str, Any] = {
        "name": path.name,
        "path": safe_relative(path, ctx.root),
        "absolute_path": str(path),
        "type": "directory" if is_dir else "file" if is_file else "other",
        "stat_size_bytes": stat.st_size,
        "size_bytes": stat.st_size,
        "size_human": format_size(stat.st_size),
        "modified": iso_from_epoch(stat.st_mtime),
        "modified_epoch": stat.st_mtime,
        "created": iso_from_epoch(stat.st_ctime),
        "created_epoch": stat.st_ctime,
        "extension": get_extension(path) if is_file else None,
        "mime_type": mimetypes.guess_type(str(path))[0] if is_file else None,
        "is_dir": is_dir,
        "is_file": is_file,
        "is_symlink": is_symlink,
        "children": [],
    }

    if is_dir:
        dir_key = (stat.st_dev, stat.st_ino)
        if dir_key in ctx.visited_dirs:
            metadata["error"] = "directory cycle detected"
            ctx.warn("error", metadata["path"], "directory cycle detected")
            return metadata
        ctx.visited_dirs.add(dir_key)

        try:
            children = sorted(path.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
        except PermissionError:
            metadata["error"] = "permission denied"
            ctx.warn("error", metadata["path"], "permission denied")
            return metadata
        except OSError as exc:
            metadata["error"] = str(exc)
            ctx.warn("error", metadata["path"], str(exc))
            return metadata

        tree_size = 0
        child_count_total = 0
        file_count_total = 0
        directory_count_total = 0

        for child in children:
            child_metadata = collect_metadata(child, ctx, current_depth + 1)
            if child_metadata is None:
                continue
            metadata["children"].append(child_metadata)
            child_size = int(child_metadata.get("size_bytes") or 0)
            tree_size += child_size
            child_count_total += 1 + int(child_metadata.get("child_count_total") or 0)
            if child_metadata.get("type") == "directory":
                directory_count_total += 1 + int(child_metadata.get("directory_count_total") or 0)
                file_count_total += int(child_metadata.get("file_count_total") or 0)
            elif child_metadata.get("type") == "file":
                file_count_total += 1
            elif child_metadata.get("type") == "symlink":
                # Keep symlink count separate in stats; do not treat as file.
                pass

        metadata["size_bytes"] = tree_size
        metadata["size_human"] = format_size(tree_size)
        metadata["children_count"] = len(metadata["children"])
        metadata["child_count_total"] = child_count_total
        metadata["file_count_total"] = file_count_total
        metadata["directory_count_total"] = directory_count_total
        return metadata

    if is_file:
        if ctx.hash_files:
            digest = sha256_file(path)
            if digest:
                metadata["sha256"] = digest
            else:
                ctx.warn("error", metadata["path"], "could not hash file")

        if ctx.count_lines and metadata["extension"] in TEXT_EXTENSIONS_FOR_LINE_COUNT:
            line_count = count_file_lines(path)
            if line_count is not None:
                metadata["line_count"] = line_count

    return metadata


def update_stats(metadata: dict[str, Any] | None, stats: Stats) -> None:
    if not metadata:
        return

    node_type = metadata.get("type")
    if metadata.get("error"):
        stats.error_count += 1

    if node_type == "directory":
        stats.total_directories += 1
        for child in metadata.get("children", []):
            update_stats(child, stats)
        return

    if node_type == "symlink":
        stats.symlink_count += 1
        return

    if node_type != "file":
        return

    stats.total_files += 1
    size = int(metadata.get("size_bytes") or 0)
    stats.total_size_bytes += size
    ext = metadata.get("extension") or "no_ext"
    stats.by_extension[ext] += 1

    line_count = int(metadata.get("line_count") or 0)
    stats.total_line_count += line_count

    path = metadata.get("path") or ""
    parent = str(Path(path).parent) if path else "."
    stats.by_directory[parent]["files"] += 1
    stats.by_directory[parent]["size_bytes"] += size

    file_summary = {
        "name": metadata.get("name", ""),
        "path": path,
        "size_bytes": size,
        "size_human": format_size(size),
        "modified": metadata.get("modified"),
        "modified_epoch": metadata.get("modified_epoch") or 0,
        "extension": ext,
    }
    if line_count:
        file_summary["line_count"] = line_count

    stats.largest_files.append(file_summary)
    stats.newest_files.append(file_summary)
    stats.oldest_files.append(file_summary)


def markdown_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def escape_mermaid_label(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace('"', "'")
        .replace("[", "(")
        .replace("]", ")")
        .replace("\n", "<br/>")
    )


def build_mermaid_for_metadata(metadata: dict[str, Any], title: str, max_nodes: int) -> str:
    builder = MermaidBuilder(max_nodes=max_nodes)
    root_label = f"{title}\nProject structure"
    root_id = builder.add_box(root_label)

    def add_node(item: dict[str, Any], parent_id: str) -> None:
        if not builder.can_add():
            builder.truncated = True
            return

        item_type = item.get("type", "unknown")
        name = item.get("name", "unknown")
        size = item.get("size_human", "N/A")

        if item_type == "directory":
            label = f"📁 {name}\n{size}\n{item.get('file_count_total', 0)} files"
        elif item_type == "symlink":
            label = f"🔗 {name}\n{size}"
        elif item_type == "error":
            label = f"⚠️ {name}\n{item.get('error', 'error')}"
        else:
            icon = get_file_icon(item.get("extension") or "")
            label = f"{icon} {name}\n{size}"

        node_id = builder.add_box(label)
        builder.add_edge(parent_id, node_id)

        if item_type == "directory":
            for child in item.get("children", []):
                add_node(child, node_id)
                if builder.truncated:
                    return

    add_node(metadata, root_id)
    return builder.finish()


def build_overview_mermaid(all_metadata: dict[str, dict[str, Any] | None], stats: Stats, max_nodes: int) -> str:
    builder = MermaidBuilder(max_nodes=max_nodes)
    root = builder.add_box(
        f"Project Structure Audit\n{stats.total_directories} directories · {stats.total_files} files · {format_size(stats.total_size_bytes)}"
    )

    for label, metadata in all_metadata.items():
        if not metadata or not builder.can_add():
            builder.truncated = True
            break
        dir_label = (
            f"📁 {label}\n"
            f"{metadata.get('file_count_total', 0)} files · "
            f"{metadata.get('directory_count_total', 0)} dirs · "
            f"{metadata.get('size_human', 'N/A')}"
        )
        node = builder.add_box(dir_label)
        builder.add_edge(root, node)

    return builder.finish()


def build_tree_text(metadata: dict[str, Any], max_depth: int = 6, current_depth: int = 0, max_items: int = 800) -> list[str]:
    lines: list[str] = []
    counter = 0

    def walk(item: dict[str, Any], depth: int) -> None:
        nonlocal counter
        if counter >= max_items:
            if not lines or not lines[-1].endswith("truncated"):
                lines.append("  " * depth + "… truncated")
            return
        if depth > max_depth:
            return

        icon = "📁" if item.get("type") == "directory" else "🔗" if item.get("type") == "symlink" else get_file_icon(item.get("extension") or "")
        extra = item.get("size_human", "N/A")
        if item.get("type") == "directory":
            extra = f"{extra}, {item.get('file_count_total', 0)} files"
        lines.append(f"{'  ' * depth}- {icon} {item.get('name', 'unknown')} ({extra})")
        counter += 1

        for child in item.get("children", []):
            walk(child, depth + 1)

    walk(metadata, current_depth)
    return lines


def make_markdown_report(
    *,
    root: Path,
    all_metadata: dict[str, dict[str, Any] | None],
    directories_to_analyze: list[tuple[str, Path]],
    stats_json: dict[str, Any],
    warnings: list[WarningItem],
    mermaid_diagrams: dict[str, str],
    overview_mermaid: str,
    args: argparse.Namespace,
) -> str:
    lines: list[str] = [
        "# Project Structure Analysis",
        "",
        f"**Generated:** {now_iso()}",
        f"**Project Root:** `{root}`",
        f"**Python:** `{platform.python_version()}`",
        f"**Platform:** `{platform.platform()}`",
        "",
        "## Executive Summary",
        "",
        f"- **Directories analyzed:** {stats_json['total_directories']}",
        f"- **Files analyzed:** {stats_json['total_files']}",
        f"- **Total file size:** {stats_json['total_size_human']}",
        f"- **File types detected:** {len(stats_json['by_extension'])}",
        f"- **Symlinks detected:** {stats_json['symlink_count']}",
        f"- **Warnings / errors:** {len(warnings)}",
    ]

    if args.count_lines:
        lines.append(f"- **Total counted lines:** {stats_json['total_line_count']:,}")

    lines.extend(
        [
            "",
            "## Scan Settings",
            "",
            f"- **Max depth:** {args.max_depth}",
            f"- **Include hidden:** {args.include_hidden}",
            f"- **Follow symlinks:** {args.follow_symlinks}",
            f"- **SHA-256 hashing:** {args.hash}",
            f"- **Line counting:** {args.count_lines}",
            f"- **Mermaid node limit:** {args.max_mermaid_nodes}",
            "",
            "## Directories Requested",
            "",
        ]
    )

    for label, path in directories_to_analyze:
        exists = "✓" if path.exists() else "✗"
        lines.append(f"- {exists} `{markdown_escape(label)}` → `{path}`")

    lines.extend(["", "## Overview Diagram", "", overview_mermaid, ""])

    lines.extend(
        [
            "## File Type Distribution",
            "",
            "| Extension | Count | Percentage |",
            "|---|---:|---:|",
        ]
    )
    total_files = stats_json["total_files"]
    for ext, count in list(stats_json["by_extension"].items())[:50]:
        percentage = (count / total_files * 100) if total_files else 0
        lines.append(f"| `{markdown_escape(ext)}` | {count} | {percentage:.1f}% |")

    lines.extend(
        [
            "",
            f"## Largest Files (Top {args.top_largest})",
            "",
            "| Rank | Name | Size | Extension | Path |",
            "|---:|---|---:|---|---|",
        ]
    )
    for index, file_info in enumerate(stats_json["largest_files"][: args.top_largest], 1):
        lines.append(
            "| "
            f"{index} | "
            f"{markdown_escape(file_info.get('name'))} | "
            f"{file_info.get('size_human')} | "
            f"`{markdown_escape(file_info.get('extension'))}` | "
            f"`{markdown_escape(file_info.get('path'))}` |"
        )

    lines.extend(
        [
            "",
            "## Directory Size Summary",
            "",
            "| Directory | Files | Size |",
            "|---|---:|---:|",
        ]
    )
    for dir_path, dir_stats in list(stats_json["by_directory"].items())[:50]:
        lines.append(
            f"| `{markdown_escape(dir_path)}` | {dir_stats['files']} | {format_size(dir_stats['size_bytes'])} |"
        )

    if args.count_lines:
        lines.extend(
            [
                "",
                "## Line Count Summary",
                "",
                f"Total counted lines across known text/source files: **{stats_json['total_line_count']:,}**",
                "",
            ]
        )

    lines.extend(["", "## Mermaid Diagrams by Directory", ""])
    for label, diagram in mermaid_diagrams.items():
        lines.extend([f"### {markdown_escape(label)}", "", diagram, ""])

    lines.extend(["", "## Compact Tree View", ""])
    for label, metadata in all_metadata.items():
        if not metadata:
            continue
        lines.extend([f"### `{markdown_escape(label)}`", "", "```text"])
        lines.extend(build_tree_text(metadata, max_depth=min(args.max_depth, 8)))
        lines.extend(["```", ""])

    lines.extend(["", "## Warnings and Validation", ""])
    if not warnings:
        lines.append("No warnings found.")
    else:
        lines.extend(["| Level | Path | Message |", "|---|---|---|"])
        for warning in warnings[:500]:
            lines.append(
                f"| {markdown_escape(warning.level)} | `{markdown_escape(warning.path)}` | {markdown_escape(warning.message)} |"
            )
        if len(warnings) > 500:
            lines.append(f"| info | `...` | {len(warnings) - 500} additional warnings omitted from Markdown report. See JSON output. |")

    lines.extend(
        [
            "",
            "## Output Files",
            "",
            "- `PROJECT_STRUCTURE_ANALYSIS.md` — human-readable audit report.",
            "- `PROJECT_STRUCTURE_METADATA.json` — full nested metadata tree.",
            "- `PROJECT_STRUCTURE_STATS.json` — summary statistics and warnings.",
            "",
        ]
    )
    return "\n".join(lines)


def resolve_project_root(script_path: Path, cli_root: str | None) -> Path:
    if cli_root:
        return Path(cli_root).expanduser().resolve()

    # Preserve the original expected layout: tools/audit/structure_analyzer.py -> project root.
    try:
        if script_path.parent.name == "audit" and script_path.parent.parent.name == "tools":
            return script_path.parents[2].resolve()
    except IndexError:
        pass

    # Fallback: current working directory is safer than guessing incorrectly.
    return Path.cwd().resolve()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze selected project folders and generate Markdown/JSON structure reports."
    )
    parser.add_argument("--root", help="Project root. Defaults to tools/audit layout or current working directory.")
    parser.add_argument(
        "--paths",
        nargs="*",
        default=DEFAULT_ANALYSIS_PATHS,
        help="Relative paths under --root to analyze.",
    )
    parser.add_argument(
        "--output",
        default="reports/structure_analysis",
        help="Output directory relative to --root unless absolute.",
    )
    parser.add_argument("--max-depth", type=int, default=10, help="Maximum recursion depth per requested path.")
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include hidden files/folders. By default they are skipped.",
    )
    parser.add_argument(
        "--follow-symlinks",
        action="store_true",
        help="Follow symlinks. Off by default to avoid loops and external traversal.",
    )
    parser.add_argument("--hash", action="store_true", help="Calculate SHA-256 for files. Slower for large projects.")
    parser.add_argument(
        "--count-lines",
        action="store_true",
        help="Count lines for known text/source extensions. Slower but useful for audits.",
    )
    parser.add_argument(
        "--skip",
        nargs="*",
        default=sorted(DEFAULT_SKIP_NAMES),
        help="Directory/file names to skip.",
    )
    parser.add_argument("--top-largest", type=int, default=50, help="Number of largest files shown in report.")
    parser.add_argument(
        "--max-mermaid-nodes",
        type=int,
        default=350,
        help="Maximum nodes per Mermaid diagram. Prevents huge broken reports.",
    )
    parser.add_argument("--quiet", action="store_true", help="Reduce console output.")
    return parser.parse_args(argv)


def print_header(root: Path, args: argparse.Namespace) -> None:
    if args.quiet:
        return
    print("=" * 88)
    print("PROJECT STRUCTURE ANALYZER")
    print("=" * 88)
    print(f"Project root : {root}")
    print(f"Output       : {args.output}")
    print(f"Max depth    : {args.max_depth}")
    print(f"Paths        : {', '.join(args.paths)}")
    print("=" * 88)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    script_path = Path(__file__).resolve()
    root = resolve_project_root(script_path, args.root)
    output_dir = Path(args.output).expanduser()
    if not output_dir.is_absolute():
        output_dir = root / output_dir
    output_dir = output_dir.resolve()

    print_header(root, args)

    ctx = ScanContext(
        root=root,
        max_depth=max(0, args.max_depth),
        skip_names=set(args.skip or []),
        include_hidden=args.include_hidden,
        follow_symlinks=args.follow_symlinks,
        hash_files=args.hash,
        count_lines=args.count_lines,
        output_dir=output_dir,
    )

    requested_paths: list[tuple[str, Path]] = []
    for raw_path in args.paths:
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = root / path
        requested_paths.append((raw_path, path.resolve()))

    all_metadata: dict[str, dict[str, Any] | None] = {}

    if not args.quiet:
        print("\n[1/5] Collecting metadata...")

    for label, path in requested_paths:
        if not path.exists():
            ctx.warn("missing", label, "requested path does not exist")
            all_metadata[label] = None
            if not args.quiet:
                print(f"  ✗ Missing: {label}")
            continue

        if not args.quiet:
            print(f"  ✓ Analyzing: {label}")
        all_metadata[label] = collect_metadata(path, ctx)

    if not args.quiet:
        print("\n[2/5] Calculating statistics...")

    stats = Stats()
    stats.skipped_count = sum(1 for warning in ctx.warnings if warning.level == "skip")
    for metadata in all_metadata.values():
        update_stats(metadata, stats)
    stats_json = stats.to_jsonable(top_n=max(args.top_largest, 50))

    if not args.quiet:
        print(f"  Directories: {stats.total_directories}")
        print(f"  Files      : {stats.total_files}")
        print(f"  Size       : {format_size(stats.total_size_bytes)}")
        print(f"  Warnings   : {len(ctx.warnings)}")

    if not args.quiet:
        print("\n[3/5] Generating Mermaid diagrams...")

    overview_mermaid = build_overview_mermaid(all_metadata, stats, max_nodes=args.max_mermaid_nodes)
    mermaid_diagrams: dict[str, str] = {}
    for label, metadata in all_metadata.items():
        if metadata:
            mermaid_diagrams[label] = build_mermaid_for_metadata(metadata, label, max_nodes=args.max_mermaid_nodes)

    if not args.quiet:
        print("\n[4/5] Writing reports...")

    output_dir.mkdir(parents=True, exist_ok=True)

    report = make_markdown_report(
        root=root,
        all_metadata=all_metadata,
        directories_to_analyze=requested_paths,
        stats_json=stats_json,
        warnings=ctx.warnings,
        mermaid_diagrams=mermaid_diagrams,
        overview_mermaid=overview_mermaid,
        args=args,
    )

    document_path = output_dir / "PROJECT_STRUCTURE_ANALYSIS.md"
    metadata_path = output_dir / "PROJECT_STRUCTURE_METADATA.json"
    stats_path = output_dir / "PROJECT_STRUCTURE_STATS.json"

    document_path.write_text(report, encoding="utf-8")
    metadata_path.write_text(json.dumps(all_metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    stats_bundle = {
        "generated": now_iso(),
        "project_root": str(root),
        "settings": {
            "paths": args.paths,
            "max_depth": args.max_depth,
            "include_hidden": args.include_hidden,
            "follow_symlinks": args.follow_symlinks,
            "hash": args.hash,
            "count_lines": args.count_lines,
            "skip": sorted(ctx.skip_names),
        },
        "stats": stats_json,
        "warnings": [asdict(warning) for warning in ctx.warnings],
    }
    stats_path.write_text(json.dumps(stats_bundle, indent=2, ensure_ascii=False), encoding="utf-8")

    if not args.quiet:
        print(f"  Markdown: {document_path}")
        print(f"  Metadata: {metadata_path}")
        print(f"  Stats   : {stats_path}")

    if not args.quiet:
        print("\n[5/5] Validation summary...")
        if ctx.warnings:
            print(f"  Completed with {len(ctx.warnings)} warning(s). See PROJECT_STRUCTURE_STATS.json.")
            for warning in ctx.warnings[:10]:
                print(f"    • [{warning.level}] {warning.path}: {warning.message}")
            if len(ctx.warnings) > 10:
                print(f"    • ... {len(ctx.warnings) - 10} more")
        else:
            print("  No warnings found.")

        print("\n" + "=" * 88)
        print("STRUCTURE ANALYSIS COMPLETE")
        print("=" * 88)
        print(f"Total directories : {stats.total_directories}")
        print(f"Total files       : {stats.total_files}")
        print(f"Total size        : {format_size(stats.total_size_bytes)}")
        print(f"File types        : {len(stats.by_extension)}")
        print(f"Reports saved to  : {output_dir}")
        print("=" * 88)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
