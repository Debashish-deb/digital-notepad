/**
 * Scientific imaging helpers — dtype profiles, physical coordinates, instrument labels.
 * Display transforms are separate from raw sensor values (Rule 3).
 */

const DTYPE_DEFAULTS = {
  uint8: { bitDepth: 8, valueMin: 0, valueMax: 255, isFloat: false },
  uint16: { bitDepth: 16, valueMin: 0, valueMax: 65535, isFloat: false },
  int16: { bitDepth: 16, valueMin: -32768, valueMax: 32767, isFloat: false },
  uint32: { bitDepth: 32, valueMin: 0, valueMax: 4294967295, isFloat: false },
  float32: { bitDepth: 32, valueMin: 0, valueMax: 1, isFloat: true },
  float64: { bitDepth: 64, valueMin: 0, valueMax: 1, isFloat: true },
};

/**
 * @param {object|null|undefined} manifestOrMeta
 */
export function resolveDtypeProfile(manifestOrMeta = {}) {
  const dtype = String(manifestOrMeta.dtype || 'uint8').toLowerCase().replace('numpy.', '');
  const known = DTYPE_DEFAULTS[dtype];
  if (known) {
    return {
      dtype,
      bitDepth: manifestOrMeta.bit_depth ?? known.bitDepth,
      valueMin: manifestOrMeta.value_min ?? known.valueMin,
      valueMax: manifestOrMeta.value_max ?? known.valueMax,
      isFloat: manifestOrMeta.is_float_dtype ?? known.isFloat,
    };
  }
  const bitMatch = dtype.match(/(int|float)(\d+)/);
  const bits = bitMatch ? Number(bitMatch[2]) : 8;
  const isFloat = dtype.includes('float');
  return {
    dtype,
    bitDepth: manifestOrMeta.bit_depth ?? bits,
    valueMin: manifestOrMeta.value_min ?? (isFloat ? 0 : 0),
    valueMax: manifestOrMeta.value_max ?? (isFloat ? 1 : (2 ** bits) - 1),
    isFloat: manifestOrMeta.is_float_dtype ?? isFloat,
  };
}

/**
 * @param {number} x pixel X
 * @param {number} y pixel Y
 * @param {number|null|undefined} umPerPixel
 */
export function pixelToPhysicalCoords(x, y, umPerPixel) {
  const um = Number(umPerPixel);
  if (!Number.isFinite(um) || um <= 0) {
    return { physicalXUm: null, physicalYUm: null, hasCalibration: false };
  }
  return {
    physicalXUm: x * um,
    physicalYUm: y * um,
    hasCalibration: true,
  };
}

export function formatScientificValue(value, profile) {
  if (value == null || Number.isNaN(value)) return '—';
  if (profile?.isFloat) return Number(value).toPrecision(6);
  return String(Math.round(Number(value)));
}

export const INSTRUMENT_PHASE_LABEL = 'Scientific Imaging Instrument · Phase 1';
