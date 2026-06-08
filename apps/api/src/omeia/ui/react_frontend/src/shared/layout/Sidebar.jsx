import { useCallback } from 'react';
import {
  ChevronDown,
  Dna,
  LogIn,
  LogOut,
  Search,
} from 'lucide-react';
import { useGuiT } from '@/i18n/useGuiT.js';
import { useTheme } from '@/contexts/ThemeContext.jsx';

function getInitials(label = 'Guest') {
  return label
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('') || 'G';
}

function Sidebar({
  navMain,
  navSub,
  sidebarExpandedMain = null,
  onNavChange,
  onMainNavClick,
  onOpenSearch,
  userLabel = 'Guest',
  userEmail = null,
  onSignOut = null,
  onSignIn = null,
  onProfileClick = null,
}) {
  const { t, nav } = useGuiT();
  const { theme: activeTheme, cycleTheme, availableThemes, themeMeta } = useTheme();

  const activeMain = navMain;
  const currentIndex = availableThemes.indexOf(activeTheme);
  const nextTheme = availableThemes[(currentIndex + 1) % availableThemes.length];
  const currentThemeMeta = themeMeta[activeTheme] || themeMeta.dark;
  const nextThemeMeta = themeMeta[nextTheme] || themeMeta.dark;
  const CurrentThemeIcon = currentThemeMeta.icon;

  const handleThemeToggle = useCallback((e) => {
    e.stopPropagation();
    cycleTheme();
  }, [cycleTheme]);

  return (
    <aside className="sidebar" aria-label={t('common.mainNavAria')}>
      <header className="sidebar-header">
        <div className="sidebar-header-top">
          <div className="sidebar-brand">
            <div className="sidebar-logo-mark" aria-hidden="true">
              <Dna size={17} strokeWidth={2.25} />
            </div>

            <div className="sidebar-logo-copy">
              <span className="sidebar-eyebrow">{t('common.appOrg')}</span>
              <span className="sidebar-title">{t('common.appLabName')}</span>
            </div>
          </div>

          <button
            type="button"
            onClick={handleThemeToggle}
            className="sidebar-header-theme-btn nav-glass-square theme-toggle-btn"
            title={t('common.themeTitle', '', { theme: currentThemeMeta.label })}
            aria-label={`Switch to ${nextThemeMeta.label} theme`}
          >
            <CurrentThemeIcon size={16} strokeWidth={2.1} aria-hidden="true" />
          </button>
        </div>

        <button
          type="button"
          className="sidebar-search-btn"
          onClick={onOpenSearch}
          aria-label={t('common.searchRegistry')}
        >
          <Search size={14} className="sidebar-search-icon" aria-hidden="true" />
          <span className="sidebar-search-label">{t('common.searchRegistry')}</span>
          <kbd className="sidebar-search-kbd">⌘K</kbd>
        </button>
      </header>

      <nav className="sidebar-menu" aria-label={t('common.mainNavAria')}>
        {nav.mainNav.map((item) => {
          const Icon = item.icon;
          const isActive = activeMain === item.id;
          const hasChildren = item.children?.length > 1;
          const isExpanded = sidebarExpandedMain === item.id;
          const showChildren = isExpanded && hasChildren;
          const handleMainClick = onMainNavClick || ((main) => onNavChange(main, item.defaultSub));

          return (
            <div
              key={item.id}
              data-main={item.id}
              className={`sidebar-group${isExpanded ? ' sidebar-group--active' : ''}${isActive ? ' sidebar-group--current' : ''}`}
            >
              <button
                type="button"
                className={`sidebar-item sidebar-item-main sidebar-item-main--${item.id}${isActive ? ' active' : ''}${isExpanded ? ' expanded' : ''}`}
                aria-current={isActive && !showChildren ? 'page' : undefined}
                aria-expanded={hasChildren ? isExpanded : undefined}
                onClick={() => handleMainClick(item.id)}
              >
                <span
                  className={`sidebar-item-icon sidebar-item-icon--${item.id}`}
                  aria-hidden="true"
                >
                  <Icon size={17} strokeWidth={2.1} />
                </span>
                <span className="sidebar-item-label">{item.sidebarLabel || item.label}</span>
                {hasChildren ? (
                  <ChevronDown
                    size={14}
                    className="sidebar-item-chevron"
                    aria-hidden="true"
                  />
                ) : null}
              </button>

              {showChildren ? (
                <div className="sidebar-subnav-wrap">
                  <p className="sidebar-subnav-heading">{t('common.sectionPages')}</p>
                  <ul className="sidebar-subnav" aria-label={t('common.sectionTabsAria')}>
                    {item.children.map((child) => {
                      const childActive = navSub === child.id;
                      const childLabel = child.sidebarLabel || child.label;
                      return (
                        <li key={child.id} className="sidebar-subnav-item">
                          <button
                            type="button"
                            className={`sidebar-item sidebar-item-sub${childActive ? ' active' : ''}`}
                            aria-current={childActive ? 'page' : undefined}
                            onClick={() => onNavChange(item.id, child.id)}
                            title={child.label}
                          >
                            <span className="sidebar-subnav-dot" aria-hidden="true" />
                            <span className="sidebar-item-label">{childLabel}</span>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              ) : null}
            </div>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-footer-row">
          <button
            type="button"
            className="sidebar-footer-profile nav-glass-square"
            onClick={onProfileClick}
            disabled={!onProfileClick}
            aria-current={navMain === 'profile' ? 'page' : undefined}
            aria-label={t('common.openProfile', 'Open profile')}
            title={userEmail || userLabel}
          >
            <div className="sidebar-user-avatar" aria-hidden="true">
              {getInitials(userLabel)}
            </div>
            <strong className="sidebar-user-name">{userLabel}</strong>
          </button>

          {onSignOut ? (
            <button
              type="button"
              className="sidebar-exit-btn nav-glass-square"
              onClick={onSignOut}
              title="Sign out"
              aria-label="Sign out"
            >
              <LogOut size={18} strokeWidth={2.25} aria-hidden="true" />
              <span>Exit</span>
            </button>
          ) : onSignIn ? (
            <button
              type="button"
              className="sidebar-exit-btn nav-glass-square sidebar-signin-btn"
              onClick={onSignIn}
              title="Sign in"
              aria-label="Sign in"
            >
              <LogIn size={18} strokeWidth={2.25} aria-hidden="true" />
              <span>Sign in</span>
            </button>
          ) : null}
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;
