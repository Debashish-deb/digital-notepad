import assert from 'node:assert/strict';
import test from 'node:test';
import { groupProjectsForScope } from './projectScopeGroups.js';

const SAMPLE = [
  {
    code: 'KRAS',
    name: 'KRAS Study',
    status: 'active',
    index: 5,
    categoryLabel: 'Spatial & Multi-Omics Studies',
    diseaseFocus: 'Lung Cancer',
    lead: 'Ada Junquera',
  },
  {
    code: 'Fanconi',
    name: 'Fanconi Project',
    status: 'completed',
    index: 8,
    categoryLabel: 'External Lab Collaborations',
    diseaseFocus: '',
    lead: '',
  },
];

test('groupProjectsForScope nests status then category', () => {
  const groups = groupProjectsForScope(SAMPLE, { selectedCodes: new Set(['KRAS']) });
  assert.equal(groups.length, 2);
  assert.equal(groups[0].status, 'active');
  assert.equal(groups[0].categories[0].label, 'Spatial & Multi-Omics Studies');
  assert.equal(groups[0].selectedCount, 1);
});

test('groupProjectsForScope filters by query', () => {
  const groups = groupProjectsForScope(SAMPLE, { query: 'fanconi' });
  assert.equal(groups.length, 1);
  assert.equal(groups[0].status, 'completed');
});

test('groupProjectsForScope filters selected only', () => {
  const groups = groupProjectsForScope(SAMPLE, {
    filter: 'selected',
    selectedCodes: new Set(['KRAS']),
  });
  assert.equal(groups.length, 1);
  assert.equal(groups[0].projectCount, 1);
});
