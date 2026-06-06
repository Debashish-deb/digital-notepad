import React from 'react';
import {
  Atom,
  BrainCircuit,
  Database,
  Dna,
  Network,
  Sparkles,
} from 'lucide-react';
import './AiAssistant3D.css';

export default function AiAssistant3DScene({
  eyebrow = 'Intelligent research interface',
  title = 'OMEIA AI Lab Assistant',
  subtitle = 'A spatial-biology copilot for research memory, RAG retrieval, and protocol intelligence.',
  stats = [],
  compact = false,
  merged = false,
  toolbar = null,
  className = '',
}) {
  const safeStats = Array.isArray(stats) ? stats.filter(Boolean).slice(0, 4) : [];

  return (
    <section
      className={`ai3d-hero${compact ? ' ai3d-hero--compact' : ''}${merged ? ' ai3d-hero--merged' : ''}${className ? ` ${className}` : ''}`}
      aria-label={title}
    >
      {toolbar ? <div className="ai3d-hero__toolbar">{toolbar}</div> : null}

      <div className="ai3d-hero__main">
      <div className="ai3d-hero__visual" aria-hidden="true">
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
      </div>

      <div className="ai3d-hero__copy">
        {!toolbar ? (
          <div className="ai3d-eyebrow">
            <Sparkles size={14} aria-hidden="true" />
            {eyebrow}
          </div>
        ) : null}

        <h2>{title}</h2>
        <p>{subtitle}</p>

        {safeStats.length > 0 && (
          <div className="ai3d-stat-row" aria-label="Assistant status">
            {safeStats.map((stat) => (
              <div key={`${stat.label}-${stat.value}`} className="ai3d-stat">
                <span>{stat.label}</span>
                <strong>{stat.value}</strong>
              </div>
            ))}
          </div>
        )}
      </div>
      </div>
    </section>
  );
}
