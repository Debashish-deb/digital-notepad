import './MacPlusVisualStyles.css';
import React, { useState, useEffect } from 'react';
import TasksScreen from './TasksScreen';
import LabSectionTwinPanel from '../components/LabSectionTwinPanel.jsx';

export function OrdersBillingPanel({ API_URL }) {
  const [documents, setDocuments] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    fetch(`${API_URL || ''}/api/billing-instructions`)
      .then(res => {
        if (!res.ok) throw new Error("Failed to load billing instructions");
        return res.json();
      })
      .then(json => {
        const docs = json.documents || [];
        setDocuments(docs);
        if (docs.length > 0) {
          setSelectedDocId(docs[0].document_id);
        }
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setError(err.message);
        setLoading(false);
      });
  }, [API_URL]);

  if (loading) return <div className="panel"><p className="text-loading">Loading Logistics and Billing blueprints...</p></div>;
  if (error) return (
    <div className="stack-md">
      <div className="panel panel-danger"><p>Error loading documents: {error}</p></div>
      <LabSectionTwinPanel sectionId="orders_archive" title="Orders archive" description="Historical purchase orders." />
    </div>
  );

  const getCategory = (docType) => {
    if (docType === 'billing_instruction') return { id: 'billing', label: 'Billing & Invoicing', icon: '💳' };
    if (docType === 'order_form') return { id: 'order_form', label: 'Order Forms', icon: '📋' };
    if (docType === 'shipping_customs_statement') return { id: 'shipping', label: 'Customs & Shipping', icon: '✈️' };
    if (docType && (docType.startsWith('courier_service') || docType.includes('courier'))) {
      return { id: 'courier', label: 'Courier Accounts', icon: '🚚' };
    }
    return { id: 'other', label: 'Other Documents', icon: '📄' };
  };

  const getDocId = (doc) => doc.document_id || doc.id || doc.document?.document_id || null;
  const getDocTitle = (doc) => doc.content?.title || doc.document?.title || doc.subject || getDocId(doc) || 'Untitled document';
  const getDocSummary = (doc) => doc.content?.short_summary || doc.document?.short_summary || doc.subject || '';
  const getDocFileName = (doc) => doc.source?.file_name || doc.document?.source?.file_name || doc.file_name || 'Unknown file';

  const filteredDocs = documents.filter(doc => {
    const query = searchQuery.toLowerCase();
    const title = getDocTitle(doc).toLowerCase();
    const summary = getDocSummary(doc).toLowerCase();
    const file = getDocFileName(doc).toLowerCase();
    
    const fieldsMatch = doc.gui_display?.sections?.some(sec => 
      sec.fields?.some(f => 
        (f.label || '').toLowerCase().includes(query) || 
        (f.value || '').toLowerCase().includes(query)
      )
    );
    
    return title.includes(query) || summary.includes(query) || file.includes(query) || fieldsMatch;
  });

  const selectedDoc = documents.find((d) => getDocId(d) === selectedDocId);

  return (
    <div className="obp-shell">
      {/* Header */}
      <div className="panel obp-header">
        <div>
          <h2 className="text-title-1 obp-title">Logistics &amp; Billing Instructions</h2>
          <p className="page-lead obp-lead">
            Unified directory of courier accounts, customs templates, order sheets, and invoicing protocols.
          </p>
        </div>
        <input
          type="search"
          className="input obp-search"
          placeholder="🔍 Search documents, keywords, IDs…"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>

      {/* Master-Detail split */}
      <div className="obp-layout">

        {/* LEFT: Master list */}
        <div className="panel obp-master feed-scroll">
          <h3 className="obp-master-heading">
            Document Blueprints <span className="obp-count">({filteredDocs.length})</span>
          </h3>

          <div className="obp-master-list">
            {['billing', 'order_form', 'shipping', 'courier', 'other'].map(catId => {
              const catDocs = filteredDocs.filter(d => getCategory(d.classification?.document_type || d.document_type || d.document?.classification?.document_type).id === catId);
              if (catDocs.length === 0) return null;
              const category = getCategory(catDocs[0].classification?.document_type || catDocs[0].document_type || catDocs[0].document?.classification?.document_type);
              return (
                <div key={catId} className="obp-cat-group">
                  <div className="obp-cat-header" data-category={catId}>
                    <span className="obp-cat-icon">{category.icon}</span>
                    <span>{category.label}</span>
                  </div>
                  {catDocs.map((doc, idx) => {
                    const isSelected = getDocId(doc) === selectedDocId;
                    return (
                      <button
                        type="button"
                        key={getDocId(doc) || `${catId}-${idx}`}
                        onClick={() => setSelectedDocId(getDocId(doc))}
                        className={`obp-doc-item${isSelected ? ' is-active' : ''}`}
                        data-category={catId}
                        aria-pressed={isSelected}
                      >
                        <span className="obp-doc-title">{getDocTitle(doc)}</span>
                        <div className="obp-doc-meta">
                          <span className="obp-doc-file">{getDocFileName(doc)}</span>
                          <span className="obp-doc-lang">{(doc.language?.original || 'en').toUpperCase()}</span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              );
            })}
            {filteredDocs.length === 0 && (
              <div className="obp-empty">No blueprints match search filter.</div>
            )}
          </div>
        </div>

        {/* RIGHT: Detail view */}
        <div className="panel obp-detail">
          {selectedDoc ? (
            <div className="obp-detail-inner">

              {/* Detail header */}
              <div className="obp-detail-header">
                <div className="obp-detail-badges">
                  <span className="obp-badge obp-badge--blue">
                    {getCategory(selectedDoc.classification?.document_type).icon}&nbsp;
                    {getCategory(selectedDoc.classification?.document_type).label}
                  </span>
                  <span className="obp-badge obp-badge--green">
                    Confidence: {Math.round((selectedDoc.classification?.confidence || 0.9) * 100)}%
                  </span>
                  {selectedDoc.quality?.needs_human_review && (
                    <span className="obp-badge obp-badge--amber">⚠️ Review Required</span>
                  )}
                </div>
                <h3 className="obp-detail-title">{selectedDoc.content?.title}</h3>
                <p className="page-lead">{selectedDoc.content?.short_summary}</p>
              </div>

              {/* Section cards grid */}
              <div className="obp-sections-grid">
                {selectedDoc.gui_display?.sections?.map((section, sidx) => {
                  const isQuality = section.section_title.toLowerCase().includes('quality');
                  return (
                    <div
                      key={sidx}
                      className={`obp-section${isQuality ? ' obp-section--warning obp-section--full' : ''}`}
                    >
                      <h4 className="obp-section-title">
                        {isQuality ? '⚠️ ' : ''}{section.section_title}
                      </h4>
                      <div className="obp-fields">
                        {section.fields?.map((field, fidx) => {
                          const isSecret = field.value && (
                            field.value.includes('REDACTED') ||
                            field.label.toLowerCase().includes('password') ||
                            field.label.toLowerCase().includes('answer')
                          );
                          return (
                            <div key={fidx} className="obp-field">
                              <span className="obp-field-label">{field.label}</span>
                              <span className="obp-field-value">
                                {isSecret ? (
                                  <span className="obp-secret">🔒 {field.value}</span>
                                ) : field.value}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Tables */}
              {selectedDoc.structured_data?.tables?.map((table, tidx) => (
                <div key={tidx} className="obp-table-wrap">
                  <h4 className="obp-table-title">📋 {table.name?.replace(/_/g, ' ')}</h4>
                  <div className="obp-table-scroll">
                    <table className="table" style={{ width: '100%', margin: 0, background: 'transparent' }}>
                      <thead>
                        <tr>
                          {table.column_names?.map((col, i) => (
                            <th key={i} className="obp-th">{col?.replace(/_/g, ' ')}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {table.rows?.map((row, ridx) => (
                          <tr key={ridx}>
                            {table.column_names?.map((col, cidx) => (
                              <td key={cidx} className="obp-td">
                                {row[col] != null ? String(row[col]) : ''}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}

              {/* Raw source drawer */}
              <details className="obp-raw-drawer">
                <summary className="obp-raw-summary">🔍 View Raw Extracted Text Source</summary>
                <pre className="code-block obp-raw-pre">
                  {selectedDoc.content?.original_text || selectedDoc.content?.canonical_text}
                </pre>
              </details>

            </div>
          ) : (
            <div className="obp-empty-detail">
              Select a document from the list to view its details.
            </div>
          )}
        </div>

      </div>
    </div>
  );
}

export function OrdersRegisterPanel() {
  return (
    <div className="stack-md">
      <LabSectionTwinPanel
        sectionId="orders_register"
        title="Orders register"
        description="Reagents, sequencing, and service orders."
      />
    </div>
  );
}

export function OrdersRelatedPanel({ auditLogs = [] }) {
  return (
    <div className="stack-md">
      <div className="panel">
        <h3 className="panel-title">Related records</h3>
        <p className="text-body-secondary">
          Cross-links between samples, shipments, sequencing batches, and project folders. Audit events from the platform
          are listed below.
        </p>
      </div>
      <div className="panel">
        <h4 className="text-title-3">Recent platform audit events</h4>
        {!auditLogs?.length ? (
          <p className="muted">No audit logs loaded.</p>
        ) : (
          <ul className="stack-sm" style={{ listStyle: 'none', padding: 0 }}>
            {auditLogs.slice(0, 20).map((log, i) => (
              <li key={log.id || i} className="overview-news-row">
                <span>{log.action || log.event_type || 'Event'}</span>
                <span className="text-caption">{log.timestamp || log.created_at || ''}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export function OrdersTasksPanel(props) {
  return <TasksScreen {...props} />;
}
