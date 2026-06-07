export function isProjectReadmePath(path) {
  if (!path) return false;
  const base = String(path).split('/').pop()?.toLowerCase() || '';
  return base === 'readme.md' || base === 'readme.txt' || base.startsWith('readme.');
}

export function twinHasReadme(twin) {
  return (twin?.document_index || []).some((doc) =>
    isProjectReadmePath(doc.path || doc.relative_path),
  );
}
