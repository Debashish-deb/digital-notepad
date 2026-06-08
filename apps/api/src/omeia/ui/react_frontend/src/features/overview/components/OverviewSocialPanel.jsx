import { useCallback, useEffect, useMemo, useState } from 'react';
import LabDocumentExplorer from '@/features/documents/components/LabDocumentExplorer.jsx';
import { useGuiT } from '@/i18n/useGuiT.js';
import { SOCIAL_INNER_TAB_IDS, getDefaultSocialSub } from '@/config/navigation.js';
import { getSocialConfig } from '@/lib/socialCategories.js';
import { SEARCH_NAV_STORAGE_KEY } from '@/lib/searchHits.js';

function resolveInitialSocialSub(activeSub) {
  if (activeSub && SOCIAL_INNER_TAB_IDS.includes(activeSub)) return activeSub;
  try {
    const raw = sessionStorage.getItem(SEARCH_NAV_STORAGE_KEY);
    if (!raw) return getDefaultSocialSub();
    const pending = JSON.parse(raw);
    if (pending?.sub && SOCIAL_INNER_TAB_IDS.includes(pending.sub)) return pending.sub;
    if (pending?.relative_path) {
      const primary = categorizeSocialPrimary(pending.relative_path);
      if (SOCIAL_INNER_TAB_IDS.includes(primary)) return primary;
    }
  } catch {
    /* ignore */
  }
  return getDefaultSocialSub();
}

export default function OverviewSocialPanel({
  activeSub,
  onSubChange,
  title,
  description,
}) {
  const { t } = useGuiT();
  const [socialSub, setSocialSub] = useState(() => resolveInitialSocialSub(activeSub));

  useEffect(() => {
    if (activeSub && SOCIAL_INNER_TAB_IDS.includes(activeSub)) {
      setSocialSub(activeSub);
    }
  }, [activeSub]);

  const setSocialSubAndNotify = useCallback(
    (nextSub) => {
      if (!SOCIAL_INNER_TAB_IDS.includes(nextSub)) return;
      setSocialSub(nextSub);
      onSubChange?.(nextSub);
    },
    [onSubChange],
  );

  const effectiveSub = activeSub && SOCIAL_INNER_TAB_IDS.includes(activeSub) ? activeSub : socialSub;
  const config = getSocialConfig(effectiveSub);

  const tabLabels = useMemo(
    () =>
      SOCIAL_INNER_TAB_IDS.map((tabId) => ({
        id: tabId,
        label: t(`navSub.social.${tabId}.label`, tabId),
        description: t(`navSub.social.${tabId}.description`, ''),
      })),
    [t],
  );

  if (!config) return null;

  return (
    <div className="overview-social-panel">
      <nav
        className="module-subnav module-subnav--horizontal module-top-tabs overview-social-tabs"
        aria-label={title || 'Social sections'}
      >
        {tabLabels.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`module-subnav-item module-top-tab${effectiveSub === tab.id ? ' active' : ''}`}
            onClick={() => setSocialSubAndNotify(tab.id)}
            aria-current={effectiveSub === tab.id ? 'page' : undefined}
            title={tab.description || tab.label}
          >
            <span className="module-subnav-label">{tab.label}</span>
          </button>
        ))}
      </nav>

      <LabDocumentExplorer
        mainId="overview"
        subId="social"
        title={tabLabels.find((tab) => tab.id === effectiveSub)?.label || title}
        description={
          tabLabels.find((tab) => tab.id === effectiveSub)?.description || description
        }
        className="overview-documents-browser overview-social-browser lab-document-explorer--social"
      />
    </div>
  );
}
