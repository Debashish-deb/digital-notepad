import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { ArrowRight, Map } from 'lucide-react';
import { LazyViewFallback } from './common/LazyViewFallback.jsx';
import './LabDocumentMapPanel.css';
import {
  buildLabDocumentMermaid,
  buildZoneStats,
} from '../utils/labDocumentMap.js';

export default function LabDocumentMapPanel({ onNavigate, onZoneSelect, activeZoneId }) {
  const containerRef = useRef(null);
  const [renderError, setRenderError] = useState(null);
  const [diagramLoading, setDiagramLoading] = useState(false);
  const [expanded, setExpanded] = useState(true);
  const [zones, setZones] = useState([]);
  const diagramId = useId().replace(/:/g, '');
  const mermaidSrc = useMemo(
    () => (zones.length ? buildLabDocumentMermaid(zones) : ''),
    [zones],
  );

  useEffect(() => {
    let alive = true;
    Promise.all([
      fetch('/processed/lab__manifest.json', { cache: 'no-store' }).then((r) => (r.ok ? r.json() : null)),
      fetch('/projects').then((r) => (r.ok ? r.json() : [])).catch(() => []),
    ]).then(([manifest, projects]) => {
      if (!alive) return;
      const projectCount = Array.isArray(projects) ? projects.length : 0;
      setZones(buildZoneStats(manifest, projectCount));
    });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (!mermaidSrc) return undefined;
    let cancelled = false;
    setRenderError(null);
    setDiagramLoading(true);

    (async () => {
      try {
        const mermaid = (await import('mermaid')).default;
        mermaid.initialize({
          startOnLoad: false,
          theme: 'base',
          themeVariables: {
            fontFamily: 'system-ui, -apple-system, sans-serif',
            fontSize: '14px',
            primaryColor: '#eef2ff',
            primaryTextColor: '#1e293b',
            primaryBorderColor: '#6366f1',
            lineColor: '#94a3b8',
            secondaryColor: '#f0fdf4',
            tertiaryColor: '#fff7ed',
          },
          flowchart: {
            curve: 'basis',
            padding: 16,
            htmlLabels: true,
          },
        });
        if (cancelled || !containerRef.current) return;
        const { svg } = await mermaid.render(`lab-doc-map-${diagramId}`, mermaidSrc);
        if (!cancelled && containerRef.current) {
          containerRef.current.innerHTML = svg;
        }
      } catch (err) {
        if (!cancelled) setRenderError(err?.message || 'Could not draw map');
      } finally {
        if (!cancelled) setDiagramLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [mermaidSrc, diagramId]);

  return (
    <section className="panel lab-doc-map-panel">
      <header className="lab-doc-map-panel__head">
        <div>
          <p className="lab-doc-map-panel__eyebrow">
            <Map size={14} aria-hidden /> Where lab files live in this app
          </p>
          <h3 className="lab-doc-map-panel__title">Lab document map</h3>
          <p className="text-footnote muted lab-doc-map-panel__lead">
            Think of it like a freezer map: each box is a folder type. Pick a zone below to jump
            straight to those files — everything opens with a readable preview.
          </p>
        </div>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
        >
          {expanded ? 'Hide diagram' : 'Show diagram'}
        </button>
      </header>

      {expanded ? (
        <div className="lab-doc-map-panel__diagram-wrap">
          {diagramLoading ? (
            <LazyViewFallback variant="map" label="Drawing document map…" />
          ) : null}
          {renderError ? (
            <pre className="lab-doc-map-panel__fallback">{mermaidSrc}</pre>
          ) : (
            <div
              ref={containerRef}
              className="lab-doc-map-panel__diagram"
              role="img"
              aria-label="Diagram of lab document zones"
            />
          )}
        </div>
      ) : null}

      <div className="lab-doc-map-zone-grid" role="list">
        {zones.map((zone) => (
          <article
            key={zone.id}
            role="listitem"
            className={`lab-doc-map-zone${activeZoneId === zone.id ? ' lab-doc-map-zone--active' : ''}`}
            style={{ '--zone-accent': zone.color }}
          >
            <div className="lab-doc-map-zone__icon" aria-hidden>
              {zone.emoji}
            </div>
            <div className="lab-doc-map-zone__copy">
              <h4 className="lab-doc-map-zone__title">{zone.label}</h4>
              <p className="text-caption muted">{zone.blurb}</p>
              <p className="lab-doc-map-zone__count">
                {zone.docCount} {zone.unit}
                {zone.totalSections > 0 && zone.processedSections < zone.totalSections
                  ? ` · ${zone.processedSections}/${zone.totalSections} sections scanned`
                  : null}
              </p>
            </div>
            <div className="lab-doc-map-zone__actions">
              {onZoneSelect ? (
                <button
                  type="button"
                  className="btn btn-sm btn-secondary"
                  onClick={() => onZoneSelect(zone.id)}
                >
                  Browse here
                </button>
              ) : null}
              {onNavigate && zone.nav ? (
                <button
                  type="button"
                  className="btn btn-sm storage-ref-btn"
                  onClick={() => onNavigate(zone.nav.main, zone.nav.sub)}
                >
                  Open module <ArrowRight size={12} />
                </button>
              ) : null}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
