import { useEffect, useRef, useState } from 'react';

/**
 * Keeps visited screens mounted (hidden via display:none).
 * The active route always renders live `children` so props refresh without remounting.
 * Inactive routes keep their last frozen tree.
 */
export default function ScreenCache({ cacheKey, isActive, children }) {
  const [mountedKeys, setMountedKeys] = useState(() => (cacheKey ? [cacheKey] : []));
  const frozenRef = useRef({});

  useEffect(() => {
    if (!cacheKey) return;
    setMountedKeys((keys) => (keys.includes(cacheKey) ? keys : [...keys, cacheKey]));
  }, [cacheKey]);

  useEffect(() => {
    if (!isActive || children == null || !cacheKey) return;
    frozenRef.current[cacheKey] = children;
  }, [cacheKey, isActive, children]);

  if (!cacheKey) {
    return children;
  }

  return (
    <>
      {mountedKeys.map((key) => {
        const show = isActive && key === cacheKey;
        const content = show ? children : frozenRef.current[key];
        if (!content) return null;
        return (
          <div
            key={key}
            className={`screen-cache-pane${show ? ' screen-cache-pane--active' : ''}`}
            style={{ display: show ? 'block' : 'none' }}
            aria-hidden={!show}
          >
            {content}
          </div>
        );
      })}
    </>
  );
}
