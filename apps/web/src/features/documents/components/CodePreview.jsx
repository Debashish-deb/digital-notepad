import { useMemo } from 'react';
import { Loader2 } from 'lucide-react';

function formatJsonSafe(text) {
  try {
    const parsed = JSON.parse(text);
    return JSON.stringify(parsed, null, 2);
  } catch {
    return text;
  }
}

export default function CodePreview({
  content,
  language = 'plaintext',
  loading = false,
  error = null,
  labels = {},
}) {
  const {
    loading: loadingLabel = 'Loading file…',
    failed = 'Could not load file content.',
  } = labels;

  const display = useMemo(() => {
    if (!content) return '';
    if (language === 'json') return formatJsonSafe(content);
    return content.replace(/\r\n/g, '\n');
  }, [content, language]);

  const lines = display ? display.split('\n') : [];

  if (loading) {
    return (
      <div className="code-preview code-preview--loading">
        <Loader2 size={18} className="spin-inline" aria-hidden />
        <span>{loadingLabel}</span>
      </div>
    );
  }

  if (error && !content) {
    return <p className="text-footnote muted code-preview--error">{error || failed}</p>;
  }

  if (!display) {
    return <p className="text-footnote muted code-preview--empty">File is empty.</p>;
  }

  return (
    <div className={`code-preview code-preview--${language}`}>
      <div className="code-preview-toolbar">
        <span className="code-preview-lang">{language}</span>
        <span className="code-preview-meta">{lines.length} lines</span>
      </div>
      <pre className="code-preview-pre">
        <code className={`code-preview-code language-${language}`}>
          {lines.map((line, idx) => (
            <span key={idx} className="code-preview-line">
              <span className="code-preview-gutter" aria-hidden>
                {idx + 1}
              </span>
              <span className="code-preview-text">{line || ' '}</span>
              {'\n'}
            </span>
          ))}
        </code>
      </pre>
    </div>
  );
}
