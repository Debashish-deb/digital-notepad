import React, { useMemo, useState } from 'react';
import { Image, FileText, Presentation, Table, Film, FolderOpen, X, ImageOff } from 'lucide-react';
import { projectAssetUrl } from '../utils/digitalTwinUtils.js';
import FileTypeBadge from './FileTypeBadge.jsx';
import SmartLink from './SmartLink.jsx';
import CopyPathButton from './CopyPathButton.jsx';

const TYPE_META = {
  figures: { label: 'Figures & Images', icon: Image },
  documents: { label: 'Documents (PDF/DOCX)', icon: FileText },
  presentations: { label: 'Presentations', icon: Presentation },
  data_files: { label: 'Data Spreadsheets', icon: Table },
  text_files: { label: 'Notes & Protocols', icon: FileText },
  videos: { label: 'Videos', icon: Film },
};

function formatSize(bytes) {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function resolveContentRoot(twin) {
  return twin?.content_root || twin?.folder_path || null;
}

function AssetImage({ src, alt, className, onClick }) {
  const [failed, setFailed] = useState(false);

  if (failed) {
    return (
      <div className={`pcl-img-fallback ${className || ''}`} onClick={onClick} role={onClick ? 'button' : undefined}>
        <ImageOff size={22} />
        <span>Failed to load</span>
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={alt}
      className={className}
      loading="lazy"
      decoding="async"
      onClick={onClick}
      onError={() => setFailed(true)}
    />
  );
}

function AssetRow({ item, projectCode, API_URL, contentRoot, onPreview }) {
  const ext = (item.extension || '').toLowerCase();
  const isImage = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'].includes(ext);
  const isPdf = ext === '.pdf';
  const url = projectAssetUrl(projectCode, item.path, API_URL, contentRoot);
  const thumbUrl = (isImage || isPdf) ? `${url}&preview=true` : url;
  
  return (
    <div className="pcl-asset-row">
      <div className="pcl-asset-main">
        {(isImage || isPdf) && (
          <button type="button" className="pcl-thumb-btn" onClick={() => onPreview(item)}>
            <AssetImage src={thumbUrl} alt={item.name} className="pcl-thumb" />
          </button>
        )}
        <div>
          <div className="pcl-asset-name-row">
            <div className="pcl-asset-name">{item.name}</div>
            <FileTypeBadge file={item} />
          </div>
          <div className="pcl-asset-path">
            <SmartLink href={item.path} showCopy maxLabelLen={56} />
          </div>
          {item.excerpt && <p className="pcl-excerpt">{item.excerpt.slice(0, 180)}…</p>}
        </div>
      </div>
      <div className="pcl-asset-meta">
        <span className="pcl-size">{formatSize(item.size_bytes)}</span>
        <CopyPathButton value={item.path} />
        <a href={url} target="_blank" rel="noopener noreferrer" className="btn btn-secondary btn-sm">
          Open
        </a>
      </div>
    </div>
  );
}

export default function ProjectContentLibrary({ twin, projectCode, API_URL }) {
  const lib = twin?.content_library;
  const contentRoot = resolveContentRoot(twin);
  const [activeSection, setActiveSection] = useState('gallery');
  const [preview, setPreview] = useState(null);

  const gallery = lib?.figures_gallery || [];
  const sections = lib?.sections || [];
  const totals = lib?.totals || {};

  const sectionTabs = useMemo(() => {
    const tabs = [{ id: 'gallery', label: `Figures (${lib?.figure_count || gallery.length})` }];
    for (const s of sections) {
      if (s.total_files > 0) tabs.push({ id: s.id, label: `${s.label} (${s.total_files})` });
    }
    return tabs;
  }, [sections, gallery.length, lib?.figure_count]);

  if (!lib || (!gallery.length && !sections.length)) {
    return <p className="muted">No folder assets indexed yet. Reprocess the digital record to scan project files.</p>;
  }

  const active = sections.find((s) => s.id === activeSection);

  return (
    <div className="project-content-library">
      {contentRoot && (
        <p className="pcl-root-hint">
          <FolderOpen size={14} aria-hidden />
          <span>Content root:</span>
          <SmartLink href={contentRoot} showCopy maxLabelLen={48} />
          {twin.total_assets_count != null && (
            <span className="pcl-scan-count">{twin.total_assets_count} files scanned</span>
          )}
        </p>
      )}

      <div className="pcl-tabs">
        {sectionTabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`btn btn-sm ${activeSection === tab.id ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveSection(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeSection === 'gallery' && (
        <div className="pcl-figure-grid">
          {gallery.length === 0 ? (
            <p className="muted">No figure images in this project folder (presentations/PDFs may still exist in other tabs).</p>
          ) : (
            gallery.map((fig) => {
              const url = projectAssetUrl(projectCode, fig.path, API_URL, contentRoot);
              return (
                <figure key={fig.path} className="pcl-figure-card" onClick={() => setPreview(fig)}>
                  <AssetImage src={url} alt={fig.name} className="pcl-figure-img" />
                  <figcaption>
                    <b>{fig.name}</b>
                    <span>{fig.section_label}</span>
                  </figcaption>
                </figure>
              );
            })
          )}
        </div>
      )}

      {active && (
        <div className="pcl-section-panel">
          {Object.entries(TYPE_META).map(([key, meta]) => {
            const items = active[key] || [];
            if (!items.length) return null;
            const Icon = meta.icon;
            const total = active.counts?.[key.replace('_files', '').replace('s', '')] || items.length;
            return (
              <div key={key} className="pcl-type-block">
                <h4 className="dt-subheading"><Icon size={16} /> {meta.label} ({items.length}{total > items.length ? ` of ${total}` : ''})</h4>
                <div className="pcl-asset-list">
                  {items.map((item) => (
                    <AssetRow
                      key={item.path}
                      item={item}
                      projectCode={projectCode}
                      API_URL={API_URL}
                      contentRoot={contentRoot}
                      onPreview={setPreview}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {preview && (
        <div className="pcl-lightbox" onClick={() => setPreview(null)}>
          <div className="pcl-lightbox-inner" onClick={(e) => e.stopPropagation()}>
            <button type="button" className="pcl-lightbox-close" onClick={() => setPreview(null)}><X size={20} /></button>
            {(preview.extension || '').toLowerCase() === '.pdf' ? (
               <object
                 data={projectAssetUrl(projectCode, preview.path, API_URL, contentRoot)}
                 type="application/pdf"
                 width="100%"
                 style={{ minHeight: '80vh', borderRadius: '8px', border: 'none' }}
                 className="pcl-lightbox-pdf"
               >
                 <p>It appears you don't have a PDF plugin for this browser. <a href={projectAssetUrl(projectCode, preview.path, API_URL, contentRoot)}>Click here to download the PDF file.</a></p>
               </object>
            ) : (
              <AssetImage
                src={projectAssetUrl(projectCode, preview.path, API_URL, contentRoot)}
                alt={preview.name}
                className="pcl-lightbox-img"
              />
            )}
            <div className="pcl-lightbox-caption">
              <b>{preview.name}</b>
              <SmartLink href={preview.path} showCopy />
            </div>
          </div>
        </div>
      )}

      {Object.keys(totals).length > 0 && (
        <div className="pcl-totals">
          {totals.figure ? <span>{totals.figure} figures</span> : null}
          {totals.image ? <span>{totals.image} images</span> : null}
          {totals.document ? <span>{totals.document} documents</span> : null}
          {totals.presentation ? <span>{totals.presentation} presentations</span> : null}
          {totals.data ? <span>{totals.data} data files</span> : null}
          {totals.text ? <span>{totals.text} text files</span> : null}
        </div>
      )}
    </div>
  );
}
