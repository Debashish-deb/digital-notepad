import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  BookOpen,
  Bot,
  Check,
  Clipboard,
  Cpu,
  Database,
  FileText,
  Layers,
  Loader2,
  Sparkles,
  UploadCloud,
} from 'lucide-react';
import ChatWidget from '../components/ChatWidget.jsx';
import AiAssistant3DScene from '../components/AiAssistant3DScene.jsx';
import { apiFetch } from '../api/client.js';

const FALLBACK_PROJECTS = ['SPACE', 'EyeMT', 'KRAS'];

function normalizeProjectCode(project) {
  if (typeof project === 'string') return project;
  return project?.project_code || project?.code || project?.id || '';
}

function getProjectOptions(dbProjects = []) {
  const fromDb = dbProjects.map(normalizeProjectCode).filter(Boolean);
  return Array.from(new Set([...fromDb, ...FALLBACK_PROJECTS]));
}

function statusToneFromMessage(message) {
  const text = String(message || '').toLowerCase();
  if (!text) return 'neutral';
  if (text.includes('failed') || text.includes('error') || text.includes('expired') || text.includes('unauthorized')) return 'danger';
  if (text.includes('success') || text.includes('indexed') || text.includes('completed')) return 'success';
  if (text.includes('stored only') || text.includes('queued')) return 'warning';
  return 'neutral';
}

export default function AiLabAssistantScreen({
  API_URL,
  activeSubTab,
  hideChrome = false,
  dbProjects = [],
  onNavigate,
  onSelectProject,
  onOpenSearch,
}) {
  const [subTab, setSubTab] = useState(activeSubTab || 'copilot');
  const [models, setModels] = useState([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [modelsError, setModelsError] = useState('');

  const [docTitle, setDocTitle] = useState('');
  const [docContent, setDocContent] = useState('');
  const [docProject, setDocProject] = useState('SPACE');
  const [ingesting, setIngesting] = useState(false);
  const [ingestStatus, setIngestStatus] = useState('');

  const projectOptions = useMemo(() => getProjectOptions(dbProjects), [dbProjects]);

  useEffect(() => {
    if (activeSubTab) setSubTab(activeSubTab);
  }, [activeSubTab]);

  useEffect(() => {
    if (!projectOptions.includes(docProject)) {
      setDocProject(projectOptions[0] || 'SPACE');
    }
  }, [docProject, projectOptions]);

  const fetchModels = useCallback(async () => {
    setLoadingModels(true);
    setModelsError('');

    try {
      const data = await apiFetch('/ai-models');
      setModels(Array.isArray(data) ? data : data?.models || []);
    } catch (error) {
      console.error('[AiLabAssistantScreen] Failed to fetch model registry:', error);
      setModelsError(
        error?.status === 401 || error?.status === 403
          ? 'Your session expired or you do not have permission to view model records.'
          : error?.message || 'Could not load model registry.',
      );
    } finally {
      setLoadingModels(false);
    }
  }, []);

  useEffect(() => {
    if (subTab === 'models') {
      fetchModels();
    }
  }, [fetchModels, subTab]);

  const handleIngest = useCallback(
    async (event) => {
      event.preventDefault();

      const cleanTitle = docTitle.trim();
      const cleanText = docContent.trim();

      if (!cleanTitle || !cleanText || ingesting) return;

      setIngesting(true);
      setIngestStatus('Queued document for parsing, chunking, embedding, and vector indexing…');

      try {
        const data = await apiFetch('/ingest-document', {
          method: 'POST',
          body: {
            project_code: docProject,
            filename: cleanTitle,
            file_type: 'txt',
            extracted_text: cleanText,
          },
        });

        const chunkCount = data?.chunk_count ?? data?.chunks_indexed ?? data?.indexed_chunks ?? 0;
        const indexed =
          data?.indexed === true ||
          data?.status === 'indexed' ||
          data?.status === 'completed' ||
          (data?.status === 'success' && Number(chunkCount) > 0);

        if (indexed) {
          setIngestStatus(
            `Success — document indexed for RAG retrieval.\nChunks indexed: ${chunkCount || 'reported by backend'}\nCollection: ${data?.qdrant_collection || data?.collection || 'doc_chunks'}`,
          );
          setDocTitle('');
          setDocContent('');
        } else if (data?.status === 'queued') {
          setIngestStatus(`Queued — backend accepted the document. Ingestion ID: ${data?.ingestion_id || data?.doc_id || 'pending'}`);
        } else if (data?.status === 'stored_only') {
          setIngestStatus('Stored only — backend saved the text but did not confirm vector indexing.');
        } else {
          setIngestStatus(`Completed with unknown indexing status: ${data?.status || 'unknown'}`);
        }
      } catch (error) {
        setIngestStatus(
          error?.status === 401 || error?.status === 403
            ? 'Your session expired or unauthorized. Please sign in again.'
            : `Connection error: ${error?.message || 'Unknown backend error'}`,
        );
      } finally {
        setIngesting(false);
      }
    },
    [docContent, docProject, docTitle, ingesting],
  );

  const menuItems = [
    {
      id: 'copilot',
      label: 'Chat Copilot',
      desc: 'Ask indexed lab memory',
      icon: Bot,
    },
    {
      id: 'prompts',
      label: 'Prompt Templates',
      desc: 'Writing and analysis helpers',
      icon: BookOpen,
    },
    {
      id: 'ingest',
      label: 'Ingest RAG Docs',
      desc: 'Chunk, embed, index',
      icon: UploadCloud,
    },
    {
      id: 'models',
      label: 'Model Registry',
      desc: 'AI tools and hardware',
      icon: Cpu,
    },
  ];

  const heroStats = useMemo(
    () => [
      { label: 'Services', value: menuItems.length },
      { label: 'Projects', value: projectOptions.length },
      { label: 'Mode', value: subTab === 'copilot' ? 'Live' : 'Tools' },
    ],
    [menuItems.length, projectOptions.length, subTab],
  );

  return (
    <section className={`ai-lab-assistant${hideChrome ? ' ai-lab-assistant--embedded' : ''}`}>
      {!hideChrome && (
        <aside className="ai-lab-rail" aria-label="AI assistant services">
          <AiAssistant3DScene
            title="AI Lab Assistant"
            subtitle="A 3D command center for RAG search, document indexing, prompt workflows, and model intelligence."
            stats={heroStats}
            compact
            className="ai-lab-rail-hero"
          />

          <div className="ai-lab-rail-label">Assistant services</div>

          <nav className="ai-lab-menu">
            {menuItems.map((item) => {
              const Icon = item.icon;
              const active = subTab === item.id;

              return (
                <button
                  key={item.id}
                  type="button"
                  className={`ai-lab-menu-item${active ? ' active' : ''}`}
                  onClick={() => setSubTab(item.id)}
                  aria-current={active ? 'page' : undefined}
                >
                  <span className="ai-lab-menu-item__icon">
                    <Icon size={17} aria-hidden="true" />
                  </span>
                  <span className="ai-lab-menu-item__copy">
                    <strong>{item.label}</strong>
                    <small>{item.desc}</small>
                  </span>
                </button>
              );
            })}
          </nav>
        </aside>
      )}

      <main className="ai-lab-main">
        {hideChrome && subTab === 'copilot' ? null : (
          <div className="ai-lab-top-hero">
            <AiAssistant3DScene
              title={
                subTab === 'copilot'
                  ? 'Research Copilot'
                  : subTab === 'ingest'
                    ? 'RAG Document Indexer'
                    : subTab === 'models'
                      ? 'Deep Learning Registry'
                      : 'Prompt Engineering Library'
              }
              subtitle={
                subTab === 'copilot'
                  ? 'Ask questions across Qdrant vectors, database counts, and lab knowledge.'
                  : subTab === 'ingest'
                    ? 'Paste or prepare protocols, scripts, and SOP text for vector retrieval.'
                    : subTab === 'models'
                      ? 'Track model families, frameworks, tasks, and target compute environments.'
                      : 'Reusable expert prompts for manuscript writing, logbooks, code review, and analysis.'
              }
              stats={heroStats}
              compact
            />
          </div>
        )}

        {subTab === 'copilot' && (
          <ChatWidget
            dbProjects={dbProjects}
            API_URL={API_URL}
            onNavigate={onNavigate}
            onSelectProject={onSelectProject}
            onOpenSearch={onOpenSearch}
          />
        )}
        {subTab === 'prompts' && <PromptsLibraryTab />}

        {subTab === 'ingest' && (
          <section className="ai-lab-tab-panel">
            <div className="page-header ai-lab-page-header">
              <span className="assistant-eyebrow">
                <Database size={14} aria-hidden="true" />
                Vector memory
              </span>
              <h2>Ingest & index RAG documents</h2>
              <p>Paste SOP protocols, scripts, methods notes, or manual transcripts into the authenticated RAG pipeline.</p>
            </div>

            <div className="panel ai-ingest-panel">
              <div className="ai-panel-title-row">
                <h3 className="panel-title">
                  <UploadCloud size={18} aria-hidden="true" />
                  Document vector ingestion
                </h3>
                <span className="ai-status-pill">
                  <Sparkles size={13} aria-hidden="true" />
                  Qdrant-ready
                </span>
              </div>

              <form onSubmit={handleIngest} className="ai-ingest-form">
                <div className="form-group">
                  <label className="form-label" htmlFor="ai-doc-project">Scope project code</label>
                  <select
                    id="ai-doc-project"
                    className="form-select"
                    value={docProject}
                    onChange={(event) => setDocProject(event.target.value)}
                  >
                    {projectOptions.map((code) => (
                      <option key={code} value={code}>{code}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="ai-doc-title">Document title</label>
                  <input
                    id="ai-doc-title"
                    type="text"
                    className="form-input"
                    required
                    value={docTitle}
                    onChange={(event) => setDocTitle(event.target.value)}
                    placeholder="e.g. GeoMx staining protocol batch 4"
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="ai-doc-content">Raw text content</label>
                  <textarea
                    id="ai-doc-content"
                    className="form-textarea ai-ingest-textarea"
                    value={docContent}
                    onChange={(event) => setDocContent(event.target.value)}
                    rows={10}
                    required
                    placeholder="Paste full document, SOP, protocol, code notes, or manual transcript here..."
                  />
                </div>

                <div className="ai-ingest-actions">
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={ingesting || !docTitle.trim() || !docContent.trim()}
                  >
                    {ingesting ? <Loader2 size={16} className="spin" aria-hidden="true" /> : <UploadCloud size={16} aria-hidden="true" />}
                    {ingesting ? 'Indexing…' : 'Run vector ingestion'}
                  </button>

                  <span className="ai-ingest-hint">
                    Text is sent through the authenticated backend. Success only means indexed if backend confirms chunks.
                  </span>
                </div>
              </form>

              {ingestStatus && (
                <div className={`ai-ingest-status ai-ingest-status--${statusToneFromMessage(ingestStatus)}`}>
                  {statusToneFromMessage(ingestStatus) === 'danger' ? (
                    <AlertTriangle size={16} aria-hidden="true" />
                  ) : statusToneFromMessage(ingestStatus) === 'success' ? (
                    <Check size={16} aria-hidden="true" />
                  ) : (
                    <Layers size={16} aria-hidden="true" />
                  )}
                  <span>{ingestStatus}</span>
                </div>
              )}
            </div>
          </section>
        )}

        {subTab === 'models' && (
          <section className="ai-lab-tab-panel">
            <div className="page-header ai-lab-page-header">
              <span className="assistant-eyebrow">
                <Cpu size={14} aria-hidden="true" />
                Registry
              </span>
              <h2>Deep learning model registry</h2>
              <p>Overview of neural network models active on local workstations, servers, and regional cluster environments.</p>
            </div>

            <div className="panel ai-models-panel">
              <div className="ai-panel-title-row">
                <h3 className="panel-title">
                  <Cpu size={18} aria-hidden="true" />
                  Active models
                </h3>

                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={fetchModels}
                  disabled={loadingModels}
                >
                  {loadingModels ? <Loader2 size={14} className="spin" aria-hidden="true" /> : <Database size={14} aria-hidden="true" />}
                  Refresh
                </button>
              </div>

              {loadingModels ? (
                <div className="ai-empty-state">
                  <Loader2 size={26} className="spin" aria-hidden="true" />
                  <p>Loading registry records…</p>
                </div>
              ) : modelsError ? (
                <div className="ai-empty-state ai-empty-state--danger">
                  <AlertTriangle size={26} aria-hidden="true" />
                  <p>{modelsError}</p>
                </div>
              ) : models.length === 0 ? (
                <div className="ai-empty-state">
                  <FileText size={28} aria-hidden="true" />
                  <p>No AI models registered in PostgreSQL schemas.</p>
                </div>
              ) : (
                <div className="ai-model-card-grid">
                  {models.map((model) => (
                    <article key={model.model_id || `${model.model_name}-${model.version}`} className="ai-model-card">
                      <div className="ai-model-card__header">
                        <div>
                          <h4>🤖 {model.model_name}</h4>
                          <p>v{model.version || 'unknown'}</p>
                        </div>
                        <span>{model.framework || 'framework n/a'}</span>
                      </div>

                      <p className="ai-model-card__desc">{model.description || 'No description recorded.'}</p>

                      <div className="ai-model-card__meta">
                        <div>Task area: <strong>{model.task_type || 'unknown'}</strong></div>
                        <div>Target environment: <code>{model.target_hardware || 'not specified'}</code></div>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </div>
          </section>
        )}
      </main>
    </section>
  );
}

function PromptsLibraryTab() {
  const [copiedIndex, setCopiedIndex] = useState(null);

  const prompts = [
    {
      title: 'Paper abstract improver',
      icon: '✍️',
      desc: 'Paste raw results, cohort counts, and spatial findings to generate a professional abstract.',
      prompt:
        'Act as an expert bioinformatician and clinical-spatial oncology scientist. Review the following raw research observations and draft a cohesive, highly structured abstract suitable for EACR/AACR. Structure: Background, Methods, Results with statistics, and Conclusions.',
    },
    {
      title: 'Code script refactoring',
      icon: '⚙️',
      desc: 'Optimize Python or R scripts for memory, parallelism, readability, and reproducibility.',
      prompt:
        'Analyze the following Python/R script for cell phenotyping or spatial clustering. Optimize it for large data arrays, add clear comments, modularize operations, and minimize memory pressure to prevent OOM errors.',
    },
    {
      title: 'Logbook summarizer',
      icon: '📓',
      desc: 'Compile meeting notes and lab updates into a clean system-of-record entry.',
      prompt:
        'Given these meeting updates and raw notebook items, synthesize them into one formal system-of-record note. Include: 1) what was discussed, 2) major gating or panel exclusions, 3) action checklist with assignees, and 4) timeline milestones.',
    },
  ];

  const copyPrompt = async (prompt, index) => {
    try {
      await navigator.clipboard.writeText(prompt);
      setCopiedIndex(index);
      window.setTimeout(() => setCopiedIndex(null), 1400);
    } catch {
      setCopiedIndex(null);
    }
  };

  return (
    <section className="ai-lab-tab-panel">
      <div className="page-header ai-lab-page-header">
        <span className="assistant-eyebrow">
          <Clipboard size={14} aria-hidden="true" />
          Prompt system
        </span>
        <h2>AI prompt engineering library</h2>
        <p>Templates to improve manuscript writing, computational workflows, and structured research documentation.</p>
      </div>

      <div className="ai-prompt-grid">
        {prompts.map((prompt, index) => (
          <article key={prompt.title} className="panel ai-prompt-card">
            <div className="ai-prompt-card__header">
              <span>{prompt.icon}</span>
              <div>
                <h4>{prompt.title}</h4>
                <p>{prompt.desc}</p>
              </div>
            </div>

            <div className="ai-prompt-template">
              <div className="ai-prompt-template__label">Prompt template</div>
              <p>{prompt.prompt}</p>

              <button
                type="button"
                className="btn btn-secondary btn-sm ai-copy-template-btn"
                onClick={() => copyPrompt(prompt.prompt, index)}
              >
                {copiedIndex === index ? <Check size={14} aria-hidden="true" /> : <Clipboard size={14} aria-hidden="true" />}
                {copiedIndex === index ? 'Copied' : 'Copy'}
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
