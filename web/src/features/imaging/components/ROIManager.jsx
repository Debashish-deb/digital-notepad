import { useCallback, useEffect, useState } from 'react';
import {
  createImageRoi,
  deleteImageRoi,
  fetchImageRois,
  measureImageRoi,
  postAnnotationFeedback,
} from '@/services/imageAssetsClient.js';

const TOOLS = [
  { id: 'rectangle', label: 'Rectangle' },
  { id: 'polygon', label: 'Polygon' },
  { id: 'circle', label: 'Circle' },
  { id: 'line', label: 'Line' },
  { id: 'freehand', label: 'Freehand' },
];

const REGION_TYPES = ['Tumor', 'Stroma', 'TLS', 'Necrosis'];

export default function ROIManager({
  assetId,
  activeTool,
  onToolChange,
  draftGeometry,
  onDraftClear,
  onRoisChange,
  manifest,
  selectedChannel = 0,
  zIndex = 0,
  tIndex = 0,
  viewerFlags = {},
}) {
  const [rois, setRois] = useState([]);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState('');
  const [project, setProject] = useState('');
  const [researcher, setResearcher] = useState('');
  const [regionType, setRegionType] = useState('');
  const [lastMeasure, setLastMeasure] = useState(null);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const data = await fetchImageRois(assetId);
      const list = data.rois || [];
      setRois(list);
      onRoisChange?.(list);
      setError(null);
    } catch (err) {
      setError(err?.message || 'Failed to load ROIs');
    }
  }, [assetId, onRoisChange]);

  useEffect(() => {
    if (viewerFlags.roi_annotations) refresh();
  }, [assetId, refresh, viewerFlags.roi_annotations]);

  const handleMeasure = async () => {
    if (!draftGeometry) return;
    const data = await measureImageRoi(assetId, {
      geometry: draftGeometry,
      roi_type: activeTool || 'rectangle',
      channel: selectedChannel,
      z: zIndex,
      t: tIndex,
    });
    setLastMeasure(data);
  };

  const exportMeasurements = (format) => {
    const payload = lastMeasure || { note: 'No measurement yet' };
    const blob = new Blob(
      [format === 'csv' ? measurementsToCsv(payload) : JSON.stringify(payload, null, 2)],
      { type: format === 'csv' ? 'text/csv' : 'application/json' },
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `roi_measure_${assetId}.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleSave = async () => {
    if (!draftGeometry || !name.trim()) return;
    const res = await createImageRoi(assetId, {
      name: name.trim(),
      description: description.trim() || null,
      tags: tags.split(',').map((t) => t.trim()).filter(Boolean),
      project: project.trim() || null,
      region_type: regionType || null,
      geometry: { ...draftGeometry, researcher: researcher.trim() || undefined },
      roi_type: activeTool || 'rectangle',
    });
    await postAnnotationFeedback(assetId, {
      target_type: 'roi',
      target_id: res.roi?.roi_id || name.trim(),
      learning_category: 'draft',
      feedback: 'neutral',
    });
    setName('');
    setDescription('');
    setTags('');
    onDraftClear?.();
    refresh();
  };

  const handleDelete = async (roiId) => {
    await deleteImageRoi(assetId, roiId);
    refresh();
  };

  if (!viewerFlags.roi_annotations) {
    return <p className="text-footnote muted">ROI annotations disabled by server flag.</p>;
  }

  return (
    <div className="image-panel image-panel--roi">
      <div className="image-panel__tool-row">
        {TOOLS.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`btn btn-ghost btn-xs${activeTool === t.id ? ' is-active' : ''}`}
            onClick={() => onToolChange?.(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <label className="image-panel__field">
        Region type
        <select value={regionType} onChange={(e) => setRegionType(e.target.value)}>
          <option value="">— none —</option>
          {REGION_TYPES.map((rt) => (
            <option key={rt} value={rt}>{rt}</option>
          ))}
        </select>
      </label>
      <input type="text" placeholder="ROI name" value={name} onChange={(e) => setName(e.target.value)} />
      <textarea placeholder="Description" value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />
      <input type="text" placeholder="Tags (comma-separated)" value={tags} onChange={(e) => setTags(e.target.value)} />
      <input type="text" placeholder="Project" value={project} onChange={(e) => setProject(e.target.value)} />
      <input type="text" placeholder="Researcher" value={researcher} onChange={(e) => setResearcher(e.target.value)} />
      <div className="image-panel__actions">
        <button type="button" className="btn btn-sm" disabled={!draftGeometry} onClick={handleMeasure}>
          Measure ROI
        </button>
        <button type="button" className="btn btn-ghost btn-xs" disabled={!lastMeasure} onClick={() => exportMeasurements('json')}>
          Export JSON
        </button>
        <button type="button" className="btn btn-ghost btn-xs" disabled={!lastMeasure} onClick={() => exportMeasurements('csv')}>
          Export CSV
        </button>
      </div>
      <button type="button" className="btn btn-sm" disabled={!draftGeometry || !name.trim()} onClick={handleSave}>
        Save ROI
      </button>
      {lastMeasure?.measurements ? (
        <div className="text-footnote">
          <p>Area: {lastMeasure.measurements.area_um2 ?? lastMeasure.measurements.area_px2} {lastMeasure.measurements.area_um2 ? 'µm²' : 'px²'}</p>
          <p>Mean: {lastMeasure.measurements.mean ?? '—'}</p>
          <p>Integrated: {lastMeasure.measurements.integrated_intensity ?? '—'}</p>
        </div>
      ) : null}
      {draftGeometry ? <p className="text-footnote">Draft: {JSON.stringify(draftGeometry).slice(0, 80)}…</p> : null}
      {error ? <p className="text-footnote text-danger">{error}</p> : null}
      <ul className="image-panel__roi-list">
        {rois.map((roi) => (
          <li key={roi.roi_id}>
            <strong>{roi.name}</strong>
            {roi.region_type ? <span className="text-footnote muted"> · {roi.region_type}</span> : null}
            <span className="text-footnote muted"> {roi.roi_type}</span>
            <button type="button" className="btn btn-ghost btn-xs text-danger" onClick={() => handleDelete(roi.roi_id)}>Delete</button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function measurementsToCsv(payload) {
  const m = payload.measurements || {};
  const rows = [
    ['field', 'value'],
    ['asset_id', payload.asset_id],
    ['roi_type', payload.roi_type],
    ['area_px2', m.area_px2],
    ['area_um2', m.area_um2],
    ['perimeter_px', m.perimeter_px],
    ['perimeter_um', m.perimeter_um],
    ['mean', m.mean],
    ['median', m.median],
    ['min', m.min],
    ['max', m.max],
    ['std', m.std],
    ['integrated_intensity', m.integrated_intensity],
  ];
  return rows.map((r) => r.join(',')).join('\n');
}
