import React from 'react';
import SearchResultCard from './SearchResultCard.jsx';

export default function SearchBucketGroup({
  group,
  query,
  activeIndexOffset = 0,
  activeIndex = -1,
  onOpenHit,
  onAskAiAboutHit,
  onHoverIndex,
}) {
  if (!group?.items?.length) return null;

  return (
    <div className="search-bucket-group">
      <div className="search-section-title">{group.label}</div>
      {group.items.map((hit, index) => {
        const rowIndex = activeIndexOffset + index;
        return (
          <SearchResultCard
            key={`${hit.bucket}-${hit.id}`}
            hit={hit}
            query={query}
            isActive={rowIndex === activeIndex}
            onOpen={onOpenHit}
            onAskAi={onAskAiAboutHit}
            onMouseEnter={() => onHoverIndex?.(rowIndex)}
          />
        );
      })}
    </div>
  );
}
