import {
  Dna,
  FlaskConical,
  Grid3x3,
  Layers,
  Microscope,
  Scan,
  ScanLine,
  Sparkles,
  TestTube2,
} from 'lucide-react';

const MODALITY_RULES = [
  { match: /tcycif|t-cycif|cycif/i, label: 'tCycIF', Icon: Microscope, tone: '#06b6d4' },
  { match: /h&e|h\.?e\.?\s*wsi|wsi|histolog/i, label: 'H&E WSI', Icon: Scan, tone: '#a78bfa' },
  { match: /\bwes\b|exome/i, label: 'WES', Icon: Dna, tone: '#60a5fa' },
  { match: /\bwgs\b|genome\s*seq/i, label: 'WGS', Icon: Dna, tone: '#818cf8' },
  { match: /geomx|nanostring/i, label: 'GeoMx', Icon: Grid3x3, tone: '#8b5cf6' },
  { match: /xenium/i, label: 'Xenium', Icon: Sparkles, tone: '#ec4899' },
  { match: /cosmx/i, label: 'CosMx', Icon: Grid3x3, tone: '#f472b6' },
  { match: /rarecyte|rare.?cyte/i, label: 'RareCyte', Icon: ScanLine, tone: '#f59e0b' },
  { match: /mass.?spec|proteom|proteo/i, label: 'Proteomics', Icon: TestTube2, tone: '#10b981' },
  { match: /rna|rnaseq|scrna|transcriptom/i, label: 'RNA-seq', Icon: Dna, tone: '#3b82f6' },
  { match: /spatial|spacex|space\b/i, label: 'Spatial', Icon: Layers, tone: '#0ea5e9' },
  { match: /flow/i, label: 'Flow', Icon: FlaskConical, tone: '#14b8a6' },
];

export function resolveModalityMeta(name) {
  const raw = String(name || '').trim();
  if (!raw) return { label: 'Assay', Icon: FlaskConical, tone: 'var(--color-primary)' };
  for (const rule of MODALITY_RULES) {
    if (rule.match.test(raw)) {
      return { label: rule.label, Icon: rule.Icon, tone: rule.tone };
    }
  }
  const short = raw.length > 14 ? `${raw.slice(0, 12)}…` : raw;
  return { label: short, Icon: FlaskConical, tone: 'var(--color-primary)' };
}

export function normalizeModalityList(modalities = []) {
  const seen = new Set();
  const out = [];
  for (const item of modalities) {
    const name = (item?.name || item || '').trim();
    if (!name) continue;
    const key = name.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push({ name, ...resolveModalityMeta(name) });
  }
  return out;
}
