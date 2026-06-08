import { useCallback, useEffect, useMemo, useState } from 'react';
import { BookOpen, FileText } from 'lucide-react';
import { technicalNotebook } from '@/data/technicalNotebook.js';
import { technicalWiki } from '@/data/technicalWiki.js';
import ResearchAssistPanel from './ResearchAssistPanel.jsx';
import './ResearchAssistPanel.css';

export default function NotebookWikiPanel({
  dbProjects = [],
  API_URL,
  projectCode = null,
  embedded = false,
  defaultSubTab = 'notebook',
  onOpenLogTab,
  onNavigate,
  onSelectProject,
}) {
  const [notebookEntries, setNotebookEntries] = useState([]);
  const [wikiDocs, setWikiDocs] = useState([]);
  const [subTab, setSubTab] = useState(defaultSubTab);
  const [selectedNotebook, setSelectedNotebook] = useState(null);
  const [selectedWiki, setSelectedWiki] = useState(null);
  const [wikiSearch, setWikiSearch] = useState('');
  const [usingApi, setUsingApi] = useState(false);
  const [aiDraft, setAiDraft] = useState(null);

  const fetchNotebook = useCallback(async () => {
    const fallback = () => {
      const data = (Array.isArray(technicalNotebook) ? technicalNotebook : []).filter(
        (e) => !projectCode || e.project_code === projectCode,
      );
      setNotebookEntries(data);
      setSelectedNotebook((prev) => {
        if (prev && data.some((e) => e.entry_id === prev.entry_id)) return prev;
        return data[0] || null;
      });
      setUsingApi(false);
    };

    if (!API_URL) {
      fallback();
      return;
    }

    try {
      const query = projectCode ? `?project_code=${encodeURIComponent(projectCode)}` : '';
      const res = await fetch(`${API_URL}/notebook${query}`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          setNotebookEntries(data);
          setSelectedNotebook((prev) => {
            if (prev && data.some((e) => e.entry_id === prev.entry_id)) return prev;
            return data[0] || null;
          });
          setUsingApi(true);
          return;
        }
      }
    } catch (e) {
      console.warn('Notebook API unavailable, using static corpus', e);
    }
    fallback();
  }, [API_URL, projectCode]);

  const fetchWiki = useCallback(() => {
    const data = Array.isArray(technicalWiki) ? technicalWiki : [];
    setWikiDocs(data);
    setSelectedWiki((prev) => prev && data.some((w) => w.wiki_id === prev.wiki_id) ? prev : data[0] || null);
  }, []);

  useEffect(() => {
    fetchNotebook();
    fetchWiki();
  }, [fetchNotebook, fetchWiki]);

  const filteredWiki = useMemo(
    () =>
      wikiDocs.filter(
        (w) =>
          w.title.toLowerCase().includes(wikiSearch.toLowerCase()) ||
          w.content.toLowerCase().includes(wikiSearch.toLowerCase()),
      ),
    [wikiDocs, wikiSearch],
  );

  return (
    <div className={`notebook-wiki-panel${embedded ? ' notebook-wiki-panel--embedded' : ''}`}>
      {embedded && projectCode ? (
        <p className="notebook-wiki-panel__lead text-footnote muted">
          Structured notebook entries for <strong>{projectCode}</strong>
          {usingApi ? ' (live register)' : ' (static corpus until API entries exist)'}.
          {onOpenLogTab ? (
            <>
              {' '}
              <button type="button" className="btn btn-sm btn-ghost" onClick={onOpenLogTab}>
                Open on-disk project log
              </button>
            </>
          ) : null}
        </p>
      ) : null}

      <div className="tabs-header notebook-wiki-panel__tabs">
        <button
          type="button"
          className={`tab-button ${subTab === 'notebook' ? 'active' : ''}`}
          onClick={() => setSubTab('notebook')}
        >
          Lab notebook logs
        </button>
        <button
          type="button"
          className={`tab-button ${subTab === 'wiki' ? 'active' : ''}`}
          onClick={() => setSubTab('wiki')}
        >
          Protocols wiki SOPs
        </button>
      </div>

      {subTab === 'notebook' && (
        <div className={projectCode ? 'research-assist-panel__layout' : ''}>
        <div className="notebook-wiki-panel__grid">
          <div className="panel">
            <h3 className="panel-title">
              <BookOpen size={18} /> {projectCode ? `${projectCode} logs` : 'Notebook logs'}
            </h3>
            <div className="notebook-wiki-panel__list">
              {notebookEntries.map((e) => (
                <button
                  key={e.entry_id}
                  type="button"
                  className={`sidebar-item notebook-wiki-panel__list-item${selectedNotebook?.entry_id === e.entry_id ? ' active' : ''}`}
                  onClick={() => setSelectedNotebook(e)}
                >
                  <span className="notebook-wiki-panel__list-title">{e.title}</span>
                  <span className="notebook-wiki-panel__list-meta">
                    {e.project_code} · {String(e.created_at || '').slice(0, 10)}
                  </span>
                </button>
              ))}
              {notebookEntries.length === 0 ? (
                <p className="text-footnote muted">No notebook entries for this scope.</p>
              ) : null}
            </div>
          </div>

          <div className="panel">
            <h3 className="panel-title">
              <FileText size={18} /> Log details
            </h3>
            {selectedNotebook ? (
              <div className="notebook-wiki-panel__detail">
                <h2 className="notebook-wiki-panel__detail-title">{selectedNotebook.title}</h2>
                <p className="text-footnote muted">
                  {selectedNotebook.project_code} · v{selectedNotebook.version || 1} ·{' '}
                  {String(selectedNotebook.created_at || '').replace('T', ' ').slice(0, 16)}
                </p>
                <div className="notebook-wiki-panel__content surface-inset">{selectedNotebook.content}</div>
                {selectedNotebook.conclusions ? (
                  <div className="notebook-wiki-panel__callout notebook-wiki-panel__callout--ok">
                    <h5>Conclusions</h5>
                    <p>{selectedNotebook.conclusions}</p>
                  </div>
                ) : null}
                {selectedNotebook.issues_found ? (
                  <div className="notebook-wiki-panel__callout notebook-wiki-panel__callout--warn">
                    <h5>Issues found</h5>
                    <p>{selectedNotebook.issues_found}</p>
                  </div>
                ) : null}
                {selectedNotebook.next_steps ? (
                  <div className="notebook-wiki-panel__callout notebook-wiki-panel__callout--next">
                    <h5>Next steps</h5>
                    <p>{selectedNotebook.next_steps}</p>
                  </div>
                ) : null}
              </div>
            ) : (
              <p className="text-footnote muted">Select a log to view details.</p>
            )}
          </div>
        </div>

        {projectCode ? (
          <div className="stack-sm">
            <ResearchAssistPanel
              mode="notebook"
              projectCode={projectCode}
              entryContext={selectedNotebook}
              onApplySuggestion={(parsed) => setAiDraft(parsed)}
              onNavigate={onNavigate}
              onSelectProject={onSelectProject}
            />
            {aiDraft ? (
              <div className="panel notebook-wiki-panel__ai-draft">
                <h4 className="panel-title">AI draft (copy into project log)</h4>
                {aiDraft.content ? <p><strong>Observations:</strong> {aiDraft.content}</p> : null}
                {aiDraft.conclusions ? <p><strong>Conclusions:</strong> {aiDraft.conclusions}</p> : null}
                {aiDraft.issues ? <p><strong>Issues:</strong> {aiDraft.issues}</p> : null}
                {aiDraft.nextSteps ? <p><strong>Next steps:</strong> {aiDraft.nextSteps}</p> : null}
                {onOpenLogTab ? (
                  <button type="button" className="btn btn-sm btn-secondary" onClick={onOpenLogTab}>
                    Open on-disk project log
                  </button>
                ) : null}
              </div>
            ) : null}
          </div>
        ) : null}
        </div>
      )}

      {subTab === 'wiki' && (
        <div className="notebook-wiki-panel__grid">
          <div className="panel">
            <h3 className="panel-title">
              <BookOpen size={18} /> Protocols wiki
            </h3>
            <input
              type="text"
              placeholder="Search wiki articles…"
              className="form-input"
              value={wikiSearch}
              onChange={(e) => setWikiSearch(e.target.value)}
            />
            <div className="notebook-wiki-panel__list">
              {filteredWiki.map((w) => (
                <button
                  key={w.wiki_id}
                  type="button"
                  className={`sidebar-item notebook-wiki-panel__list-item${selectedWiki?.wiki_id === w.wiki_id ? ' active' : ''}`}
                  onClick={() => setSelectedWiki(w)}
                >
                  <span className="notebook-wiki-panel__list-title">{w.title}</span>
                  <span className="notebook-wiki-panel__list-meta">
                    {w.wiki_type || 'SOP'} · rev {w.revision || 1}
                  </span>
                </button>
              ))}
            </div>
          </div>

          <div className="panel">
            <h3 className="panel-title">
              <FileText size={18} /> Wiki content
            </h3>
            {selectedWiki ? (
              <div className="notebook-wiki-panel__detail">
                <h2 className="notebook-wiki-panel__detail-title">{selectedWiki.title}</h2>
                <p className="text-footnote muted">
                  {selectedWiki.wiki_type || 'SOP'} · rev {selectedWiki.revision || 1}
                </p>
                <div className="notebook-wiki-panel__content surface-inset">{selectedWiki.content}</div>
              </div>
            ) : (
              <p className="text-footnote muted">Select a wiki article.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
