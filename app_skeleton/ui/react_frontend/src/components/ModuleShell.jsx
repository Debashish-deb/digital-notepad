import React, { useEffect, useMemo, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import TaskpadSheet from './TaskpadSheet.jsx';
import { useTaskpad } from '../contexts/TaskpadContext.jsx';
import ModuleCoverHero from './ModuleCoverHero.jsx';
import { useGuiT } from '../i18n/useGuiT.js';
import { moduleHasCover } from '../data/moduleCoverContent.js';
import { ModuleShellHeaderSlotContext } from '../contexts/ModuleShellHeaderSlotContext.jsx';
import { ModuleShellCoverContext } from '../contexts/ModuleShellCoverContext.jsx';

/**
 * Section layout: title row (section + page), full-width content.
 * Sub-tabs live in the sidebar under the active main nav item.
 */
export default function ModuleShell({
  mainId,
  subId,
  onSubChange,
  onRefresh,
  isRefreshing = false,
  compact = false,
  landing = false,
  children,
}) {
  const { t, nav } = useGuiT();
  const { setSectionScope } = useTaskpad();
  const main = nav.findMain(mainId);
  const sub = nav.findSub(mainId, subId);

  useEffect(() => {
    setSectionScope(mainId, subId);
  }, [mainId, subId, setSectionScope]);
  const useCover = landing && moduleHasCover(mainId);
  const isAiCopilot = mainId === 'ai_assistant' && subId === 'copilot';
  const showModuleCover = useCover && !isAiCopilot;
  const showSubnav = false;
  const [headerSlot, setHeaderSlot] = useState(null);
  const setHeaderSlotStable = useMemo(() => setHeaderSlot, []);
  const coverContext = useMemo(
    () => ({ mainId, subId, onRefresh, isRefreshing }),
    [mainId, subId, onRefresh, isRefreshing],
  );

  return (
    <ModuleShellCoverContext.Provider value={coverContext}>
    <ModuleShellHeaderSlotContext.Provider value={setHeaderSlotStable}>
    <div
      className={`module-shell module-shell--top-tabs${mainId !== 'projects_data' ? ' module-shell--catalog-docs' : ''}${mainId === 'orders' ? ' module-shell--orders' : ''}${compact ? ' module-shell--compact' : ''}${useCover ? ' module-shell--cover' : ''}`}
    >
      {!useCover ? (
      <header className="module-shell-header">
        <div className="module-shell-heading">
          <p className="module-shell-eyebrow">{main.label}</p>
          <h1 className="module-shell-title">{sub.label}</h1>
          {sub.description ? (
            <p className="module-shell-lead">{sub.description}</p>
          ) : null}
        </div>
        <div className="module-shell-header-actions">
          {headerSlot ? <div className="module-shell-header-slot">{headerSlot}</div> : null}
          <div className="module-header-taskpad">
            <TaskpadSheet mainId={mainId} subId={subId} />
          </div>
          {onRefresh ? (
            <button
              type="button"
              className="module-refresh-btn"
              onClick={onRefresh}
              disabled={isRefreshing}
              aria-label={isRefreshing ? t('common.syncing') : t('common.refreshAria')}
              title={isRefreshing ? t('common.syncing') : t('common.refresh')}
            >
              <RefreshCw size={15} className={isRefreshing ? 'spin' : undefined} aria-hidden />
            </button>
          ) : null}
        </div>
      </header>
      ) : null}

      {showSubnav ? (
        <nav
          className="module-subnav module-subnav--horizontal module-top-tabs"
          aria-label={`${main.label} sections`}
        >
          {main.children.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`module-subnav-item module-top-tab${subId === item.id ? ' active' : ''}`}
              onClick={() => onSubChange(item.id)}
              aria-current={subId === item.id ? 'page' : undefined}
              title={item.description || item.label}
            >
              <span className="module-subnav-label">{item.label}</span>
            </button>
          ))}
        </nav>
      ) : null}

      <div className="module-shell-body">
        {showModuleCover ? (
          <ModuleCoverHero
            mainId={mainId}
            subId={subId}
            onSubChange={onSubChange}
            onRefresh={onRefresh}
            isRefreshing={isRefreshing}
          />
        ) : null}
        <div className="module-shell-page">{children}</div>
      </div>
    </div>
    </ModuleShellHeaderSlotContext.Provider>
    </ModuleShellCoverContext.Provider>
  );
}
