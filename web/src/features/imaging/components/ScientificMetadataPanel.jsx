import { resolveDtypeProfile } from '@/lib/scientificImagery.js';

function MetaRow({ label, value, mono = false }) {
  if (value == null || value === '' || value === '—') return null;
  return (
    <div className="sci-meta-row">
      <span className="sci-meta-row__label">{label}</span>
      <span className={`sci-meta-row__value${mono ? ' sci-meta-row__value--mono' : ''}`}>{value}</span>
    </div>
  );
}

export default function ScientificMetadataPanel({ manifest, metadata }) {
  const imgMeta = metadata?.image_metadata || {};
  const merged = { ...imgMeta, ...manifest };
  const profile = resolveDtypeProfile(merged);
  const dims =
    manifest?.width && manifest?.height
      ? `${manifest.width} × ${manifest.height} px`
      : imgMeta.dimensions?.shape?.join(' × ') || '—';

  return (
    <aside className="sci-metadata-panel" aria-label="Acquisition metadata">
      <header className="sci-metadata-panel__header">
        <p className="text-caption">Instrument record</p>
        <h4 className="sci-metadata-panel__title">Source metadata</h4>
        <p className="sci-metadata-panel__note">
          Raw pixel values and calibration are preserved. Display windowing does not modify source files.
        </p>
      </header>

      <section className="sci-metadata-panel__section">
        <h5 className="sci-metadata-panel__section-title">Image plane</h5>
        <MetaRow label="Asset" value={manifest?.asset_id || imgMeta.asset_id} mono />
        <MetaRow label="Format" value={merged.format} />
        <MetaRow label="Status" value={merged.streaming_status} />
        <MetaRow label="Dimensions" value={dims} mono />
        <MetaRow label="Channels" value={merged.channels} />
        <MetaRow
          label="Z / T"
          value={`${manifest?.z_slices ?? 1} / ${manifest?.timepoints ?? 1}`}
        />
        <MetaRow label="Pyramid levels" value={manifest?.pyramid_levels ?? imgMeta.pyramid_levels} />
      </section>

      <section className="sci-metadata-panel__section">
        <h5 className="sci-metadata-panel__section-title">Scientific encoding</h5>
        <MetaRow label="Dtype" value={profile.dtype} mono />
        <MetaRow label="Bit depth" value={`${profile.bitDepth}-bit`} />
        <MetaRow
          label="Value range"
          value={`${profile.valueMin} – ${profile.valueMax}`}
          mono
        />
        <MetaRow
          label="Pixel size"
          value={
            merged.physical_pixel_size_um || merged.pixel_size_um
              ? `${merged.physical_pixel_size_um || merged.pixel_size_um} µm/px`
              : 'Not calibrated'
          }
        />
        <MetaRow label="OME-XML" value={merged.ome_xml_present ? 'Present' : 'Absent'} />
        <MetaRow label="Inspected" value={merged.inspected_at?.replace('T', ' ').slice(0, 19)} />
      </section>

      {Array.isArray(merged.channel_names) && merged.channel_names.length ? (
        <section className="sci-metadata-panel__section">
          <h5 className="sci-metadata-panel__section-title">Markers / channels</h5>
          <ul className="sci-metadata-panel__channels">
            {merged.channel_names.map((name, index) => (
              <li key={`${name}-${index}`}>
                <span className="sci-meta-channel-index">C{index}</span>
                <span>{name}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </aside>
  );
}
