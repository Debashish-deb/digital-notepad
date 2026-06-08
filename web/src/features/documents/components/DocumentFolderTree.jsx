import { useMemo, useState } from 'react';
import { ChevronDown, ChevronRight, FolderOpen, FolderTree, Search } from 'lucide-react';
import { buildFolderTreeFromNodes } from '@/lib/documentFolderTree.js';

function FolderTreeNode({
  node,
  depth = 0,
  selectedPath,
  expandedPaths,
  onToggleExpand,
  onSelect,
}) {
  const hasChildren = node.children?.length > 0;
  const isExpanded = expandedPaths.has(node.path);
  const isSelected = selectedPath === node.path;

  return (
    <div className="sfe-folder-node" style={{ '--sfe-folder-depth': depth }}>
      <button
        type="button"
        className={`sfe-folder-item${isSelected ? ' is-active' : ''}`}
        onClick={() => onSelect(node.path)}
        title={node.path}
      >
        {hasChildren ? (
          <span
            className="sfe-folder-expand"
            role="button"
            tabIndex={0}
            aria-expanded={isExpanded}
            aria-label={isExpanded ? 'Collapse folder' : 'Expand folder'}
            onClick={(event) => {
              event.stopPropagation();
              onToggleExpand(node.path);
            }}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                event.stopPropagation();
                onToggleExpand(node.path);
              }
            }}
          >
            {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </span>
        ) : (
          <span className="sfe-folder-expand sfe-folder-expand--spacer" aria-hidden />
        )}
        <FolderOpen size={14} className="sfe-folder-icon" aria-hidden />
        <span className="sfe-folder-label">{node.label}</span>
        <span className="sfe-folder-count">{node.file_count}</span>
      </button>
      {hasChildren && isExpanded ? (
        <div className="sfe-folder-children">
          {node.children.map((child) => (
            <FolderTreeNode
              key={child.path}
              node={child}
              depth={depth + 1}
              selectedPath={selectedPath}
              expandedPaths={expandedPaths}
              onToggleExpand={onToggleExpand}
              onSelect={onSelect}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

export default function DocumentFolderTree({
  nodes = [],
  rootPrefix = null,
  selectedPath = null,
  onSelect,
  loading = false,
  error = null,
}) {
  const [query, setQuery] = useState('');
  const [expandedPaths, setExpandedPaths] = useState(() => new Set());

  const tree = useMemo(
    () => buildFolderTreeFromNodes(nodes, rootPrefix),
    [nodes, rootPrefix],
  );

  const filteredTree = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return tree;

    const filterNodes = (items) => items
      .map((node) => {
        const childMatches = filterNodes(node.children || []);
        const selfMatch =
          node.label.toLowerCase().includes(q) ||
          node.path.toLowerCase().includes(q);
        if (!selfMatch && !childMatches.length) return null;
        return { ...node, children: childMatches };
      })
      .filter(Boolean);

    return filterNodes(tree);
  }, [tree, query]);

  const totalFolders = nodes.length;
  const visibleCount = filteredTree.reduce((sum, node) => sum + 1 + (node.children?.length || 0), 0);

  const handleToggleExpand = (path) => {
    setExpandedPaths((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  const handleSelect = (path) => {
    onSelect?.(path);
    if (path.includes('/')) {
      setExpandedPaths((prev) => {
        const next = new Set(prev);
        const parts = path.split('/');
        let acc = '';
        parts.slice(0, -1).forEach((part, index) => {
          acc = index === 0 ? part : `${acc}/${part}`;
          next.add(acc);
        });
        return next;
      });
    }
  };

  return (
    <aside className="sfe-folder-tree" aria-label="Folder tree">
      <header className="sfe-folder-tree__header">
        <h3 className="sfe-folder-tree__title">
          <FolderTree size={16} aria-hidden />
          Folders
        </h3>
        <span className="sfe-folder-tree__meta muted text-footnote">
          {loading ? 'Loading…' : `${totalFolders} indexed`}
        </span>
      </header>

      <label className="sfe-folder-tree__search">
        <Search size={14} aria-hidden />
        <input
          type="search"
          className="form-input sfe-folder-tree__search-input"
          placeholder="Filter folders…"
          aria-label="Filter folders"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </label>

      {error ? (
        <p className="sfe-folder-tree__empty muted text-footnote" role="alert">{error}</p>
      ) : loading ? (
        <p className="sfe-folder-tree__empty muted text-footnote">Loading folder tree…</p>
      ) : filteredTree.length === 0 ? (
        <p className="sfe-folder-tree__empty muted text-footnote">
          {query ? 'No folders match your filter.' : 'No folders in this scope.'}
        </p>
      ) : (
        <div className="sfe-folder-tree__list">
          {filteredTree.map((node) => (
            <FolderTreeNode
              key={node.path}
              node={node}
              selectedPath={selectedPath}
              expandedPaths={expandedPaths}
              onToggleExpand={handleToggleExpand}
              onSelect={handleSelect}
            />
          ))}
        </div>
      )}

      {query && filteredTree.length > 0 ? (
        <p className="sfe-folder-tree__hint muted text-footnote">
          Showing {visibleCount} matching folders
        </p>
      ) : null}
    </aside>
  );
}
