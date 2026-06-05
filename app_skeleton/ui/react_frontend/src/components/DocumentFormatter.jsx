import React from 'react';
import { PlusSquare } from 'lucide-react';

export default function DocumentFormatter({ text, onCreateTask }) {
  if (!text) return null;

  // Smartly clean and parse the raw extracted text
  const cleanText = (raw) => {
    let cleaned = raw.replace(/\r\n/g, '\n');
    cleaned = cleaned.replace(/\*\*/g, ''); // Remove stray markdown bolding
    cleaned = cleaned.replace(/^>[ \t]*/gm, ''); // Remove stray markdown blockquotes

    const blocks = cleaned.split(/\n\n+/);
    const elements = [];

    for (let i = 0; i < blocks.length; i++) {
      let lines = blocks[i].split('\n').map(l => l.trim());
      
      // Filter out trailing page numbers and orphaned numbers (common in PDF TOCs)
      lines = lines.map(l => l.replace(/\s+\d{1,3}$/, '')).filter(l => !/^\d{1,3}$/.test(l) && l);
      
      if (!lines.length) continue;

      // Detect lists (lines starting with -, *, or 1.)
      const isList = lines.every(l => /^[-*•]|\d+\.\s/.test(l));

      if (isList) {
        elements.push(
          <ul key={i} style={{ paddingLeft: '2rem', marginBottom: '1.5rem', lineHeight: 1.8 }}>
            {lines.map((l, idx) => (
              <li key={idx} style={{ marginBottom: '0.5rem', textAlign: 'justify' }}>
                {renderLinks(l.replace(/^[-*•]\s*|\d+\.\s*/, ''))}
              </li>
            ))}
          </ul>
        );
        continue;
      }

      // Merge remaining lines to fix broken PDF sentences
      const merged = lines.join(' ').replace(/\s+/g, ' ');
      
      // Heuristic for Headings: short line without trailing punctuation
      if (merged.length < 100 && !/[.,:;!?]$/.test(merged)) {
        // If it's very short, make it an h3, else h4
        const isMajor = merged.length < 50;
        const HeadingTag = isMajor ? 'h3' : 'h4';
        const styles = isMajor 
          ? { marginTop: '2.5rem', marginBottom: '1rem', paddingBottom: '0.5rem', borderBottom: '1px solid var(--mac-border)', color: 'var(--mac-ink)', fontWeight: 600, fontSize: '1.4rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }
          : { marginTop: '2rem', marginBottom: '0.75rem', color: 'var(--mac-ink)', fontWeight: 600, fontSize: '1.1rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' };

        elements.push(
          <HeadingTag key={i} style={styles} className="doc-section-heading">
            <span>{merged}</span>
            {onCreateTask && (
              <button 
                type="button" 
                className="btn btn-secondary btn-sm" 
                style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem' }}
                onClick={() => onCreateTask(merged)}
                title="Create task from this section"
              >
                <PlusSquare size={12} style={{ marginRight: '4px' }} /> Task
              </button>
            )}
          </HeadingTag>
        );
      } else {
        // It's a normal paragraph
        elements.push(
          <p key={i} style={{ marginBottom: '1.25rem', lineHeight: 1.8, color: 'var(--mac-ink)', textAlign: 'justify' }}>
            {renderLinks(merged)}
          </p>
        );
      }
    }
    
    return elements;
  };

  const renderLinks = (str) => {
    // Match Markdown links [text](url) and bare URLs (http:// or https://)
    const parts = str.split(/(\[.*?\]\(.*?\)|https?:\/\/[^\s]+)/g);
    return parts.map((part, pIdx) => {
      if (!part) return null;
      
      const mdMatch = part.match(/\[(.*?)\]\((.*?)\)/);
      if (mdMatch) {
        return <a key={pIdx} href={mdMatch[2]} target="_blank" rel="noreferrer" style={{ color: 'var(--color-primary)', textDecoration: 'underline', fontWeight: 500 }}>{mdMatch[1]}</a>;
      }
      if (part.match(/^https?:\/\//)) {
        return <a key={pIdx} href={part} target="_blank" rel="noreferrer" style={{ color: 'var(--color-primary)', textDecoration: 'underline', fontWeight: 500 }}>{part}</a>;
      }
      return part;
    });
  };

  return (
    <div className="document-formatter-content professional-doc" style={{ fontSize: '1.05rem', fontFamily: 'var(--font-serif, "Georgia", serif)' }}>
      {cleanText(text)}
    </div>
  );
}
