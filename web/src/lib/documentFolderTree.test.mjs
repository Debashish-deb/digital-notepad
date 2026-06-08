import assert from 'node:assert/strict';
import test from 'node:test';
import {
  buildFolderTreeFromNodes,
  folderPathBreadcrumbs,
  normalizeFolderPath,
} from './documentFolderTree.js';

test('normalizeFolderPath strips slashes and backslashes', () => {
  assert.equal(normalizeFolderPath('/WET_LAB/protocols/'), 'WET_LAB/protocols');
  assert.equal(normalizeFolderPath('WET_LAB\\protocols'), 'WET_LAB/protocols');
});

test('buildFolderTreeFromNodes scopes to rootPrefix', () => {
  const nodes = [
    { path: 'WET_LAB', label: 'WET_LAB', depth: 1, file_count: 10 },
    { path: 'WET_LAB/protocols', label: 'protocols', depth: 2, file_count: 4 },
    { path: 'projects', label: 'projects', depth: 1, file_count: 99 },
  ];
  const tree = buildFolderTreeFromNodes(nodes, 'WET_LAB');
  assert.equal(tree.length, 1);
  assert.equal(tree[0].path, 'WET_LAB');
  assert.equal(tree[0].children.length, 1);
  assert.equal(tree[0].children[0].path, 'WET_LAB/protocols');
});

test('folderPathBreadcrumbs builds clickable segments', () => {
  const crumbs = folderPathBreadcrumbs('WET_LAB/protocols/SOPs', 'WET_LAB');
  assert.deepEqual(crumbs.map((c) => c.path), [
    'WET_LAB',
    'WET_LAB/protocols',
    'WET_LAB/protocols/SOPs',
  ]);
});
