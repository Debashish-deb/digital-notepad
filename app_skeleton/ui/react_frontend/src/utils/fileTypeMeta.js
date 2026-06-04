/** File extension → badge label and tone (display only). */

const EXT_MAP = {
  '.md': { label: 'Markdown', tone: 'doc' },
  '.txt': { label: 'Text', tone: 'doc' },
  '.pdf': { label: 'PDF', tone: 'doc' },
  '.doc': { label: 'Word', tone: 'doc' },
  '.docx': { label: 'Word', tone: 'doc' },
  '.ppt': { label: 'Slides', tone: 'pres' },
  '.pptx': { label: 'Slides', tone: 'pres' },
  '.png': { label: 'Image', tone: 'image' },
  '.jpg': { label: 'Image', tone: 'image' },
  '.jpeg': { label: 'Image', tone: 'image' },
  '.gif': { label: 'Image', tone: 'image' },
  '.webp': { label: 'Image', tone: 'image' },
  '.svg': { label: 'SVG', tone: 'image' },
  '.tif': { label: 'Image', tone: 'image' },
  '.tiff': { label: 'Image', tone: 'image' },
  '.csv': { label: 'CSV', tone: 'data' },
  '.tsv': { label: 'TSV', tone: 'data' },
  '.xlsx': { label: 'Excel', tone: 'data' },
  '.xls': { label: 'Excel', tone: 'data' },
  '.json': { label: 'JSON', tone: 'data' },
  '.yaml': { label: 'YAML', tone: 'data' },
  '.yml': { label: 'YAML', tone: 'data' },
  '.py': { label: 'Python', tone: 'code' },
  '.r': { label: 'R', tone: 'code' },
  '.sh': { label: 'Shell', tone: 'code' },
  '.sql': { label: 'SQL', tone: 'code' },
  '.ipynb': { label: 'Notebook', tone: 'code' },
  '.html': { label: 'HTML', tone: 'code' },
  '.xml': { label: 'XML', tone: 'code' },
  '.fasta': { label: 'FASTA', tone: 'bio' },
  '.fa': { label: 'FASTA', tone: 'bio' },
  '.vcf': { label: 'VCF', tone: 'bio' },
  '.bam': { label: 'BAM', tone: 'bio' },
  '.bw': { label: 'BigWig', tone: 'bio' },
  '.bed': { label: 'BED', tone: 'bio' },
  '.h5': { label: 'HDF5', tone: 'bio' },
  '.h5ad': { label: 'AnnData', tone: 'bio' },
  '.mp4': { label: 'Video', tone: 'media' },
  '.mov': { label: 'Video', tone: 'media' },
};

const ASSET_TYPE_MAP = {
  figures: { label: 'Figure', tone: 'image' },
  documents: { label: 'Document', tone: 'doc' },
  presentations: { label: 'Slides', tone: 'pres' },
  data_files: { label: 'Data', tone: 'data' },
  text_files: { label: 'Notes', tone: 'doc' },
  videos: { label: 'Video', tone: 'media' },
};

export function inferExtension(name, extension) {
  if (extension) return extension.toLowerCase();
  const m = (name || '').match(/(\.[a-z0-9]+)$/i);
  return m ? m[1].toLowerCase() : '';
}

export function getFileTypeMeta(file) {
  const ext = inferExtension(file?.name, file?.extension);
  if (ext && EXT_MAP[ext]) return { ...EXT_MAP[ext], ext };
  const assetType = file?.asset_type;
  if (assetType && ASSET_TYPE_MAP[assetType]) {
    return { ...ASSET_TYPE_MAP[assetType], ext: ext || '' };
  }
  if (ext) return { label: ext.slice(1).toUpperCase(), tone: 'default', ext };
  return { label: 'File', tone: 'default', ext: '' };
}
