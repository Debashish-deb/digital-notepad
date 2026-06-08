import { useCallback, useEffect, useState } from 'react';
import { createImageRoi, deleteImageRoi, fetchImageRois } from '@/services/imageAssetsClient.js';

const TOOLS = [
  { id: 'rectangle', label: 'Rectangle' },
  { id: 'polygon', label: 'Polygon' },
  { id: 'freehand', label: 'Freehand' },
];

export default function ROIManager({
  assetId,
  activeTool,
  onToolChange,
  draftGeometry,
  onDraftClear,
  viewerFlags = {},
}) {
  const [rois, setRois] = useState([]);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState('');
  const [project, setProject] = useState('');
  const [researcher, setResearcher] = useState('');
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const data = await fetchImageRois(assetId);
      setRois(data.rois || []);
      setError(null);
    } catch (err) {
      setError(err?.message || 'Failed to load ROIs');
    }
  }, [assetId]);

  useEffect(() => {
    if (viewerFlags.roi_annotations) refresh();
  }, [assetId, refresh, viewerFlags.roi_annotations]);

  const handleSave = async () => {
    if (!draftGeometry || !name.trim()) return;
    await createImageRoi(assetId, {
      name: name.trim(),
      description: description.trim() || null,
      tags: tags.split(',').map((t) => t.trim()).filter(Boolean),
      project: project.trim() || null,
      geometry: { ...draftGeometry, researcher: researcher.trim() || undefined },
      roi_type: activeTool || 'rectangle',
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
      <input type="text" placeholder="ROI name" value={name} onChange={(e) => setName(e.target.value)} />
      <textarea placeholder="Description" value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />
      <input type="text" placeholder="Tags (comma-separated)" value={tags} onChange={(e) => setTags(e.target.value)} />
      <input type="text" placeholder="Project" value={project} onChange={(e) => setProject(e.target.value)} />
      <input type="text" placeholder="Researcher" value={researcher} onChange={(e) => setResearcher(e.target.value)} />
      <button type="button" className="btn btn-sm" disabled={!draftGeometry || !name.trim()} onClick={handleSave}>
        Save ROI
      </button>
      {draftGeometry ? <p className="text-footnote">Draft: {JSON.stringify(draftGeometry).slice(0, 80)}…</p> : null}
      {error ? <p className="text-footnote text-danger">{error}</p> : null}
      <ul className="image-panel__roi-list">
        {rois.map((roi) => (
          <li key={roi.roi_id}>
            <strong>{roi.name}</strong>
            <span className="text-footnote muted"> {roi.roi_type}</span>
            <button type="button" className="btn btn-ghost btn-xs text-danger" onClick={() => handleDelete(roi.roi_id)}>Delete</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
