import { formatScientificValue, resolveDtypeProfile } from '@/lib/scientificImagery.js';

export default function PixelInspector({ pixel, imageCoords, channelState, rawProbe, manifest }) {
  const profile = resolveDtypeProfile(manifest || rawProbe || {});

  if (!pixel && !imageCoords && !rawProbe) {
    return (
      <div className="image-panel image-panel--inspector">
        <p className="text-footnote muted">
          Move the cursor over the image. Raw sensor values load from the source file; display values reflect windowing only.
        </p>
      </div>
    );
  }

  return (
    <div className="image-panel image-panel--inspector">
      {imageCoords ? (
        <p className="text-footnote">
          <strong>Pixel:</strong> X {Math.round(imageCoords.x)}, Y {Math.round(imageCoords.y)}
          {rawProbe?.physical_x_um != null ? (
            <>
              {' '}
              · <strong>Physical:</strong> {rawProbe.physical_x_um.toFixed(2)} µm,{' '}
              {rawProbe.physical_y_um.toFixed(2)} µm
            </>
          ) : null}
        </p>
      ) : null}
      <p className="text-footnote muted">
        Encoding: {profile.dtype} ({profile.bitDepth}-bit)
      </p>
      {rawProbe?.channels?.length ? (
        <ul className="image-panel__intensity-list">
          {rawProbe.channels.map((entry) => {
            const display = pixel?.intensities?.find((d) => d.index === entry.channel);
            const ch = channelState?.[entry.channel];
            return (
              <li key={entry.channel}>
                <span style={{ color: ch?.color || entry.color }}>{entry.label}</span>
                {' '}
                raw {formatScientificValue(entry.raw_value, profile)}
                {display ? ` · display ${Math.round(display.value)}` : ''}
              </li>
            );
          })}
        </ul>
      ) : pixel?.intensities?.length ? (
        <ul className="image-panel__intensity-list">
          {pixel.intensities.map((entry) => (
            <li key={entry.index}>
              <span style={{ color: entry.color }}>{entry.label}</span>: display {entry.value}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-footnote muted">Sampling pixel values…</p>
      )}
    </div>
  );
}
