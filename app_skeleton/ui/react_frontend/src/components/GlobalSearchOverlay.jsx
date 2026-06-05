import React, { useState, useEffect, useRef } from 'react';
import { Search, X, Book, FileText, Scale, CheckSquare, ChevronDown, ChevronUp } from 'lucide-react';
import { apiGet } from '../api/client.js';

export default function GlobalSearchOverlay({ isOpen, onClose, API_URL }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState({ notebook: [], wiki: [], decisions: [], tasks: [] });
  const [loading, setLoading] = useState(false);
  const [expandedItem, setExpandedItem] = useState(null); // { type, id }
  const inputRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 100);
      setQuery('');
      setResults({ notebook: [], wiki: [], decisions: [], tasks: [] });
      setExpandedItem(null);
    }
  }, [isOpen]);

  useEffect(() => {
    if (!query.trim()) {
      setResults({ notebook: [], wiki: [], decisions: [], tasks: [] });
      return;
    }

    const delayDebounce = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await apiGet('/platform/search', {
          params: new URLSearchParams({ q: query })
        });
        if (data) {
          setResults({
            notebook: data.notebook || [],
            wiki: data.wiki || [],
            decisions: data.decisions || [],
            tasks: data.tasks || []
          });
        }
      } catch (err) {
        console.error('Search failed:', err);
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => clearTimeout(delayDebounce);
  }, [query]);

  if (!isOpen) return null;

  const totalResults = results.notebook.length + results.wiki.length + results.decisions.length + results.tasks.length;

  const toggleExpand = (type, id) => {
    if (expandedItem?.type === type && expandedItem?.id === id) {
      setExpandedItem(null);
    } else {
      setExpandedItem({ type, id });
    }
  };

  return (
    <div className="search-overlay-backdrop" onClick={onClose}>
      <style>{`
        .search-overlay-backdrop {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.75);
          backdrop-filter: blur(8px);
          z-index: 9999;
          display: flex;
          justify-content: center;
          align-items: flex-start;
          padding-top: 10vh;
        }
        .search-overlay-card {
          width: 90%;
          max-width: 650px;
          background: rgba(30, 30, 40, 0.95);
          border: 1px solid var(--border-color, #333);
          border-radius: 12px;
          box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
          overflow: hidden;
          color: #fff;
        }
        .search-input-container {
          display: flex;
          align-items: center;
          padding: 1rem;
          border-bottom: 1px solid var(--border-color, #333);
          gap: 0.75rem;
        }
        .search-input-field {
          flex: 1;
          background: transparent;
          border: none;
          color: #fff;
          font-size: 1.2rem;
          outline: none;
        }
        .search-close-btn {
          background: transparent;
          border: none;
          color: var(--text-muted, #888);
          cursor: pointer;
        }
        .search-close-btn:hover {
          color: #fff;
        }
        .search-results-container {
          max-height: 60vh;
          overflow-y: auto;
          padding: 1rem;
        }
        .search-section-title {
          font-size: 0.75rem;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          color: var(--color-primary, #6366f1);
          margin-bottom: 0.5rem;
          margin-top: 1rem;
          border-bottom: 1px dashed rgba(255, 255, 255, 0.1);
          padding-bottom: 0.25rem;
        }
        .search-section-title:first-of-type {
          margin-top: 0;
        }
        .search-item {
          display: flex;
          align-items: flex-start;
          gap: 0.75rem;
          padding: 0.75rem;
          border-radius: 8px;
          cursor: pointer;
          transition: background 0.2s;
          border-bottom: 1px solid rgba(255, 255, 255, 0.02);
        }
        .search-item:hover {
          background: rgba(255, 255, 255, 0.04);
        }
        .search-item-content {
          flex: 1;
        }
        .search-item-title {
          font-weight: 600;
          font-size: 0.95rem;
        }
        .search-item-meta {
          font-size: 0.75rem;
          color: var(--text-muted, #888);
          margin-top: 0.25rem;
        }
        .search-item-body {
          font-size: 0.85rem;
          color: #ccc;
          margin-top: 0.35rem;
          line-height: 1.4;
        }
        .search-item-body.clamped {
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
        .search-empty {
          padding: 2.5rem;
          text-align: center;
          color: var(--text-muted, #888);
        }
        .expand-icon {
          align-self: center;
          color: var(--text-muted, #888);
        }
      `}</style>
      <div className="search-overlay-card" onClick={(e) => e.stopPropagation()}>
        <div className="search-input-container">
          <Search size={22} className="text-muted" />
          <input
            ref={inputRef}
            type="text"
            className="search-input-field"
            placeholder="Search notebook, wiki, decisions, or tasks..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button className="search-close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="search-results-container">
          {loading && (
            <div className="search-empty">Searching lab registry...</div>
          )}

          {!loading && !query && (
            <div className="search-empty">Type to search database...</div>
          )}

          {!loading && query && totalResults === 0 && (
            <div className="search-empty">No matching records found.</div>
          )}

          {!loading && query && totalResults > 0 && (
            <>
              {results.notebook.length > 0 && (
                <div>
                  <div className="search-section-title">📓 Notebook Logs</div>
                  {results.notebook.map((item) => {
                    const isExpanded = expandedItem?.type === 'notebook' && expandedItem?.id === item.entry_id;
                    return (
                      <div key={item.entry_id} className="search-item" onClick={() => toggleExpand('notebook', item.entry_id)}>
                        <Book size={16} style={{ marginTop: '3px', color: 'var(--color-primary)' }} />
                        <div className="search-item-content">
                          <div className="search-item-title">{item.title}</div>
                          <div className="search-item-meta">Project: {item.project_code} · {item.created_at?.slice(0, 10)}</div>
                          <div className={`search-item-body ${isExpanded ? '' : 'clamped'}`}>
                            {item.content}
                          </div>
                          {isExpanded && item.conclusions && (
                            <div style={{ marginTop: '0.5rem', background: 'rgba(52,211,153,0.05)', padding: '0.5rem', borderRadius: '4px', fontSize: '0.8rem' }}>
                              <strong style={{ color: 'var(--color-success)' }}>Conclusions:</strong> {item.conclusions}
                            </div>
                          )}
                        </div>
                        <div className="expand-icon">
                          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {results.wiki.length > 0 && (
                <div>
                  <div className="search-section-title">📚 Wiki SOPs</div>
                  {results.wiki.map((item) => {
                    const isExpanded = expandedItem?.type === 'wiki' && expandedItem?.id === item.wiki_id;
                    return (
                      <div key={item.wiki_id} className="search-item" onClick={() => toggleExpand('wiki', item.wiki_id)}>
                        <FileText size={16} style={{ marginTop: '3px', color: 'var(--color-success)' }} />
                        <div className="search-item-content">
                          <div className="search-item-title">{item.title}</div>
                          <div className="search-item-meta">Category: {item.wiki_type} · Rev {item.revision || 1}</div>
                          <div className={`search-item-body ${isExpanded ? '' : 'clamped'}`} style={{ whiteSpace: isExpanded ? 'pre-wrap' : 'normal' }}>
                            {item.content}
                          </div>
                        </div>
                        <div className="expand-icon">
                          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {results.decisions.length > 0 && (
                <div>
                  <div className="search-section-title">⚖️ Decisions Ledger</div>
                  {results.decisions.map((item) => {
                    const isExpanded = expandedItem?.type === 'decision' && expandedItem?.id === item.decision_id;
                    return (
                      <div key={item.decision_id} className="search-item" onClick={() => toggleExpand('decision', item.decision_id)}>
                        <Scale size={16} style={{ marginTop: '3px', color: 'var(--color-accent)' }} />
                        <div className="search-item-content">
                          <div className="search-item-title">{item.title}</div>
                          <div className="search-item-meta">Project: {item.project_code} · {item.decision_date}</div>
                          <div className={`search-item-body ${isExpanded ? '' : 'clamped'}`}>
                            {item.decision_details}
                          </div>
                          {isExpanded && item.rationale && (
                            <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', opacity: 0.8 }}>
                              <strong>Rationale:</strong> {item.rationale}
                            </div>
                          )}
                        </div>
                        <div className="expand-icon">
                          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {results.tasks.length > 0 && (
                <div>
                  <div className="search-section-title">☑️ Lab Tasks</div>
                  {results.tasks.map((item) => {
                    const isExpanded = expandedItem?.type === 'task' && expandedItem?.id === item.task_id;
                    return (
                      <div key={item.task_id} className="search-item" onClick={() => toggleExpand('task', item.task_id)}>
                        <CheckSquare size={16} style={{ marginTop: '3px', color: 'var(--color-warning)' }} />
                        <div className="search-item-content">
                          <div className="search-item-title">{item.title}</div>
                          <div className="search-item-meta">Project: {item.project_code} · Status: <span style={{ textTransform: 'capitalize' }}>{item.status?.replace('_', ' ')}</span></div>
                          <div className={`search-item-body ${isExpanded ? '' : 'clamped'}`}>
                            {item.description}
                          </div>
                          {isExpanded && item.assignee && (
                            <div style={{ marginTop: '0.35rem', fontSize: '0.8rem', opacity: 0.8 }}>
                              <strong>Assignee:</strong> {item.assignee}
                            </div>
                          )}
                        </div>
                        <div className="expand-icon">
                          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
