export function isProjectReadmePath(path) {
  if (!path) return false;
  const base = String(path).split('/').pop()?.toLowerCase() || '';
  return base === 'readme.md' || base === 'readme.txt' || base.startsWith('readme.');
}

function readmePathsFromTwin(twin) {
  const paths = [];
  for (const doc of twin?.document_index || []) {
    const p = doc.path || doc.relative_path;
    if (p) paths.push(p);
  }
  for (const section of twin?.content_library?.sections || []) {
    for (const key of ['documents', 'text_files', 'presentations', 'data_files']) {
      for (const item of section[key] || []) {
        if (item?.path) paths.push(item.path);
      }
    }
  }
  return paths;
}

export function twinHasReadme(twin) {
  return readmePathsFromTwin(twin).some((path) => isProjectReadmePath(path));
}

/** Primary README document entry for selection in the file browser. */
export function findReadmeInTwin(twin) {
  for (const doc of twin?.document_index || []) {
    const path = doc.path || doc.relative_path;
    if (isProjectReadmePath(path)) {
      return { ...doc, path };
    }
  }
  for (const section of twin?.content_library?.sections || []) {
    for (const key of ['text_files', 'documents']) {
      for (const item of section[key] || []) {
        if (isProjectReadmePath(item.path)) {
          return { ...item, path: item.path, section_label: section.label };
        }
      }
    }
  }
  return null;
}
