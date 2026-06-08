import { Database, ExternalLink, Search, Sparkles } from 'lucide-react';
import HighlightedSnippet from '@/features/search/components/HighlightedSnippet.jsx';
import { BUCKET_LABELS } from '@/lib/searchHits.js';
import AssistantSourcePreview from './AssistantSourcePreview.jsx';

function hitPreview(hit) {
  return hit?.text_preview || hit?.snippet || hit?.highlights?.[0] || '';
}

export default function AssistantSourcesPanel({
  items = [],
  query = '',
  selectedIndex = 0,
  onSelectIndex,
  onOpenHit,
  onAskFollowUp,
  onSearchOmnibox,
}) {
  if (!items.length) {
    return (
      <aside className="assistant-sources-panel assistant-sources-panel--empty" aria-label="Evidence sources">
        <header className="assistant-sources-panel__head">
          <Database size={15} aria-hidden />
          <span>Evidence</span>
        </header>
        <p className="assistant-sources-panel__empty">
          Sources from your latest grounded answer will appear here — citations, scores, and PDF preview.
        </p>
      </aside>
    );
  }

  const selected = items[selectedIndex] || items[0];

  return (
    <aside className="assistant-sources-panel" aria-label="Evidence sources">
      <header className="assistant-sources-panel__head">
        <Database size={15} aria-hidden />
        <span>Evidence</span>
        <span className="assistant-sources-panel__count">{items.length}</span>
      </header>

      <ol className="assistant-sources-panel__list">
        {items.map((hit, index) => {
          const title = hit.title || 'Untitled source';
          const preview = hitPreview(hit);
          const nav = hit.nav;
          const meta = hit.metadata || {};
          const chipLabel = meta.smart_chip || meta.domain_tab || meta.review_reason || null;
          const active = index === selectedIndex;
          const followUp = `Tell me more about: ${title}`;

          return (
            <li key={`${hit.chunk_id || hit.id || title}-${index}`}>
              <button
                type="button"
                className={`assistant-sources-panel__item${active ? ' is-active' : ''}`}
                onClick={() => onSelectIndex?.(index)}
                aria-current={active ? 'true' : undefined}
              >
                <span className="assistant-sources-panel__index">[{index + 1}]</span>
                <span className="assistant-sources-panel__title">{title}</span>
                {hit.score != null ? (
                  <span className="assistant-sources-panel__score">{Number(hit.score).toFixed(2)}</span>
                ) : null}
              </button>

              {active ? (
                <div className="assistant-sources-panel__detail">
                  <div className="assistant-sources-panel__meta">
                    {(hit.source || hit.bucket || hit.source_type) ? (
                      <span className="assistant-sources-panel__bucket">
                        {BUCKET_LABELS[hit.bucket] || hit.source || hit.bucket || hit.source_type}
                      </span>
                    ) : null}
                    {chipLabel ? <span className="assistant-sources-panel__bucket">{chipLabel}</span> : null}
                  </div>
                  {preview ? (
                    <HighlightedSnippet text={preview} query={query} className="assistant-sources-panel__snippet" />
                  ) : null}
                  <div className="assistant-sources-panel__actions">
                    {nav && onOpenHit ? (
                      <button type="button" className="btn btn-sm btn-secondary" onClick={() => onOpenHit(nav, hit)}>
                        <ExternalLink size={12} aria-hidden />
                        Open in OMEIA
                      </button>
                    ) : null}
                    {onAskFollowUp ? (
                      <button type="button" className="btn btn-sm btn-secondary" onClick={() => onAskFollowUp(followUp)}>
                        <Sparkles size={12} aria-hidden />
                        Follow-up
                      </button>
                    ) : null}
                    {onSearchOmnibox ? (
                      <button type="button" className="btn btn-sm btn-secondary" onClick={() => onSearchOmnibox(title || query)}>
                        <Search size={12} aria-hidden />
                        Search
                      </button>
                    ) : null}
                  </div>
                  <AssistantSourcePreview hit={hit} />
                </div>
              ) : null}
            </li>
          );
        })}
      </ol>
    </aside>
  );
}
