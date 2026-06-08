import { FileText, Lock } from 'lucide-react';

/**
 * Horizontal category chips — replaces the left sidebar in compact document browsers.
 */
export default function DocumentCategoryBar({
  filteredGroups,
  grouped,
  activeCategory,
  onSelectCategory,
  categoryIcons = {},
  sensitiveCategories = [],
}) {
  const chips = [];
  for (const group of filteredGroups) {
    for (const cat of group.categories) {
      const count = (grouped[cat.id] || []).length;
      if (!count) continue;
      chips.push({ ...cat, groupLabel: group.label, count });
    }
  }

  if (!chips.length) return null;

  let lastGroup = null;

  return (
    <div className="doc-category-bar" role="tablist" aria-label="Document categories">
      {chips.map((cat) => {
        const CatIcon = categoryIcons[cat.id] || FileText;
        const showGroup = cat.groupLabel && cat.groupLabel !== lastGroup;
        if (showGroup) lastGroup = cat.groupLabel;
        const active = activeCategory === cat.id;
        return (
          <span key={cat.id} className="doc-category-bar-item">
            {showGroup && filteredGroups.length > 1 ? (
              <span className="doc-category-group-label">{cat.groupLabel}</span>
            ) : null}
            <button
              type="button"
              role="tab"
              aria-selected={active}
              className={`doc-category-chip${active ? ' active' : ''}`}
              onClick={() => onSelectCategory(cat.id)}
              title={cat.description || cat.label}
            >
              <CatIcon size={12} aria-hidden />
              <span>{cat.label}</span>
              {cat.sensitive || sensitiveCategories.includes(cat.id) ? (
                <Lock size={10} aria-label="Sensitive" />
              ) : null}
              <span className="doc-category-chip-count">{cat.count}</span>
            </button>
          </span>
        );
      })}
    </div>
  );
}
