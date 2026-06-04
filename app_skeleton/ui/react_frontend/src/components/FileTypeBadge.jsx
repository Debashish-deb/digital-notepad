import { getFileTypeMeta } from '../utils/fileTypeMeta.js';

export default function FileTypeBadge({ file, className = '' }) {
  const meta = getFileTypeMeta(file);
  return (
    <span className={`file-type-badge tone-${meta.tone} ${className}`.trim()} title={meta.ext || meta.label}>
      {meta.label}
    </span>
  );
}
