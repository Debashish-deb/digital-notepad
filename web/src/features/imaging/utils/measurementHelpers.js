/** Physical measurement helpers for microscopy viewer overlays. */

export function pixelSizeUm(manifest) {
  const um =
    manifest?.physical_pixel_size_um ??
    manifest?.pixel_size_um ??
    manifest?.mpp ??
    null;
  return um != null && Number(um) > 0 ? Number(um) : null;
}

export function pixelsToMicrons(pixels, umPerPixel) {
  if (!umPerPixel || umPerPixel <= 0) return null;
  return pixels * umPerPixel;
}

export function formatLength(um, unit = 'um') {
  if (um == null || Number.isNaN(um)) return '—';
  if (unit === 'mm') return `${(um / 1000).toFixed(3)} mm`;
  if (um >= 1000) return `${(um / 1000).toFixed(2)} mm`;
  return `${um.toFixed(2)} µm`;
}

export function distancePixels(p1, p2) {
  const dx = p2.x - p1.x;
  const dy = p2.y - p1.y;
  return Math.hypot(dx, dy);
}

export function polygonArea(points) {
  if (!points || points.length < 3) return 0;
  let sum = 0;
  for (let i = 0; i < points.length; i += 1) {
    const j = (i + 1) % points.length;
    sum += points[i].x * points[j].y - points[j].x * points[i].y;
  }
  return Math.abs(sum) / 2;
}

export function polygonPerimeter(points) {
  if (!points || points.length < 2) return 0;
  let len = 0;
  for (let i = 0; i < points.length; i += 1) {
    const j = (i + 1) % points.length;
    len += distancePixels(points[i], points[j]);
  }
  return len;
}

export function rectangleArea(rect) {
  return Math.abs(rect.width * rect.height);
}

export function rectanglePerimeter(rect) {
  return 2 * (Math.abs(rect.width) + Math.abs(rect.height));
}
