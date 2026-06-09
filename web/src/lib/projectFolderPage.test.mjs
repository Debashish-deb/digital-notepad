import assert from 'node:assert/strict';
import test from 'node:test';
import {
  findFolderTreeNode,
  projectFolderScopeLabel,
  projectFolderTreeRoot,
  summarizeProjectFolderTree,
} from './projectFolderPage.js';

test('projectFolderTreeRoot builds projects path', () => {
  assert.equal(projectFolderTreeRoot('12_SPACE'), 'projects/12_SPACE');
  assert.equal(projectFolderTreeRoot(''), null);
});

test('summarizeProjectFolderTree counts scoped folders and files', () => {
  const nodes = [
    { path: 'projects/12_SPACE', label: '12_SPACE', file_count: 2 },
    { path: 'projects/12_SPACE/1_Management & planning', label: 'Management', file_count: 5 },
    { path: 'projects/14_CIN2_project', label: 'Other', file_count: 99 },
  ];
  const summary = summarizeProjectFolderTree(nodes, 'projects/12_SPACE');
  assert.equal(summary.hasTree, true);
  assert.equal(summary.folderCount, 2);
  assert.equal(summary.fileCount, 7);
});

test('findFolderTreeNode resolves normalized path', () => {
  const nodes = [{ path: 'projects/12_SPACE/3_Data & Figures', file_count: 12 }];
  const hit = findFolderTreeNode(nodes, 'projects/12_SPACE/3_Data & Figures');
  assert.equal(hit?.file_count, 12);
});

test('projectFolderScopeLabel prefers name with code', () => {
  assert.equal(projectFolderScopeLabel('SPACE study', '12_SPACE'), 'SPACE study (12_SPACE)');
  assert.equal(projectFolderScopeLabel('', '12_SPACE'), '12_SPACE');
});
