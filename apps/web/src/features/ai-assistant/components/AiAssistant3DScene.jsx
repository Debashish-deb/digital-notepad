import {
  Atom,
  BrainCircuit,
  Database,
  Dna,
  FlaskConical,
  Layers,
  Network,
  Radio,
  Sparkles,
} from 'lucide-react';
import AiSolarBrainVisual from './AiSolarBrainVisual.jsx';

const TELEMETRY_ICONS = {
  database: Database,
  team: FlaskConical,
  scope: Layers,
  collab: Network,
  status: Radio,
};
import SwimmingProjectTopics from '@/shared/ui/SwimmingProjectTopics.jsx';
import '@/features/ai-assistant/styles/AiAssistant3D.css';

export default function AiAssistant3DScene({
  eyebrow = 'Intelligent research interface',
  title = 'OMEIA AI Lab Assistant',
  subtitle = 'A spatial-biology copilot for research memory, RAG retrieval, and protocol intelligence.',
  stats = [],
  swimmingTopics = [],
  compact = false,
  merged = false,
  visualPosition = 'left',
  visualOnly = false,
  visual = 'classic',
  dense = false,
  toolbar = null,
  className = '',
}) {
  const safeStats = Array.isArray(stats) ? stats.filter(Boolean).slice(0, 4) : [];

  return (
    <section
      className={`ai3d-hero${compact ? ' ai3d-hero--compact' : ''}${dense ? ' ai3d-hero--dense' : ''}${merged ? ' ai3d-hero--merged' : ''}${className ? ` ${className}` : ''}`}
      aria-label={title}
    >
      {swimmingTopics.length > 0 ? <SwimmingProjectTopics topics={swimmingTopics} /> : null}
      {toolbar ? <div className="ai3d-hero__toolbar">{toolbar}</div> : null}

      <div className={`ai3d-hero__main${visualPosition === 'right' ? ' ai3d-hero__main--visual-right' : ''}${visualOnly ? ' ai3d-hero__main--visual-only' : ''}`}>
      <div className="ai3d-hero__visual" aria-hidden="true">
        {visual === 'solar' ? (
          <AiSolarBrainVisual compact={compact || dense} />
        ) : (
          <div className="ai3d-stage">
            <div className="ai3d-orbit ai3d-orbit--outer" />
            <div className="ai3d-orbit ai3d-orbit--middle" />
            <div className="ai3d-orbit ai3d-orbit--inner" />

            <div className="ai3d-grid-plane ai3d-grid-plane--back" />
            <div className="ai3d-grid-plane ai3d-grid-plane--floor" />

            <div className="ai3d-core">
              <div className="ai3d-core__glow" />
              <div className="ai3d-core__shell">
                <BrainCircuit size={compact ? 34 : 42} />
              </div>
              <div className="ai3d-core__scanline" />
            </div>

            <div className="ai3d-ring ai3d-ring--one" />
            <div className="ai3d-ring ai3d-ring--two" />
            <div className="ai3d-ring ai3d-ring--three" />

            <div className="ai3d-node ai3d-node--a"><Dna size={16} /></div>
            <div className="ai3d-node ai3d-node--b"><Database size={16} /></div>
            <div className="ai3d-node ai3d-node--c"><Atom size={16} /></div>
            <div className="ai3d-node ai3d-node--d"><Network size={16} /></div>

            <span className="ai3d-particle ai3d-particle--1" />
            <span className="ai3d-particle ai3d-particle--2" />
            <span className="ai3d-particle ai3d-particle--3" />
            <span className="ai3d-particle ai3d-particle--4" />
            <span className="ai3d-particle ai3d-particle--5" />
          </div>
        )}
      </div>

      {!visualOnly ? (
        <div className="ai3d-hero__copy">
          {!toolbar ? (
            <div className="ai3d-eyebrow">
              <Sparkles size={14} aria-hidden="true" />
              {eyebrow}
            </div>
          ) : null}

          <div className="ai3d-hero__title-block">
            <h2>{title}</h2>
            {!dense ? <p>{subtitle}</p> : null}
            {safeStats.length > 0 && dense ? (
              <div className="ai3d-telemetry ai3d-telemetry--grid2" aria-label="Assistant status">
                {safeStats.map((stat) => {
                  const Icon = TELEMETRY_ICONS[stat.icon] || Radio;
                  return (
                    <div
                      key={stat.id || `${stat.label}-${stat.value}`}
                      className={`ai3d-telemetry__chip ai3d-telemetry__chip--${stat.tone || 'neutral'}`}
                      title={stat.title || stat.value}
                    >
                      <span className="ai3d-telemetry__label">{stat.label || stat.id}</span>
                      <div className="ai3d-telemetry__body">
                        <Icon size={10} aria-hidden="true" />
                        <span className="ai3d-telemetry__value">{stat.value}</span>
                        {stat.sub ? <span className="ai3d-telemetry__sub">{stat.sub}</span> : null}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : null}
          </div>

          {safeStats.length > 0 && !dense ? (
            <div className="ai3d-stat-row" aria-label="Assistant status">
              {safeStats.map((stat) => (
                <div key={`${stat.label}-${stat.value}`} className="ai3d-stat">
                  <span>{stat.label}</span>
                  <strong>{stat.value}</strong>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
      </div>
    </section>
  );
}
