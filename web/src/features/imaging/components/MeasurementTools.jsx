import { useEffect, useState } from 'react';
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

export default function MeasurementTools({
  manifest,
  measurement,
  draftRoi,
  roiTool,
  unit = 'um',
}) {
  const umPerPx = pixelSizeUm(manifest);
  const [live, setLive] = useState(null);

  useEffect(() => {
    if (!draftRoi) {
      setLive(null);
      return;
    }
    let pxValue = 0;
    let mode = 'area';
    if (roiTool === 'line' && draftRoi.points?.length >= 2) {
      pxValue = distancePixels(draftRoi.points[0], draftRoi.points[1]);
      mode = 'distance';
    } else if (roiTool === 'circle' && draftRoi.radius) {
      pxValue = Math.PI * draftRoi.radius ** 2;
      mode = 'area';
    } else if ((roiTool === 'polygon' || roiTool === 'freehand') && draftRoi.points?.length >= 3) {
      pxValue = polygonArea(draftRoi.points);
      mode = 'area';
    } else if (draftRoi.width != null) {
      pxValue = rectangleArea(draftRoi);
      mode = 'area';
    }
    const um = umPerPx ? pixelsToMicrons(pxValue, umPerPx) : null;
    setLive({ pxValue, um, mode, label: mode === 'area' ? 'Area' : 'Distance' });
  }, [draftRoi, roiTool, umPerPx]);

  if (!measurement && !live) {
    return (
      <div className="image-panel image-panel--measure">
        <p className="text-footnote muted">Enable inspection mode and draw on the canvas to measure.</p>
      </div>
    );
  }

  let pxValue = live?.pxValue ?? 0;
  let label = live?.label ?? 'Measurement';
  let um = live?.um ?? null;

  if (measurement?.type === 'distance' && measurement.points?.length >= 2) {
    pxValue = distancePixels(measurement.points[0], measurement.points[1]);
    um = umPerPx ? pixelsToMicrons(pxValue, umPerPx) : null;
    label = 'Distance';
  } else if (measurement?.type === 'rectangle' && measurement.rect) {
    pxValue = measurement.mode === 'area' ? rectangleArea(measurement.rect) : rectanglePerimeter(measurement.rect);
    um = umPerPx ? pixelsToMicrons(pxValue, umPerPx) : null;
    label = measurement.mode === 'area' ? 'Area' : 'Perimeter';
  } else if (measurement?.type === 'polygon' && measurement.points?.length >= 3) {
    pxValue = measurement.mode === 'area' ? polygonArea(measurement.points) : polygonPerimeter(measurement.points);
    um = umPerPx ? pixelsToMicrons(pxValue, umPerPx) : null;
    label = measurement.mode === 'area' ? 'Area' : 'Perimeter';
  }

  const areaUm2 = label === 'Area' && um != null ? um : null;
  const lengthUm = label !== 'Area' && um != null ? um : null;

  return (
    <div className="image-panel image-panel--measure">
      <p className="text-footnote"><strong>{label}</strong></p>
      <p className="text-footnote">{pxValue.toFixed(1)} px{label === 'Area' ? '²' : ''}</p>
      {areaUm2 != null ? <p className="text-footnote">{areaUm2.toFixed(2)} µm²</p> : null}
      {lengthUm != null ? <p className="text-footnote">{formatLength(lengthUm, unit)}</p> : null}
      {!umPerPx ? <p className="text-footnote muted">No µm calibration (physical_pixel_size_um)</p> : null}
    </div>
  );
}
