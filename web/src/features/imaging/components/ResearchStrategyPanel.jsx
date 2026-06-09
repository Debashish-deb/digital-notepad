import { useState } from 'react';
import { postImagingCouncil } from '@/services/imageAssetsClient.js';
import { apiFetch } from '@/services/client.js';
import InterpretationDisclaimer from './InterpretationDisclaimer.jsx';

export default function ResearchStrategyPanel({ assetId, manifest, channelState }) {
  const [question, setQuestion] = useState('');
  const [strategy, setStrategy] = useState(null);
  const [council, setCouncil] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const markers = channelState.map((ch) => ch.label).filter(Boolean);
  const project = manifest?.project_hint || manifest?.project;

  const runStrategy = async () => {
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const imagingContext = [
        `Asset: ${assetId}`,
        `Markers: ${markers.join(', ') || 'none'}`,
        `Dtype: ${manifest?.dtype || 'unknown'}`,
        `Pixel size µm: ${manifest?.physical_pixel_size_um ?? 'uncalibrated'}`,
        `Question: ${question.trim()}`,
      ].join('\n');
      const chat = await apiFetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: imagingContext,
          project_codes: project ? [project] : [],
          agent_category: 'research_strategy',
        }),
      });
      setStrategy(chat);
      const councilResult = await postImagingCouncil({
        asset_id: assetId,
        question: question.trim(),
        markers,
        project,
      });
      setCouncil(councilResult);
    } catch (err) {
      setError(err?.message || 'Strategy request failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="image-panel image-panel--strategy">
      <h4>Research strategy</h4>
      <p className="text-footnote muted">
        Grounded chat + multi-agent council with imaging context (asset, markers, project).
      </p>
      <textarea
        rows={3}
        placeholder="Ask about marker interpretation, study design, or spatial hypotheses…"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
      />
      <button type="button" className="btn btn-sm" disabled={loading || !question.trim()} onClick={runStrategy}>
        {loading ? 'Running…' : 'Analyze strategy'}
      </button>
      {error ? <p className="text-footnote text-danger">{error}</p> : null}
      {strategy?.answer ? (
        <div className="text-footnote">
          <h4>Strategy response</h4>
          <p>{strategy.answer}</p>
        </div>
      ) : null}
      {council?.opinions?.length ? (
        <div className="text-footnote">
          <h4>Council opinions</h4>
          <ul>
            {council.opinions.map((op) => (
              <li key={op.role}>
                <strong>{op.role}:</strong> {op.summary?.slice(0, 240)}
                {op.uncertainty ? <span className="muted"> · uncertainty: {op.uncertainty}</span> : null}
              </li>
            ))}
          </ul>
          {council.consensus ? <p><em>Consensus:</em> {council.consensus}</p> : null}
        </div>
      ) : null}
      <InterpretationDisclaimer compact />
    </div>
  );
}
