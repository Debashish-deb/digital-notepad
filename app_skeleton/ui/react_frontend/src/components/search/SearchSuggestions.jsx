import React from 'react';

export default function SearchSuggestions({
  recentQueries = [],
  suggestions = [],
  synonymHints = [],
  onSelect,
}) {
  const hasRecent = recentQueries.length > 0;
  const hasSuggestions = suggestions.length > 0;
  const hasSynonyms = synonymHints.length > 0;

  if (!hasRecent && !hasSuggestions && !hasSynonyms) {
    return <div className="search-empty">Type at least 2 characters to search the lab platform.</div>;
  }

  return (
    <div className="search-suggestions-wrap">
      {!hasRecent && !hasSuggestions && !hasSynonyms ? null : (
        <p className="search-suggestions-lead">Type at least 2 characters to search the lab platform.</p>
      )}

      {hasRecent ? (
        <div className="search-recent-list">
          <div className="search-section-title">Recent</div>
          <div className="search-suggestion-chips">
            {recentQueries.map((item) => (
              <button
                key={item}
                type="button"
                className="search-recent-chip"
                onClick={() => onSelect?.(item)}
              >
                {item}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {hasSuggestions ? (
        <div className="search-suggestions-block">
          <div className="search-section-title">Suggestions</div>
          <div className="search-suggestion-chips">
            {suggestions.map((item) => (
              <button
                key={item}
                type="button"
                className="search-suggestion-chip"
                onClick={() => onSelect?.(item)}
              >
                {item}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {hasSynonyms ? (
        <div className="search-suggestions-block">
          <div className="search-section-title">Related terms</div>
          <div className="search-suggestion-chips">
            {synonymHints.map((item) => (
              <button
                key={item}
                type="button"
                className="search-synonym-chip"
                onClick={() => onSelect?.(item)}
              >
                {item}
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
