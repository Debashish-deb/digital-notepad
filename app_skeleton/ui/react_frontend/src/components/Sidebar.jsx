import React, { memo, useCallback, useMemo } from 'react';
import {
  ChevronDown,
  Dna,
  GitBranch,
  LogOut,
  Moon,
  Search,
  Sun,
} from 'lucide-react';
import LanguageSwitcher from './LanguageSwitcher.jsx';
import { useGuiT } from '../i18n/useGuiT.js';
import { useTaskpad } from '../contexts/TaskpadContext.jsx';
import { useTheme } from '../contexts/ThemeContext.jsx';

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
  apiHealth,
  onOpenSearch,
  userLabel = 'Guest',
  userEmail = null,
  onSignOut = null,
}) {
  const { t, nav } = useGuiT();
  const { openCentralTaskpad } = useTaskpad();
  const { theme: activeTheme, cycleTheme, availableThemes, themeMeta } = useTheme();

  const activeMain = navMain;
  const currentIndex = availableThemes.indexOf(activeTheme);
  const nextTheme = availableThemes[(currentIndex + 1) % availableThemes.length];

  const currentThemeMeta = themeMeta[activeTheme] || themeMeta.dark;
  const nextThemeMeta = themeMeta[nextTheme] || themeMeta.dark;
  const CurrentThemeIcon = currentThemeMeta.icon;

  const apiStatus = useMemo(() => {
    if (!apiHealth) {
      return {
        label: 'Offline',
        tone: 'muted',
      };
    }

    if (apiHealth.ok || apiHealth.status === 'ok' || apiHealth.status === 'healthy') {
      return {
        label: 'Online',
        tone: 'success',
      };
    }

    if (apiHealth.status === 'degraded') {
      return {
        label: 'Degraded',
        tone: 'warning',
      };
    }

    return {
      label: 'Check',
      tone: 'danger',
    };
  }, [apiHealth]);

  const handleThemeToggle = useCallback(() => {
    cycleTheme();
  }, [cycleTheme]);

  return (
    <aside className="sidebar" aria-label={t('common.mainNavAria')}>
      <header className="sidebar-header">
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
              className={`sidebar-group${isExpanded ? ' sidebar-group--active' : ''}${isActive ? ' sidebar-group--current' : ''}`}
            >
              <button
                type="button"
                className={`sidebar-item sidebar-item-main${isActive ? ' active' : ''}${isExpanded ? ' expanded' : ''}`}
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
        <button
          type="button"
          className="sidebar-central-taskpad-btn"
          onClick={openCentralTaskpad}
          title={t('taskpad.centralTitle')}
        >
          <GitBranch size={15} aria-hidden="true" />
          <span>{t('taskpad.centralTitle')}</span>
        </button>

        <div className="sidebar-footer-profile">
          <div className="sidebar-user-avatar" aria-hidden="true">
            {getInitials(userLabel)}
          </div>

          <div className="sidebar-user-copy">
            <span className="sidebar-user-label">{t('common.user')}</span>
            <strong className="sidebar-user-name" title={userEmail || userLabel}>
              {userLabel}
            </strong>
            {userEmail ? <span className="sidebar-user-email">{userEmail}</span> : null}
          </div>

          <span
            className={`sidebar-api-dot sidebar-api-dot--${apiStatus.tone}`}
            title={`API: ${apiStatus.label}`}
            aria-label={`API ${apiStatus.label}`}
          />
        </div>

        <div className="sidebar-footer-toolbar" role="toolbar" aria-label={t('common.sidebarToolbarAria', 'Sidebar settings')}>
          <div className="sidebar-footer-toolbar-lang">
            <LanguageSwitcher variant="select" showLabel={false} />
          </div>

          <div className="sidebar-footer-toolbar-actions">
            <button
              type="button"
              onClick={handleThemeToggle}
              className="theme-toggle-btn sidebar-icon-btn"
              title={`${currentThemeMeta.label} — switch to ${nextThemeMeta.label}`}
              aria-label={`Switch to ${nextThemeMeta.label} theme`}
            >
              <CurrentThemeIcon size={17} aria-hidden="true" />
            </button>

            {onSignOut ? (
              <button
                type="button"
                className="theme-toggle-btn sidebar-icon-btn sidebar-icon-btn--danger"
                onClick={onSignOut}
                title="Sign out"
                aria-label="Sign out"
              >
                <LogOut size={17} aria-hidden="true" />
              </button>
            ) : null}
          </div>
        </div>
      </div>
    </aside>
  );
}

export default memo(Sidebar);
