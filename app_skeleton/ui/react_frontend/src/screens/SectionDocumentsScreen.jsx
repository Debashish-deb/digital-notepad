import {
  Beaker,
  BookOpen,
  Camera,
  ClipboardList,
  FileText,
  FlaskConical,
  Microscope,
  PartyPopper,
  Shield,
  TestTubes,
  Users,
} from 'lucide-react';
import LabDocumentsBrowser from '../components/LabDocumentsBrowser.jsx';
import { getSectionDocumentsConfig } from '../utils/sectionDocumentsConfig.js';
import { overviewDocumentTitle } from '../utils/overviewCategories.js';
import { socialDocumentTitle } from '../utils/socialCategories.js';
import { wetLabDocumentTitle } from '../utils/wetLabCategories.js';
import { cycifDocumentTitle } from '../utils/cycifCategories.js';

const MAIN_ICONS = {
  social: PartyPopper,
  wet_lab: FlaskConical,
  cycif: Microscope,
};

const SUB_ICONS = {
  lab_parties: PartyPopper,
  winter_events: Camera,
  lab_retreats: Users,
  lab_photos: Camera,
  researcher_visits: Users,
  outreach: Camera,
  files: Microscope,
  cycif_projects: Microscope,
  cycif_instructions: BookOpen,
  cycif_sectioning: FileText,
  cycif_inventory: FlaskConical,
  cycif_protocols: BookOpen,
  knowledge: BookOpen,
};

const TITLE_FN = {
  social: socialDocumentTitle,
  wet_lab: wetLabDocumentTitle,
  cycif: cycifDocumentTitle,
  overview: overviewDocumentTitle,
};

const WET_LAB_CATEGORY_ICONS = {
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
  geomx: Microscope,
  xenium: Microscope,
  inventories: FileText,
  waste_mgmt: FlaskConical,
  wet_spreadsheets: FileText,
};

const CYCIF_CATEGORY_ICONS = {
  project_runs: Microscope,
  project_validation: FlaskConical,
  project_templates: FileText,
  cycif_planning: BookOpen,
  cycif_antibody_scan: FlaskConical,
  cycif_instruction_other: FileText,
  sectioning_orders: FileText,
  he_after_cycif: FileText,
  sectioning_other: FileText,
  antibody_inventory: FlaskConical,
  spatial_protocols: FileText,
  geomx_cycif: Microscope,
  cycif_other: FileText,
  individual_projects: Microscope,
  instructions: FileText,
  sectioning: FileText,
};

const OVERVIEW_CATEGORY_ICONS = {
  biobank: ClipboardList,
  bsl_forms: FileText,
  bsl1_2: Shield,
  bsl_drafts: FileText,
  bsl_gmo: ClipboardList,
  ethanol: Shield,
  datasheets: BookOpen,
  qiagen: BookOpen,
  equipment_barcodes: Camera,
  root_docs: FileText,
  gsk_nov2021: FileText,
  gsk_filled: ClipboardList,
  gsk_unfilled: FileText,
  gsk_root: FileText,
  orientation: BookOpen,
  contacts: Users,
  research: BookOpen,
  work: ClipboardList,
  cleaning_20250528: FlaskConical,
  cleaning_251205: FlaskConical,
  roster: Users,
  hiring: Users,
  lab_management: ClipboardList,
  conference: FileText,
  phd_apps: BookOpen,
  peer_review: FileText,
  presentations: FileText,
};

const SOCIAL_CATEGORY_ICONS = {
  party_halloween: PartyPopper,
  party_grilling: PartyPopper,
  party_planning: PartyPopper,
  winter_photos: Camera,
  winter_docs: FileText,
  retreat_2024: Users,
  retreat_2025: Users,
  retreat_planning: FileText,
  photo_retreats: Camera,
  photo_shoot: Camera,
  photo_group: Camera,
  photo_events: PartyPopper,
  photo_misc: Camera,
  visit_records: Users,
  outreach_media: Camera,
  lab_parties: PartyPopper,
  winter_events: Camera,
  lab_retreats: Users,
  lab_photos: Camera,
  researcher_visits: Users,
  outreach: Camera,
  social_misc: FileText,
};

export default function SectionDocumentsScreen({ mainId, subId, title, description }) {
  const config = getSectionDocumentsConfig(mainId, subId);
  if (!config) return null;

  const Icon = SUB_ICONS[subId] || MAIN_ICONS[mainId] || FileText;
  const documentTitle = TITLE_FN[mainId] || config.documentTitle || overviewDocumentTitle;
  const categoryIcons =
    mainId === 'overview'
      ? OVERVIEW_CATEGORY_ICONS
      : mainId === 'wet_lab'
        ? WET_LAB_CATEGORY_ICONS
        : mainId === 'cycif'
          ? CYCIF_CATEGORY_ICONS
          : mainId === 'social'
            ? SOCIAL_CATEGORY_ICONS
            : {};

  return (
    <LabDocumentsBrowser
      key={`${mainId}-${subId}`}
      sectionIds={config.sectionIds}
      title={title}
      description={description}
      icon={Icon}
      categoryGroups={config.categoryGroups}
      defaultCategory={config.defaultCategory}
      categorizePath={(path, sourceSection) => config.categorizePath(path, sourceSection)}
      documentTitle={documentTitle}
      documentFilter={config.documentFilter}
      categoryIcons={categoryIcons}
      className={`section-documents-browser section-documents-browser--${mainId} catalog-space-browser`}
    />
  );
}
