import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { getStoredLocale, storeLocale } from '../data/localeStorage.js';
import { isSupportedLocale } from '../i18n/translate.js';

const LocaleContext = createContext(null);

export function LocaleProvider({ children }) {
  const [locale, setLocaleState] = useState(() => getStoredLocale());

  const setLocale = useCallback((id) => {
    if (!isSupportedLocale(id)) return;
    setLocaleState(id);
    storeLocale(id);
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const value = useMemo(() => ({ locale, setLocale }), [locale, setLocale]);

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale() {
  const ctx = useContext(LocaleContext);
  if (!ctx) {
    throw new Error('useLocale must be used within LocaleProvider');
  }
  return ctx;
}
