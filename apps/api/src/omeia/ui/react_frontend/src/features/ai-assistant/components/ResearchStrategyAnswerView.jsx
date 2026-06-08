import {
  AlertTriangle,
  BookOpen,
  FlaskConical,
  Lightbulb,
  ListChecks,
  Route,
  Scale,
  Sparkles,
  Target,
} from 'lucide-react';
import './ResearchStrategyAnswerView.css';

function confidenceClass(level) {
  const v = String(level || '').toLowerCase();
  if (v === 'high') return 'rsa-confidence rsa-confidence--high';
  if (v === 'medium') return 'rsa-confidence rsa-confidence--medium';
  return 'rsa-confidence rsa-confidence--low';
}

function EvidenceList({ items, label }) {
  if (!items?.length) return null;
  return (
    <div className="rsa-evidence-block">
      <h4>{label}</h4>
      <ul className="rsa-evidence-list">
        {items.map((item, idx) => (
          <li key={`${item.title}-${idx}`}>
            <strong>{item.title}</strong>
            {item.bucket ? <span className="rsa-badge">{item.bucket}</span> : null}
            {item.snippet ? <p>{item.snippet}</p> : null}
            {item.doi ? <span className="rsa-meta">DOI: {item.doi}</span> : null}
            {item.pmid ? <span className="rsa-meta">PMID: {item.pmid}</span> : null}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function ResearchStrategyAnswerView({ report }) {
  if (!report || report.answer_type !== 'research_strategy') return null;

  const directions = report.recommended_directions || [];

  return (
    <article className="rsa-answer" aria-label="Research strategy answer">
      <header className="rsa-header">
        <Sparkles size={18} aria-hidden="true" />
        <div>
          <h3>Research Strategy</h3>
          <span className={confidenceClass(report.confidence_overall)}>
            Overall confidence: {report.confidence_overall || 'medium'}
          </span>
        </div>
      </header>

      {report.executive_summary ? (
        <section className="rsa-section">
          <h4><Target size={16} /> Executive Summary</h4>
          <p>{report.executive_summary}</p>
        </section>
      ) : null}

      {directions.length ? (
        <section className="rsa-section">
          <h4><Route size={16} /> Top Recommended Directions</h4>
          {directions.map((dir, i) => (
            <div className="rsa-direction" key={`${dir.title}-${i}`}>
              <div className="rsa-direction__head">
                <strong>{i + 1}. {dir.title}</strong>
                <span className={confidenceClass(dir.confidence)}>{dir.confidence}</span>
              </div>
              {dir.rationale ? <p>{dir.rationale}</p> : null}
              {dir.expected_impact ? (
                <p className="rsa-impact"><Lightbulb size={14} /> {dir.expected_impact}</p>
              ) : null}
              <EvidenceList items={dir.internal_evidence} label="Internal evidence" />
              <EvidenceList items={dir.external_evidence} label="External literature" />
              {dir.risks?.length ? (
                <div className="rsa-risks">
                  <AlertTriangle size={14} />
                  <span>{dir.risks.join(' ')}</span>
                </div>
              ) : null}
              {dir.validation_experiments?.length ? (
                <div className="rsa-validation">
                  <FlaskConical size={14} />
                  <span>{dir.validation_experiments.join('; ')}</span>
                </div>
              ) : null}
            </div>
          ))}
        </section>
      ) : null}

      {report.evidence_summary ? (
        <section className="rsa-section">
          <h4><ListChecks size={16} /> Evidence Summary</h4>
          <p>{report.evidence_summary}</p>
        </section>
      ) : null}

      {report.contradictions?.length ? (
        <section className="rsa-section rsa-section--warn">
          <h4><Scale size={16} /> Contradictions</h4>
          <ul>{report.contradictions.map((c) => <li key={c}>{c}</li>)}</ul>
        </section>
      ) : null}

      {report.knowledge_gaps?.length ? (
        <section className="rsa-section">
          <h4>Knowledge Gaps</h4>
          <ul>{report.knowledge_gaps.map((g) => <li key={g}>{g}</li>)}</ul>
        </section>
      ) : null}

      {report.limitations?.length ? (
        <section className="rsa-section rsa-section--muted">
          <h4>Limitations</h4>
          <ul>{report.limitations.map((l) => <li key={l}>{l}</li>)}</ul>
        </section>
      ) : null}

      {report.suggested_next_actions?.length ? (
        <section className="rsa-section">
          <h4>Next Actions</h4>
          <ul>{report.suggested_next_actions.map((a) => <li key={a}>{a}</li>)}</ul>
        </section>
      ) : null}

      {report.references?.length ? (
        <section className="rsa-section">
          <h4><BookOpen size={16} /> References</h4>
          <ul className="rsa-ref-list">
            {report.references.map((ref, idx) => (
              <li key={`${ref.title}-${idx}`}>
                {ref.title}
                {ref.doi ? ` — DOI ${ref.doi}` : ''}
                {ref.pmid ? ` — PMID ${ref.pmid}` : ''}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </article>
  );
}
