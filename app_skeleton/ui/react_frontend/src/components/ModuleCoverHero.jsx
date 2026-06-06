import { ExternalLink, Globe2, RefreshCw } from 'lucide-react';
import LanguageSwitcher from './LanguageSwitcher.jsx';
import TaskpadSheet from './TaskpadSheet.jsx';
import { useGuiT } from '../i18n/useGuiT.js';
import { getModuleCover } from '../data/moduleCoverContent.js';

const LAB_SITE = 'https://www.farkkilab.org';

export default function ModuleCoverHero({
  mainId,
  subId,
  onSubChange,
  onRefresh,
  isRefreshing = false,
}) {
  const { locale, intro, nav, t: guiT } = useGuiT();
  const main = nav.findMain(mainId);
  const cover = getModuleCover(mainId, subId);

  if (!cover || !main) return null;

  const eyebrow = cover.useIntroCopy ? main.label : cover.eyebrow;
  const title = cover.useIntroCopy ? intro.title : cover.title || main.label;
  const lead = cover.useIntroCopy ? intro.lead : cover.lead || main.children[0]?.description || '';

  const MainIcon = main.icon;

  return (
    <header
      className={`module-cover-hero module-cover-hero--${cover.tone || mainId}`}
      lang={mainId === 'overview' ? locale : undefined}
    >
      <div className="module-cover-hero__glow" aria-hidden />
      {cover.overlayArt?.src ? (
        <img
          className={`module-cover-hero__overlay module-cover-hero__overlay--${cover.overlayArt.position || 'bottom-right'}`}
          src={cover.overlayArt.src}
          alt=""
          aria-hidden
          loading="lazy"
          decoding="async"
          draggable={false}
        />
      ) : null}
      <div className="module-cover-hero__inner">
        <div className="module-cover-hero__toolbar">
          <div className="module-cover-hero__meta">
            <p className="module-cover-hero__eyebrow">
              {MainIcon ? <MainIcon size={14} aria-hidden /> : null}
              {eyebrow}
            </p>
            {mainId === 'overview' ? <LanguageSwitcher variant="pills" /> : null}
          </div>
          <div className="module-cover-hero__actions">
            <div className="module-cover-hero__taskpad">
              <TaskpadSheet mainId={mainId} subId={subId} />
            </div>
            {onRefresh ? (
              <button
                type="button"
                className="module-cover-hero__icon-btn"
                onClick={onRefresh}
                disabled={isRefreshing}
                aria-label={isRefreshing ? guiT('common.syncing') : guiT('common.refreshAria')}
                title={isRefreshing ? guiT('common.syncing') : guiT('common.refresh')}
              >
                <RefreshCw size={15} className={isRefreshing ? 'spin' : undefined} aria-hidden />
              </button>
            ) : null}
            {mainId === 'overview' ? (
              <a
                href={LAB_SITE}
                className="module-cover-hero__link-btn"
                target="_blank"
                rel="noopener noreferrer"
                title={intro.visitHint}
              >
                <Globe2 size={14} aria-hidden />
                <span>{intro.visitSite}</span>
                <ExternalLink size={12} aria-hidden />
              </a>
            ) : null}
          </div>
        </div>

        <h1 className="module-cover-hero__title">{title}</h1>
        <p className="module-cover-hero__lead">{lead}</p>
      </div>
    </header>
  );
}
