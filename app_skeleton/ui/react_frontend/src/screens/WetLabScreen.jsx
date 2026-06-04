import './MacPlusVisualStyles.css';
import React, { useState, useEffect } from 'react';
import { BookOpen, CheckSquare } from 'lucide-react';
import TasksScreen from './TasksScreen';
import LabSectionTwinPanel from '../components/LabSectionTwinPanel.jsx';

const WET_KEYWORDS = /wet|stain|sample|ffpe|tissue|antibody|chamber|bleach|protocol|prep/i;

function filterWikiDocs(docs) {
  return (docs || []).filter((d) => {
    const blob = `${d.title || ''} ${d.category || ''} ${d.content || ''}`.toLowerCase();
    return WET_KEYWORDS.test(blob) || blob.includes('wet-lab') || blob.includes('wet lab');
  });
}

export function WetLabProtocolsPanel({ API_URL }) {
  const [wikiDocs, setWikiDocs] = useState([]);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    fetch(`${API_URL}/wiki`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => {
        const filtered = filterWikiDocs(data);
        setWikiDocs(filtered.length ? filtered : data);
        if (filtered[0]) setSelected(filtered[0]);
      })
      .catch(console.error);
  }, [API_URL]);

  return (
    <div className="grid-2col">
      <div className="panel">
        <h3 className="panel-title"><BookOpen size={18} /> Wet-lab SOPs</h3>
        <div className="stack-sm">
          {wikiDocs.map((doc) => (
            <button
              key={doc.wiki_id || doc.id}
              type="button"
              className={`sidebar-item ${selected?.wiki_id === doc.wiki_id ? 'active' : ''}`}
              style={{ width: '100%', textAlign: 'left', border: 'none', background: 'transparent', cursor: 'pointer' }}
              onClick={() => setSelected(doc)}
            >
              {doc.title}
            </button>
          ))}
          {!wikiDocs.length && <p className="muted">No wiki documents yet.</p>}
        </div>
      </div>
      <div className="panel markdown-body">
        {selected ? (
          <>
            <h3>{selected.title}</h3>
            <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>{selected.content}</pre>
          </>
        ) : (
          <p className="muted">Select a protocol.</p>
        )}
      </div>
    </div>
  );
}

export function WetLabTasksPanel(props) {
  return <TasksScreen {...props} categoryFilter="Wet_Lab" />;
}

export function WetLabInventoryPanel() {
  return (
    <LabSectionTwinPanel
      sectionId="wet_lab_files"
      title="Reagents, panels & wet-lab files"
      description="Protocols, inventories, GeoMx/Xenium notes, and wet-lab spreadsheets from WET_LAB."
    />
  );
}
