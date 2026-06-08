/** Classify URLs and paths for consistent link styling (no API changes). */

export function classifyHref(value) {
  if (!value || typeof value !== 'string') return 'text';
  const v = value.trim();

  if (/^https?:\/\//i.test(v)) {
    if (/doi\.org|dx\.doi\.org/i.test(v)) return 'doi';
    if (/github\.com|gitlab\.com|bitbucket\.org/i.test(v)) return 'github';
    return 'external';
  }

  if (/^10\.\d{4,9}\//i.test(v)) return 'doi';

  if (/github\.com|gitlab\.com/i.test(v)) return 'github';

  if (/\.(md|txt|py|r|json|ya?ml|csv|tsv|xlsx?|pdf|docx?|pptx?|html?|xml|sh|sql|ipynb|fasta|vcf|bam|bw|bed|h5ad?)$/i.test(v)) {
    return 'file';
  }

  if (/^[A-Za-z]:\\/.test(v) || v.startsWith('/') || v.includes('/') || v.includes('\\')) {
    return 'path';
  }

  return 'text';
}

export function hrefForDisplay(value) {
  const v = (value || '').trim();
  const kind = classifyHref(v);
  if (kind === 'doi' && !/^https?:\/\//i.test(v)) {
    return `https://doi.org/${v.replace(/^doi:\s*/i, '')}`;
  }
  if (kind === 'external' || kind === 'github' || kind === 'doi') return v;
  return null;
}

export function linkLabel(value, maxLen = 72) {
  const v = (value || '').trim();
  if (!v) return '—';
  const kind = classifyHref(v);
  let label = v;
  if (kind === 'github') {
    try {
      const u = new URL(v.startsWith('http') ? v : `https://${v}`);
      label = u.pathname.replace(/^\//, '') || u.hostname;
    } catch {
      label = v;
    }
  } else if (kind === 'doi') {
    label = v.replace(/^https?:\/\/(dx\.)?doi\.org\//i, '').replace(/^doi:\s*/i, '');
  } else if (kind === 'file' || kind === 'path') {
    label = v.split(/[/\\]/).pop() || v;
  }
  if (label.length > maxLen) return `${label.slice(0, maxLen - 1)}…`;
  return label;
}
