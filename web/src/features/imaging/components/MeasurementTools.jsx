import {
  distancePixels,
  formatLength,
  pixelSizeUm,
  pixelsToMicrons,
  polygonArea,
  polygonPerimeter,
  rectangleArea,
  rectanglePerimeter,
} from '@/features/imaging/utils/measurementHelpers.js';

export default function MeasurementTools({ manifest, measurement, unit = 'um' }) {
  const umPerPx = pixelSizeUm(manifest);

  if (!measurement) {
    return (
      <div className="image-panel image-panel--measure">
        <p className="text-footnote muted">Enable inspection mode and draw on the canvas to measure.</p>
      </div>
    );
  }

  let pxValue = 0;
  if (measurement.type === 'distance' && measurement.points?.length >= 2) {
    pxValue = distancePixels(measurement.points[0], measurement.points[1]);
  } else if (measurement.type === 'rectangle' && measurement.rect) {
    pxValue = measurement.mode === 'area' ? rectangleArea(measurement.rect) : rectanglePerimeter(measurement.rect);
  } else if (measurement.type === 'polygon' && measurement.points?.length >= 3) {
    pxValue = measurement.mode === 'area' ? polygonArea(measurement.points) : polygonPerimeter(measurement.points);
  }

  const um = umPerPx ? pixelsToMicrons(pxValue, umPerPx) : null;
  const label = measurement.mode === 'area' ? 'Area' : measurement.mode === 'perimeter' ? 'Perimeter' : 'Distance';

  return (
    <div className="image-panel image-panel--measure">
      <p className="text-footnote"><strong>{label}</strong></p>
      <p className="text-footnote">{pxValue.toFixed(1)} px</p>
      {um != null ? <p className="text-footnote">{formatLength(um, unit)}</p> : <p className="text-footnote muted">No µm calibration</p>}
    </div>
  );
}
