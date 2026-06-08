import { useId, useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

/**
 * Readable prose block with optional truncation and expand/collapse.
 * Parses simple Markdown links: [[Text]](url) or [[Text]]{url}
 * and respects line breaks.
 */
export default function ExpandableText({
  children,
  maxLength = 320,
  className = 'prose-block',
  as: Tag = 'div', // Changed to div to support internal block styles safely
  heading,
}) {
  const text = typeof children === 'string' ? children : '';
  const id = useId();
  const needsTruncate = text.length > maxLength;
  const [expanded, setExpanded] = useState(false);

  if (!text) return null;
  const visible = needsTruncate && !expanded ? `${text.slice(0, maxLength).trim()}…` : text;

  // Simple Markdown parser for links and headings
  const getFormattedContent = (content) => {
    let html = content
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      // Parse [[Text]](url) and [[Text]]{url}
      .replace(/\[\[(.*?)\]\][{(](.*?)[})]/g, '<a href="$2" target="_blank" rel="noreferrer" style="color: var(--color-primary); text-decoration: none; font-weight: 500;">$1</a>')
      // Parse standard markdown [Text](url)
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer" style="color: var(--color-primary); text-decoration: none; font-weight: 500;">$1</a>')
      // Make Markdown headings bold
      .replace(/^#+\s+(.*)$/gm, '<strong style="display: block; margin-top: 0.75rem; margin-bottom: 0.25rem; font-size: 1.05em; color: var(--mac-ink);">$1</strong>');
      
    return { __html: html };
  };

  return (
    <div className={`expandable-text ${className}`.trim()}>
      {heading && <h4 className="expandable-text-heading">{heading}</h4>}
      <Tag 
        className="expandable-text-body" 
        style={{ whiteSpace: 'pre-wrap', lineHeight: 1.5, wordBreak: 'break-word' }}
        dangerouslySetInnerHTML={getFormattedContent(visible)} 
      />
      {needsTruncate && (
        <button
          type="button"
          className="expandable-text-toggle"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
          aria-controls={id}
          style={{ marginTop: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}
        >
          {expanded ? (
            <>
              <ChevronUp size={14} /> Show less
            </>
          ) : (
            <>
              <ChevronDown size={14} /> Read more
            </>
          )}
        </button>
      )}
    </div>
  );
}
