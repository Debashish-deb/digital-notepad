/**
 * Build a hierarchical folder tree from flat category-tree nodes.
 * @param {Array<{ path: string, label: string, depth?: number, file_count?: number }>} nodes
 * @param {string|null|undefined} rootPrefix - optional path prefix to scope the tree
 * @returns {{ path: string, label: string, file_count: number, depth: number, children: object[] }[]}
 */
export function buildFolderTreeFromNodes(nodes = [], rootPrefix = null) {
  if (!nodes.length) return [];

  const normalizedRoot = rootPrefix ? normalizeFolderPath(rootPrefix) : null;
  const nodeByPath = new Map();

  for (const node of nodes) {
    const path = normalizeFolderPath(node.path);
    if (!path) continue;
    if (normalizedRoot && path !== normalizedRoot && !path.startsWith(`${normalizedRoot}/`)) {
      continue;
    }
    nodeByPath.set(path, {
      path,
      label: node.label || path.split('/').pop() || path,
      file_count: Number(node.file_count) || 0,
      depth: Number(node.depth) || path.split('/').length,
      children: [],
    });
  }

  const roots = [];
  const sortedPaths = [...nodeByPath.keys()].sort((a, b) => a.localeCompare(b));

  for (const path of sortedPaths) {
    const entry = nodeByPath.get(path);
    if (!entry) continue;

    if (normalizedRoot) {
      if (path === normalizedRoot) {
        roots.push(entry);
        continue;
      }
      const parentPath = path.slice(0, path.lastIndexOf('/'));
      const parent = nodeByPath.get(parentPath);
      if (parent) parent.children.push(entry);
      else if (parentPath === normalizedRoot || parentPath.startsWith(`${normalizedRoot}/`)) {
        roots.push(entry);
      }
      continue;
    }

    const parentPath = path.includes('/') ? path.slice(0, path.lastIndexOf('/')) : '';
    if (!parentPath) {
      roots.push(entry);
      continue;
    }
    const parent = nodeByPath.get(parentPath);
    if (parent) parent.children.push(entry);
    else roots.push(entry);
  }

  const sortTree = (items) => {
    items.sort((a, b) => a.label.localeCompare(b.label));
    items.forEach((item) => sortTree(item.children));
  };
  sortTree(roots);
  return roots;
}

/** @param {string|null|undefined} path */
export function normalizeFolderPath(path) {
  return String(path || '')
    .replace(/\\/g, '/')
    .replace(/^\/+/, '')
    .replace(/\/+$/, '');
}

/**
 * Split a folder path into breadcrumb segments.
 * @param {string|null|undefined} path
 * @param {string|null|undefined} rootPrefix
 */
export function folderPathBreadcrumbs(path, rootPrefix = null) {
  const normalized = normalizeFolderPath(path);
  if (!normalized) return [];

  const root = normalizeFolderPath(rootPrefix);
  const segments = normalized.split('/');
  const crumbs = [];
  let acc = '';

  segments.forEach((segment, index) => {
    acc = index === 0 ? segment : `${acc}/${segment}`;
    if (root && acc.length < root.length && acc !== root) return;
    crumbs.push({
      path: acc,
      label: segment,
      isRoot: acc === root,
    });
  });

  return crumbs;
}
