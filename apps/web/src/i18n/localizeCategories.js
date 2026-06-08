import { GUI_STRINGS } from './guiStrings/index.js';
import { translate, translateCategory } from './translate.js';

export function localizeCategoryGroups(groups, locale) {
  if (!groups?.length) return groups;
  return groups.map((group) => ({
    ...group,
    label: translate(GUI_STRINGS, locale, `catGroup.${group.id}`, group.label),
    categories: group.categories.map((cat) => ({
      ...cat,
      label: translateCategory(GUI_STRINGS, locale, cat.id, 'label', cat.label),
      description: translateCategory(
        GUI_STRINGS,
        locale,
        cat.id,
        'description',
        cat.description
      ),
    })),
  }));
}
