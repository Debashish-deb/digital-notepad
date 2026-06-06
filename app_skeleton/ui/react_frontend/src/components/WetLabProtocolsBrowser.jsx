import {
  Beaker,
  Camera,
  ClipboardList,
  FileText,
  FlaskConical,
  Microscope,
  TestTubes,
} from 'lucide-react';
import LabDocumentsBrowser from './LabDocumentsBrowser.jsx';
import { WET_LAB_PROTOCOLS_CONFIG, wetLabDocumentTitle } from '../utils/wetLabCategories.js';

const PROTOCOL_CATEGORY_ICONS = {
  patient_omentum: FlaskConical,
  patient_adnexa: FlaskConical,
  patient_other_sites: FlaskConical,
  patient_misc: FlaskConical,
  proto_sample_prep: Beaker,
  proto_tissue_processing: TestTubes,
  proto_spatial: Microscope,
  proto_staining: Beaker,
  proto_archive: FileText,
  proto_imaging: Camera,
  proto_lab_ops: ClipboardList,
  proto_scrna: Microscope,
  proto_general: FileText,
  slide_orders: FileText,
};

/**
 * Protocol-focused document browser — workflow chips, flat file lists, split preview layout.
 */
export default function WetLabProtocolsBrowser({ title, description }) {
  return (
    <LabDocumentsBrowser
      sectionIds={WET_LAB_PROTOCOLS_CONFIG.sectionIds}
      title={title}
      description={description}
      categoryGroups={WET_LAB_PROTOCOLS_CONFIG.categoryGroups}
      defaultCategory={WET_LAB_PROTOCOLS_CONFIG.defaultCategory}
      categorizePath={WET_LAB_PROTOCOLS_CONFIG.categorizePath}
      documentTitle={wetLabDocumentTitle}
      documentFilter={WET_LAB_PROTOCOLS_CONFIG.documentFilter}
      categoryIcons={PROTOCOL_CATEGORY_ICONS}
      className="lab-documents-browser wet-lab-protocols-browser catalog-space-browser"
    />
  );
}
