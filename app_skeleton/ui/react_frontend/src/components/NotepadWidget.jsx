import React, { useState, useEffect } from 'react';
import { Edit, Save } from 'lucide-react';

export default function NotepadWidget({ projectCode, fileList, fetchReport, API_URL }) {
  const [selectedFile, setSelectedFile] = useState('');
  const [content, setContent] = useState('');
  const [editMode, setEditMode] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (fileList && fileList.length > 0) {
      const defaultFile = fileList[0].name;
      setSelectedFile(defaultFile);
      fetchFileContent(defaultFile);
    }
  }, [fileList, projectCode]);

  const fetchFileContent = async (relPath) => {
    try {
      const res = await fetch(`${API_URL}/api/project-files/read?project_code=${projectCode}&relative_path=${encodeURIComponent(relPath)}`);
      if (res.ok) {
        const data = await res.json();
        setContent(data.content);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API_URL}/api/project-files/write`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_code: projectCode,
          relative_path: selectedFile,
          content: content
        })
      });
      if (res.ok) {
        alert("Notepad revisions successfully saved to disk!");
        setEditMode(false);
        fetchReport();
      } else {
        alert("Failed to write revisions.");
      }
    } catch (e) {
      alert("Error: " + e);
    } finally {
      setSaving(false);
    }
  };

  if (!fileList || fileList.length === 0) {
    return <p style={{color: 'var(--text-muted)'}}>No note documentation files found to display.</p>;
  }

  return (
    <div>
      <div style={{display: 'flex', gap: '1.5rem', alignItems: 'center', marginBottom: '1rem'}}>
        <div style={{flexGrow: 1}}>
          <label className="form-label">Select File to View / Edit (Direct Disk Notepad):</label>
          <select 
            className="form-select"
            value={selectedFile}
            onChange={(e) => {
              setSelectedFile(e.target.value);
              fetchFileContent(e.target.value);
            }}
          >
            {fileList.map(f => (
              <option key={f.name} value={f.name}>{f.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="form-label">&nbsp;</label>
          <button 
            className={`btn ${editMode ? 'btn-secondary' : 'btn-primary'}`} 
            onClick={() => setEditMode(!editMode)}
          >
            {editMode ? "Cancel Editing" : "✍️ Edit File"}
          </button>
        </div>
      </div>

      <div style={{marginTop: '1rem'}}>
        {editMode ? (
          <div>
            <textarea 
              className="form-textarea" 
              value={content}
              onChange={(e) => setContent(e.target.value)}
              style={{fontFamily: 'var(--font-mono)', fontSize: '0.9rem', height: '400px'}}
            />
            <button 
              className="btn btn-success" 
              style={{marginTop: '1rem'}} 
              onClick={handleSave}
              disabled={saving}
            >
              <Save size={16} /> {saving ? "Saving changes..." : "Save Revisions to Disk"}
            </button>
          </div>
        ) : (
          <div className="surface-inset" style={{padding: '1.5rem', borderRadius: '8px', border: '1px solid var(--border-color)', fontFamily: 'var(--font-mono)', fontSize: '0.9rem', overflowX: 'auto', whiteSpace: 'pre-wrap', maxHeight: '450px'}}>
            {content}
          </div>
        )}
      </div>
    </div>
  );
}
