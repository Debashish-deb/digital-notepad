import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Camera,
  FileText,
  PartyPopper,
  Users,
} from 'lucide-react';
import LabDocumentsBrowser from '../LabDocumentsBrowser.jsx';
import { useGuiT } from '../../i18n/useGuiT.js';
import { SOCIAL_INNER_TAB_IDS } from '../../config/navigation.js';
import {
  categorizeSocialPrimary,
  getSocialConfig,
  socialDocumentTitle,
} from '../../utils/socialCategories.js';
import { SEARCH_NAV_STORAGE_KEY } from '../../utils/searchHits.js';

const SUB_ICONS = {
  lab_parties: PartyPopper,
  winter_events: Camera,
  lab_retreats: Users,
  lab_photos: Camera,
  researcher_visits: Users,
  outreach: Camera,
};

const CATEGORY_ICONS = {
  party_halloween: PartyPopper,
  party_grilling: PartyPopper,
  party_planning: PartyPopper,
  winter_photos: Camera,
  winter_docs: FileText,
  retreat_2024: Users,
  retreat_2025: Users,
  retreat_planning: FileText,
  photo_retreats: Camera,
  photo_shoot: Camera,
  photo_group: Camera,
  photo_events: PartyPopper,
  photo_misc: Camera,
  visit_records: Users,
  outreach_media: Camera,
  social_misc: FileText,
};

function resolveInitialSocialSub(activeSub) {
  if (activeSub && SOCIAL_INNER_TAB_IDS.includes(activeSub)) return activeSub;
  try {
    const raw = sessionStorage.getItem(SEARCH_NAV_STORAGE_KEY);
    if (!raw) return 'lab_photos';
    const pending = JSON.parse(raw);
    if (pending?.sub && SOCIAL_INNER_TAB_IDS.includes(pending.sub)) return pending.sub;
    if (pending?.relative_path) {
      const primary = categorizeSocialPrimary(pending.relative_path);
      if (SOCIAL_INNER_TAB_IDS.includes(primary)) return primary;
    }
  } catch {
    /* ignore */
  }
  return 'lab_photos';
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
  const Icon = SUB_ICONS[effectiveSub] || PartyPopper;

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

      <LabDocumentsBrowser
        key={`overview-social-${effectiveSub}`}
        sectionIds={config.sectionIds}
        title={tabLabels.find((tab) => tab.id === effectiveSub)?.label || title}
        description={
          tabLabels.find((tab) => tab.id === effectiveSub)?.description || description
        }
        icon={Icon}
        categoryGroups={config.categoryGroups}
        defaultCategory={config.defaultCategory}
        categorizePath={(path, sourceSection) => config.categorizePath(path, sourceSection)}
        documentTitle={socialDocumentTitle}
        documentFilter={config.documentFilter}
        categoryIcons={CATEGORY_ICONS}
        className="overview-documents-browser overview-social-browser catalog-space-browser"
      />
    </div>
  );
}
