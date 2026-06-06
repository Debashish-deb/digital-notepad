import {
  BookOpen,
  ClipboardList,
  FileText,
  Users,
  Brush,
} from 'lucide-react';
import LabDocumentsBrowser from '../components/LabDocumentsBrowser.jsx';
import OverviewIntroBody from '../components/overview/OverviewIntroBody.jsx';
import OverviewSocialPanel from '../components/overview/OverviewSocialPanel.jsx';
import { teamDirectory } from '../data/teamDirectory.js';
import LabTeamRoster from '../components/LabTeamRoster.jsx';
import { useGuiT } from '../i18n/useGuiT.js';
import { getOverviewConfig, overviewDocumentTitle } from '../utils/overviewCategories.js';

const SUB_ICONS = {
  get_started: BookOpen,
  onboarding: ClipboardList,
  guidelines: BookOpen,
  documents_permits: FileText,
  personnel: Users,
  cleaning: Brush,
};

const INTRO_SUB_IDS = new Set(['get_started', 'dashboard', 'research']);

function categorizeForConfig(config, path, sourceSection) {
  if (config.categorizePath) {
    return config.categorizePath(path, sourceSection);
  }
  return path;
}

function PersonnelPanel() {
  const { t } = useGuiT();
  return (
    <div className="panel lab-team-panel" style={{ marginBottom: '1rem', flexShrink: 0 }}>
      <h3 className="panel-title" style={{ fontSize: '1rem' }}>
        <Users size={16} /> {t('docs.teamDirectory')}
      </h3>
      <p className="text-caption muted" style={{ marginTop: '0.35rem' }}>
        Principal Investigator on top; Joonas Jukonen leads the second row. Platform IT listed last.
      </p>
      <LabTeamRoster members={teamDirectory} className="lab-team-panel__roster" />
    </div>
  );
}

export default function OverviewDocumentsScreen({
  subId,
  title,
  description,
  onSubChange,
  onNavigate,
  socialSubId,
  onSocialSubChange,
}) {
  const showIntroBody = INTRO_SUB_IDS.has(subId);

  return (
    <section className="overview-page">
      {showIntroBody ? (
        <OverviewIntroBody onSubChange={onSubChange} onNavigate={onNavigate} />
      ) : subId === 'social' ? (
        <OverviewSocialPanel
          activeSub={socialSubId}
          onSubChange={onSocialSubChange}
          title={title}
          description={description}
        />
      ) : (
        <OverviewTabDocuments subId={subId} title={title} description={description} />
      )}
    </section>
  );
}

function OverviewTabDocuments({ subId, title, description }) {
  const config = getOverviewConfig(subId);
  const Icon = SUB_ICONS[subId] || FileText;

  const categorizePath = (path, sourceSection) =>
    categorizeForConfig(config, path, sourceSection);

  const descriptions = {
    onboarding: description || 'Orientation decks, checklists, and important contacts.',
    guidelines: description || 'Research and work-related lab guidelines.',
    documents_permits:
      description || 'Permits, BSL-2 documents, datasheets, GSK papers, and compliance files.',
    personnel: description || 'Personnel records, hiring materials, and lab management docs.',
    cleaning: description || 'Cleaning day schedules, tasks, and storage inventories.',
  };

  return (
    <LabDocumentsBrowser
      key={subId}
      sectionIds={config.sectionIds}
      title={title || 'Lab Documents'}
      description={descriptions[subId] || description}
      icon={Icon}
      categoryGroups={config.categoryGroups}
      defaultCategory={config.defaultCategory}
      categorizePath={categorizePath}
      documentTitle={overviewDocumentTitle}
      className="overview-documents-browser catalog-space-browser"
      topPanel={subId === 'personnel' ? <PersonnelPanel /> : null}
    />
  );
}
