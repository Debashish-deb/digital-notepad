import { useState } from 'react';
import { Loader2, SpellCheck } from 'lucide-react';
import { proofreadDatapadContent } from '../api/datapad.js';

function simpleDiffLines(before, after) {
  const a = (before || '').split('\n');
  const b = (after || '').split('\n');
  const lines = [];
  const max = Math.max(a.length, b.length);
  for (let i = 0; i < max; i += 1) {
    const left = a[i] ?? '';
    const right = b[i] ?? '';
    if (left !== right) {
      lines.push({ line: i + 1, before: left, after: right });
    }
  }
  return lines.slice(0, 80);
}

export default function DocumentProofreadPanel({ content, className = '' }) {
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState(null);

  const text = String(content || '').trim();
  if (!text) return null;

  const diffLines = preview ? simpleDiffLines(text, preview.corrected_text) : [];

  const handleProofread = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await proofreadDatapadContent(text);
      setPreview(result);
    } catch (err) {
      setError(err.message || 'Proofread failed');
      setPreview(null);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={`doc-proofread-panel ${className}`.trim()}>
      <button
        type="button"
        className="btn btn-secondary btn-sm"
        onClick={handleProofread}
        disabled={busy}
        title="Check spelling and grammar"
      >
        {busy ? <Loader2 size={14} className="spin" aria-hidden /> : <SpellCheck size={14} aria-hidden />}
        Check spelling
      </button>

      {error ? (
        <p className="text-footnote muted doc-proofread-panel__error" role="alert">
          {error}
        </p>
      ) : null}

      {preview ? (
        <div className="doc-proofread-panel__results datapad-ai-panel">
          <h5 className="workspace-subpanel-title">
            <SpellCheck size={14} aria-hidden /> Suggestions ({preview.mode}) — {preview.fixes?.length ?? 0} fix(es)
          </h5>
          {diffLines.length > 0 ? (
            <div className="datapad-diff-wrap">
              <table className="datapad-diff-table">
                <thead>
                  <tr>
                    <th>Line</th>
                    <th>Before</th>
                    <th>After</th>
                  </tr>
                </thead>
                <tbody>
                  {diffLines.map((row) => (
                    <tr key={row.line}>
                      <td>{row.line}</td>
                      <td>{row.before}</td>
                      <td>{row.after}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-footnote muted">No spelling or grammar issues detected.</p>
          )}
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => setPreview(null)}>
            Dismiss
          </button>
        </div>
      ) : null}
    </div>
  );
}
