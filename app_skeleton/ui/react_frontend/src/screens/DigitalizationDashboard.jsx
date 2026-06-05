import React, { useState, useEffect, useCallback } from 'react';
import { Play, Search, AlertCircle, CheckCircle2, ShieldAlert, FileText, Database, Activity, RefreshCw } from 'lucide-react';
import { apiFetch } from '../api/client';
import DataPadEditor from '../components/DataPadEditor';

export default function DigitalizationDashboard({ title, description }) {
  const [status, setStatus] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [docDetail, setDocDetail] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [statusRes, docsRes] = await Promise.all([
        apiFetch('/digitalization/status'),
        apiFetch('/digitalization/documents?limit=50')
      ]);
      setStatus(statusRes);
      setDocuments(docsRes?.documents || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const fetchDocDetail = async (docId) => {
    try {
      setDocDetail(null);
      const detail = await apiFetch(`/digitalization/documents/${docId}`);
      setDocDetail(detail);
    } catch (err) {
      console.error(err);
    }
  };

  const [rootPath, setRootPath] = useState('');

  const handleScan = async (dryRun = true) => {
    try {
      setActionLoading(true);
      await apiFetch(dryRun ? '/digitalization/scan' : '/digitalization/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: 'local',
          root_path: rootPath,
          dry_run: dryRun,
          max_files: 50
        })
      });
      fetchData();
    } catch (err) {
      console.error(err);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="module-content">
      <div className="module-header">
        <h1 className="module-title">{title}</h1>
        <p className="module-description">{description}</p>
      </div>

      <div className="stack-lg">
        {/* Settings & Actions */}
        <div className="card">
          <div className="disk-pad-toolbar" style={{ marginBottom: '1rem' }}>
            <span className="text-secondary" style={{ fontSize: '0.85rem', fontWeight: 600 }}>Source Directory:</span>
            <input 
              type="text" 
              className="form-input" 
              value={rootPath} 
              onChange={e => setRootPath(e.target.value)} 
              style={{ flex: 1 }}
            />
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', justifyContent: 'center' }}>
            <div style={{ fontSize: '1.5rem', fontWeight: 600 }}>{status?.discovered || 0}</div>
            <div className="text-secondary" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Search size={16} /> Discovered Files
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
              <button 
                className="btn btn-secondary btn-sm" 
                onClick={() => handleScan(true)}
                disabled={actionLoading}
              >
                <Search size={14} /> Dry-run Scan
              </button>
            </div>
          </div>

          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', justifyContent: 'center' }}>
            <div style={{ fontSize: '1.5rem', fontWeight: 600 }}>{status?.extracted || 0}</div>
            <div className="text-secondary" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <FileText size={16} /> Extracted Documents
            </div>
          </div>

          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', justifyContent: 'center' }}>
            <div style={{ fontSize: '1.5rem', fontWeight: 600, color: 'var(--color-primary)' }}>{status?.canonicalized || 0}</div>
            <div className="text-secondary" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <CheckCircle2 size={16} /> Canonicalized JSON
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
              <button 
                className="btn btn-primary btn-sm" 
                onClick={() => handleScan(false)}
                disabled={actionLoading}
              >
                <Play size={14} /> Run Pipeline
              </button>
            </div>
          </div>

          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', justifyContent: 'center' }}>
            <div style={{ fontSize: '1.5rem', fontWeight: 600, color: 'var(--color-success)' }}>{status?.ready_for_rag || 0}</div>
            <div className="text-secondary" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Database size={16} /> Ready for RAG
            </div>
            <div className="text-footnote text-secondary">
              Chunks: {status?.chunks_total || 0}
            </div>
          </div>

          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', justifyContent: 'center' }}>
            <div style={{ fontSize: '1.5rem', fontWeight: 600, color: 'var(--color-warning)' }}>{status?.needs_review || 0}</div>
            <div className="text-secondary" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <AlertCircle size={16} /> Needs Review
            </div>
            <div className="text-footnote text-secondary" style={{ color: 'var(--color-danger)' }}>
              Failed: {status?.failed || 0}
            </div>
          </div>
        </div>

        {/* Document Table */}
        <div className="card p-0">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 className="card-title">Canonicalized Documents</h3>
            <button className="btn btn-secondary btn-sm" onClick={fetchData} disabled={loading}>
              <RefreshCw size={14} className={loading ? 'spin' : ''} /> Refresh
            </button>
          </div>
          <div className="table-responsive">
            <table className="table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Source File</th>
                  <th>Type / Domain</th>
                  <th>Status</th>
                  <th>Review</th>
                </tr>
              </thead>
              <tbody>
                {documents.map(doc => (
                  <tr key={doc.document_id} onClick={() => {
                    setSelectedDoc(doc);
                    fetchDocDetail(doc.document_id);
                  }} style={{ cursor: 'pointer', background: selectedDoc?.document_id === doc.document_id ? 'var(--bg-tertiary)' : 'transparent' }}>
                    <td>
                      <div style={{ fontWeight: 500 }}>{doc.title || 'Untitled'}</div>
                      <div className="text-footnote text-secondary" style={{ maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {doc.short_summary || 'No summary'}
                      </div>
                    </td>
                    <td>
                      <div className="text-footnote">{doc.logical_path}</div>
                      <span className="badge badge-secondary">{doc.provider}</span>
                    </td>
                    <td>
                      <span className="badge badge-outline">{doc.document_type}</span>
                      <span className="badge badge-outline" style={{ marginLeft: '4px' }}>{doc.domain}</span>
                    </td>
                    <td>
                      {doc.validation_status === 'validated' ? (
                        <span className="badge badge-success"><CheckCircle2 size={12}/> Validated</span>
                      ) : (
                        <span className="badge badge-danger"><AlertCircle size={12}/> Failed</span>
                      )}
                      <div className="text-footnote text-secondary mt-1">Chunks: {doc.chunk_count}</div>
                    </td>
                    <td>
                      {doc.needs_review ? (
                        <span className="badge badge-warning"><ShieldAlert size={12}/> Needs Review</span>
                      ) : (
                        <span className="badge badge-secondary">Auto</span>
                      )}
                    </td>
                  </tr>
                ))}
                {documents.length === 0 && (
                  <tr>
                    <td colSpan="5" className="text-center text-secondary py-4">
                      No canonical documents found. Run the pipeline to digitalize files.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Detail Panel */}
        {selectedDoc && (
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Document Detail: {selectedDoc.title}</h3>
            </div>
            {docDetail ? (
              <div className="stack-md">
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div>
                    <strong>Manifest Status:</strong> {docDetail.manifest_status} <br/>
                    <strong>Extraction Status:</strong> {docDetail.extraction_status} <br/>
                    <strong>Extractor:</strong> {docDetail.extractor_name} (Conf: {docDetail.extraction_confidence})
                  </div>
                  <div>
                    <strong>Logical Path:</strong> <span style={{ wordBreak: 'break-all' }}>{docDetail.logical_path}</span><br/>
                    <strong>Provider:</strong> {docDetail.provider} <br/>
                    <strong>Should Index:</strong> {docDetail.should_index ? 'Yes' : 'No'}
                  </div>
                </div>

                {docDetail.warnings && docDetail.warnings.length > 0 && (
                  <div className="alert alert-warning">
                    <strong>Warnings:</strong>
                    <ul style={{ margin: 0, paddingLeft: '1.5rem' }}>
                      {docDetail.warnings.map((w, i) => (
                        <li key={i}>{w}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <div style={{ marginTop: '1rem' }}>
                  <h4>Canonical JSON</h4>
                  <DataPadEditor 
                    initialContent={JSON.stringify(docDetail.canonical_json, null, 2)}
                    fileName="canonical.json"
                    readOnly
                    height="300px"
                  />
                </div>

                <div style={{ marginTop: '1rem' }}>
                  <h4>Extracted Text (Redacted)</h4>
                  <DataPadEditor 
                    initialContent={docDetail.canonical_text}
                    fileName="extracted.md"
                    readOnly
                    height="400px"
                  />
                </div>
              </div>
            ) : (
              <div className="text-center text-secondary py-4">Loading details...</div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}
