import { useState } from 'react';
import { postSpatialAnalyze } from '@/services/imageAssetsClient.js';

export default function SpatialAnalysisOverlay({ assetId, manifest }) {
  const [radiusUm, setRadiusUm] = useState(50);
  const [phenotypeFilter, setPhenotypeFilter] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const runAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await postSpatialAnalyze(assetId, {
        radius_um: radiusUm,
        phenotype_filter: phenotypeFilter || null,
      });
      setResult(data);
    } catch (err) {
      setError(err?.message || 'Spatial analysis failed');
    } finally {
      setLoading(false);
    }
  };

  const umCalibrated = Boolean(manifest?.physical_pixel_size_um || manifest?.pixel_size_um);

  return (
    <div className="image-panel image-panel--spatial">
      <p className="text-footnote">
        Nearest-neighbor counts and radius density on cell centroids
        {umCalibrated ? ' (µm calibrated)' : ' (pixel units — no µm calibration)'}.
      </p>
      <label className="image-panel__field">
        Analysis radius (µm)
        <input type="number" min={5} max={500} value={radiusUm} onChange={(e) => setRadiusUm(Number(e.target.value))} />
      </label>
      <label className="image-panel__field">
        Phenotype filter
        <input type="text" placeholder="CD8, tumor…" value={phenotypeFilter} onChange={(e) => setPhenotypeFilter(e.target.value)} />
      </label>
      <button type="button" className="btn btn-sm" disabled={loading} onClick={runAnalysis}>
        {loading ? 'Analyzing…' : 'Run spatial analysis'}
      </button>
      {error ? <p className="text-footnote text-danger">{error}</p> : null}
      {result ? (
        <div className="text-footnote">
          <p><strong>Cells:</strong> {result.cell_count}</p>
          <p><strong>Radius:</strong> {result.radius_um} µm ({result.radius_px} px)</p>
          {result.tumor_immune_distances?.length ? (
            <div>
              <h4>Tumor–immune distances</h4>
              <ul>
                {result.tumor_immune_distances.slice(0, 5).map((row) => (
                  <li key={row.tumor_cell_id}>
                    {row.tumor_cell_id} → {row.nearest_immune_id}:{' '}
                    {row.distance_um != null ? `${row.distance_um} µm` : `${row.distance_px} px`}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {result.nearest_neighbors?.length ? (
            <div>
              <h4>Nearest neighbors (sample)</h4>
              <ul>
                {result.nearest_neighbors.slice(0, 5).map((nn) => (
                  <li key={nn.cell_id}>
                    {nn.cell_id}: {nn.nearest_count} within radius
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
