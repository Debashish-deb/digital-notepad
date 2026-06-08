/** Smooth text reveal and scroll helpers for chat UX. */

export function revealTextProgressively(text, onUpdate, options = {}) {
  const full = String(text || '');
  const chunkSize = options.chunkSize ?? 4;
  const delayMs = options.delayMs ?? 10;
  const signal = options.signal;

  return new Promise((resolve) => {
    if (!full.length) {
      onUpdate('');
      resolve();
      return;
    }

    let index = 0;
    let cancelled = false;

    const tick = () => {
      if (cancelled || signal?.aborted) {
        onUpdate(full);
        resolve();
        return;
      }
      index = Math.min(full.length, index + chunkSize);
      onUpdate(full.slice(0, index));
      if (index >= full.length) {
        resolve();
        return;
      }
      window.setTimeout(tick, delayMs);
    };

    if (signal) {
      signal.addEventListener('abort', () => {
        cancelled = true;
        onUpdate(full);
        resolve();
      }, { once: true });
    }

    tick();
  });
}

export function isNearScrollBottom(container, threshold = 96) {
  if (!container) return true;
  const { scrollTop, scrollHeight, clientHeight } = container;
  return scrollHeight - scrollTop - clientHeight <= threshold;
}

export function smoothScrollToBottom(container, behavior = 'smooth') {
  if (!container) return;
  window.requestAnimationFrame(() => {
    container.scrollTo({
      top: container.scrollHeight,
      behavior,
    });
  });
}
