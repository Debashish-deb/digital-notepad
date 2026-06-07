import { useEffect, useState } from 'react';
import {
  Beaker,
  BookOpen,
  Brain,
  ChartBar,
  Code2,
  Dna,
  FlaskConical,
  Grid3x3,
  Image,
  Zap,
} from 'lucide-react';
import { fetchCategoryDetail } from '../api/agentCategoryClient.js';

const ICONS = {
  flask: FlaskConical,
  dna: Dna,
  grid: Grid3x3,
  beaker: Beaker,
  chart: ChartBar,
  book: BookOpen,
  code: Code2,
  image: Image,
  zap: Zap,
  brain: Brain,
};

const MODES = [
  { id: 'fast', label: 'Fast' },
  { id: 'balanced', label: 'Balanced' },
  { id: 'deep', label: 'Deep' },
];

export default function AgentCategorySelector({
  categories = [],
  selectedCategory = 'general_research',
  selectedMode = 'balanced',
  onCategoryChange,
  onModeChange,
  disabled = false,
  loading = false,
  variant = 'panel',
  layout = 'default',
  compact = false,
  showDebug = false,
  modelCatalog = null,
  debugModels = false,
  onToggleDebugModels,
  teamRoster: teamRosterProp = null,
}) {
  const active = categories.find((c) => c.id === selectedCategory) || categories[0];
  const [teamRoster, setTeamRoster] = useState(teamRosterProp || []);

  useEffect(() => {
    if (teamRosterProp?.length) {
      setTeamRoster(teamRosterProp);
      return undefined;
    }
    let cancelled = false;
    fetchCategoryDetail(selectedCategory, selectedMode)
      .then((detail) => {
        if (!cancelled) setTeamRoster(detail?.team_roster || []);
      })
      .catch(() => {
        if (!cancelled) setTeamRoster([]);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedCategory, selectedMode, teamRosterProp]);

  const roster = teamRoster.length
    ? teamRoster
    : (active?.team_preview || []).map((label) => ({ label, model: 'Auto', chains: [label] }));

  if (variant === 'context') {
    const ActiveIcon = ICONS[active?.icon] || FlaskConical;
    const toneId = active?.id || 'general_research';
    return (
      <div
        className={`agent-category-context-strip agent-category-context-strip--tone-${toneId}`}
        aria-label="Active intelligence team"
      >
        <div className="agent-category-context-strip__head">
          <span className="agent-category-context-strip__icon" aria-hidden>
            <ActiveIcon size={15} />
          </span>
          <span className="agent-category-context-strip__label">{active?.label || 'Lab Research Assistant'}</span>
          <span className={`agent-category-context-strip__mode agent-category-context-strip__mode--${selectedMode}`}>
            {selectedMode}
          </span>
        </div>
        <div className="agent-category-context-strip__team">
          {roster.map((member, index) => (
            <span
              key={member.id || member.label}
              className={`agent-category-context-strip__member agent-category-context-strip__member--tone-${(index % 5) + 1}`}
              title={member.model}
            >
              {member.label}
              <em>{member.model || 'Auto'}</em>
            </span>
          ))}
        </div>
      </div>
    );
  }

  const isCover = layout === 'cover';

  return (
    <div
      className={`agent-category-selector${compact ? ' agent-category-selector--compact' : ''}${isCover ? ' agent-category-selector--cover' : ''}`}
      aria-label="Research intelligence mode"
    >
      <div className="agent-category-selector__header">
        <span className="agent-category-selector__title">{isCover ? 'Intelligence' : 'Research Intelligence Mode'}</span>
        <div className="agent-category-mode-pills" role="tablist" aria-label="Collaboration mode">
          {MODES.map((m) => (
            <button
              key={m.id}
              type="button"
              role="tab"
              aria-selected={selectedMode === m.id}
              className={`agent-category-mode-pill agent-category-mode-pill--${m.id}${selectedMode === m.id ? ' is-active' : ''}`}
              onClick={() => onModeChange?.(m.id)}
              disabled={disabled}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      <div className={`agent-category-grid${compact || isCover ? ' agent-category-grid--compact' : ''}`}>
        {loading && !categories.length ? (
          <p className="agent-category-empty text-footnote muted">Loading research modes…</p>
        ) : null}
        {!loading && !categories.length ? (
          <p className="agent-category-empty text-footnote muted">No research intelligence modes available.</p>
        ) : null}
        {categories.map((cat) => {
          const Icon = ICONS[cat.icon] || FlaskConical;
          const isActive = cat.id === selectedCategory;
          const labelOnly = compact || isCover;
          return (
            <button
              key={cat.id}
              type="button"
              className={`agent-category-card agent-category-card--tone-${cat.id}${isActive ? ' is-active' : ''}${labelOnly ? ' agent-category-card--compact' : ''}${isCover ? ' agent-category-card--label-only' : ''}`}
              onClick={() => onCategoryChange?.(cat.id)}
              disabled={disabled}
              aria-pressed={isActive}
              title={labelOnly ? undefined : cat.description}
            >
              <span className="agent-category-card__icon" aria-hidden>
                <Icon size={labelOnly ? 13 : 16} />
              </span>
              <span className="agent-category-card__label">{cat.label}</span>
              {!labelOnly && cat.description ? (
                <span className="agent-category-card__desc">{cat.description}</span>
              ) : null}
            </button>
          );
        })}
      </div>

      {active && !isCover ? (
        <div className="agent-category-active-team">
          <span className="agent-category-active-team__label">Active team</span>
          <div className="agent-category-active-team__roster">
            {roster.map((member) => (
              <div key={member.id || member.label} className="agent-category-team-member">
                <div className="agent-category-team-member__head">
                  <span className="agent-category-team-member__name">{member.label}</span>
                  <span className="agent-category-team-member__model">{member.model || 'Auto'}</span>
                </div>
                <div className="agent-category-team-member__chains">
                  {(member.chains || []).map((chain) => (
                    <span key={`${member.label}-${chain}`} className="agent-category-team-chip">{chain}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {showDebug ? (
        <details className="agent-category-debug">
          <summary>Advanced details</summary>
          <label className="agent-category-debug__toggle">
            <input
              type="checkbox"
              checked={debugModels}
              onChange={(e) => onToggleDebugModels?.(e.target.checked)}
            />
            Show legacy model picker (developer)
          </label>
          {debugModels && modelCatalog?.groups?.length ? (
            <p className="agent-category-debug__note text-footnote muted">
              Debug only — internal routing selects models per agent automatically.
            </p>
          ) : null}
        </details>
      ) : null}
    </div>
  );
}
