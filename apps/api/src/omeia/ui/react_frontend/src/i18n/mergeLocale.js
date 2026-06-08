/** Deep-merge locale overrides onto the English source catalog. */
export function mergeLocale(base, overrides) {
  if (!overrides) return base;
  const out = { ...base };
  for (const key of Object.keys(overrides)) {
    const patch = overrides[key];
    const baseVal = base[key];
    if (
      patch &&
      typeof patch === 'object' &&
      !Array.isArray(patch) &&
      baseVal &&
      typeof baseVal === 'object' &&
      !Array.isArray(baseVal)
    ) {
      out[key] = mergeLocale(baseVal, patch);
    } else {
      out[key] = patch;
    }
  }
  return out;
}
