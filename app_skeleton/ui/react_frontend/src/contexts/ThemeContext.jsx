import React, { createContext, useContext, useEffect, useState, useMemo, useCallback } from 'react';
import { BookOpen, Moon, Sun } from 'lucide-react';

const ThemeContext = createContext();

export const THEME_CYCLE = ['dark', 'light', 'academic'];

export const THEME_META = {
  dark: {
    label: 'Dark',
    icon: Moon,
  },
  light: {
    label: 'Light',
    icon: Sun,
  },
  academic: {
    label: 'Academic',
    icon: BookOpen,
  },
};

const STORAGE_KEY = 'farkki-theme';

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(() => {
    if (typeof window === 'undefined') return 'academic';
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (THEME_CYCLE.includes(stored)) {
        return stored;
      }
    } catch (e) {
      console.warn('Could not access localStorage for theme.', e);
    }
    return 'academic';
  });

  const setTheme = useCallback((newTheme) => {
    if (!THEME_CYCLE.includes(newTheme)) {
      newTheme = 'dark';
    }
    setThemeState(newTheme);
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem(STORAGE_KEY, newTheme);
      } catch (e) {
        // ignore
      }
    }
  }, []);

  const cycleTheme = useCallback(() => {
    setThemeState((prev) => {
      const currentIndex = THEME_CYCLE.indexOf(prev);
      const nextTheme = THEME_CYCLE[(currentIndex + 1) % THEME_CYCLE.length];
      if (typeof window !== 'undefined') {
        try {
          localStorage.setItem(STORAGE_KEY, nextTheme);
        } catch (e) {
          // ignore
        }
      }
      return nextTheme;
    });
  }, []);

  useEffect(() => {
    if (typeof document === 'undefined') return;
    
    document.documentElement.setAttribute('data-theme', theme);
    
    if (theme === 'dark') {
      document.documentElement.style.colorScheme = 'dark';
    } else {
      document.documentElement.style.colorScheme = 'light';
    }
  }, [theme]);

  const value = useMemo(
    () => ({
      theme,
      setTheme,
      cycleTheme,
      availableThemes: THEME_CYCLE,
      themeMeta: THEME_META,
    }),
    [theme, setTheme, cycleTheme]
  );

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}
