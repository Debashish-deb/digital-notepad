/** Shared channel state, intensity mapping, LUT presets, and panel presets. */

export const CHANNEL_COLORS = [
  '#00d4ff',
  '#ff4fd8',
  '#ffd400',
  '#4ade80',
  '#fb923c',
  '#a78bfa',
  '#f472b6',
  '#38bdf8',
];

/** Solid pseudo-color labels for multiplex channels. */
export const SOLID_LUTS = {
  Gray: '#b0b8c4',
  Red: '#ff3b3b',
  Green: '#22c55e',
  Blue: '#3b82f6',
  Yellow: '#facc15',
  Magenta: '#e879f9',
  Cyan: '#22d3ee',
  White: '#f8fafc',
};

/** Scientific colormap names (display mapping only). */
export const COLORMAP_LUTS = ['Viridis', 'Inferno', 'Magma', 'Plasma', 'Turbo'];

export const LUT_OPTIONS = [...Object.keys(SOLID_LUTS), ...COLORMAP_LUTS];

import { resolveDtypeProfile } from '@/lib/scientificImagery.js';

/** Approximate RGB for normalized intensity t in [0,1] — display only. */
const COLORMAP_RGB = {
  Viridis: (t) => {
    const r = Math.round(255 * (0.267 + 0.005 * t + 0.32 * t ** 2));
    const g = Math.round(255 * (0.004 + 0.99 * t ** 0.8));
    const b = Math.round(255 * (0.329 + 0.4 * (1 - t)));
    return { r, g, b };
  },
  Inferno: (t) => {
    const r = Math.round(255 * Math.min(1, 1.2 * t));
    const g = Math.round(255 * (0.1 + 0.7 * t ** 1.5));
    const b = Math.round(255 * (0.4 * (1 - t) + 0.2 * t));
    return { r, g, b };
  },
  Magma: (t) => ({
    r: Math.round(255 * (0.15 + 0.85 * t)),
    g: Math.round(255 * (0.05 + 0.55 * t ** 1.2)),
    b: Math.round(255 * (0.35 + 0.25 * t)),
  }),
  Plasma: (t) => ({
    r: Math.round(255 * (0.5 + 0.5 * t)),
    g: Math.round(255 * (0.05 + 0.75 * t ** 0.9)),
    b: Math.round(255 * (0.75 - 0.55 * t)),
  }),
  Turbo: (t) => ({
    r: Math.round(255 * (0.2 + 0.8 * Math.sin(Math.PI * t))),
    g: Math.round(255 * (0.3 + 0.7 * Math.sin(Math.PI * (t - 0.25)) ** 2)),
    b: Math.round(255 * (0.5 + 0.5 * Math.cos(Math.PI * t))),
  }),
};

export function resolveLutRgb(lut, normalized) {
  const t = Math.max(0, Math.min(1, normalized));
  if (SOLID_LUTS[lut]) {
    const hex = SOLID_LUTS[lut].replace('#', '');
    return {
      r: parseInt(hex.slice(0, 2), 16),
      g: parseInt(hex.slice(2, 4), 16),
      b: parseInt(hex.slice(4, 6), 16),
    };
  }
  const fn = COLORMAP_RGB[lut];
  return fn ? fn(t) : COLORMAP_RGB.Viridis(t);
}

function defaultIntensityForProfile(profile) {
  return {
    min: profile?.valueMin ?? 0,
    max: profile?.valueMax ?? 255,
    gamma: 1,
    brightness: 0,
    contrast: 1,
    opacity: 1,
    lut: 'Gray',
  };
}

/**
 * Build per-channel viewer state from manifest channel count and optional names.
 */
export function defaultChannelState(channels, channelNames = [], manifestOrMeta = null) {
  const count = Math.max(1, Number(channels) || 1);
  const names = Array.isArray(channelNames) ? channelNames : [];
  const profile = resolveDtypeProfile(manifestOrMeta || {});
  const intensity = defaultIntensityForProfile(profile);
  return Array.from({ length: count }, (_, i) => ({
    index: i,
    visible: i < 3,
    color: CHANNEL_COLORS[i % CHANNEL_COLORS.length],
    label: names[i] || `Channel ${i + 1}`,
    ...intensity,
  }));
}

/**
 * Map raw luminance through window, gamma, brightness, contrast, opacity, and optional LUT.
 */
export function applyIntensity(lum, opts = {}) {
  const {
    min = 0,
    max = 255,
    gamma = 1,
    brightness = 0,
    contrast = 1,
    opacity = 1,
    lut = null,
    color = '#ffffff',
  } = opts;
  const lo = Math.min(min, max);
  const hi = Math.max(min, max);
  const span = Math.max(hi - lo, 1e-6);
  let v = (Number(lum) - lo) / span;
  v = Math.max(0, Math.min(1, v));
  if (gamma !== 1 && gamma > 0) {
    v = v ** (1 / gamma);
  }
  v = (v - 0.5) * contrast + 0.5 + brightness / 255;
  v = Math.max(0, Math.min(1, v));
  const alpha = v * Math.max(0, Math.min(1, opacity)) * 255;

  if (lut && (SOLID_LUTS[lut] || COLORMAP_RGB[lut])) {
    const { r, g, b } = resolveLutRgb(lut, v);
    return { r: (alpha * r) / 255, g: (alpha * g) / 255, b: (alpha * b) / 255, a: alpha };
  }

  const hex = color.replace('#', '');
  const r = parseInt(hex.slice(0, 2), 16);
  const g = parseInt(hex.slice(2, 4), 16);
  const b = parseInt(hex.slice(4, 6), 16);
  return { r: (alpha * r) / 255, g: (alpha * g) / 255, b: (alpha * b) / 255, a: alpha };
}

/** Named channel presets for common multiplex panels (indices are 0-based). */
export const DEFAULT_PRESETS = {
  'Immune Panel': {
    channels: [
      { index: 0, visible: true, color: '#00d4ff', label: 'CD3', lut: 'Cyan', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 0.9 },
      { index: 1, visible: true, color: '#ff4fd8', label: 'CD8', lut: 'Magenta', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 0.9 },
      { index: 2, visible: true, color: '#ffd400', label: 'CD68', lut: 'Yellow', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 0.85 },
      { index: 3, visible: false, color: '#4ade80', label: 'DAPI', lut: 'Blue', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 1 },
    ],
  },
  'Tumor Panel': {
    channels: [
      { index: 0, visible: true, color: '#fb923c', label: 'PanCK', lut: 'Red', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 0.9 },
      { index: 1, visible: true, color: '#a78bfa', label: 'Ki67', lut: 'Magenta', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 0.85 },
      { index: 2, visible: true, color: '#38bdf8', label: 'DAPI', lut: 'Blue', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 1 },
    ],
  },
  'Tumor Microenvironment': {
    channels: [
      { index: 0, visible: true, color: '#38bdf8', label: 'DAPI', lut: 'Blue', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 1 },
      { index: 1, visible: true, color: '#22c55e', label: 'CD4', lut: 'Green', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 0.9 },
      { index: 2, visible: true, color: '#ff4fd8', label: 'CD8', lut: 'Magenta', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 0.9 },
      { index: 3, visible: true, color: '#fb923c', label: 'TIM3', lut: 'Inferno', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 0.85 },
      { index: 4, visible: false, color: '#a78bfa', label: 'NKG2A', lut: 'Plasma', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 0.85 },
      { index: 5, visible: false, color: '#ffd400', label: 'CD163', lut: 'Yellow', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 0.85 },
      { index: 6, visible: false, color: '#00d4ff', label: 'CD20', lut: 'Cyan', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 0.85 },
      { index: 7, visible: false, color: '#f472b6', label: 'Ki67', lut: 'Magma', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 0.85 },
      { index: 8, visible: false, color: '#fb923c', label: 'PanCK', lut: 'Red', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 0.9 },
      { index: 9, visible: false, color: '#4ade80', label: 'HLA-DPB1', lut: 'Viridis', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 0.85 },
    ],
  },
  'Macrophage Panel': {
    channels: [
      { index: 0, visible: true, color: '#ffd400', label: 'CD68', lut: 'Yellow', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 0.9 },
      { index: 1, visible: true, color: '#f472b6', label: 'CD163', lut: 'Magenta', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 0.85 },
      { index: 2, visible: true, color: '#4ade80', label: 'DAPI', lut: 'Blue', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 1 },
    ],
  },
  'Exhaustion Panel': {
    channels: [
      { index: 0, visible: true, color: '#ff4fd8', label: 'TIM3', lut: 'Inferno', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 0.9 },
      { index: 1, visible: true, color: '#00d4ff', label: 'NKG2A', lut: 'Plasma', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 0.9 },
      { index: 2, visible: true, color: '#ffd400', label: 'CD8', lut: 'Magenta', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 0.85 },
      { index: 3, visible: true, color: '#4ade80', label: 'DAPI', lut: 'Blue', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 1 },
    ],
  },
};

export function mergePresetIntoState(channelState, presetChannels) {
  if (!Array.isArray(presetChannels) || !presetChannels.length) return channelState;
  const byIndex = new Map(presetChannels.map((ch) => [ch.index, ch]));
  return channelState.map((row) => {
    const patch = byIndex.get(row.index);
    return patch ? { ...row, ...patch, index: row.index } : { ...row, visible: false };
  });
}

export function resetChannelIntensity(row, manifestOrMeta = null) {
  const profile = resolveDtypeProfile(manifestOrMeta || {});
  return { ...row, ...defaultIntensityForProfile(profile) };
}

export function mapRawToDisplay(rawValue, opts = {}) {
  const mapped = applyIntensity(rawValue, opts);
  return typeof mapped === 'number' ? mapped : mapped.a;
}
