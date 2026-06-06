import React from 'react';
import { Database, ExternalLink, Search, Sparkles } from 'lucide-react';
import HighlightedSnippet from './HighlightedSnippet.jsx';

function hitPreview(hit) {
  return hit?.text_preview || hit?.snippet || hit?.highlights?.[0] || '';
}

export default function AssistantSearchHits({
  hits = [],
  sources = [],
  query = '',
  onOpenHit,
  onAskFollowUp,
  onSearchOmnibox,
}) {
  const items = hits?.length ? hits : sources;
  if (!items?.length) return null;

  return (
    <details className="chat-sources assistant-search-hits" open={hits?.length > 0}>
      <summary>
        <Database size={13} aria-hidden="true" />
        {hits?.length ? 'Search hits' : 'Sources & citations'}
        <span>{items.length}</span>
      </summary>

      <ol className="assistant-search-hits__list">
        {items.map((hit, index) => {
          const title = hit.title || 'Untitled source';
          const preview = hitPreview(hit);
          const nav = hit.nav;
          const followUp = `Tell me more about: ${title}`;

          return (
            <li key={`${hit.chunk_id || hit.id || title}-${index}`} className="assistant-search-hit">
              <div className="assistant-search-hit__head">
                {nav && onOpenHit ? (
                  <button
                    type="button"
                    className="chat-source-link"
                    onClick={() => onOpenHit(nav, hit)}
                  >
                    <strong>{title}</strong>
                  </button>
                ) : (
                  <strong>{title}</strong>
                )}
                {hit.score !== undefined && hit.score !== null ? (
                  <span className="chat-source-score">score {Number(hit.score).toFixed(3)}</span>
                ) : null}
                {hit.bucket || hit.source_type ? (
                  <span className={`chat-source-bucket chat-source-bucket--${hit.bucket || hit.source_type}`}>
                    {hit.bucket || hit.source_type}
                  </span>
                ) : null}
                {hit.rank ? <span className="chat-source-bucket">#{hit.rank}</span> : null}
              </div>

              {preview ? (
                <HighlightedSnippet text={preview} query={query} className="assistant-search-hit__snippet" />
              ) : null}

              <div className="assistant-search-hit__actions">
                {nav && onOpenHit ? (
                  <button type="button" className="btn btn-sm btn-secondary" onClick={() => onOpenHit(nav, hit)}>
                    <ExternalLink size={12} aria-hidden />
                    Open
                  </button>
                ) : null}
                {onAskFollowUp ? (
                  <button
                    type="button"
                    className="btn btn-sm btn-secondary"
                    onClick={() => onAskFollowUp(followUp)}
                  >
                    <Sparkles size={12} aria-hidden />
                    Ask follow-up
                  </button>
                ) : null}
                {onSearchOmnibox ? (
                  <button
                    type="button"
                    className="btn btn-sm btn-secondary"
                    onClick={() => onSearchOmnibox(hit.title || query)}
                  >
                    <Search size={12} aria-hidden />
                    Search in omnibox
                  </button>
                ) : null}
              </div>
            </li>
          );
        })}
      </ol>
    </details>
  );
}
