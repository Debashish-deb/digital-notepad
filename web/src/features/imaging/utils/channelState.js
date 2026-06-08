/** Shared channel state, intensity mapping, and panel presets for ImageTileViewer. */

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

const DEFAULT_INTENSITY = {
  min: 0,
  max: 255,
  gamma: 1,
  brightness: 0,
  contrast: 1,
  opacity: 1,
};

/**
 * Build per-channel viewer state from manifest channel count and optional names.
 */
export function defaultChannelState(channels, channelNames = []) {
  const count = Math.max(1, Number(channels) || 1);
  const names = Array.isArray(channelNames) ? channelNames : [];
  return Array.from({ length: count }, (_, i) => ({
    index: i,
    visible: i < 3,
    color: CHANNEL_COLORS[i % CHANNEL_COLORS.length],
    label: names[i] || `Channel ${i + 1}`,
    ...DEFAULT_INTENSITY,
  }));
}

/**
 * Map raw luminance (0–255) through window, gamma, brightness, contrast, opacity.
 */
export function applyIntensity(lum, opts = {}) {
  const {
    min = 0,
    max = 255,
    gamma = 1,
    brightness = 0,
    contrast = 1,
    opacity = 1,
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
  return v * Math.max(0, Math.min(1, opacity)) * 255;
}

/** Named channel presets for common multiplex panels (indices are 0-based). */
export const DEFAULT_PRESETS = {
  'Immune Panel': {
    channels: [
      { index: 0, visible: true, color: '#00d4ff', label: 'CD3', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 0.9 },
      { index: 1, visible: true, color: '#ff4fd8', label: 'CD8', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 0.9 },
      { index: 2, visible: true, color: '#ffd400', label: 'CD68', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 0.85 },
      { index: 3, visible: false, color: '#4ade80', label: 'DAPI', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 1 },
    ],
  },
  'Tumor Panel': {
    channels: [
      { index: 0, visible: true, color: '#fb923c', label: 'PanCK', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 0.9 },
      { index: 1, visible: true, color: '#a78bfa', label: 'Ki67', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 0.85 },
      { index: 2, visible: true, color: '#38bdf8', label: 'DAPI', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 1 },
    ],
  },
  'Macrophage Panel': {
    channels: [
      { index: 0, visible: true, color: '#ffd400', label: 'CD68', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 0.9 },
      { index: 1, visible: true, color: '#f472b6', label: 'CD163', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 0.85 },
      { index: 2, visible: true, color: '#4ade80', label: 'DAPI', min: 0, max: 255, gamma: 1, brightness: 0, contrast: 1, opacity: 1 },
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

export function resetChannelIntensity(row) {
  return { ...row, ...DEFAULT_INTENSITY };
}
