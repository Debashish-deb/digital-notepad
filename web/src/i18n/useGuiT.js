import { useCallback, useMemo } from 'react';
import { useLocale } from '../contexts/LocaleContext.jsx';
import { overviewIntroCopy } from '../data/overviewIntroTranslations.js';
import { GUI_STRINGS } from './guiStrings/index.js';
import { localizeCategoryGroups } from './localizeCategories.js';
import {
  findLocalizedMainNav,
  findLocalizedSubNav,
  localizeMainNav,
  localizeNavSections,
  localizedSectionTitle,
} from './localizeNav.js';
import { translate } from './translate.js';

export function useGuiT() {
  const { locale, setLocale } = useLocale();

  const t = useCallback(
    (key, fallback = '', vars) => {
      let value = translate(GUI_STRINGS, locale, key, fallback);
      if (vars && typeof value === 'string') {
        for (const [k, v] of Object.entries(vars)) {
          value = value.replaceAll(`{${k}}`, String(v));
        }
      }
      return value;
    },
    [locale]
  );

  const intro = useMemo(() => {
    const base = overviewIntroCopy.en;
    const localized = overviewIntroCopy[locale] || {};
    return {
      ...base,
      ...localized,
      topics: localized.topics || base.topics,
      quickLinks: { ...base.quickLinks, ...(localized.quickLinks || {}) },
      sections: { ...base.sections, ...(localized.sections || {}) },
    };
  }, [locale]);

  const nav = useMemo(
    () => ({
      mainNav: localizeMainNav(locale),
      navSections: localizeNavSections(locale),
      findMain: (mainId) => findLocalizedMainNav(mainId, locale),
      findSub: (mainId, subId) => findLocalizedSubNav(mainId, subId, locale),
      sectionTitle: (mainId, subId) => localizedSectionTitle(mainId, subId, locale),
    }),
    [locale]
  );

  const localizeCategories = useCallback(
    (groups) => localizeCategoryGroups(groups, locale),
    [locale]
  );

  return { locale, setLocale, t, intro, nav, localizeCategories };
}
