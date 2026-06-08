export default function PixelInspector({ pixel, imageCoords, channelState }) {
  if (!pixel && !imageCoords) {
    return (
      <div className="image-panel image-panel--inspector">
        <p className="text-footnote muted">Hover or click the image to inspect pixels.</p>
      </div>
    );
  }

  return (
    <div className="image-panel image-panel--inspector">
      {imageCoords ? (
        <p className="text-footnote">
          <strong>Position:</strong> X {Math.round(imageCoords.x)}, Y {Math.round(imageCoords.y)}
        </p>
      ) : null}
      {pixel?.intensities?.length ? (
        <ul className="image-panel__intensity-list">
          {pixel.intensities.map((entry) => (
            <li key={entry.index}>
              <span style={{ color: entry.color }}>{entry.label}</span>: {entry.value}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-footnote muted">No intensity data yet.</p>
      )}
    </div>
  );
}
