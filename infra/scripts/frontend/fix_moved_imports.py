#!/usr/bin/env python3
"""Fix broken relative imports after src restructure."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "omeia" / "ui" / "react_frontend" / "src"

ALIAS_TARGETS = [
    "contexts",
    "config",
    "data",
    "i18n",
    "services",
    "lib",
    "pages",
    "assets",
    "types",
    "styles",
    "shared/hooks",
]

SEARCH_ROOT = SRC / "features" / "search" / "components"


def fix_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    original = text

    for target in ALIAS_TARGETS:
        text = re.sub(rf"from ['\"](?:\.\./)+{target}/", f"from '@/{target}/", text)
        text = re.sub(rf'from ["\'](?:\.\./)+{target}/', f"from '@/{target}/", text)

    # same-folder search imports after search/ folder flatten
    if path.parent == SEARCH_ROOT:
        text = text.replace("from './search/", "from './")
        text = text.replace('from "./search/', 'from "./')

    # layout siblings moved to features
    text = text.replace("from './TaskpadSheet.jsx'", "from '@/features/taskpad/components/TaskpadSheet.jsx'")
    text = text.replace('from "./TaskpadSheet.jsx"', 'from "@/features/taskpad/components/TaskpadSheet.jsx"')
    text = text.replace("from './CompactCornerSearch.jsx'", "from '@/shared/layout/CompactCornerSearch.jsx'")
    text = text.replace('from "./CompactCornerSearch.jsx"', 'from "@/shared/layout/CompactCornerSearch.jsx"')
    text = text.replace("from './ModuleCoverHero.jsx'", "from '@/shared/layout/ModuleCoverHero.jsx'")
    text = text.replace('from "./ModuleCoverHero.jsx"', 'from "@/shared/layout/ModuleCoverHero.jsx"')
    text = text.replace("from './SubsectionCoverCard.jsx'", "from '@/shared/layout/SubsectionCoverCard.jsx'")
    text = text.replace('from "./SubsectionCoverCard.jsx"', 'from "@/shared/layout/SubsectionCoverCard.jsx"')

    # shared UI moved out of feature folders
    for name, alias in [
        ("SmartLink", "@/shared/ui/SmartLink.jsx"),
        ("ExpandableText", "@/shared/ui/ExpandableText.jsx"),
        ("FileTypeBadge", "@/shared/ui/FileTypeBadge.jsx"),
        ("CopyPathButton", "@/shared/ui/CopyPathButton.jsx"),
        ("GlassCardStack", "@/shared/layout/GlassCardStack.jsx"),
        ("DocumentPreviewPane", "@/features/documents/components/DocumentPreviewPane.jsx"),
        ("DocumentFileSearch", "@/features/documents/components/DocumentFileSearch.jsx"),
        ("DocumentCategoryFileList", "@/features/documents/components/DocumentCategoryFileList.jsx"),
        ("MediaViewer", "@/features/documents/components/MediaViewer.jsx"),
    ]:
        text = text.replace(f"from './{name}.jsx'", f"from '{alias}'")
        text = text.replace(f'from "./{name}.jsx"', f'from "{alias}"')

    text = text.replace(
        "import './GlassCardStack.css'",
        "import '@/shared/layout/GlassCardStack.css'",
    )
    text = text.replace(
        'import "./GlassCardStack.css"',
        'import "@/shared/layout/GlassCardStack.css"',
    )
    text = text.replace(
        "import './OverviewReadingPage.css'",
        "import '@/features/overview/components/OverviewReadingPage.css'",
    )
    text = text.replace(
        'import "./OverviewReadingPage.css"',
        'import "@/features/overview/components/OverviewReadingPage.css"',
    )

    # ai-assistant styles path
    text = text.replace("import './AiAssistantChat.css'", "import '@/features/ai-assistant/styles/AiAssistantChat.css'")
    text = text.replace('import "./AiAssistantChat.css"', 'import "@/features/ai-assistant/styles/AiAssistantChat.css"')
    text = text.replace("import './AiAssistant3D.css'", "import '@/features/ai-assistant/styles/AiAssistant3D.css'")
    text = text.replace('import "./AiAssistant3D.css"', 'import "@/features/ai-assistant/styles/AiAssistant3D.css"')
    text = text.replace("import './search/UnifiedSearch.css'", "import '@/features/search/components/UnifiedSearch.css'")
    text = text.replace('import "./search/UnifiedSearch.css"', 'import "@/features/search/components/UnifiedSearch.css"')

    # remaining ../components/ -> try to map via known paths
    text = re.sub(
        r"from ['\"](?:\.\./)+components/([^'\"]+)['\"]",
        lambda m: f"from '@/{resolve_component_import(m.group(1))}'",
        text,
    )

    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def resolve_component_import(rel: str) -> str:
    rel = rel.replace(".jsx", "").replace(".js", "")
    candidates = list(SRC.rglob(f"{Path(rel).name}.jsx")) + list(SRC.rglob(f"{Path(rel).name}.js"))
    for c in candidates:
        if "node_modules" in str(c):
            continue
        try:
            return str(c.relative_to(SRC)).replace("\\", "/").removesuffix(".jsx").removesuffix(".js")
        except ValueError:
            pass
    return f"features/unknown/{rel}"


def main() -> None:
    changed = 0
    for folder in [SRC / "features", SRC / "shared", SRC / "pages"]:
        if not folder.exists():
            continue
        for path in folder.rglob("*.jsx"):
            if fix_file(path):
                changed += 1
        for path in folder.rglob("*.js"):
            if fix_file(path):
                changed += 1
    print(f"Updated {changed} files")


if __name__ == "__main__":
    main()
