import { ChevronRight, FolderOpen } from 'lucide-react';
import { folderPathBreadcrumbs } from '@/lib/documentFolderTree.js';

export default function DocumentFolderBreadcrumb({
  selectedPath = null,
  rootPrefix = null,
  onNavigate,
  scopeLabel = '',
}) {
  const crumbs = folderPathBreadcrumbs(selectedPath, rootPrefix);
  if (!crumbs.length) return null;

  return (
    <nav className="sfe-folder-breadcrumb" aria-label="Folder location">
      <span className="sfe-folder-breadcrumb__icon" aria-hidden>
        <FolderOpen size={14} />
      </span>
      {scopeLabel ? (
        <button
          type="button"
          className="sfe-folder-breadcrumb__crumb"
          onClick={() => onNavigate?.(rootPrefix || null)}
        >
          {scopeLabel}
        </button>
      ) : null}
      {crumbs.map((crumb, index) => (
        <span key={crumb.path} className="sfe-folder-breadcrumb__segment">
          {(scopeLabel || index > 0) ? (
            <ChevronRight size={12} className="sfe-folder-breadcrumb__sep" aria-hidden />
          ) : null}
          <button
            type="button"
            className={`sfe-folder-breadcrumb__crumb${
              index === crumbs.length - 1 ? ' is-current' : ''
            }`}
            onClick={() => onNavigate?.(crumb.path)}
            aria-current={index === crumbs.length - 1 ? 'location' : undefined}
          >
            {crumb.label}
          </button>
        </span>
      ))}
    </nav>
  );
}
