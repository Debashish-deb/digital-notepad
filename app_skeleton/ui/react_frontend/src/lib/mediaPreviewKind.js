const IMAGE_EXTENSIONS = new Set([
  '.png',
  '.jpg',
  '.jpeg',
  '.gif',
  '.webp',
  '.svg',
  '.tif',
  '.tiff',
  '.bmp',
  '.avif',
  '.heic',
  '.heif',
]);

const VIDEO_EXTENSIONS = new Set([
  '.mp4',
  '.webm',
  '.mov',
  '.m4v',
  '.mkv',
  '.ogv',
  '.avi',
]);

const MODEL_3D_EXTENSIONS = new Set([
  '.glb',
  '.gltf',
  '.obj',
  '.usdz',
  '.fbx',
  '.stl',
  '.dae',
]);

/** @returns {'image'|'video'|'model3d'|null} */
export function getMediaPreviewKind(extension) {
  const ext = (extension || '').toLowerCase();
  if (IMAGE_EXTENSIONS.has(ext)) return 'image';
  if (VIDEO_EXTENSIONS.has(ext)) return 'video';
  if (MODEL_3D_EXTENSIONS.has(ext)) return 'model3d';
  return null;
}

export function isImagePreviewable(extension) {
  return getMediaPreviewKind(extension) === 'image';
}

export function isVideoPreviewable(extension) {
  return getMediaPreviewKind(extension) === 'video';
}

export function isModel3dPreviewable(extension) {
  return getMediaPreviewKind(extension) === 'model3d';
}

export function isMediaPreviewable(extension) {
  return Boolean(getMediaPreviewKind(extension));
}

export function isDirectMediaAsset(extension) {
  return isMediaPreviewable(extension);
}
