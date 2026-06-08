/**
 * Data Pad API — section document read/write, AI assists, backups.
 */
import { apiGet, apiPost, apiPut } from './client.js';

export function fetchDatapadConfig() {
  return apiGet('/api/datapad/config');
}

export function fetchDatapadDocument(projectCode, relativePath) {
  const params = new URLSearchParams({
    project_code: projectCode,
    relative_path: relativePath,
  });
  return apiGet('/api/datapad/document', { params });
}

export function saveDatapadDocument({
  projectCode,
  relativePath,
  content,
  createBackup = true,
  expectedEtag = null,
}) {
  return apiPut('/api/datapad/document', {
    body: {
      project_code: projectCode,
      relative_path: relativePath,
      content,
      create_backup: createBackup,
      expected_etag: expectedEtag,
    },
  });
}

export function suggestDatapadHeadings(content, docType = 'markdown') {
  return apiPost('/api/datapad/suggest-headings', {
    body: { content, doc_type: docType },
  });
}

export function proofreadDatapadContent(content) {
  return apiPost('/api/datapad/proofread', { body: { content } });
}

export function fetchDatapadSectionSummary(projectCode, sectionId = null) {
  const params = new URLSearchParams({ project_code: projectCode });
  if (sectionId) params.set('section_id', sectionId);
  return apiGet('/api/datapad/section-summary', { params });
}

export function restoreDatapadBackup({ projectCode, relativePath, backupPath }) {
  return apiPost('/api/datapad/restore-backup', {
    body: {
      project_code: projectCode,
      relative_path: relativePath,
      backup_path: backupPath,
    },
  });
}

export function ensureProjectReadme(projectCode) {
  const code = encodeURIComponent(projectCode);
  return apiPost(`/api/projects/${code}/ensure-readme`);
}
