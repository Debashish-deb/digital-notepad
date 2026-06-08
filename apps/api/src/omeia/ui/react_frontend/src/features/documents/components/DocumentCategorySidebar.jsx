import { FileText, Lock } from 'lucide-react';

/**
 * Vertical sub-tabs for categories within a section (not the top module nav).
 */
export default function DocumentCategorySidebar({
  filteredGroups,
  grouped,
  activeCategory,
  onSelectCategory,
  categoryIcons = {},
  sensitiveCategories = [],
}) {
  const hasAny = filteredGroups.some((group) =>
    group.categories.some((cat) => (grouped[cat.id] || []).length > 0)
  );
  if (!hasAny) return null;

  return (
    <nav
      className="lab-doc-subnav"
      role="tablist"
      aria-label="Section categories"
    >
      {filteredGroups.map((group) => {
        const catsWithFiles = group.categories.filter((cat) => (grouped[cat.id] || []).length > 0);
        if (!catsWithFiles.length) return null;
        return (
          <div key={group.id} className="lab-doc-subnav-group">
            {filteredGroups.length > 1 ? (
              <div className="lab-doc-subnav-group-label">{group.label}</div>
            ) : null}
            {catsWithFiles.map((cat) => {
              const CatIcon = categoryIcons[cat.id] || FileText;
              const count = (grouped[cat.id] || []).length;
              const active = activeCategory === cat.id;
              const sensitive = cat.sensitive || sensitiveCategories.includes(cat.id);
              return (
                <button
                  key={cat.id}
                  type="button"
                  role="tab"
                  aria-selected={active}
                  className={`lab-doc-subnav-item${active ? ' active' : ''}`}
                  onClick={() => onSelectCategory(cat.id)}
                  title={cat.description || cat.label}
                >
                  <CatIcon size={14} className="lab-doc-subnav-icon" aria-hidden />
                  <span className="lab-doc-subnav-label">{cat.label}</span>
                  {sensitive ? (
                    <Lock size={10} className="lab-doc-subnav-sensitive" aria-label="Sensitive" />
                  ) : null}
                  <span className="lab-doc-subnav-count">{count}</span>
                </button>
              );
            })}
          </div>
        );
      })}
    </nav>
  );
}
