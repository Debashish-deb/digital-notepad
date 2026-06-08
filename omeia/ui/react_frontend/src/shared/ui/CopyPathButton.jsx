import { useState } from 'react';
import { Check, Copy } from 'lucide-react';

export default function CopyPathButton({
  value,
  label = 'Copy path',
  className = '',
  iconOnly = false,
}) {
  const [copied, setCopied] = useState(false);

  if (!value) return null;

  const handleCopy = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      /* ignore */
    }
  };

  return (
    <button
      type="button"
      className={`copy-path-btn${iconOnly ? ' copy-path-btn--icon-only' : ''}${className ? ` ${className}` : ''}`.trim()}
      onClick={handleCopy}
      title={label}
      aria-label={label}
    >
      {copied ? <Check size={14} /> : <Copy size={14} />}
      {iconOnly ? null : <span>{copied ? 'Copied' : 'Copy'}</span>}
    </button>
  );
}
