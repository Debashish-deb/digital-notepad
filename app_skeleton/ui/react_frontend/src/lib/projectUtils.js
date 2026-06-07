import { getProjectByCode } from '../data/projectsCatalog.js';

export function asArray(value) {
  if (Array.isArray(value)) return value;
  if (value == null || value === '') return [];
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (trimmed.startsWith('[')) {
      try {
        const parsed = JSON.parse(trimmed);
        return Array.isArray(parsed) ? parsed : [trimmed];
      } catch {
        return [trimmed];
      }
    }
    if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
      return trimmed.slice(1, -1).split(',').map((s) => s.trim().replace(/^"|"$/g, '')).filter(Boolean);
    }
    return [trimmed];
  }
  return [];
}

export function mergeProjectRecord(apiProject = {}, catalogProject = null) {
  const catalog = catalogProject || getProjectByCode(apiProject.project_code) || {};
  const merged = { ...catalog, ...apiProject };

  return {
    ...merged,
    collaborators: asArray(merged.collaborators),
    members: asArray(merged.members),
    modalities: asArray(merged.modalities),
    folder_structure: asArray(merged.folder_structure),
    project_summary: merged.project_summary || catalog.project_summary || merged.research_question || '',
    research_question: merged.research_question || catalog.research_question || merged.project_summary || '',
    project_lead: merged.project_lead || catalog.project_lead || '',
    principal_investigator: merged.principal_investigator || catalog.principal_investigator || '',
    disease_focus: merged.disease_focus || catalog.disease_focus || '',
    status: merged.status || catalog.status || '',
    priority: merged.priority || catalog.priority || '',
    category: merged.category || catalog.category || '',
    category_label: merged.category_label || catalog.category_label || merged.category || '',
  };
}

export function resolveProject(projectCode, apiProjects = []) {
  const apiProject = apiProjects.find((p) => p.project_code === projectCode);
  const catalogProject = getProjectByCode(projectCode);
  if (apiProject) return mergeProjectRecord(apiProject, catalogProject);
  return catalogProject || null;
}

export async function fetchWithTimeout(url, options = {}, timeoutMs = 4000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}
