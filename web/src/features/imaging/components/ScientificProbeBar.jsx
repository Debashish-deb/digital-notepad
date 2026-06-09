import { formatScientificValue, resolveDtypeProfile } from '@/lib/scientificImagery.js';

export default function ScientificProbeBar({
  manifest,
  imageCoords,
  rawProbe,
  displayProbe,
  zIndex = 0,
  tIndex = 0,
}) {
  const profile = resolveDtypeProfile(manifest || {});
  const ix = imageCoords ? Math.round(imageCoords.x) : null;
  const iy = imageCoords ? Math.round(imageCoords.y) : null;

  return (
    <footer className="sci-probe-bar" aria-label="Pixel probe">
      <div className="sci-probe-bar__coords">
        <span className="sci-probe-bar__label">Position</span>
        {ix != null && iy != null ? (
          <span className="sci-probe-bar__value sci-probe-bar__value--mono">
            X {ix} · Y {iy}
            {rawProbe?.physical_x_um != null ? (
              <> · {rawProbe.physical_x_um.toFixed(2)} µm · {rawProbe.physical_y_um.toFixed(2)} µm</>
            ) : (
              <span className="sci-probe-bar__muted"> · no µm calibration</span>
            )}
          </span>
        ) : (
          <span className="sci-probe-bar__muted">Move cursor over image</span>
        )}
      </div>

      <div className="sci-probe-bar__stack">
        <span className="sci-probe-bar__label">Z/T</span>
        <span className="sci-probe-bar__value sci-probe-bar__value--mono">
          Z {zIndex + 1} · T {tIndex + 1}
        </span>
      </div>

      <div className="sci-probe-bar__channels">
        <span className="sci-probe-bar__label">
          Intensity ({profile.bitDepth}-bit raw)
        </span>
        {rawProbe?.channels?.length ? (
          <ul className="sci-probe-bar__intensity-list">
            {rawProbe.channels.map((entry) => {
              const display = displayProbe?.intensities?.find((d) => d.index === entry.channel);
              return (
                <li key={entry.channel}>
                  <span className="sci-probe-bar__ch-label">{entry.label}</span>
                  <span className="sci-probe-bar__raw">
                    {formatScientificValue(entry.raw_value, profile)}
                  </span>
                  {display ? (
                    <span className="sci-probe-bar__display">
                      disp {Math.round(display.value)}
                    </span>
                  ) : null}
                </li>
              );
            })}
          </ul>
        ) : ix != null ? (
          <span className="sci-probe-bar__muted">Sampling…</span>
        ) : (
          <span className="sci-probe-bar__muted">—</span>
        )}
      </div>
    </footer>
  );
}
