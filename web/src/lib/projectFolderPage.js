import { buildFolderTreeFromNodes, normalizeFolderPath } from './documentFolderTree.js';

/**
 * Document-library folder tree root for a single project workspace.
 * @param {string|null|undefined} projectCode
 * @returns {string|null}
 */
export function projectFolderTreeRoot(projectCode) {
  const code = String(projectCode || '').trim();
  if (!code) return null;
  return `projects/${code}`;
}

/**
 * Aggregate folder/file counts for nodes under a project root.
 * @param {Array<{ path: string, file_count?: number }>} nodes
 * @param {string|null} rootPrefix
 */
export function summarizeProjectFolderTree(nodes = [], rootPrefix = null) {
  const root = normalizeFolderPath(rootPrefix);
  if (!root) {
    return { folderCount: 0, fileCount: 0, hasTree: false };
  }

  const scoped = nodes.filter((node) => {
    const path = normalizeFolderPath(node.path);
    return path === root || path.startsWith(`${root}/`);
  });

  const tree = buildFolderTreeFromNodes(scoped, root);
  let folderCount = 0;
  let fileCount = 0;

  const walk = (items) => {
    items.forEach((item) => {
      folderCount += 1;
      fileCount += Number(item.file_count) || 0;
      if (item.children?.length) walk(item.children);
    });
  };
  walk(tree);

  const rootNode = scoped.find((node) => normalizeFolderPath(node.path) === root);
  if (rootNode && !folderCount) {
    folderCount = 1;
    fileCount = Number(rootNode.file_count) || 0;
  }

  return {
    folderCount,
    fileCount,
    hasTree: tree.length > 0 || Boolean(rootNode),
  };
}

/**
 * Lookup a flat category-tree node by path.
 * @param {Array<{ path: string }>} nodes
 * @param {string|null|undefined} path
 */
export function findFolderTreeNode(nodes = [], path) {
  const normalized = normalizeFolderPath(path);
  if (!normalized) return null;
  return nodes.find((node) => normalizeFolderPath(node.path) === normalized) || null;
}

/**
 * Human label for the project hub scope breadcrumb.
 * @param {string|null|undefined} projectName
 * @param {string|null|undefined} projectCode
 */
export function projectFolderScopeLabel(projectName, projectCode) {
  const name = String(projectName || '').trim();
  const code = String(projectCode || '').trim();
  if (name && code && name !== code) return `${name} (${code})`;
  return name || code || 'Project';
}
