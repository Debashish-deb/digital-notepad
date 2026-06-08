import { useCallback, useEffect, useRef, useState } from 'react';

const DEFAULT_BATCH = 20;

/**
 * Incremental reveal for long lists — revealed count only grows, never shrinks.
 * Once a card/row is mounted it stays in the DOM when scrolling back up.
 */
export function usePersistentReveal(itemCount, { batchSize = DEFAULT_BATCH, rootMargin = '480px 0px' } = {}) {
  const initial = Math.min(batchSize, itemCount);
  const [revealed, setRevealed] = useState(initial);
  const sentinelRef = useRef(null);
  const maxRevealedRef = useRef(initial);

  useEffect(() => {
    setRevealed((prev) => {
      const next = Math.max(prev, Math.min(batchSize, itemCount));
      maxRevealedRef.current = Math.max(maxRevealedRef.current, next, prev);
      return Math.max(prev, Math.min(itemCount, next));
    });
  }, [itemCount, batchSize]);

  const grow = useCallback(() => {
    setRevealed((prev) => {
      if (prev >= itemCount) return prev;
      const next = Math.min(itemCount, prev + batchSize);
      maxRevealedRef.current = Math.max(maxRevealedRef.current, next);
      return next;
    });
  }, [itemCount, batchSize]);

  useEffect(() => {
    const node = sentinelRef.current;
    if (!node) return undefined;

    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) grow();
      },
      { root: null, rootMargin, threshold: 0 },
    );

    io.observe(node);
    return () => io.disconnect();
  }, [grow, itemCount, revealed]);

  const revealedCount = Math.min(Math.max(revealed, maxRevealedRef.current), itemCount);

  return { revealedCount, sentinelRef, grow };
}
