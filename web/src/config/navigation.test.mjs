import assert from 'node:assert/strict';
import test from 'node:test';

import {
  MAIN_NAV,
  NAV_GROUP_ORDER,
  buildNavSections,
  findMainNav,
  findSubNav,
  lookupMainNav,
  normalizeLegacyNavPair,
  parseNavFromStorage,
  resolveStoredNavigation,
} from './navigation.js';

test('every main nav item belongs to a known sidebar group', () => {
  for (const item of MAIN_NAV) {
    assert.ok(item.group, `missing group on ${item.id}`);
    assert.ok(NAV_GROUP_ORDER.includes(item.group), `unknown group ${item.group} on ${item.id}`);
  }
});

test('sidebar groups include workbench and unified library', () => {
  const ids = MAIN_NAV.map((item) => item.id);
  assert.ok(ids.includes('workbench'));
  assert.ok(ids.includes('library'));
});

test('legacy storage all_files redirects to library', () => {
  const parsed = parseNavFromStorage('data_storage:all_files');
  assert.equal(parsed.main, 'library');
  assert.equal(parsed.sub, 'all_files');
});

test('legacy dashboard redirects to workbench home', () => {
  const pair = normalizeLegacyNavPair('overview', 'dashboard');
  assert.equal(pair.main, 'workbench');
  assert.equal(pair.sub, 'home');
});

test('library wet_lab sub resolves to wet_lab files explorer preset path', () => {
  const sub = findSubNav('library', 'wet_lab');
  assert.equal(sub.libraryMain, 'wet_lab');
  assert.equal(sub.librarySub, 'files');
  assert.equal(sub.screen, 'document_library');
});

test('buildNavSections preserves all modules', () => {
  const sections = buildNavSections(MAIN_NAV);
  const flattened = sections.flatMap((section) => section.items);
  assert.equal(flattened.length, MAIN_NAV.length);
  assert.equal(findMainNav('workbench').defaultSub, 'home');
});

test('lookupMainNav returns null for unknown main ids', () => {
  assert.equal(lookupMainNav('tasks'), null);
  assert.equal(lookupMainNav('bioinformatics'), null);
  assert.ok(lookupMainNav('workbench'));
});

test('bare legacy tasks redirects to project portfolio', () => {
  const parsed = parseNavFromStorage('tasks');
  assert.equal(parsed.main, 'projects_data');
  assert.equal(parsed.sub, 'portfolio');
});

test('computational conda legacy preserves nested utilities section', () => {
  const parsed = parseNavFromStorage('computational:conda');
  assert.equal(parsed.main, 'computational');
  assert.equal(parsed.sub, 'utilities');
  assert.equal(parsed.hubNested, 'conda');
});

test('resolveStoredNavigation handles invalid mains with safe default', () => {
  const resolved = resolveStoredNavigation('totally_invalid:foo');
  assert.equal(resolved.main, 'workbench');
  assert.equal(resolved.sub, 'home');
});

test('every nav screen id is a non-empty string', () => {
  for (const main of MAIN_NAV) {
    for (const child of main.children) {
      assert.ok(child.screen, `missing screen on ${main.id}:${child.id}`);
      assert.equal(typeof child.screen, 'string');
    }
  }
});
