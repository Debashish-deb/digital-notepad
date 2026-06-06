import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { BookOpen, ChevronDown, Pencil, Save, X } from 'lucide-react';
import { findProjectLogFile } from '../utils/projectLogUtils.js';
import { fetchProjectLogContent } from '../utils/projectLogContent.js';
import { inferExtension } from '../utils/fileTypeMeta.js';
import { apiGet, apiPost } from '../api/client.js';

const EDITABLE_EXTS = new Set(['.md', '.txt', '.html', '.rtf']);

function CodeBlock({ code, lang }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="log-code-block-container">
      <div className="log-code-block-header">
        <span className="log-code-block-lang">{lang || 'code'}</span>
        <button type="button" className="log-code-block-copy" onClick={handleCopy}>
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <pre className="log-code-block">
        <code>{code}</code>
      </pre>
    </div>
  );
}

export default function ProjectLogPanel({ twin, projectCode, API_URL }) {
  const logFile = useMemo(() => findProjectLogFile(twin), [twin]);

  const [rawContent, setRawContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [draftContent, setDraftContent] = useState('');
  const [saving, setSaving] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [scrollThroughActive, setScrollThroughActive] = useState(false);
  const [contentSource, setContentSource] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [toast, setToast] = useState(null);

  const scrollRef = useRef(null);

  // Show status toasts
  const showToast = useCallback((message, tone = 'info') => {
    setToast({ message, tone });
    window.setTimeout(() => setToast(null), 4000);
  }, []);

  // Fetch full log file contents
  const fetchContent = useCallback(async () => {
    if (!logFile?.path) return;
    setLoading(true);
    setLoadError(null);
    try {
      const result = await fetchProjectLogContent({
        projectCode,
        logFile,
        twin,
        API_URL,
      });
      setRawContent(result.content || '');
      setContentSource(result.source || null);
      if (!result.content) {
        setLoadError('Project log file is indexed but has no readable text yet. Rescan the project folder.');
      }
    } catch (e) {
      console.error('Failed to load full project log content:', e);
      setLoadError(e.message || 'Failed to load project log.');
    } finally {
      setLoading(false);
    }
  }, [projectCode, logFile, twin, API_URL]);

  useEffect(() => {
    fetchContent();
  }, [fetchContent]);

  // Real-time synchronization event listener (e.g. from Taskpad edits)
  useEffect(() => {
    const handleRemoteUpdate = (e) => {
      const { projectCode: pCode, relativePath, content } = e.detail;
      if (
        pCode === projectCode &&
        relativePath === logFile?.path &&
        content !== undefined
      ) {
        setRawContent(content);
      }
    };

    window.addEventListener('project-log-updated', handleRemoteUpdate);
    return () => {
      window.removeEventListener('project-log-updated', handleRemoteUpdate);
    };
  }, [projectCode, logFile?.path]);

  // Slow scroll through the full log when the user presses "Scroll through log"
  useEffect(() => {
    if (!scrollThroughActive || editMode || !scrollRef.current || !rawContent) return;

    let animationFrameId;
    const scrollContainer = scrollRef.current;

    const step = () => {
      if (!scrollContainer) return;
      const maxScroll = scrollContainer.scrollHeight - scrollContainer.clientHeight;
      if (maxScroll <= 0) {
        setScrollThroughActive(false);
        return;
      }
      if (scrollContainer.scrollTop >= maxScroll - 1) {
        setScrollThroughActive(false);
        return;
      }
      scrollContainer.scrollTop += 0.45;
      animationFrameId = requestAnimationFrame(step);
    };

    animationFrameId = requestAnimationFrame(step);
    return () => cancelAnimationFrame(animationFrameId);
  }, [scrollThroughActive, editMode, rawContent]);

  const startScrollThrough = () => {
    if (!scrollRef.current) return;
    setIsPaused(true);
    setScrollThroughActive(true);
    scrollRef.current.scrollTop = 0;
  };

  const stopScrollThrough = () => {
    setScrollThroughActive(false);
  };

  // Parse raw text into structured log entries
  const logEntries = useMemo(() => {
    if (!rawContent) return [];
    
    // Split entries by markdown headers (H1, H2, H3)
    const sections = rawContent.split(/(?=^#{1,4} )/m);
    const parsed = [];

    sections.forEach((sec, idx) => {
      const trimmed = sec.trim();
      if (!trimmed) return;

      const lines = trimmed.split('\n');
      let header = lines[0].replace(/^#{1,4}\s+/, '').trim();
      let body = lines.slice(1).join('\n').trim();

      if (!lines[0].startsWith('#')) {
        header = `Log Entry ${idx + 1}`;
        body = trimmed;
      }

      // Deduce category based on content keywords
      let category = 'general';
      const lowerBody = body.toLowerCase();
      
      if (
        lowerBody.includes('```') || 
        lowerBody.includes('code') || 
        lowerBody.includes('run') || 
        lowerBody.includes('script') || 
        lowerBody.includes('api')
      ) {
        category = 'code';
      } else if (
        lowerBody.includes('link') || 
        lowerBody.includes('url') || 
        lowerBody.includes('http') || 
        lowerBody.includes('href')
      ) {
        category = 'links-resources';
      } else if (
        lowerBody.includes('error') || 
        lowerBody.includes('fail') || 
        lowerBody.includes('fix') || 
        lowerBody.includes('debug') || 
        lowerBody.includes('bug')
      ) {
        category = 'debug';
      } else if (
        lowerBody.includes('result') || 
        lowerBody.includes('plot') || 
        lowerBody.includes('fig') || 
        lowerBody.includes('analysis') || 
        lowerBody.includes('output') || 
        lowerBody.includes('metric')
      ) {
        category = 'analysis';
      } else if (
        lowerBody.includes('plan') || 
        lowerBody.includes('todo') || 
        lowerBody.includes('step') || 
        lowerBody.includes('milestone') || 
        lowerBody.includes('task')
      ) {
        category = 'planning';
      }

      // Extract code blocks
      const codeBlocks = [];
      const codeRegex = /```(\w*)\n([\s\S]*?)```/g;
      let match;
      while ((match = codeRegex.exec(body)) !== null) {
        codeBlocks.push({
          lang: match[1] || 'code',
          code: match[2].trim(),
        });
      }

      // Clean body text (strip code blocks from description body)
      const cleanBody = body.replace(/```(\w*)\n([\s\S]*?)```/g, '').trim();

      parsed.push({
        id: idx,
        header,
        body: cleanBody,
        category,
        codeBlocks,
      });
    });

    return parsed;
  }, [rawContent]);

  if (!logFile) {
    return (
      <section className="panel project-log-panel">
        <h3 className="text-title-3" style={{ margin: '0 0 0.5rem' }}>
          <BookOpen size={18} style={{ verticalAlign: 'middle', marginRight: '0.35rem' }} />
          Project Log
        </h3>
        <p className="text-footnote muted" style={{ margin: 0 }}>
          No project log file found. Add a file named <code>*_Project_log.md</code> at the project
          root to start a living log editable in Taskpad.
        </p>
      </section>
    );
  }

  const ext = inferExtension(logFile.name, logFile.extension);
  const editable = EDITABLE_EXTS.has(ext);

  const startInlineEdit = () => {
    setDraftContent(rawContent);
    setEditMode(true);
  };

  const handleSaveInline = async () => {
    setSaving(true);
    try {
      await apiPost(`/api/project-files/write`, {
        body: {
          project_code: projectCode,
          relative_path: logFile.path,
          content: draftContent,
        },
      });

      setRawContent(draftContent);
      setEditMode(false);
      showToast('Changes saved successfully', 'success');

      // Dispatch sync event so Taskpad or other tabs refresh immediately
      window.dispatchEvent(
        new CustomEvent('project-log-updated', {
          detail: {
            projectCode,
            relativePath: logFile.path,
            content: draftContent,
          },
        })
      );
    } catch (e) {
      showToast(`Error saving: ${e.message}`, 'error');
    } finally {
      setSaving(false);
    }
  };

  // Render text blocks containing inline ticks and markdown link pills
  const renderFormattedLine = (line, lineIdx) => {
    const trimmed = line.trim();
    if (!trimmed) return <div key={lineIdx} style={{ height: '0.35rem' }} />;

    if (trimmed.startsWith('>')) {
      return (
        <blockquote key={lineIdx} className="log-blockquote">
          {renderInlineTokens(trimmed.substring(1).trim())}
        </blockquote>
      );
    }

    if (trimmed.startsWith('-') || trimmed.startsWith('*') || /^\d+\./.test(trimmed)) {
      const bulletContent = trimmed.replace(/^[-*]|\d+\./, '').trim();
      return (
        <ul key={lineIdx} className="log-list">
          <li>{renderInlineTokens(bulletContent)}</li>
        </ul>
      );
    }

    return (
      <p key={lineIdx} className="log-paragraph">
        {renderInlineTokens(line)}
      </p>
    );
  };

  const renderInlineTokens = (text) => {
    const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
    const tokens = [];
    let lastIndex = 0;
    let match;

    const renderTicks = (str, keyPrefix) => {
      const codeRegex = /`([^`]+)`/g;
      const ticks = [];
      let lastTickIdx = 0;
      let tickMatch;

      while ((tickMatch = codeRegex.exec(str)) !== null) {
        if (tickMatch.index > lastTickIdx) {
          ticks.push(str.substring(lastTickIdx, tickMatch.index));
        }
        ticks.push(
          <code key={`${keyPrefix}-tick-${tickMatch.index}`} className="log-code-inline">
            {tickMatch[1]}
          </code>
        );
        lastTickIdx = codeRegex.lastIndex;
      }

      if (lastTickIdx < str.length) {
        ticks.push(str.substring(lastTickIdx));
      }
      return ticks.length > 0 ? ticks : str;
    };

    let idx = 0;
    while ((match = linkRegex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        tokens.push(...[].concat(renderTicks(text.substring(lastIndex, match.index), `txt-${idx++}`)));
      }
      tokens.push(
        <a
          key={`link-${match.index}`}
          href={match[2]}
          target="_blank"
          rel="noopener noreferrer"
          className="log-link-pill"
        >
          🔗 {match[1]}
        </a>
      );
      lastIndex = linkRegex.lastIndex;
    }

    if (lastIndex < text.length) {
      tokens.push(...[].concat(renderTicks(text.substring(lastIndex), `txt-${idx++}`)));
    }

    return tokens.length > 0 ? tokens : text;
  };

  return (
    <section className="panel project-log-panel">
      <div className="project-log-panel-header">
        <div>
          <h3 className="text-title-3" style={{ margin: '0 0 0.15rem', display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
            <BookOpen size={18} />
            <span>Project Log Stream</span>
          </h3>
          <span className="text-caption muted">
            {logFile.name}
            {contentSource && contentSource !== 'disk_text' && contentSource !== 'live_extract'
              ? ` · restored from ${contentSource.replace(/_/g, ' ')}`
              : ''}
            {!editable ? ' (preview only — convert to .md to edit on disk)' : ''}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', flexWrap: 'wrap' }}>
          {!editMode && rawContent && logEntries.length > 0 ? (
            scrollThroughActive ? (
              <button type="button" className="btn btn-secondary btn-sm" onClick={stopScrollThrough}>
                <X size={13} aria-hidden /> Stop scroll
              </button>
            ) : (
              <button type="button" className="btn btn-secondary btn-sm" onClick={startScrollThrough}>
                <ChevronDown size={13} aria-hidden /> Scroll through log
              </button>
            )
          ) : null}

          {editable && (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={editMode ? () => setEditMode(false) : startInlineEdit}
            >
              {editMode ? <X size={13} /> : <Pencil size={13} />}
              {editMode ? ' Cancel' : ' Quick edit'}
            </button>
          )}
        </div>
      </div>

      {toast && (
        <div className={`datapad-toast tone-${toast.tone}`} style={{ position: 'absolute', top: '4.5rem', right: '1.5rem', zIndex: 10 }}>
          {toast.message}
        </div>
      )}

      {loadError && !loading && !rawContent ? (
        <p className="text-footnote project-log-panel__error" style={{ margin: '1rem 0 0' }}>
          {loadError}
        </p>
      ) : null}

      {loading ? (
        <div className="text-loading" style={{ margin: '2rem 0' }}>Loading activity log stream...</div>
      ) : editMode ? (
        /* Inline log file editor with quick save keys */
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <textarea
            className="log-inline-textarea"
            value={draftContent}
            onChange={(e) => setDraftContent(e.target.value)}
            placeholder="# Project Log ... Write markdown here"
          />
          <div className="log-edit-hint">
            <Save size={13} /> Write markdown logs directly. Click Save to immediately sync revisions.
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.25rem' }}>
            <button
              type="button"
              className="btn btn-success"
              onClick={handleSaveInline}
              disabled={saving}
            >
              Save Revisions to Disk
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setEditMode(false)}
            >
              Discard
            </button>
          </div>
        </div>
      ) : logEntries.length > 0 ? (
        /* Live Streaming timeline viewport */
        <div
          ref={scrollRef}
          className="log-scroller-viewport"
          onMouseEnter={() => setIsPaused(true)}
          onMouseLeave={() => setIsPaused(false)}
          title="Hover to pause. Use Scroll through log to read the full activity stream."
        >
          <div className="log-scroller-content">
            {logEntries.map((entry) => {
              const catClass = entry.category;
              const catLabel = entry.category.replace('-', ' ');

              return (
                <div key={entry.id} className="log-card">
                  <div className="log-card-header">
                    <h4 className="log-card-title">{entry.header}</h4>
                    <span className={`log-category-badge ${catClass}`}>
                      {catLabel}
                    </span>
                  </div>
                  
                  {entry.body && (
                    <div className="log-card-body">
                      {entry.body.split('\n').map((line, lineIdx) => renderFormattedLine(line, lineIdx))}
                    </div>
                  )}

                  {entry.codeBlocks?.map((block, bIdx) => (
                    <CodeBlock key={bIdx} code={block.code} lang={block.lang} />
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="panel text-empty" style={{ margin: '1rem 0' }}>
          <p>
            The project log file <code>{logFile.name}</code> has no displayable content yet.
            Use the Data Pad editor below or rescan the project folder.
          </p>
        </div>
      )}
    </section>
  );
}
