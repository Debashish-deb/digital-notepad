import { ExternalLink, FileCode, FolderOpen, GitBranch, Link2, BookOpen } from 'lucide-react';
import { classifyHref, hrefForDisplay, linkLabel } from '../utils/linkUtils.js';
import CopyPathButton from './CopyPathButton.jsx';

const KIND_ICON = {
  doi: BookOpen,
  github: GitBranch,
  external: ExternalLink,
  file: FileCode,
  path: FolderOpen,
  text: Link2,
};

export default function SmartLink({
  href,
  children,
  onFileClick,
  showCopy = true,
  className = '',
  maxLabelLen,
}) {
  const value = (href || children || '').trim();
  if (!value) return <span className="muted">—</span>;

  const kind = classifyHref(value);
  const Icon = KIND_ICON[kind] || Link2;
  const externalUrl = hrefForDisplay(value);
  const label = children || linkLabel(value, maxLabelLen);

  if (kind === 'file' || kind === 'path') {
    if (onFileClick) {
      return (
        <span className={`smart-link smart-link--${kind} ${className}`.trim()}>
          <button type="button" className="smart-link-btn" onClick={() => onFileClick(value)} title={value}>
            <Icon size={14} aria-hidden />
            <span className="smart-link-label">{label}</span>
          </button>
          {showCopy && <CopyPathButton value={value} />}
        </span>
      );
    }
    return (
      <span className={`smart-link smart-link--${kind} ${className}`.trim()} title={value}>
        <Icon size={14} aria-hidden />
        <code className="smart-link-path">{label}</code>
        {showCopy && <CopyPathButton value={value} />}
      </span>
    );
  }

  if (externalUrl) {
    return (
      <span className={`smart-link smart-link--${kind} ${className}`.trim()}>
        <a href={externalUrl} target="_blank" rel="noopener noreferrer" className={`smart-link-anchor smart-link--${kind}`} title={value}>
          <Icon size={14} aria-hidden />
          <span className="smart-link-label">{label}</span>
          <ExternalLink size={12} className="smart-link-external-icon" aria-hidden />
        </a>
        {showCopy && <CopyPathButton value={value} />}
      </span>
    );
  }

  return (
    <span className={`smart-link smart-link--${kind} ${className}`.trim()} title={value}>
      <Icon size={14} aria-hidden />
      <span className="smart-link-label">{label}</span>
      {showCopy && <CopyPathButton value={value} />}
    </span>
  );
}
