import {
  ArrowRight,
  BookOpen,
  Brush,
  ClipboardList,
  FileText,
  FolderOpen,
  Microscope,
  Sparkles,
  Dna,
  Target,
  Users,
  PartyPopper,
} from 'lucide-react';
import { useGuiT } from '../../i18n/useGuiT.js';
import { labMembers } from '../../data/labMembers.js';
import LabTeamRoster from '../LabTeamRoster.jsx';

const SECTION_META = [
  { id: 'onboarding', icon: ClipboardList, highlight: true },
  { id: 'guidelines', icon: BookOpen },
  { id: 'documents_permits', icon: FileText },
  { id: 'personnel', icon: Users },
  { id: 'cleaning', icon: Brush },
  { id: 'social', icon: PartyPopper },
];

const QUICK_LINKS = [
  {
    id: 'projects',
    main: 'projects_data',
    sub: 'portfolio',
    icon: FolderOpen,
    labelKey: 'projectsPortfolio',
    descKey: 'projectsPortfolioDesc',
  },
  {
    id: 'decisions',
    main: 'projects_data',
    sub: 'decisions',
    icon: ClipboardList,
    labelKey: 'researchDecisions',
    descKey: 'researchDecisionsDesc',
  },
];

const TOPIC_ICONS = {
  spatial: Microscope,
  omics: Dna,
  precision: Target,
};

export default function OverviewIntroBody({ onSubChange, onNavigate }) {
  const { intro: t } = useGuiT();

  return (
    <div className="overview-intro-body">
      <article className="overview-intro-panel overview-intro-panel--about">
        <div className="overview-intro-panel-head">
          <Sparkles size={18} className="overview-intro-panel-icon" aria-hidden />
          <h2 className="overview-intro-panel-title">{t.aboutTitle}</h2>
        </div>
        <p className="overview-intro-prose">{t.aboutBody}</p>
      </article>

      <section className="overview-intro-panel">
        <div className="overview-intro-panel-head">
          <Microscope size={18} className="overview-intro-panel-icon" aria-hidden />
          <h2 className="overview-intro-panel-title">{t.topicsTitle}</h2>
        </div>
        <div className="overview-intro-topic-grid">
          {t.topics.map((topic) => {
            const Icon = TOPIC_ICONS[topic.id] || Sparkles;
            return (
              <article key={topic.id} className="overview-intro-topic-card">
                <span className="overview-intro-topic-icon" aria-hidden>
                  <Icon size={20} />
                </span>
                <h3 className="overview-intro-topic-title">{topic.title}</h3>
                <p className="overview-intro-topic-desc">{topic.description}</p>
              </article>
            );
          })}
        </div>
      </section>

      <section className="overview-intro-panel">
        <div className="overview-intro-panel-head">
          <h2 className="overview-intro-panel-title">{t.teamTitle}</h2>
          <p className="overview-intro-panel-hint">{t.teamHint}</p>
        </div>
        <LabTeamRoster members={labMembers} className="overview-intro-team-roster" />
      </section>

      <section className="overview-intro-panel">
        <div className="overview-intro-panel-head">
          <FolderOpen size={18} className="overview-intro-panel-icon" aria-hidden />
          <div>
            <h2 className="overview-intro-panel-title">{t.platformTitle}</h2>
            <p className="overview-intro-panel-hint">{t.platformLead}</p>
          </div>
        </div>
        <div className="overview-intro-nav-grid">
          {QUICK_LINKS.map(({ id, main, sub, icon: Icon, labelKey, descKey }) => (
            <button
              key={id}
              type="button"
              className="overview-intro-nav-card"
              onClick={() => onNavigate?.(main, sub)}
            >
              <div className="overview-intro-nav-card-head">
                <span className="overview-intro-nav-icon" aria-hidden>
                  <Icon size={18} />
                </span>
                <span className="overview-intro-nav-label">{t.quickLinks[labelKey]}</span>
                <ArrowRight size={15} className="overview-intro-nav-arrow" aria-hidden />
              </div>
              <p className="overview-intro-nav-desc">{t.quickLinks[descKey]}</p>
            </button>
          ))}
        </div>
      </section>

      <section className="overview-intro-panel overview-intro-panel--docs">
        <div className="overview-intro-panel-head">
          <FileText size={18} className="overview-intro-panel-icon" aria-hidden />
          <div>
            <h2 className="overview-intro-panel-title">{t.docsTitle}</h2>
            <p className="overview-intro-panel-hint">{t.docsLead}</p>
          </div>
        </div>
        <div className="overview-intro-nav-grid">
          {SECTION_META.map(({ id, icon: Icon, highlight }) => {
            const section = t.sections[id];
            return (
              <button
                key={id}
                type="button"
                className={`overview-intro-nav-card${highlight ? ' overview-intro-nav-card--primary' : ''}`}
                onClick={() => onSubChange?.(id)}
              >
                <div className="overview-intro-nav-card-head">
                  <span className="overview-intro-nav-icon" aria-hidden>
                    <Icon size={18} />
                  </span>
                  <span className="overview-intro-nav-label">{section.label}</span>
                  <ArrowRight size={15} className="overview-intro-nav-arrow" aria-hidden />
                </div>
                <p className="overview-intro-nav-desc">{section.description}</p>
              </button>
            );
          })}
        </div>
      </section>
    </div>
  );
}
