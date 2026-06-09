import { useEffect, useMemo, useState } from 'react';
import {
  BookOpen,
  BookMarked,
  Calendar,
  Database,
  Edit,
  FileText,
  FolderTree,
  LayoutDashboard,
  NotebookPen,
  Scale,
} from 'lucide-react';
import { useGuiT } from '@/i18n/useGuiT.js';
import { useTaskpad } from '@/contexts/TaskpadContext.jsx';

export const WORKSPACE_TAB_IDS = new Set([
  'overview',
  'folders',
  'plan',
  'data',
  'methods',
  'writing',
  'archive',
  'log',
  'notebook',
  'decisions',
]);

export default function useWorkspaceTabs(projectCode, initialTab = 'overview') {
  const { t } = useGuiT();
  const { setTargetSection } = useTaskpad();
  const [workspaceMenu, setWorkspaceMenu] = useState(
    WORKSPACE_TAB_IDS.has(initialTab) ? initialTab : 'overview',
  );

  const menuItems = useMemo(
    () => [
      { id: 'overview', label: t('workspace.overview'), icon: LayoutDashboard },
      { id: 'folders', label: t('workspace.folders', 'Project files'), icon: FolderTree },
      { id: 'plan', label: t('workspace.plan'), icon: Calendar },
      { id: 'data', label: t('workspace.data'), icon: Database },
      { id: 'methods', label: t('workspace.methods'), icon: FileText },
      { id: 'writing', label: t('workspace.writing'), icon: Edit },
      { id: 'archive', label: t('workspace.archive'), icon: BookMarked },
      { id: 'log', label: t('workspace.log'), icon: BookOpen },
      { id: 'notebook', label: t('workspace.notebook'), icon: NotebookPen },
      { id: 'decisions', label: t('workspace.decisions'), icon: Scale },
    ],
    [t],
  );

  useEffect(() => {
    if (WORKSPACE_TAB_IDS.has(initialTab)) {
      setWorkspaceMenu(initialTab);
    }
  }, [projectCode, initialTab]);

  useEffect(() => {
    setTargetSection(workspaceMenu);
  }, [workspaceMenu, setTargetSection]);

  const currentMenu = menuItems.find((m) => m.id === workspaceMenu) || menuItems[0];

  return {
    workspaceMenu,
    setWorkspaceMenu,
    menuItems,
    currentMenu,
  };
}
