import { useState } from 'react';
import './CopyableCodeBlock.css';

const TYPE_CLASS = {
  primary: 'copyable-code-block__pre--primary',
  success: 'copyable-code-block__pre--success',
  warning: 'copyable-code-block__pre--warning',
  danger: 'copyable-code-block__pre--danger',
};

/**
 * Shared copy-to-clipboard code block for hub guides, logs, and pipeline panels.
 */
export function CopyableCodeBlock({
  code,
  type = 'success',
  className = '',
  fontSize,
  /** @deprecated use `language` */
  lang,
  language,
  title,
  filename,
  compact = false,
}) {
  const [copied, setCopied] = useState(false);
  const languageLabel = language || lang;

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (languageLabel) {
    return (
      <div className={`log-code-block-container ${className}`.trim()}>
        <div className="log-code-block-header">
          <span className="log-code-block-lang">{languageLabel}</span>
          <button type="button" className="log-code-block-copy" onClick={handleCopy}>
            {copied ? 'Copied!' : 'Copy'}
          </button>
        </div>
        <pre className="log-code-block">
          <code>{code}</code>
        </pre>
      </div>
    );
  }

  const typeClass = TYPE_CLASS[type] || TYPE_CLASS.success;
  const hasHead = Boolean(title || filename);

  return (
    <div
      className={[
        'copyable-code-block',
        compact ? 'copyable-code-block--compact' : '',
        hasHead ? 'copyable-code-block--has-head' : '',
        className,
      ].filter(Boolean).join(' ')}
    >
      {hasHead ? (
        <div className="copyable-code-block__head">
          {title ? <p className="copyable-code-block__title">{title}</p> : null}
          {filename ? <span className="copyable-code-block__filename">{filename}</span> : null}
        </div>
      ) : null}
      <pre
        className={[
          'code-block',
          'copyable-code-block__pre',
          typeClass,
          compact ? 'copyable-code-block__pre--compact' : '',
        ].filter(Boolean).join(' ')}
        style={fontSize ? { fontSize } : undefined}
      >
        {code}
      </pre>
      <button type="button" className="btn btn-secondary copyable-code-block__btn" onClick={handleCopy}>
        {copied ? '✓ Copied' : 'Copy'}
      </button>
    </div>
  );
}

export default CopyableCodeBlock;
