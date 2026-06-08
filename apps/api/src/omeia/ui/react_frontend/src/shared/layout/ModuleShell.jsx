import { useCallback, useEffect, useMemo, useState } from 'react';
import CompactCornerSearch from '@/shared/layout/CompactCornerSearch.jsx';
import { RefreshCw } from 'lucide-react';
import TaskpadSheet from '@/features/taskpad/components/TaskpadSheet.jsx';
import { useTaskpad } from '@/contexts/TaskpadContext.jsx';
import ModuleCoverHero from '@/shared/layout/ModuleCoverHero.jsx';
import SubsectionCoverCard from '@/shared/layout/SubsectionCoverCard.jsx';
import { useGuiT } from '@/i18n/useGuiT.js';
import { moduleHasCover } from '@/data/moduleCoverContent.js';
import { ModuleShellHeaderSlotContext } from '@/contexts/ModuleShellHeaderSlotContext.jsx';
import { ModuleShellCoverContext } from '@/contexts/ModuleShellCoverContext.jsx';

/**
 * Section layout: title row (section + page), full-width content.
 * Sub-tabs live in the sidebar under the active main nav item.
 */
function ModuleShell({
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
  const useCover = landing && moduleHasCover(mainId, subId);
  const isAiCopilot = mainId === 'ai_assistant' && subId === 'copilot';
  const showModuleCover = useCover && !isAiCopilot;
  const showSubnav = false;
  const [headerSlot, setHeaderSlot] = useState(null);
  const [subsectionSearch, setSubsectionSearch] = useState(null);
  const setHeaderSlotStable = useCallback((node) => setHeaderSlot(node), []);
  const setSubsectionSearchStable = useCallback((config) => setSubsectionSearch(config), []);
  const coverContext = useMemo(
    () => ({
      mainId,
      subId,
      showModuleCover,
      onRefresh,
      isRefreshing,
      setSubsectionSearch: setSubsectionSearchStable,
    }),
    [mainId, subId, showModuleCover, onRefresh, isRefreshing, setSubsectionSearchStable],
  );

  useEffect(() => {
    if (!showModuleCover) setSubsectionSearch(null);
  }, [mainId, subId, showModuleCover]);

  return (
    <ModuleShellCoverContext.Provider value={coverContext}>
    <ModuleShellHeaderSlotContext.Provider value={setHeaderSlotStable}>
    <div
      className={`module-shell module-shell--top-tabs${mainId !== 'projects_data' ? ' module-shell--catalog-docs' : ''}${mainId === 'orders' ? ' module-shell--orders' : ''}${compact ? ' module-shell--compact' : ''}${useCover ? ' module-shell--cover' : ''}${isAiCopilot ? ' module-shell--ai-copilot' : ''}`}
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
        {showModuleCover ? (
          <SubsectionCoverCard
            mainId={mainId}
            subId={subId}
            title={sub.label}
            description={sub.description}
            actions={subsectionSearch ? (
              <CompactCornerSearch
                value={subsectionSearch.value ?? ''}
                onChange={subsectionSearch.onChange}
                placeholder={subsectionSearch.placeholder}
                ariaLabel={subsectionSearch.ariaLabel}
              />
            ) : null}
          />
        ) : null}
        <div className="module-shell-page">{children}</div>
      </div>
    </div>
    </ModuleShellHeaderSlotContext.Provider>
    </ModuleShellCoverContext.Provider>
  );
}

export default ModuleShell;
