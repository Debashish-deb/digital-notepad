import React from 'react';
import { ChevronRight, Sparkles } from 'lucide-react';
import HighlightedSnippet from './HighlightedSnippet.jsx';

export default function SearchResultCard({
  hit,
  query = '',
  isActive = false,
  onOpen,
  onAskAi,
  onMouseEnter,
}) {
  if (!hit) return null;

  const snippet = hit.highlights?.[0] || hit.snippet;
  const askLabel = hit.title ? `Ask AI about “${hit.title.slice(0, 48)}”` : 'Ask AI about this';

  return (
    <div
      className={`search-item search-item--actionable${isActive ? ' is-active' : ''}`}
      onMouseEnter={onMouseEnter}
    >
      <button type="button" className="search-item-main-btn" onClick={() => onOpen?.(hit)}>
        <div className="search-item-content">
          <div className="search-item-title">{hit.title}</div>
          <div className="search-item-meta">
            <span className="search-item-source">{hit.source}</span>
            {hit.project_code ? <span> · {hit.project_code}</span> : null}
            {hit.rank ? <span className="search-item-score"> · #{hit.rank}</span> : null}
            {hit.score != null ? (
              <span className="search-item-score"> · {Number(hit.score).toFixed(2)}</span>
            ) : null}
          </div>
          {snippet ? <HighlightedSnippet text={snippet} query={query} /> : null}
          {hit.metadata?.where_to_find ? (
            <div className="search-item-where">{hit.metadata.where_to_find}</div>
          ) : null}
        </div>
        <ChevronRight size={16} className="search-item-open-icon" aria-hidden />
      </button>
      {onAskAi ? (
        <button
          type="button"
          className="search-hit-ask-ai"
          title={askLabel}
          aria-label={askLabel}
          onClick={(e) => {
            e.stopPropagation();
            onAskAi(hit);
          }}
        >
          <Sparkles size={12} aria-hidden />
        </button>
      ) : null}
    </div>
  );
}
