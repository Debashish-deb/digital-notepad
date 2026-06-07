import {
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
import { useGuiT } from '@/i18n/useGuiT.js';
import { overviewIntroCopy } from '@/data/overviewIntroTranslations.js';
import { labMembers } from '@/data/labMembers.js';
import LabTeamRoster from '@/features/lab/components/LabTeamRoster.jsx';
import GlassCardStack, { GlassMiniCard } from '@/shared/layout/GlassCardStack.jsx';
import '@/shared/layout/GlassCardStack.css';

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

const FALLBACK_SECTIONS = overviewIntroCopy.en.sections;

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

      <section className="overview-intro-panel overview-intro-panel--cards">
        <div className="overview-intro-card-band">
          <div className="overview-intro-card-band__head">
            <div className="overview-intro-panel-head">
              <Microscope size={18} className="overview-intro-panel-icon" aria-hidden />
              <h2 className="overview-intro-panel-title">{t.topicsTitle}</h2>
            </div>
            <p className="overview-intro-prose overview-intro-prose--compact">
              {t.topicsLead || 'Spatial multi-omics, precision medicine, and translational pipelines across the lab portfolio.'}
            </p>
          </div>
          <GlassCardStack columns={3} rows={1} meta className="overview-intro-focus-stack">
            {(Array.isArray(t.topics) ? t.topics : overviewIntroCopy.en.topics).map((topic, index) => {
              const Icon = TOPIC_ICONS[topic.id] || Sparkles;
              return (
                <GlassMiniCard
                  key={topic.id}
                  label={topic.title}
                  value={topic.description}
                  icon={Icon}
                  tone="#0ea5e9"
                  delay={index * 85}
                  title={`${topic.title} — ${topic.description}`}
                />
              );
            })}
          </GlassCardStack>
        </div>
      </section>

      <section className="overview-intro-panel">
        <div className="overview-intro-panel-head">
          <h2 className="overview-intro-panel-title">{t.teamTitle}</h2>
          <p className="overview-intro-panel-hint">{t.teamHint}</p>
        </div>
        <LabTeamRoster members={labMembers} className="overview-intro-team-roster" />
      </section>

      <section className="overview-intro-panel overview-intro-panel--cards">
        <div className="overview-intro-card-band">
          <div className="overview-intro-card-band__head">
            <div className="overview-intro-panel-head">
              <FolderOpen size={18} className="overview-intro-panel-icon" aria-hidden />
              <div>
                <h2 className="overview-intro-panel-title">{t.platformTitle}</h2>
                <p className="overview-intro-panel-hint">{t.platformLead}</p>
              </div>
            </div>
          </div>
          <GlassCardStack columns={2} rows={1} meta className="overview-intro-platform-stack">
            {QUICK_LINKS.map(({ id, main, sub, icon: Icon, labelKey, descKey }, index) => (
              <GlassMiniCard
                key={id}
                label={t.quickLinks?.[labelKey] || labelKey}
                value={t.quickLinks?.[descKey] || ''}
                icon={Icon}
                tone="#2563eb"
                delay={index * 90}
                onClick={() => onNavigate?.(main, sub)}
                title={`${t.quickLinks?.[labelKey] || labelKey} — ${t.quickLinks?.[descKey] || ''}`}
              />
            ))}
          </GlassCardStack>
        </div>
      </section>

      <section className="overview-intro-panel overview-intro-panel--docs overview-intro-panel--cards">
        <div className="overview-intro-card-band">
          <div className="overview-intro-card-band__head">
            <div className="overview-intro-panel-head">
              <FileText size={18} className="overview-intro-panel-icon" aria-hidden />
              <div>
                <h2 className="overview-intro-panel-title">{t.docsTitle}</h2>
                <p className="overview-intro-panel-hint">{t.docsLead}</p>
              </div>
            </div>
          </div>
          <GlassCardStack columns={3} rows={2} meta className="overview-intro-docs-stack">
            {SECTION_META.map(({ id, icon: Icon, highlight }, index) => {
              const section = t.sections?.[id] ?? FALLBACK_SECTIONS[id];
              if (!section) return null;
              return (
                <GlassMiniCard
                  key={id}
                  label={section.label}
                  value={section.description}
                  icon={Icon}
                  tone={highlight ? '#d97706' : '#64748b'}
                  highlight={highlight}
                  delay={index * 75}
                  onClick={() => onSubChange?.(id)}
                  title={`${section.label} — ${section.description}`}
                />
              );
            })}
          </GlassCardStack>
        </div>
      </section>
    </div>
  );
}
