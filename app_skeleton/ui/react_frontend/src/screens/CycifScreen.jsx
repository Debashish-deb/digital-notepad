import './MacPlusVisualStyles.css';
import React from 'react';
import ToolingScreen from './ToolingScreen';
import LabSectionTwinPanel from '../components/LabSectionTwinPanel.jsx';

/** CyCif hub — reuses tooling console with imaging-focused defaults. */
export default function CycifScreen({ variant = 'pipeline', ...props }) {
  if (variant === 'knowledge') {
    return (
      <div className="panel">
        <LabSectionTwinPanel
          sectionId="04_Wet_Lab"
          title="t-CyCIF Knowledge Base"
          description="Antibody validations, experimental planning, and protocols extracted for t-CyCIF workflows."
          filterFolder="tCycIF projects"
        />
      </div>
    );
  }

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
