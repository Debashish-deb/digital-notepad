import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  Calendar,
  Check,
  Clock,
  Copy,
  FileText,
  FileType,
  Folder,
  HardDrive,
  Loader2,
  RefreshCw,
  Tag,
} from 'lucide-react';
import DocumentFormatter from './DocumentFormatter.jsx';
import { useTaskpad } from '../contexts/TaskpadContext.jsx';
import './DocumentViewer.css';

function normalizeDocumentId(documentId) {
  const value = String(documentId || '')
    .trim()
    .replace(/^\/+/, '')
    .replace(/\.json$/i, '');

  if (!value || value.includes('..') || value.includes('\\')) return null;

  return value
    .split('/')
    .filter(Boolean)
    .map((part) => encodeURIComponent(part))
    .join('/');
}

function formatDate(value) {
  if (!value) return null;

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

function formatFamily(classification = {}) {
  const family = classification.family;
  const extension = classification.extension;

  if (!family && !extension) return null;

  const cleanFamily = family
    ? String(family).replace(/[_-]+/g, ' ')
    : 'File';

  return extension
    ? `${cleanFamily} (${String(extension).replace(/^\./, '').toUpperCase()})`
    : cleanFamily;
}

function countWords(text) {
  if (!text || typeof text !== 'string') return 0;

  const matches = text.trim().match(/\S+/g);
  return matches?.length || 0;
}

function getDocumentTags(metadata = {}) {
  const classification = metadata.classification || {};

  if (Array.isArray(metadata.tags)) return metadata.tags.filter(Boolean);
  if (Array.isArray(classification.tags)) return classification.tags.filter(Boolean);
  if (Array.isArray(classification.labels)) return classification.labels.filter(Boolean);

  return [];
}

function StatePanel({
  icon,
  title,
  description,
  action,
  tone = 'neutral',
}) {
  return (
    <section className={`document-viewer-state document-viewer-state--${tone} panel`}>
      <div className="document-viewer-state__icon" aria-hidden="true">
        {icon}
      </div>

      <div className="document-viewer-state__copy">
        <h2>{title}</h2>
        {description && <p>{description}</p>}
      </div>

      {action}
    </section>
  );
}

function MetaItem({ icon, label, value }) {
  if (!value) return null;

  return (
    <div className="notebook-meta-item">
      <span className="notebook-meta-label">
        {icon}
        {label}
      </span>
      <span className="notebook-meta-value">{value}</span>
    </div>
  );
}

export default function DocumentViewer({ documentId }) {
  const [doc, setDoc] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [copied, setCopied] = useState(false);

  const { openTaskpad } = useTaskpad();

  const documentPath = useMemo(() => normalizeDocumentId(documentId), [documentId]);

  const documentUrl = useMemo(() => {
    if (!documentPath) return null;
    return `/database/docs/${documentPath}.json`;
  }, [documentPath]);

  useEffect(() => {
    if (!documentUrl) {
      setDoc(null);
      setLoading(false);
      setError(null);
      return undefined;
    }

    const controller = new AbortController();
    let active = true;

    async function loadDocument() {
      setLoading(true);
      setError(null);
      setCopied(false);

      try {
        const response = await fetch(documentUrl, {
          signal: controller.signal,
          headers: {
            Accept: 'application/json',
          },
        });

        if (!response.ok) {
          if (response.status === 404) {
            throw new Error('Document not found in the static database.');
          }

          throw new Error(`Could not load document. Server returned ${response.status}.`);
        }

        const data = await response.json();

        if (active) {
          setDoc(data || null);
        }
      } catch (err) {
        if (err.name === 'AbortError') return;

        console.error('[DocumentViewer] Failed to load document:', err);

        if (active) {
          setDoc(null);
          setError(err.message || 'Failed to load document.');
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadDocument();

    return () => {
      active = false;
      controller.abort();
    };
  }, [documentUrl, reloadKey]);

  const handleRetry = useCallback(() => {
    setReloadKey((value) => value + 1);
  }, []);

  const handleCreateTask = useCallback(
    (section) => {
      if (typeof openTaskpad === 'function') {
        openTaskpad(section);
      }
    },
    [openTaskpad],
  );

  const metadata = doc?.metadata || {};
  const source = metadata.source || {};
  const classification = metadata.classification || {};

  const displayTitle = doc?.title || doc?.filename || documentId || 'Untitled document';
  const relativePath = doc?.relative_path || source.relative_path || source.path || '';
  const modifiedDate = formatDate(source.modified);
  const extractedDate = formatDate(metadata.converted_at);
  const fileFormat = formatFamily(classification);
  const tags = getDocumentTags(metadata);
  const wordCount = countWords(doc?.full_text);

  const metaItems = useMemo(
    () => [
      {
        key: 'size',
        label: 'Size',
        value: source.size_human,
        icon: <HardDrive size={13} aria-hidden="true" />,
      },
      {
        key: 'modified',
        label: 'Modified',
        value: modifiedDate,
        icon: <Calendar size={13} aria-hidden="true" />,
      },
      {
        key: 'format',
        label: 'Format',
        value: fileFormat,
        icon: <FileType size={13} aria-hidden="true" />,
      },
      {
        key: 'extracted',
        label: 'Extracted',
        value: extractedDate,
        icon: <Clock size={13} aria-hidden="true" />,
      },
      {
        key: 'words',
        label: 'Words',
        value: wordCount ? wordCount.toLocaleString() : null,
        icon: <FileText size={13} aria-hidden="true" />,
      },
    ],
    [source.size_human, modifiedDate, fileFormat, extractedDate, wordCount],
  );

  const handleCopyPath = useCallback(async () => {
    if (!relativePath || !navigator?.clipboard) return;

    try {
      await navigator.clipboard.writeText(relativePath);
      setCopied(true);

      window.setTimeout(() => {
        setCopied(false);
      }, 1400);
    } catch (err) {
      console.warn('[DocumentViewer] Could not copy path:', err);
    }
  }, [relativePath]);

  if (!documentId) {
    return (
      <StatePanel
        icon={<FileText size={34} />}
        title="Select a document"
        description="Choose a document from the index to view its extracted content, metadata, and research notes."
      />
    );
  }

  if (!documentPath) {
    return (
      <StatePanel
        icon={<AlertTriangle size={34} />}
        title="Invalid document identifier"
        description="The selected document ID contains an unsafe or unsupported path."
        tone="warning"
      />
    );
  }

  if (loading) {
    return (
      <section className="document-viewer-state document-viewer-state--loading panel" aria-busy="true">
        <Loader2 size={28} className="spin document-viewer-spinner" aria-hidden="true" />
        <div className="document-viewer-state__copy">
          <h2>Loading document</h2>
          <p>Preparing the extracted text and metadata.</p>
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <StatePanel
        icon={<AlertTriangle size={34} />}
        title="Could not open document"
        description={error}
        tone="danger"
        action={
          <button type="button" className="btn btn-secondary" onClick={handleRetry}>
            <RefreshCw size={15} aria-hidden="true" />
            Retry
          </button>
        }
      />
    );
  }

  if (!doc) return null;

  return (
    <article className="notebook-page document-viewer" aria-labelledby="document-viewer-title">
      <header className="notebook-page-header document-viewer-header">
        <div className="notebook-page-header-main">
          <div className="notebook-page-title-row">
            <span className="notebook-page-title-icon" aria-hidden="true">
              <FileText size={20} />
            </span>

            <h2 id="document-viewer-title" className="notebook-page-title">
              {displayTitle}
            </h2>
          </div>

          {relativePath && (
            <div className="notebook-page-path" title={relativePath}>
              <Folder size={14} aria-hidden="true" />
              <span>{relativePath}</span>
            </div>
          )}
        </div>

        <div className="document-viewer-actions" aria-label="Document actions">
          {relativePath && (
            <button
              type="button"
              className="document-viewer-icon-btn"
              onClick={handleCopyPath}
              title={copied ? 'Copied path' : 'Copy document path'}
              aria-label={copied ? 'Copied document path' : 'Copy document path'}
            >
              {copied ? <Check size={16} aria-hidden="true" /> : <Copy size={16} aria-hidden="true" />}
            </button>
          )}

          <button
            type="button"
            className="document-viewer-icon-btn"
            onClick={handleRetry}
            title="Reload document"
            aria-label="Reload document"
          >
            <RefreshCw size={16} aria-hidden="true" />
          </button>
        </div>
      </header>

      {(metaItems.some((item) => item.value) || tags.length > 0) && (
        <section className="notebook-meta-section" aria-label="Document metadata">
          <div className="notebook-meta-grid">
            {metaItems.map((item) => (
              <MetaItem
                key={item.key}
                label={item.label}
                value={item.value}
                icon={item.icon}
              />
            ))}
          </div>

          {tags.length > 0 && (
            <div className="notebook-tag-row" aria-label="Document tags">
              <span className="notebook-tag-label">
                <Tag size={13} aria-hidden="true" />
                Tags
              </span>

              <div className="notebook-tags">
                {tags.map((tag) => (
                  <span key={tag} className="notebook-tag">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      <section className="notebook-page-body document-viewer-body">
        {doc.full_text ? (
          <DocumentFormatter
            text={doc.full_text}
            onCreateTask={handleCreateTask}
          />
        ) : (
          <div className="document-viewer-no-text">
            <FileText size={52} aria-hidden="true" />
            <h3>No readable text extracted</h3>
            <p>
              This file may be binary, image-based, encrypted, unsupported, or missing text
              from the static extraction output.
            </p>
          </div>
        )}
      </section>
    </article>
  );
}