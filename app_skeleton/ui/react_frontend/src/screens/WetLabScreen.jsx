import './MacPlusVisualStyles.css';
import React, { useState, useEffect } from 'react';
import { BookOpen } from 'lucide-react';
import DocumentFormatter from '../components/DocumentFormatter.jsx';
import { useTaskpad } from '../contexts/TaskpadContext.jsx';
import TasksScreen from './TasksScreen';
import LabSectionTwinPanel from '../components/LabSectionTwinPanel.jsx';

const WET_KEYWORDS = /wet|stain|sample|ffpe|tissue|antibody|chamber|bleach|protocol|prep/i;

export function WetLabProtocolsPanel() {
  return (
    <LabSectionTwinPanel
      sectionId="04_Wet_Lab"
      title="Wet-lab SOPs"
      description="Structured protocols, procedures, and methodologies for the wet lab. (Excludes tCycIF documents which are under the CyCIF tab)."
      excludeFolder="tCycIF projects"
    />
  );
}

export function WetLabTasksPanel(props) {
  return <TasksScreen {...props} categoryFilter="Wet_Lab" />;
}

export function WetLabInventoryPanel() {
  return (
    <LabSectionTwinPanel
      sectionId="wet_lab_files"
      title="Reagents, panels & wet-lab files"
      description="Protocols, inventories, GeoMx/Xenium notes, and wet-lab spreadsheets from WET_LAB."
    />
  );
}
