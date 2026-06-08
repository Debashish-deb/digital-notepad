import { useMemo } from 'react';
import { AlertTriangle, BookOpen, FlaskConical, ListChecks, Scale, Sparkles } from 'lucide-react';
import './OrchestratorAnswerView.css';

const SECTION_ICONS = {
  executive_summary: Sparkles,
  evidence: ListChecks,
  methods: FlaskConical,
  limitations: Scale,
  references: BookOpen,
  preamble: Sparkles,
};

const SECTION_ACCENTS = {
  executive_summary: 'summary',
  evidence: 'evidence',
  methods: 'methods',
  limitations: 'limitations',
  references: 'references',
  preamble: 'summary',
};

const ORCHESTRATOR_SECTION_PATTERNS = [
  { id: 'executive_summary', label: 'Executive summary', pattern: /executive\s+summary/i },
  { id: 'evidence', label: 'Evidence', pattern: /^(?:evidence|key\s+findings)/i },
  { id: 'methods', label: 'Methods & context', pattern: /methods?(?:\s*&\s*context)?|context(?:\s*&\s*methods)?/i },
  { id: 'limitations', label: 'Limitations & confidence', pattern: /limitations?(?:\s*&\s*confidence)?|confidence(?:\s*assessment)?/i },
  { id: 'references', label: 'References', pattern: /references?|supporting\s+literature|citations?/i },
];

const HEADER_LINE_RE = /^(?:#{1,3}\s*|\d+\.\s*)?\*{0,2}(.+?)\*{0,2}\s*:?\s*$/;

function matchSectionHeader(line) {
  const trimmed = String(line || '').trim();
  if (!trimmed) return null;
  const headerMatch = trimmed.match(HEADER_LINE_RE);
  const headerText = (headerMatch?.[1] || trimmed).trim();
  for (const def of ORCHESTRATOR_SECTION_PATTERNS) {
    if (def.pattern.test(headerText)) {
      return { id: def.id, label: def.label };
    }
  }
  return null;
}

export function parseOrchestratorSections(text) {
  const raw = String(text || '').trim();
  if (!raw) return [];

  const lines = raw.split('\n');
  const sections = [];
  let current = { id: 'preamble', label: 'Overview', body: [] };

  const flush = () => {
    const body = current.body.join('\n').trim();
    if (body || current.id !== 'preamble') {
      sections.push({ id: current.id, label: current.label, body });
    }
  };

  for (const line of lines) {
    const matched = matchSectionHeader(line);
    if (matched) {
      flush();
      current = { id: matched.id, label: matched.label, body: [] };
      continue;
    }
    current.body.push(line);
  }
  flush();

  if (sections.length === 1 && sections[0].id === 'preamble') {
    return [];
  }
  return sections.filter((section) => section.body);
}

function renderInlineMarkdown(text, keyPrefix = 'inline') {
  const raw = String(text || '');
  const tokens = raw.split(/(\[[^\]]+\]\([^)]+\)|\*\*[^*]+\*\*|`[^`]+`|https?:\/\/[^\s)]+)/g);
  return tokens.map((part, i) => {
    if (!part) return null;
    const linkMatch = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (linkMatch) {
      return (
        <a key={`${keyPrefix}-link-${i}`} href={linkMatch[2]} target="_blank" rel="noopener noreferrer">
          {linkMatch[1]}
        </a>
      );
    }
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={`${keyPrefix}-strong-${i}`}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return <code key={`${keyPrefix}-code-${i}`}>{part.slice(1, -1)}</code>;
    }
    if (/^https?:\/\//.test(part)) {
      return (
        <a key={`${keyPrefix}-url-${i}`} href={part} target="_blank" rel="noopener noreferrer">
          {part}
        </a>
      );
    }
    return <span key={`${keyPrefix}-text-${i}`}>{part}</span>;
  });
}

function SectionBody({ text }) {
  const blocks = useMemo(() => {
    const lines = String(text || '').split('\n');
    const parsed = [];
    let listItems = null;
    let listType = null;

    const flushList = () => {
      if (listItems?.length) parsed.push({ type: listType, items: listItems });
      listItems = null;
      listType = null;
    };

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) {
        flushList();
        parsed.push({ type: 'space' });
        continue;
      }
      if (trimmed.startsWith('- ')) {
        if (listType !== 'ul') {
          flushList();
          listItems = [];
          listType = 'ul';
        }
        listItems.push(trimmed.slice(2));
        continue;
      }
      const numbered = trimmed.match(/^(\d+)\.\s+(.*)$/);
      if (numbered) {
        if (listType !== 'ol') {
          flushList();
          listItems = [];
          listType = 'ol';
        }
        listItems.push(numbered[2]);
        continue;
      }
      flushList();
      parsed.push({ type: 'p', text: line });
    }
    flushList();
    return parsed;
  }, [text]);

  return (
    <div className="orchestrator-section__body">
      {blocks.map((block, index) => {
        if (block.type === 'space') {
          return <div key={`space-${index}`} className="orchestrator-section__spacer" aria-hidden="true" />;
        }
        if (block.type === 'ul') {
          return (
            <ul key={index} className="orchestrator-section__list">
              {block.items.map((item, j) => (
                <li key={j}>{renderInlineMarkdown(item, `ul-${index}-${j}`)}</li>
              ))}
            </ul>
          );
        }
        if (block.type === 'ol') {
          return (
            <ol key={index} className="orchestrator-section__list orchestrator-section__list--numbered">
              {block.items.map((item, j) => (
                <li key={j}>{renderInlineMarkdown(item, `ol-${index}-${j}`)}</li>
              ))}
            </ol>
          );
        }
        return <p key={index}>{renderInlineMarkdown(block.text, `p-${index}`)}</p>;
      })}
    </div>
  );
}

export default function OrchestratorAnswerView({ text, sections: presetSections = null, claimValidations = [] }) {
  const sections = useMemo(() => {
    if (Array.isArray(presetSections) && presetSections.length > 0) {
      return presetSections
        .map((section) => ({
          id: section.id || 'section',
          label: section.label || section.id || 'Section',
          body: section.body || '',
        }))
        .filter((section) => section.body);
    }
    return parseOrchestratorSections(text);
  }, [text, presetSections]);

  if (!sections.length) {
    return null;
  }

  const conflicts = (claimValidations || []).filter((row) => row?.status === 'conflicting');

  return (
    <div className="orchestrator-answer">
      {conflicts.length ? (
        <div className="orchestrator-answer__conflicts" role="note">
          <AlertTriangle size={14} aria-hidden />
          <span>
            {conflicts.length} cross-source claim conflict{conflicts.length === 1 ? '' : 's'} flagged in evidence review.
          </span>
        </div>
      ) : null}
      {sections.map((section) => {
        const Icon = SECTION_ICONS[section.id] || ListChecks;
        const accent = SECTION_ACCENTS[section.id] || 'evidence';
        return (
          <section
            key={`${section.id}-${section.label}`}
            className={`orchestrator-section orchestrator-section--${accent}`}
          >
            <header className="orchestrator-section__header">
              <Icon size={15} aria-hidden />
              <h4 className="orchestrator-section__title">{section.label}</h4>
            </header>
            <SectionBody text={section.body} />
          </section>
        );
      })}
    </div>
  );
}
