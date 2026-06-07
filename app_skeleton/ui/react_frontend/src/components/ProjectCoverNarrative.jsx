import { useId, useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { sanitizeCoverSummary } from '../utils/projectCoverSummary.js';

/** Readable intro prose for the project cover — compact clamp with optional expand. */
export default function ProjectCoverNarrative({ summary, className = '', compact = true }) {
  const paragraphs = sanitizeCoverSummary(summary);
  const id = useId();
  const [expanded, setExpanded] = useState(false);

  if (!paragraphs.length) return null;

  const fullText = paragraphs.join(' ');
  const isLong = fullText.length > 220 || paragraphs.length > 1;

  return (
    <div className={`project-cover-narrative${compact ? ' project-cover-narrative--compact' : ''}${className ? ` ${className}` : ''}`}>
      <p
        id={id}
        className={`project-cover-narrative__para${compact && !expanded ? ' is-clamped' : ''}`}
      >
        {compact && !expanded ? fullText : paragraphs.map((para, index) => (
          <span key={`${id}-p-${index}`}>
            {index > 0 ? ' ' : ''}
            {para}
          </span>
        ))}
      </p>
      {compact && isLong ? (
        <button
          type="button"
          className="project-cover-narrative__toggle"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
          aria-controls={id}
        >
          {expanded ? (
            <>
              <ChevronUp size={12} aria-hidden /> Less
            </>
          ) : (
            <>
              <ChevronDown size={12} aria-hidden /> More
            </>
          )}
        </button>
      ) : null}
    </div>
  );
}
