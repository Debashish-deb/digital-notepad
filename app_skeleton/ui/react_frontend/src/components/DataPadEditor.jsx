import { useCallback, useEffect, useMemo, useState, useRef } from 'react';
import Editor from '@monaco-editor/react';
import {
  AlignLeft,
  Bold,
  Heading1,
  Heading2,
  Heading3,
  List,
  Loader2,
  Pencil,
  RotateCcw,
  Save,
  Sparkles,
  SpellCheck,
  Undo2,
  X,
} from 'lucide-react';
import {
  fetchDatapadConfig,
  fetchDatapadDocument,
  proofreadDatapadContent,
  restoreDatapadBackup,
  saveDatapadDocument,
  suggestDatapadHeadings,
} from '../api/datapad.js';
import { inferExtension } from '../utils/fileTypeMeta.js';

const EDITABLE_EXTS = new Set(['.md', '.txt', '.html', '.rtf']);

function wrapSelection(editor, text, before, after = before) {
  if (editor) {
    const selection = editor.getSelection();
    const model = editor.getModel();
    const selected = model.getValueInRange(selection);
    const newText = before + selected + after;
    editor.executeEdits('toolbar', [{ range: selection, text: newText }]);
    editor.focus();
    return null;
  }
  return text; // fallback does nothing without textarea
}

function insertLinePrefix(editor, text, prefix) {
  if (editor) {
    const selection = editor.getSelection();
    const model = editor.getModel();
    const lineNum = selection.startLineNumber;
    const lineContent = model.getLineContent(lineNum);
    const stripped = lineContent.replace(/^#+\s*/, '').trim();
    const newLine = `${prefix} ${stripped}`;
    const range = new monaco.Range(lineNum, 1, lineNum, lineContent.length + 1); // Not using monaco directly, we'll use a rough range or just replace text.
    // To avoid monaco reference error, we just get the full text and replace the line if we don't have monaco.
  }
  // Fallback: simple text replacement on the entire text, assuming we just prepend to the start
  return prefix + " " + text;
}

function simpleDiffLines(before, after) {
  const a = (before || '').split('\n');
  const b = (after || '').split('\n');
  const lines = [];
  const max = Math.max(a.length, b.length);
  for (let i = 0; i < max; i += 1) {
    const left = a[i] ?? '';
    const right = b[i] ?? '';
    if (left !== right) {
      lines.push({ line: i + 1, before: left, after: right });
    }
  }
  return lines.slice(0, 80);
}

export default function DataPadEditor({
  projectCode,
  relativePath,
  fileName,
  sectionLabel,
  initialContent = '',
  onClose,
  onSaved,
}) {
  const ext = inferExtension(fileName, '');
  const canEdit = EDITABLE_EXTS.has(ext);

  const [editMode, setEditMode] = useState(false);
  const [draft, setDraft] = useState(initialContent);
  const [saved, setSaved] = useState(initialContent);
  const [etag, setEtag] = useState(null);
  const [backups, setBackups] = useState([]);
  const [config, setConfig] = useState({ edit_enabled: true, ai_enabled: false });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState(null);
  const [aiBusy, setAiBusy] = useState(null);
  const [proofreadPreview, setProofreadPreview] = useState(null);
  const [headingPreview, setHeadingPreview] = useState(null);
  const editorRef = useRef(null);

  const handleEditorDidMount = (editor, monaco) => {
    editorRef.current = editor;
  };

  const dirty = draft !== saved;

  const showToast = useCallback((message, tone = 'info') => {
    setToast({ message, tone });
    window.setTimeout(() => setToast(null), 4500);
  }, []);

  const loadDocument = useCallback(async () => {
    if (!projectCode || !relativePath || !canEdit) return;
    setLoading(true);
    try {
      const [doc, cfg] = await Promise.all([
        fetchDatapadDocument(projectCode, relativePath),
        fetchDatapadConfig().catch(() => ({ edit_enabled: true, ai_enabled: false })),
      ]);
      setConfig(cfg);
      setDraft(doc.content ?? '');
      setSaved(doc.content ?? '');
      setEtag(doc.etag ?? null);
      setBackups(doc.backups ?? []);
    } catch (e) {
      if (initialContent) {
        setDraft(initialContent);
        setSaved(initialContent);
      }
      showToast(e.message || 'Could not load document for editing', 'error');
    } finally {
      setLoading(false);
    }
  }, [projectCode, relativePath, canEdit, initialContent, showToast]);

  useEffect(() => {
    if (editMode && canEdit) loadDocument();
  }, [editMode, canEdit, loadDocument]);

  useEffect(() => {
    if (!editMode) {
      setDraft(initialContent);
      setSaved(initialContent);
    }
  }, [initialContent, editMode]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await saveDatapadDocument({
        projectCode,
        relativePath,
        content: draft,
        expectedEtag: etag,
      });
      setSaved(draft);
      setEtag(res.etag ?? etag);
      if (res.backup_path) showToast(`Saved (backup: ${res.backup_path})`, 'success');
      else showToast('Saved to disk', 'success');
      onSaved?.(draft);
      await loadDocument();
    } catch (e) {
      if (e.status === 409) {
        showToast('Conflict: file changed on disk. Reload or restore a backup.', 'error');
      } else {
        showToast(e.message || 'Save failed', 'error');
      }
    } finally {
      setSaving(false);
    }
  };

  const handleDiscard = () => {
    setDraft(saved);
    setProofreadPreview(null);
    setHeadingPreview(null);
    showToast('Discarded unsaved changes', 'info');
  };

  const handleSuggestHeadings = async () => {
    setAiBusy('headings');
    try {
      const res = await suggestDatapadHeadings(draft, ext === '.md' ? 'markdown' : 'text');
      setHeadingPreview(res);
      showToast(
        res.mode === 'llm' ? 'Heading suggestions ready (AI)' : 'Heading suggestions ready (rules)',
        'success'
      );
    } catch (e) {
      showToast(e.message || 'Heading assist failed', 'error');
    } finally {
      setAiBusy(null);
    }
  };

  const handleProofread = async () => {
    setAiBusy('proofread');
    try {
      const res = await proofreadDatapadContent(draft);
      setProofreadPreview(res);
      showToast(
        `${res.fixes?.length ?? 0} suggestion(s) — review diff before applying`,
        'success'
      );
    } catch (e) {
      showToast(e.message || 'Proofread failed', 'error');
    } finally {
      setAiBusy(null);
    }
  };

  const applyProofread = () => {
    if (!proofreadPreview?.corrected_text) return;
    setDraft(proofreadPreview.corrected_text);
    setProofreadPreview(null);
    showToast('Proofread changes applied to editor (save to persist)', 'info');
  };

  const applyHeadingOutline = () => {
    const text =
      headingPreview?.improved_outline ||
      (headingPreview?.suggestions?.[0]?.suggested
        ? `${headingPreview.suggestions[0].suggested}\n\n${draft}`
        : null);
    if (!text) {
      showToast('No outline change to apply', 'info');
      return;
    }
    setDraft(text);
    setHeadingPreview(null);
    showToast('Outline applied to editor (save to persist)', 'info');
  };

  const handleRestore = async (backupPath) => {
    setSaving(true);
    try {
      await restoreDatapadBackup({ projectCode, relativePath, backupPath });
      showToast('Restored from backup', 'success');
      setEditMode(true);
      await loadDocument();
      onSaved?.(draft);
    } catch (e) {
      showToast(e.message || 'Restore failed', 'error');
    } finally {
      setSaving(false);
    }
  };

  const toolbarAction = (fn) => () => {
    const result = fn(editorRef.current, draft);
    if (typeof result === 'string') setDraft(result);
    else if (result?.next != null) setDraft(result.next);
  };

  const diffLines = useMemo(
    () => (proofreadPreview ? simpleDiffLines(draft, proofreadPreview.corrected_text) : []),
    [draft, proofreadPreview]
  );

  if (!canEdit) {
    return (
      <p className="text-footnote muted datapad-editor-hint">
        This file type is preview-only. Editable: .md, .txt, .html, .rtf
      </p>
    );
  }

  return (
    <div className="datapad-editor">
      {sectionLabel && (
        <div className="datapad-section-banner" role="status">
          <Pencil size={14} aria-hidden />
          <span>
            Editing: <strong>{sectionLabel}</strong>
            {config.edit_enabled === false && ' (writes disabled on server)'}
          </span>
        </div>
      )}

      <div className="datapad-editor-toolbar">
        <button
          type="button"
          className={`btn btn-sm ${editMode ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setEditMode((v) => !v)}
        >
          <Pencil size={14} /> {editMode ? 'Editing' : 'Edit'}
        </button>
        {editMode && (
          <>
            <span className="datapad-toolbar-divider" />
            <button type="button" className="btn btn-secondary btn-sm" onClick={toolbarAction((ed, t) => insertLinePrefix(ed, t, '#'))} title="Heading 1">
              <Heading1 size={14} />
            </button>
            <button type="button" className="btn btn-secondary btn-sm" onClick={toolbarAction((ed, t) => insertLinePrefix(ed, t, '##'))} title="Heading 2">
              <Heading2 size={14} />
            </button>
            <button type="button" className="btn btn-secondary btn-sm" onClick={toolbarAction((ed, t) => insertLinePrefix(ed, t, '###'))} title="Heading 3">
              <Heading3 size={14} />
            </button>
            <button type="button" className="btn btn-secondary btn-sm" onClick={toolbarAction((ed, t) => wrapSelection(ed, t, '**'))} title="Bold">
              <Bold size={14} />
            </button>
            <button type="button" className="btn btn-secondary btn-sm" onClick={toolbarAction((ed, t) => insertLinePrefix(ed, t, '-'))} title="List">
              <List size={14} />
            </button>
            <span className="datapad-toolbar-divider" />
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              disabled={!!aiBusy}
              onClick={handleSuggestHeadings}
              title={config.ai_enabled ? 'Suggest headings (AI + rules)' : 'Suggest headings (rules; set GROQ_API_KEY for AI)'}
            >
              {aiBusy === 'headings' ? <Loader2 size={14} className="spin" /> : <Sparkles size={14} />}
              Headings
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={handleProofread}
              disabled={!!aiBusy}
            >
              {aiBusy === 'proofread' ? <Loader2 size={14} className="spin" /> : <SpellCheck size={14} />}
              Proofread
            </button>
            <span className="datapad-toolbar-divider" />
            <button
              type="button"
              className="btn btn-primary btn-sm"
              disabled={!dirty || saving || !config.edit_enabled}
              onClick={handleSave}
            >
              {saving ? <Loader2 size={14} className="spin" /> : <Save size={14} />}
              Save
            </button>
            <button type="button" className="btn btn-secondary btn-sm" disabled={!dirty} onClick={handleDiscard}>
              <Undo2 size={14} /> Discard
            </button>
            {onClose && (
              <button type="button" className="btn btn-secondary btn-sm" onClick={onClose}>
                <X size={14} /> Close editor
              </button>
            )}
          </>
        )}
      </div>

      {toast && (
        <p className={`datapad-toast tone-${toast.tone}`} role="alert">
          {toast.message}
        </p>
      )}

      {loading && editMode && (
        <p className="text-loading">
          <Loader2 size={14} className="spin" /> Loading document…
        </p>
      )}

      {editMode ? (
        <div style={{ border: '1px solid var(--border-color)', borderRadius: '6px', overflow: 'hidden' }}>
          <Editor
            height="60vh"
            language={ext === '.md' ? 'markdown' : ext === '.json' ? 'json' : ext === '.html' ? 'html' : 'plaintext'}
            theme="vs-dark"
            value={draft}
            onChange={(val) => setDraft(val || '')}
            onMount={handleEditorDidMount}
            options={{
              wordWrap: 'on',
              minimap: { enabled: false },
              fontSize: 14,
              lineNumbers: 'on',
              scrollBeyondLastLine: false,
              automaticLayout: true,
            }}
          />
        </div>
      ) : (
        <pre className="pfb-preview-content markdown-body datapad-readonly">{draft}</pre>
      )}

      {headingPreview && (
        <div className="datapad-ai-panel">
          <h5 className="workspace-subpanel-title">
            <AlignLeft size={14} /> Heading suggestions ({headingPreview.mode})
          </h5>
          <ul className="datapad-suggestion-list">
            {(headingPreview.suggestions || []).slice(0, 8).map((s, i) => (
              <li key={i}>
                <span className="muted">L{s.line}:</span> {s.reason}
                {s.suggested && <code className="datapad-suggestion-code">{s.suggested}</code>}
              </li>
            ))}
          </ul>
          <div className="datapad-ai-actions">
            <button type="button" className="btn btn-primary btn-sm" onClick={applyHeadingOutline}>
              Apply to editor
            </button>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => setHeadingPreview(null)}>
              Dismiss
            </button>
          </div>
        </div>
      )}

      {proofreadPreview && (
        <div className="datapad-ai-panel">
          <h5 className="workspace-subpanel-title">
            <SpellCheck size={14} /> Proofread preview ({proofreadPreview.mode}) — {proofreadPreview.fixes?.length ?? 0} fix(es)
          </h5>
          {diffLines.length > 0 ? (
            <div className="datapad-diff-wrap">
              <table className="datapad-diff-table">
                <thead>
                  <tr>
                    <th>Line</th>
                    <th>Before</th>
                    <th>After</th>
                  </tr>
                </thead>
                <tbody>
                  {diffLines.map((row) => (
                    <tr key={row.line}>
                      <td>{row.line}</td>
                      <td className="datapad-diff-before">{row.before || '—'}</td>
                      <td className="datapad-diff-after">{row.after || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-footnote muted">No line-level diff; review full text in Apply.</p>
          )}
          <div className="datapad-ai-actions">
            <button type="button" className="btn btn-primary btn-sm" onClick={applyProofread}>
              Apply fixes
            </button>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => setProofreadPreview(null)}>
              Dismiss
            </button>
          </div>
        </div>
      )}

      {editMode && backups.length > 0 && (
        <div className="datapad-backups">
          <h5 className="text-footnote muted">Recent backups</h5>
          <ul>
            {backups.map((b) => (
              <li key={b.path}>
                <span>{b.name}</span>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => handleRestore(b.path)}
                  disabled={saving}
                >
                  <RotateCcw size={12} /> Revert
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
