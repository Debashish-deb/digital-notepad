import { Users } from 'lucide-react';
import LabDocumentExplorer from '@/features/documents/components/LabDocumentExplorer.jsx';
import OverviewIntroBody from '@/features/overview/components/OverviewIntroBody.jsx';
import OverviewSocialPanel from '@/features/overview/components/OverviewSocialPanel.jsx';
import { teamDirectory } from '@/data/teamDirectory.js';
import LabTeamRoster from '@/features/lab/components/LabTeamRoster.jsx';
import { useGuiT } from '@/i18n/useGuiT.js';

const INTRO_SUB_IDS = new Set(['get_started', 'dashboard', 'research']);

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
  const descriptions = {
    onboarding: description || 'Orientation decks, checklists, and important contacts.',
    guidelines: description || 'Research and work-related lab guidelines.',
    documents_permits:
      description || 'Permits, BSL-2 documents, datasheets, GSK papers, and compliance files.',
    personnel: description || 'Personnel records, hiring materials, and lab management docs.',
    cleaning: description || 'Cleaning day schedules, tasks, and storage inventories.',
  };

  return (
    <LabDocumentExplorer
      mainId="overview"
      subId={subId}
      title={title || 'Lab Documents'}
      description={descriptions[subId] || description}
      className="overview-documents-browser lab-document-explorer--overview"
      topPanel={subId === 'personnel' ? <PersonnelPanel /> : null}
    />
  );
}
