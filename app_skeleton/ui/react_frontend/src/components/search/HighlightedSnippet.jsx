import { splitHighlightedText } from '../../utils/highlightText.js';

export default function HighlightedSnippet({ text, query, className = 'search-item-body clamped' }) {
  const segments = splitHighlightedText(text, query);
  if (!segments.length) return null;

  return (
    <div className={className}>
      {segments.map((seg, index) =>
        seg.highlight ? (
          <mark key={`${index}-${seg.text}`} className="search-highlight">
            {seg.text}
          </mark>
        ) : (
          <span key={`${index}-${seg.text}`}>{seg.text}</span>
        ),
      )}
    </div>
  );
}
