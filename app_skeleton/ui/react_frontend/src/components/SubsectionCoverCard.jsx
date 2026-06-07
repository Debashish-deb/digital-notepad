import { getModuleCover } from '../data/moduleCoverContent.js';
import { useGuiT } from '../i18n/useGuiT.js';
import './SubsectionCoverCard.css';

/**
 * Compact subsection header shown below ModuleCoverHero — kicker, title, one-line description.
 */
export default function SubsectionCoverCard({
  mainId,
  subId,
  kicker,
  title,
  description,
  actions = null,
  className = '',
}) {
  const { nav } = useGuiT();
  const main = nav.findMain(mainId);
  const sub = nav.findSub(mainId, subId);
  const cover = getModuleCover(mainId, subId);
  const tone = cover?.tone || mainId;

  const resolvedKicker = kicker ?? (cover?.useIntroCopy ? main?.label : cover?.eyebrow) ?? main?.label ?? '';
  const resolvedTitle = title ?? sub?.label ?? '';
  const resolvedDescription = description ?? sub?.description ?? '';

  if (!resolvedTitle) return null;

  return (
    <header
      className={`subsection-cover-card subsection-cover-card--${tone}${className ? ` ${className}` : ''}`.trim()}
      style={cover?.accentHue ? { '--cover-accent': cover.accentHue } : undefined}
    >
      <div className="subsection-cover-card__inner">
        {resolvedKicker ? (
          <p className="subsection-cover-card__kicker">{resolvedKicker}</p>
        ) : null}
        <div className="subsection-cover-card__headline">
          <h2 className="subsection-cover-card__title">{resolvedTitle}</h2>
          {resolvedDescription ? (
            <p className="subsection-cover-card__lead" title={resolvedDescription}>
              {resolvedDescription}
            </p>
          ) : null}
        </div>
      </div>
      {actions ? <div className="subsection-cover-card__actions">{actions}</div> : null}
    </header>
  );
}
