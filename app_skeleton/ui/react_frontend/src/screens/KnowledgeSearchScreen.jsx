import './MacPlusVisualStyles.css';
import { useState } from 'react';
import { BookOpen, Search } from 'lucide-react';
import { apiGet } from '../api/client.js';

export default function KnowledgeSearchScreen({ title, description }) {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState('hybrid');
  const [labHits, setLabHits] = useState([]);
  const [vaultHits, setVaultHits] = useState([]);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const runSearch = async () => {
    const q = query.trim();
    if (q.length < 2) return;
    setBusy(true);
    setError(null);
    try {
      if (mode === 'hybrid-lab') {
        const data = await apiGet('/api/knowledge/hybrid-search', {
          params: new URLSearchParams({ q, limit: '15' }),
        });
        setLabHits(data.lab_results || []);
        setVaultHits(data.vault_results || []);
      } else {
        const data = await apiGet('/api/search', {
          params: new URLSearchParams({ q, mode: mode === 'hybrid-lab' ? 'hybrid' : mode, limit: '20' }),
        });
        setLabHits(data.lab_results || []);
        setVaultHits(data.vault_results || []);
      }
    } catch (e) {
      setError(String(e.message || e));
      setLabHits([]);
      setVaultHits([]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="stack-md">
      <div className="panel">
        <h3 className="panel-title">
          <BookOpen size={18} /> {title || 'Knowledge search'}
        </h3>
        <p className="panel-lead prose-block">
          {description || 'Unified lab index and vault metadata search via the platform API.'}
        </p>
        <div className="disk-pad-toolbar" style={{ marginTop: '0.75rem' }}>
          <input
            type="search"
            className="input"
            placeholder="Query protocols, documents, vault metadata…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && runSearch()}
          />
          <select className="input" value={mode} onChange={(e) => setMode(e.target.value)} aria-label="Search mode">
            <option value="hybrid">Hybrid (lab + vault)</option>
            <option value="hybrid-lab">Hybrid-search endpoint</option>
            <option value="semantic">Semantic (lab)</option>
            <option value="metadata">Metadata (vault)</option>
            <option value="exact">Exact</option>
          </select>
          <button type="button" className="btn btn-primary btn-sm" onClick={runSearch} disabled={busy}>
            <Search size={14} /> {busy ? 'Searching…' : 'Search'}
          </button>
        </div>
        {error && <p className="text-footnote citation-footnote" style={{ color: 'var(--color-danger)' }}>{error}</p>}
      </div>

      {labHits.length > 0 && (
        <div className="panel">
          <h4 className="text-title-3">Lab corpus ({labHits.length})</h4>
          <ul className="stack-sm" style={{ listStyle: 'none', padding: 0 }}>
            {labHits.map((h, i) => (
              <li key={h.section_id || h.path || i} className="text-footnote">
                <strong>{h.title || h.filename || h.section_id}</strong>
                {h.snippet && <span className="muted"> — {h.snippet.slice(0, 120)}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {vaultHits.length > 0 && (
        <div className="panel">
          <h4 className="text-title-3">Vault metadata ({vaultHits.length})</h4>
          <ul className="stack-sm" style={{ listStyle: 'none', padding: 0 }}>
            {vaultHits.map((h) => (
              <li key={h.asset_id} className="text-footnote">
                {h.filename} <span className="muted">— {h.logical_path}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
