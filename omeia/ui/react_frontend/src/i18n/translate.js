import { SUPPORTED_LOCALES } from './constants.js';

export function isSupportedLocale(locale) {
  return SUPPORTED_LOCALES.includes(locale);
}

export function getNested(obj, path) {
  if (!obj || !path) return undefined;
  return path.split('.').reduce((acc, key) => (acc == null ? undefined : acc[key]), obj);
}

export function translate(strings, locale, key, fallback = '') {
  const value = getNested(strings[locale], key) ?? getNested(strings.en, key);
  return value ?? fallback;
}

export function translateNavSub(strings, locale, mainId, subId, field, fallback = '') {
  return (
    getNested(strings[locale], `navSub.${mainId}.${subId}.${field}`) ??
    getNested(strings.en, `navSub.${mainId}.${subId}.${field}`) ??
    fallback
  );
}

export function translateCategory(strings, locale, catId, field, fallback = '') {
  return (
    getNested(strings[locale], `cat.${catId}.${field}`) ??
    getNested(strings.en, `cat.${catId}.${field}`) ??
    fallback
  );
}
