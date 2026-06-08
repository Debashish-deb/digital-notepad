import { findMainNav, MAIN_NAV } from '../config/navigation.js';
import { GUI_STRINGS } from './guiStrings/index.js';
import { translate, translateNavSub } from './translate.js';

export function localizeMainNav(locale) {
  return MAIN_NAV.map((main) => ({
    ...main,
    label: translate(GUI_STRINGS, locale, `navMain.${main.id}`, main.label),
    sidebarLabel: main.sidebarLabel
      ? translate(GUI_STRINGS, locale, `navMainSidebar.${main.id}`, main.sidebarLabel)
      : undefined,
    children: main.children.map((child) => localizeSubItem(main.id, child, locale)),
  }));
}

function localizeSubItem(mainId, child, locale) {
  return {
    ...child,
    label: translateNavSub(GUI_STRINGS, locale, mainId, child.id, 'label', child.label),
    sidebarLabel: child.sidebarLabel
      ? translateNavSub(GUI_STRINGS, locale, mainId, child.id, 'sidebarLabel', child.sidebarLabel)
      : undefined,
    description: child.description
      ? translateNavSub(GUI_STRINGS, locale, mainId, child.id, 'description', child.description)
      : undefined,
  };
}

function localizeNavItem(main, locale) {
  return {
    ...main,
    label: translate(GUI_STRINGS, locale, `navMain.${main.id}`, main.label),
    sidebarLabel: main.sidebarLabel
      ? translate(GUI_STRINGS, locale, `navMainSidebar.${main.id}`, main.sidebarLabel)
      : undefined,
    children: main.children.map((child) => localizeSubItem(main.id, child, locale)),
  };
}

export function findLocalizedMainNav(mainId, locale) {
  const base = findMainNav(mainId);
  const nav = localizeMainNav(locale);
  return nav.find((m) => m.id === base.id) || localizeNavItem(base, locale);
}

export function findLocalizedSubNav(mainId, subId, locale) {
  const main = findLocalizedMainNav(mainId, locale);
  return main.children.find((c) => c.id === subId) || main.children[0];
}

export function localizedSectionTitle(mainId, subId, locale) {
  const main = findLocalizedMainNav(mainId, locale);
  const sub = findLocalizedSubNav(mainId, subId, locale);
  return `${main.label} · ${sub.label}`;
}
