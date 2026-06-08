import { useCallback, useEffect, useRef, useState } from 'react';
import { isNearScrollBottom, smoothScrollToBottom } from '@/lib/chatMotion.js';

export function useChatAutoScroll(
  deps = [],
  { enabled = true, behavior = 'smooth', forceKey = null } = {},
) {
  const [scrollRoot, setScrollRoot] = useState(null);
  const endRef = useRef(null);
  const userPinnedRef = useRef(false);
  const lastForceKeyRef = useRef(null);

  const containerRef = useCallback((node) => {
    setScrollRoot(node);
  }, []);

  const scrollToBottom = useCallback((scrollBehavior) => {
    if (!scrollRoot || !enabled) return;
    smoothScrollToBottom(scrollRoot, scrollBehavior ?? behavior);
    userPinnedRef.current = false;
  }, [enabled, behavior, scrollRoot]);

  useEffect(() => {
    if (!scrollRoot || !enabled) return undefined;

    const handleScroll = () => {
      userPinnedRef.current = !isNearScrollBottom(scrollRoot);
    };

    handleScroll();
    scrollRoot.addEventListener('scroll', handleScroll, { passive: true });
    return () => scrollRoot.removeEventListener('scroll', handleScroll);
  }, [scrollRoot, enabled]);

  useEffect(() => {
    if (!scrollRoot || !enabled) return;

    const isNewForce = forceKey != null && forceKey !== lastForceKeyRef.current;
    if (isNewForce) lastForceKeyRef.current = forceKey;

    const nearBottom = isNearScrollBottom(scrollRoot);
    const shouldScroll = isNewForce || (nearBottom && !userPinnedRef.current);
    if (!shouldScroll) return;

    smoothScrollToBottom(scrollRoot, isNewForce ? 'auto' : behavior);

    if (isNewForce || nearBottom) {
      userPinnedRef.current = false;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, forceKey, scrollRoot, enabled, behavior]);

  return { containerRef, endRef, scrollToBottom };
}
