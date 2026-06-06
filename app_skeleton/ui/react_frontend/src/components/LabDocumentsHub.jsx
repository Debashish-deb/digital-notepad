import { useCallback, useEffect, useMemo, useState } from 'react';
import { FileCode2, Loader2 } from 'lucide-react';
import LabDocumentsBrowser from './LabDocumentsBrowser.jsx';
import LabDocumentMapPanel from './LabDocumentMapPanel.jsx';
import {
  getLabDocumentsHubConfig,
  sectionLabelForHub,
} from '../utils/labDocumentsHubConfig.js';
import { LAB_DOCUMENT_ZONES } from '../utils/labDocumentMap.js';

const ZONE_CATEGORY_MATCH = {
  orders: (catId) => catId.startsWith('orders_'),
  meetings: (catId) => catId === 'meetings' || catId.startsWith('section_meetings'),
  storage: (catId) => catId.startsWith('storage_') || catId === 'repo_setup',
  wet_lab: () => false,
  social: () => false,
  projects: () => false,
  overview: () => false,
};

async function fetchRepoMarkdown(path) {
  const file = (path || '').replace(/^configs\//, '');
  try {
    const res = await fetch(`/repo-static/${file}`);
    if (!res.ok) return null;
    return await res.text();
  } catch {
    return null;
  }
}

export default function LabDocumentsHub({ onNavigate }) {
  const config = useMemo(() => getLabDocumentsHubConfig(), []);
  const [activeZoneId, setActiveZoneId] = useState(null);
  const [repoDocs, setRepoDocs] = useState([]);
  const [repoLoading, setRepoLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    setRepoLoading(true);
    Promise.all(
      config.repoDocs.map(async (doc) => {
        const content = await fetchRepoMarkdown(doc.path);
        return {
          path: `repo://${doc.id}`,
          name: `${doc.id}.md`,
          extension: '.md',
          display_title: doc.label,
          excerpt: content?.slice(0, 4000) || doc.summary,
          inlineContent: content,
          categoryId: 'repo_setup',
          sourceSection: 'platform_config',
          section_label: 'Platform setup',
          isSynthetic: true,
          repoPath: doc.path,
          summary: doc.summary,
        };
      }),
    ).then((docs) => {
      if (!alive) return;
      setRepoDocs(docs.filter((d) => d.inlineContent));
      setRepoLoading(false);
    });
    return () => {
      alive = false;
    };
  }, [config.repoDocs]);

  const documentFilter = useCallback(
    (doc) => {
      if (config.documentFilter && !config.documentFilter(doc)) return false;
      if (!activeZoneId) return true;
      const zone = LAB_DOCUMENT_ZONES.find((z) => z.id === activeZoneId);
      if (!zone) return true;
      if (zone.id === 'projects' || zone.id === 'wet_lab' || zone.id === 'social' || zone.id === 'overview') {
        return false;
      }
      const catId = doc.categoryId || '';
      const matcher = ZONE_CATEGORY_MATCH[zone.id];
      if (matcher) return matcher(catId);
      if (zone.sectionIds?.length && doc.sourceSection) {
        return zone.sectionIds.includes(doc.sourceSection);
      }
      return true;
    },
    [activeZoneId, config.documentFilter],
  );

  const categoryGroups = useMemo(() => {
    if (!activeZoneId) return config.categoryGroups;
    const zone = LAB_DOCUMENT_ZONES.find((z) => z.id === activeZoneId);
    if (!zone || zone.id === 'projects') return config.categoryGroups;

    if (zone.id === 'storage') {
      return config.categoryGroups.filter((g) =>
        ['cleaning_storage', 'platform'].includes(g.id),
      );
    }
    if (zone.id === 'orders') {
      return config.categoryGroups.filter((g) => g.id === 'orders');
    }
    if (zone.id === 'meetings') {
      return config.categoryGroups.filter((g) => g.id === 'meetings');
    }
    return config.categoryGroups;
  }, [activeZoneId, config.categoryGroups]);

  const handleZoneSelect = (zoneId) => {
    const zone = LAB_DOCUMENT_ZONES.find((z) => z.id === zoneId);
    if (zone?.id === 'projects' && onNavigate) {
      onNavigate('projects_data', 'portfolio');
      return;
    }
    if (zone?.id === 'wet_lab' && onNavigate) {
      onNavigate('wet_lab', 'files');
      return;
    }
    if (zone?.id === 'social' && onNavigate) {
      onNavigate('social', 'lab_photos');
      return;
    }
    if (zone?.id === 'overview' && onNavigate) {
      onNavigate('overview', 'documents_permits');
      return;
    }
    setActiveZoneId((prev) => (prev === zoneId ? null : zoneId));
  };

  return (
    <div className="lab-documents-hub stack-lg">
      <LabDocumentMapPanel
        onNavigate={onNavigate}
        onZoneSelect={handleZoneSelect}
        activeZoneId={activeZoneId}
      />

      {activeZoneId === 'projects' ? null : (
        <>
          {repoLoading ? (
            <p className="text-footnote muted">
              <Loader2 size={14} className="spin-inline" /> Loading platform setup guides…
            </p>
          ) : null}

          <LabDocumentsBrowser
            key={`hub-${activeZoneId || 'all'}`}
            sectionIds={config.sectionIds}
            categoryGroups={categoryGroups}
            defaultCategory={config.defaultCategory}
            categorizePath={config.categorizePath}
            documentTitle={config.documentTitle}
            documentFilter={documentFilter}
            syntheticDocs={repoDocs}
            syntheticPreviewField="inlineContent"
            className="lab-documents-browser storage-documents-browser lab-documents-hub__browser catalog-space-browser"
            topPanel={
              activeZoneId ? (
                <p className="lab-doc-hub-filter-note text-footnote">
                  Showing: <strong>{LAB_DOCUMENT_ZONES.find((z) => z.id === activeZoneId)?.label}</strong>
                  {' · '}
                  <button type="button" className="btn-link" onClick={() => setActiveZoneId(null)}>
                    Show all lab files
                  </button>
                </p>
              ) : (
                <p className="lab-doc-hub-filter-note text-footnote muted">
                  <FileCode2 size={13} aria-hidden /> Storage inventories, orders, and meetings live here.
                  Onboarding, guidelines, and permits are under{' '}
                  <button type="button" className="btn-link" onClick={() => onNavigate?.('overview', 'onboarding')}>
                    Overview
                  </button>
                  .
                </p>
              )
            }
            folderHintResolver={sectionLabelForHub}
          />
        </>
      )}
    </div>
  );
}
