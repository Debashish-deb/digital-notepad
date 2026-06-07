import { useEffect, useRef } from 'react';
import { smoothScrollToBottom } from '../utils/chatMotion.js';

export function useChatAutoScroll(deps = [], { enabled = true, behavior = 'smooth' } = {}) {
  const containerRef = useRef(null);
  const endRef = useRef(null);

  useEffect(() => {
    if (!enabled) return;
    smoothScrollToBottom(containerRef.current, behavior);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    const node = containerRef.current;
    if (!node || !enabled) return undefined;

    const observer = new ResizeObserver(() => {
      smoothScrollToBottom(node, 'auto');
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, [enabled]);

  return { containerRef, endRef };
}
