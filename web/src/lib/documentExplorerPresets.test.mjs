import assert from 'node:assert/strict';
import test from 'node:test';

import {
  getExplorerPreset,
  getLibraryScopeContext,
  resolveExplorerNav,
} from './documentExplorerPresets.js';

test('resolveExplorerNav maps library wet_lab to wet_lab files preset', () => {
  const resolved = resolveExplorerNav('library', 'wet_lab');
  assert.equal(resolved.mainId, 'wet_lab');
  assert.equal(resolved.subId, 'files');
});

test('getExplorerPreset scopes library cycif to CyCIF filters', () => {
  const preset = getExplorerPreset('library', 'cycif');
  assert.equal(preset.domainTab, 'wet_lab');
  assert.equal(preset.filters.cycif_only, true);
  assert.equal(preset.folderTreeRoot, 'WET_LAB');
});

test('getLibraryScopeContext resolves library lab_admin for backend nav scope', () => {
  const scope = getLibraryScopeContext('library', 'lab_admin');
  assert.ok(scope);
  assert.equal(scope.ui_main_id, 'library');
  assert.equal(scope.ui_sub_id, 'lab_admin');
  assert.equal(scope.main_id, 'overview');
  assert.equal(scope.sub_id, 'get_started');
  assert.equal(scope.domain_tab, 'overview');
  assert.equal(scope.filters.domain, 'administration');
});
