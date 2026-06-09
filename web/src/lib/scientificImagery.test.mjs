import assert from 'node:assert/strict';
import test from 'node:test';
import { resolveDtypeProfile, pixelToPhysicalCoords } from './scientificImagery.js';

test('resolveDtypeProfile handles uint16', () => {
  const p = resolveDtypeProfile({ dtype: 'uint16', bit_depth: 16 });
  assert.equal(p.bitDepth, 16);
  assert.equal(p.valueMax, 65535);
});

test('pixelToPhysicalCoords converts with calibration', () => {
  const coords = pixelToPhysicalCoords(100, 200, 0.5);
  assert.equal(coords.physicalXUm, 50);
  assert.equal(coords.physicalYUm, 100);
  assert.equal(coords.hasCalibration, true);
});
