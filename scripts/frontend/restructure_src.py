#!/usr/bin/env python3
"""One-shot React src restructure: feature folders, shared layer, path aliases."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "app_skeleton" / "ui" / "react_frontend" / "src"

# (relative to SRC) file or directory moves
DIR_MOVES = [
    ("screens", "pages"),
    ("api", "services"),
    ("utils", "lib"),
    ("hooks", "shared/hooks"),
]

COMPONENT_MOVES: dict[str, str] = {
    # shared layout / shell
    "Sidebar.jsx": "shared/layout/Sidebar.jsx",
    "ModuleShell.jsx": "shared/layout/ModuleShell.jsx",
    "ErrorBoundary.jsx": "shared/layout/ErrorBoundary.jsx",
    "CentralTaskpadBackground.jsx": "shared/layout/CentralTaskpadBackground.jsx",
    "HubNestedNav.jsx": "shared/layout/HubNestedNav.jsx",
    "HubNestedNav.css": "shared/layout/HubNestedNav.css",
    "SubsectionCoverCard.jsx": "shared/layout/SubsectionCoverCard.jsx",
    "SubsectionCoverCard.css": "shared/layout/SubsectionCoverCard.css",
    "ModuleCoverHero.jsx": "shared/layout/ModuleCoverHero.jsx",
    "CompactCornerSearch.jsx": "shared/layout/CompactCornerSearch.jsx",
    "CompactCornerSearch.css": "shared/layout/CompactCornerSearch.css",
    "LanguageSwitcher.jsx": "shared/layout/LanguageSwitcher.jsx",
    "MetricCard.jsx": "shared/layout/MetricCard.jsx",
    "GlassCardStack.jsx": "shared/layout/GlassCardStack.jsx",
    "GlassCardStack.css": "shared/layout/GlassCardStack.css",
    "Timeline.jsx": "shared/layout/Timeline.jsx",
    # shared ui
    "ExpandableText.jsx": "shared/ui/ExpandableText.jsx",
    "FileTypeBadge.jsx": "shared/ui/FileTypeBadge.jsx",
    "SmartLink.jsx": "shared/ui/SmartLink.jsx",
    "CopyPathButton.jsx": "shared/ui/CopyPathButton.jsx",
    "SwimmingProjectTopics.jsx": "shared/ui/SwimmingProjectTopics.jsx",
    # ai assistant
    "ChatWidget.jsx": "features/ai-assistant/components/ChatWidget.jsx",
    "AgentCategorySelector.jsx": "features/ai-assistant/components/AgentCategorySelector.jsx",
    "AiAssistant3DScene.jsx": "features/ai-assistant/components/AiAssistant3DScene.jsx",
    "AiSolarBrainVisual.jsx": "features/ai-assistant/components/AiSolarBrainVisual.jsx",
    "AiAssistantChat.css": "features/ai-assistant/styles/AiAssistantChat.css",
    "AiAssistant3D.css": "features/ai-assistant/styles/AiAssistant3D.css",
    # search
    "GlobalSearchOverlay.jsx": "features/search/components/GlobalSearchOverlay.jsx",
    # documents
    "DocumentCategoryBar.jsx": "features/documents/components/DocumentCategoryBar.jsx",
    "DocumentCategoryFileList.jsx": "features/documents/components/DocumentCategoryFileList.jsx",
    "DocumentCategorySidebar.jsx": "features/documents/components/DocumentCategorySidebar.jsx",
    "DocumentExportMenu.jsx": "features/documents/components/DocumentExportMenu.jsx",
    "DocumentExportMenu.css": "features/documents/components/DocumentExportMenu.css",
    "DocumentFileSearch.jsx": "features/documents/components/DocumentFileSearch.jsx",
    "DocumentFormatter.jsx": "features/documents/components/DocumentFormatter.jsx",
    "DocumentFormatter.css": "features/documents/components/DocumentFormatter.css",
    "DocumentMediaGallery.jsx": "features/documents/components/DocumentMediaGallery.jsx",
    "DocumentPreviewPane.jsx": "features/documents/components/DocumentPreviewPane.jsx",
    "DocumentPreviewPane.css": "features/documents/components/DocumentPreviewPane.css",
    "DocumentProofreadPanel.jsx": "features/documents/components/DocumentProofreadPanel.jsx",
    "DocumentSectionHeader.jsx": "features/documents/components/DocumentSectionHeader.jsx",
    "DocumentSubfolderAlbums.jsx": "features/documents/components/DocumentSubfolderAlbums.jsx",
    "DocumentViewer.jsx": "features/documents/components/DocumentViewer.jsx",
    "DocumentViewer.css": "features/documents/components/DocumentViewer.css",
    "DocumentViewerExpand.jsx": "features/documents/components/DocumentViewerExpand.jsx",
    "DocumentViewerExpand.css": "features/documents/components/DocumentViewerExpand.css",
    "DocumentViewerToolbar.jsx": "features/documents/components/DocumentViewerToolbar.jsx",
    "DocumentViewerToolbar.css": "features/documents/components/DocumentViewerToolbar.css",
    "LabDocumentExplorer.jsx": "features/documents/components/LabDocumentExplorer.jsx",
    "LabDocumentMapPanel.jsx": "features/documents/components/LabDocumentMapPanel.jsx",
    "LabDocumentMapPanel.css": "features/documents/components/LabDocumentMapPanel.css",
    "LabDocumentsBrowser.jsx": "features/documents/components/LabDocumentsBrowser.jsx",
    "ScientificFileExplorer.jsx": "features/documents/components/ScientificFileExplorer.jsx",
    "ScientificFileExplorer.css": "features/documents/components/ScientificFileExplorer.css",
    "MediaViewer.jsx": "features/documents/components/MediaViewer.jsx",
    "SpreadsheetPreview.jsx": "features/documents/components/SpreadsheetPreview.jsx",
    "CodePreview.jsx": "features/documents/components/CodePreview.jsx",
    "CopyableCodeBlock.jsx": "features/documents/components/CopyableCodeBlock.jsx",
    # projects / portfolio
    "DigitalTwinPanel.jsx": "features/projects/components/DigitalTwinPanel.jsx",
    "NotepadWidget.jsx": "features/projects/components/NotepadWidget.jsx",
    "ProjectBrandMark.jsx": "features/projects/components/ProjectBrandMark.jsx",
    "ProjectCohortStrip.jsx": "features/projects/components/ProjectCohortStrip.jsx",
    "ProjectContentLibrary.jsx": "features/projects/components/ProjectContentLibrary.jsx",
    "ProjectCoverMeta.jsx": "features/projects/components/ProjectCoverMeta.jsx",
    "ProjectCoverNarrative.jsx": "features/projects/components/ProjectCoverNarrative.jsx",
    "ProjectCoverTeamStrip.jsx": "features/projects/components/ProjectCoverTeamStrip.jsx",
    "ProjectDigitalTwinView.jsx": "features/projects/components/ProjectDigitalTwinView.jsx",
    "ProjectDocumentsBrowser.jsx": "features/projects/components/ProjectDocumentsBrowser.jsx",
    "ProjectFolderBrowser.jsx": "features/projects/components/ProjectFolderBrowser.jsx",
    "ProjectIntroHeader.jsx": "features/projects/components/ProjectIntroHeader.jsx",
    "ProjectIntroHeader.css": "features/projects/components/ProjectIntroHeader.css",
    "ProjectLogPanel.jsx": "features/projects/components/ProjectLogPanel.jsx",
    "ProjectModalityPills.jsx": "features/projects/components/ProjectModalityPills.jsx",
    "ProjectReadmeSetupPanel.jsx": "features/projects/components/ProjectReadmeSetupPanel.jsx",
    "ProjectRegistryEditor.jsx": "features/projects/components/ProjectRegistryEditor.jsx",
    "ProjectResourceCorner.jsx": "features/projects/components/ProjectResourceCorner.jsx",
    "ProjectTeamRoster.jsx": "features/projects/components/ProjectTeamRoster.jsx",
    "ProjectTwinStats.jsx": "features/projects/components/ProjectTwinStats.jsx",
    "ProjectWorkspaceTaskbar.jsx": "features/projects/components/ProjectWorkspaceTaskbar.jsx",
    "RunPipelineTab.jsx": "features/projects/components/RunPipelineTab.jsx",
    "DataPadEditor.jsx": "features/projects/components/DataPadEditor.jsx",
    "LazyDataPadEditor.jsx": "features/projects/components/LazyDataPadEditor.jsx",
    "WorkspaceSectionDataPad.jsx": "features/projects/components/WorkspaceSectionDataPad.jsx",
    # lab
    "LabCorpusBrowser.jsx": "features/lab/components/LabCorpusBrowser.jsx",
    "LabDocumentsHub.jsx": "features/lab/components/LabDocumentsHub.jsx",
    "LabSectionTwinPanel.jsx": "features/lab/components/LabSectionTwinPanel.jsx",
    "LabTeamRoster.jsx": "features/lab/components/LabTeamRoster.jsx",
    "WetLabProtocolsBrowser.jsx": "features/lab/components/WetLabProtocolsBrowser.jsx",
    # storage / orders
    "StorageTabDocuments.jsx": "features/storage/components/StorageTabDocuments.jsx",
    "OrdersArchiveBrowser.jsx": "features/orders/components/OrdersArchiveBrowser.jsx",
    "OrdersBillingBrowser.jsx": "features/orders/components/OrdersBillingBrowser.jsx",
    "OrdersSpacePanel.jsx": "features/orders/components/OrdersSpacePanel.jsx",
    # auth
    "AuthLoginPanel.jsx": "features/auth/components/AuthLoginPanel.jsx",
    # computational / 3d
    "Pipeline3DScene.jsx": "features/computational/components/Pipeline3DScene.jsx",
    "ModelViewer3D.jsx": "features/computational/components/ModelViewer3D.jsx",
    # imaging
    "ImageTileViewer.jsx": "features/imaging/components/ImageTileViewer.jsx",
    "ImageTileViewer.css": "features/imaging/components/ImageTileViewer.css",
    # taskpad
    "TaskpadSheet.jsx": "features/taskpad/components/TaskpadSheet.jsx",
}

SUBDIR_MOVES = [
    ("components/search", "features/search/components"),
    ("components/auth", "features/auth/components"),
    ("components/overview", "features/overview/components"),
    ("components/projectPortfolio", "features/projects/components/portfolio"),
    ("components/computationalHub", "features/computational/components/hub"),
    ("components/common", "shared/ui/common"),
]

IMPORT_REPLACEMENTS = [
    (r"from ['\"](\.\./)*screens/", r"from '@/pages/"),
    (r"from ['\"]\./screens/", r"from '@/pages/"),
    (r"from ['\"](\.\./)*api/", r"from '@/services/"),
    (r"from ['\"]\./api/", r"from '@/services/"),
    (r"from ['\"](\.\./)*utils/", r"from '@/lib/"),
    (r"from ['\"]\./utils/", r"from '@/lib/"),
    (r"from ['\"](\.\./)*hooks/", r"from '@/shared/hooks/"),
    (r"from ['\"]\./hooks/", r"from '@/shared/hooks/"),
    (r"from ['\"](\.\./)+components/Sidebar", r"from '@/shared/layout/Sidebar"),
    (r"from ['\"](\.\./)+components/ModuleShell", r"from '@/shared/layout/ModuleShell"),
    (r"from ['\"](\.\./)+components/ErrorBoundary", r"from '@/shared/layout/ErrorBoundary"),
    (r"from ['\"](\.\./)+components/CentralTaskpadBackground", r"from '@/shared/layout/CentralTaskpadBackground"),
    (r"from ['\"](\.\./)+components/ChatWidget", r"from '@/features/ai-assistant/components/ChatWidget"),
    (r"from ['\"](\.\./)+components/GlobalSearchOverlay", r"from '@/features/search/components/GlobalSearchOverlay"),
    (r"from ['\"](\.\./)+components/search/", r"from '@/features/search/components/"),
    (r"from ['\"]\./components/search/", r"from '@/features/search/components/"),
    (r"from ['\"](\.\./)+components/projectPortfolio/", r"from '@/features/projects/components/portfolio/"),
    (r"from ['\"](\.\./)+components/overview/", r"from '@/features/overview/components/"),
    (r"from ['\"](\.\./)+components/computationalHub/", r"from '@/features/computational/components/hub/"),
    (r"from ['\"](\.\./)+components/common/", r"from '@/shared/ui/common/"),
    (r"from ['\"](\.\./)+components/auth/", r"from '@/features/auth/components/"),
    (r"import\(['\"](\.\./)*screens/", r"import('@/pages/"),
    (r"import\(['\"]\./screens/", r"import('@/pages/"),
    (r"import\(['\"](\.\./)*components/", r"import('@/features/"),
]

# Per-component explicit import rewrites (old path fragment -> new @ path)
COMPONENT_IMPORT_MAP = {
    "components/Sidebar": "@/shared/layout/Sidebar",
    "components/ModuleShell": "@/shared/layout/ModuleShell",
    "components/ErrorBoundary": "@/shared/layout/ErrorBoundary",
    "components/CentralTaskpadBackground": "@/shared/layout/CentralTaskpadBackground",
    "components/HubNestedNav": "@/shared/layout/HubNestedNav",
    "components/SubsectionCoverCard": "@/shared/layout/SubsectionCoverCard",
    "components/ModuleCoverHero": "@/shared/layout/ModuleCoverHero",
    "components/CompactCornerSearch": "@/shared/layout/CompactCornerSearch",
    "components/LanguageSwitcher": "@/shared/layout/LanguageSwitcher",
    "components/MetricCard": "@/shared/layout/MetricCard",
    "components/GlassCardStack": "@/shared/layout/GlassCardStack",
    "components/Timeline": "@/shared/layout/Timeline",
    "components/ExpandableText": "@/shared/ui/ExpandableText",
    "components/FileTypeBadge": "@/shared/ui/FileTypeBadge",
    "components/SmartLink": "@/shared/ui/SmartLink",
    "components/CopyPathButton": "@/shared/ui/CopyPathButton",
    "components/SwimmingProjectTopics": "@/shared/ui/SwimmingProjectTopics",
    "components/ChatWidget": "@/features/ai-assistant/components/ChatWidget",
    "components/AgentCategorySelector": "@/features/ai-assistant/components/AgentCategorySelector",
    "components/AiAssistant3DScene": "@/features/ai-assistant/components/AiAssistant3DScene",
    "components/AiSolarBrainVisual": "@/features/ai-assistant/components/AiSolarBrainVisual",
    "components/GlobalSearchOverlay": "@/features/search/components/GlobalSearchOverlay",
    "components/AuthLoginPanel": "@/features/auth/components/AuthLoginPanel",
    "components/TaskpadSheet": "@/features/taskpad/components/TaskpadSheet",
    "components/LabCorpusBrowser": "@/features/lab/components/LabCorpusBrowser",
    "components/LabDocumentsHub": "@/features/lab/components/LabDocumentsHub",
    "components/LabTeamRoster": "@/features/lab/components/LabTeamRoster",
    "components/StorageTabDocuments": "@/features/storage/components/StorageTabDocuments",
    "components/OrdersSpacePanel": "@/features/orders/components/OrdersSpacePanel",
    "components/OrdersArchiveBrowser": "@/features/orders/components/OrdersArchiveBrowser",
    "components/OrdersBillingBrowser": "@/features/orders/components/OrdersBillingBrowser",
    "components/Pipeline3DScene": "@/features/computational/components/Pipeline3DScene",
    "components/ModelViewer3D": "@/features/computational/components/ModelViewer3D",
    "components/ImageTileViewer": "@/features/imaging/components/ImageTileViewer",
}


def git_mv(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        return
    subprocess.run(["git", "mv", str(src), str(dest)], cwd=ROOT, check=True)


def move_dirs() -> None:
    for old, new in DIR_MOVES:
        src = SRC / old
        dest = SRC / new
        if src.exists() and not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            git_mv(src, dest)


def move_subdirs() -> None:
    for old, new in SUBDIR_MOVES:
        src = SRC / old
        dest = SRC / new
        if src.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                subprocess.run(["rm", "-rf", str(dest)], check=False)
            git_mv(src, dest)


def move_components() -> None:
    comp = SRC / "components"
    for name, rel_dest in COMPONENT_MOVES.items():
        src = comp / name
        dest = SRC / rel_dest
        if src.exists():
            git_mv(src, dest)
    # move theme to styles
    theme_src = SRC / "theme"
    theme_dest = SRC / "styles" / "theme"
    if theme_src.exists() and not theme_dest.exists():
        (SRC / "styles").mkdir(parents=True, exist_ok=True)
        git_mv(theme_src, theme_dest)
    # remove empty components dir artifacts
    overview_css = comp / "OverviewReadingPage.css"
    if overview_css.exists():
        git_mv(overview_css, SRC / "features/overview/components/OverviewReadingPage.css")


def build_component_import_map() -> dict[str, str]:
    mapping = dict(COMPONENT_IMPORT_MAP)
    for name, rel_dest in COMPONENT_MOVES.items():
        if not name.endswith((".jsx", ".js")):
            continue
        stem = Path(name).stem
        old = f"components/{stem}"
        new = "@/" + rel_dest.replace(".jsx", "").replace(".js", "")
        mapping[old] = new
    for old_prefix, new_prefix in [
        ("components/search", "features/search/components"),
        ("components/auth", "features/auth/components"),
        ("components/overview", "features/overview/components"),
        ("components/projectPortfolio", "features/projects/components/portfolio"),
        ("components/computationalHub", "features/computational/components/hub"),
        ("components/common", "shared/ui/common"),
    ]:
        mapping[old_prefix] = f"@/{new_prefix}"
    return mapping


def patch_imports() -> None:
    import_map = build_component_import_map()
    for path in list(SRC.rglob("*.js")) + list(SRC.rglob("*.jsx")):
        text = path.read_text(encoding="utf-8")
        original = text
        for old, new in import_map.items():
            text = text.replace(f"from '../{old}", f"from '{new}")
            text = text.replace(f'from "../{old}', f'from "{new}')
            text = text.replace(f"from './{old}", f"from '{new}")
            text = text.replace(f'from "./{old}', f'from "{new}')
            text = re.sub(rf"from ['\"](\.\./)+{re.escape(old)}", f"from '{new}", text)
            text = text.replace(f"import('./{old}", f"import('{new}")
            text = text.replace(f"import('../{old}", f"import('{new}")
            text = re.sub(rf"import\(['\"](\.\./)+{re.escape(old)}", f"import('{new}", text)
        for pattern, repl in IMPORT_REPLACEMENTS:
            text = re.sub(pattern, repl, text)
        # screens -> pages in lazy imports
        text = text.replace("import('./screens/", "import('@/pages/")
        text = text.replace('import("./screens/', 'import("@/pages/')
        text = text.replace("import('../screens/", "import('@/pages/")
        text = text.replace('import("../screens/', 'import("@/pages/')
        text = text.replace("from './screens/", "from '@/pages/")
        text = text.replace('from "./screens/', 'from "@/pages/')
        text = text.replace("from '../screens/", "from '@/pages/")
        text = text.replace('from "../screens/', 'from "@/pages/')
        text = text.replace("from './api/", "from '@/services/")
        text = text.replace("from '../api/", "from '@/services/")
        text = text.replace("from './utils/", "from '@/lib/")
        text = text.replace("from '../utils/", "from '@/lib/")
        text = text.replace("from './hooks/", "from '@/shared/hooks/")
        text = text.replace("from '../hooks/", "from '@/shared/hooks/")
        text = text.replace("from './theme/", "from '@/styles/theme/")
        text = text.replace("from '../theme/", "from '@/styles/theme/")
        if text != original:
            path.write_text(text, encoding="utf-8")


def main() -> None:
    move_dirs()
    move_subdirs()
    move_components()
    patch_imports()
    print("Restructure complete. Run: npm run build")


if __name__ == "__main__":
    main()
