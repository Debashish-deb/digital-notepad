
import React from 'react';
import ToolingScreen from './ToolingScreen';

/** CyCif hub — reuses tooling console with imaging-focused defaults. */
export default function CycifScreen({ variant = 'pipeline', ...props }) {
  const subMap = {
    pipeline: 'pipeline',
    install: 'install',
    structure: 'diagnostics',
  };
  return (
    <ToolingScreen
      {...props}
      embedded
      initialSubTab={subMap[variant] || 'pipeline'}
      titleOverride="CyCif imaging & QC"
      subtitleOverride="Stitching, segmentation, structure checks, and spatial viewer setup for multiplex CycIF workflows."
    />
  );
}
