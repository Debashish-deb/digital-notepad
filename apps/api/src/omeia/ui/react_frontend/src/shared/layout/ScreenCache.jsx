import { useState } from 'react';

/**
 * Keeps visited screens mounted (hidden via display:none) so revisiting a nav
 * section does not remount lazy-loaded panes or replay Suspense fallbacks.
 */
export default function ScreenCache({ cacheKey, isActive, children }) {
  const [screens, setScreens] = useState({});

  if (
    isActive
    && children != null
    && !Object.prototype.hasOwnProperty.call(screens, cacheKey)
  ) {
    setScreens({ ...screens, [cacheKey]: children });
  }

  return (
    <>
      {Object.entries(screens).map(([key, screen]) => (
        <div
          key={key}
          className="screen-cache-pane"
          style={{ display: isActive && key === cacheKey ? 'contents' : 'none' }}
          aria-hidden={!(isActive && key === cacheKey)}
        >
          {screen}
        </div>
      ))}
    </>
  );
}
