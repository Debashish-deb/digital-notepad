import { SUPPORTED_LOCALES } from '../i18n/constants.js';

const STORAGE_KEY = 'app-locale';
const LEGACY_STORAGE_KEY = 'overview-intro-locale';

export function getStoredLocale() {
  try {
    const stored =
      localStorage.getItem(STORAGE_KEY) || localStorage.getItem(LEGACY_STORAGE_KEY);
    if (stored && SUPPORTED_LOCALES.includes(stored)) {
      if (!localStorage.getItem(STORAGE_KEY)) {
        localStorage.setItem(STORAGE_KEY, stored);
      }
      return stored;
    }
  } catch {
    /* ignore */
  }
  return 'en';
}

export function storeLocale(locale) {
  try {
    localStorage.setItem(STORAGE_KEY, locale);
  } catch {
    /* ignore */
  }
}
