import { useCallback, useEffect, useRef } from 'react';
import { loadTileBitmap } from '@/services/imageAssetsClient.js';

const MAX_CACHE = 180;

function tileKey(assetId, params) {
  const wm = params.windowMin ?? '';
  const wx = params.windowMax ?? '';
  return `${assetId}:${params.level}:${params.x}:${params.y}:${params.width}:${params.height}:${params.channel}:${params.z}:${params.t}:${wm}:${wx}`;
}

/**
 * LRU tile cache with in-flight deduplication for Napari-style canvas rendering.
 */
export function useImageTileLoader(assetId, channelState = []) {
  const cacheRef = useRef(new Map());
  const orderRef = useRef([]);

  const touch = useCallback((key) => {
    const order = orderRef.current.filter((k) => k !== key);
    order.push(key);
    orderRef.current = order;
    while (order.length > MAX_CACHE) {
      const evict = order.shift();
      cacheRef.current.delete(evict);
    }
  }, []);

  const loadTile = useCallback(
    async (params) => {
      if (!assetId) return null;
      const ch = channelState[params.channel];
      const merged = {
        ...params,
        windowMin: params.windowMin ?? ch?.min,
        windowMax: params.windowMax ?? ch?.max,
      };
      const key = tileKey(assetId, merged);
      if (cacheRef.current.has(key)) {
        touch(key);
        return cacheRef.current.get(key);
      }
      const bitmap = await loadTileBitmap(assetId, merged);
      cacheRef.current.set(key, bitmap);
      touch(key);
      return bitmap;
    },
    [assetId, channelState, touch],
  );

  const clearCache = useCallback(() => {
    for (const bitmap of cacheRef.current.values()) {
      bitmap.close?.();
    }
    cacheRef.current.clear();
    orderRef.current = [];
  }, []);

  useEffect(() => () => clearCache(), [assetId, clearCache]);

  return { loadTile, clearCache };
}
