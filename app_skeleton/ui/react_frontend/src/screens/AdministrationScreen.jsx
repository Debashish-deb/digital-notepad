import { useCallback, useEffect, useState } from 'react';
import { Activity, Image, Shield } from 'lucide-react';
import AuthLoginPanel from '../components/AuthLoginPanel.jsx';
import { apiGet, apiPost } from '../api/client.js';
import { useApiContext } from '../api/ApiContext.jsx';

export default function AdministrationScreen({ title, description, onNavigate }) {
  const { onAuthToken } = useApiContext();
  const [emails, setEmails] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [newEmail, setNewEmail] = useState('');
  const [note, setNote] = useState(null);
  const [error, setError] = useState(null);
  const [authConfig, setAuthConfig] = useState(null);
  const [connectors, setConnectors] = useState(null);
  const [health, setHealth] = useState(null);
  const [digRuns, setDigRuns] = useState([]);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [e, j, t, auth, conn, h, runs] = await Promise.all([
        apiGet('/api/admin/allowed-emails').catch(() => ({ emails: [] })),
        apiGet('/api/admin/ingestion-jobs').catch(() => ({ jobs: [] })),
        apiGet('/api/admin/review-tasks').catch(() => ({ tasks: [] })),
        apiGet('/api/auth/config').catch(() => null),
        apiGet('/api/platform/connectors').catch(() => null),
        apiGet('/health').catch(() => null),
        apiGet('/api/digitalize/runs', { params: new URLSearchParams({ limit: '10' }) }).catch(() => ({ runs: [] })),
      ]);
      setEmails(e.emails || []);
      setJobs(j.jobs || []);
      setTasks(t.tasks || []);
      setAuthConfig(auth);
      setConnectors(conn);
      setHealth(h);
      setDigRuns(runs.runs || []);
    } catch (err) {
      setError(String(err.message || err));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const addEmail = async () => {
    const email = newEmail.trim().toLowerCase();
    if (!email.includes('@')) return;
    try {
      const params = new URLSearchParams({ email, status: 'approved' });
      await apiPost(`/api/admin/allowed-emails?${params}`);
      setNewEmail('');
      setNote(`Added ${email} to allowlist.`);
      load();
    } catch (err) {
      setError(String(err.message || err));
    }
  };

  return (
    <div className="panel">
      <h3 className="panel-title" style={{ marginBottom: '1.5rem' }}>
        <Shield size={18} /> {title || 'Administration Panel'}
      </h3>
      
      {note && <p className="text-footnote citation-footnote muted">{note}</p>}
      {error && <p className="text-footnote" style={{ color: 'var(--color-danger)' }}>{error}</p>}
      
      <div className="grid-2col" style={{ gap: '2rem', alignItems: 'start' }}>
        <div className="stack-md">
          {health && (
            <div>
              <h4 className="text-title-3" style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: '0.5rem', marginBottom: '0.5rem' }}>
                <Activity size={16} style={{ verticalAlign: 'middle', marginRight: '0.25rem' }} /> API health
              </h4>
              <ul className="stack-sm" style={{ listStyle: 'none', padding: 0 }}>
                <li className="text-footnote">Status: {health.status}</li>
                <li className="text-footnote">Database: {health.database_connected ? 'connected' : 'unavailable'}</li>
                <li className="text-footnote">LLM ({health.llm_client_provider}): {health.llm_client_healthy ? 'healthy' : 'degraded'}</li>
              </ul>
            </div>
          )}

          <div>
            <h4 className="text-title-3" style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: '0.5rem', marginBottom: '0.5rem' }}>
              Auth & Security
            </h4>
            <div style={{ marginLeft: '-1rem', marginRight: '-1rem' }}>
              <AuthLoginPanel
                onToken={(token) => {
                  onAuthToken(token);
                  setNote('Signed in — API requests include Authorization Bearer when auth is enabled.');
                }}
              />
            </div>
            {authConfig && authConfig.firebase && (
              <p className="text-footnote muted" style={{ marginTop: '0.5rem' }}>
                Firebase: {authConfig.firebase.project_name} ({authConfig.firebase.project_id}) —{' '}
                {authConfig.firebase.auth_method === 'email_password' ? 'Email/Password' : authConfig.firebase.auth_method}
                {authConfig.auth_disabled ? ' · PLATFORM_AUTH_DISABLED' : ''}
              </p>
            )}
          </div>

          <div>
            <h4 className="text-title-3" style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: '0.5rem', marginBottom: '0.5rem' }}>Allowed emails</h4>
            <div className="disk-pad-toolbar" style={{ marginBottom: '0.5rem' }}>
              <input
                className="input"
                placeholder="university.email@helsinki.fi"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
              />
              <button type="button" className="btn btn-secondary btn-sm" onClick={addEmail}>
                Add
              </button>
            </div>
            <ul className="stack-sm" style={{ listStyle: 'none', padding: 0, maxHeight: 150, overflowY: 'auto' }}>
              {emails.map((row) => (
                <li key={row.email} className="text-footnote">
                  {row.email} — {row.status}
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="stack-md">
          {connectors?.storage_primary && (
            <div>
              <h4 className="text-title-3" style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: '0.5rem', marginBottom: '0.5rem' }}>Platform connectors</h4>
              <ul className="stack-sm" style={{ listStyle: 'none', padding: 0 }}>
                {Object.entries(connectors.storage_primary).map(([id, row]) => (
                  <li key={id} className="text-footnote">
                    <strong>{id}</strong>: {row.configured ? 'configured' : 'not configured'}
                    {row.required_for_production_files ? ' · required' : ' · optional'}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div>
            <h4 className="text-title-3" style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: '0.5rem', marginBottom: '0.5rem' }}>Ingestion jobs</h4>
            {!jobs.length && <p className="text-footnote muted">No jobs recorded yet.</p>}
            <ul className="stack-sm" style={{ listStyle: 'none', padding: 0, maxHeight: 150, overflowY: 'auto' }}>
              {jobs.map((j) => (
                <li key={j.job_id} className="text-caption">
                  {j.job_type} — {j.status} ({j.items_processed}/{j.items_total})
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="text-title-3" style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: '0.5rem', marginBottom: '0.5rem' }}>Digitalization runs</h4>
            <ul className="stack-sm" style={{ listStyle: 'none', padding: 0, maxHeight: 150, overflowY: 'auto' }}>
              {digRuns.map((r) => (
                <li key={r.run_id} className="text-caption">
                  {r.mode} · {r.project_name || '—'} · {r.status}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="text-title-3" style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: '0.5rem', marginBottom: '0.5rem' }}>
              <Image size={16} style={{ verticalAlign: 'middle', marginRight: '0.25rem' }} /> Image streaming
            </h4>
            <p className="text-footnote muted" style={{ marginBottom: '0.5rem' }}>
              TIFF/OME-TIFF readiness dashboard — inspect metadata, thumbnails, and tile API coverage.
            </p>
            {onNavigate ? (
              <button
                type="button"
                className="btn btn-sm btn-secondary"
                onClick={() => onNavigate('profile', 'image_streaming_admin')}
              >
                Open readiness dashboard
              </button>
            ) : null}
          </div>

          <div>
            <h4 className="text-title-3" style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: '0.5rem', marginBottom: '0.5rem' }}>Open review tasks</h4>
            <ul className="stack-sm" style={{ listStyle: 'none', padding: 0, maxHeight: 150, overflowY: 'auto' }}>
              {tasks.slice(0, 30).map((t) => (
                <li key={t.task_id} className="text-caption">
                  {t.asset_id} — {(Number(t.assignment_confidence) * 100).toFixed(0)}%
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
