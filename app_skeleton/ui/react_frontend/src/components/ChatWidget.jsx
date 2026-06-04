import React, { useState } from 'react';

export default function ChatWidget({ dbProjects, API_URL }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hello! I am OMEIA Research Copilot. Ask me anything about staining methodology, spatial deconvolution parameters (like ROI selection, Gate normalization, SPACEstat, Ashlar stitching, or Stardist segmentation masks).' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [selProjs, setSelProjs] = useState(['EyeMT']);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;
    
    const userMsg = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: input,
          project_codes: selProjs,
          mode: 'documentation_only'
        })
      });
      if (res.ok) {
        const data = await res.json();
        let formattedAnswer = data.answer;
        if (data.sources && data.sources.length > 0) {
          formattedAnswer += "\n\n**Sources & Citations:**\n" + data.sources.map(s => `- *${s.title}*`).join('\n');
        }
        setMessages(prev => [...prev, { role: 'assistant', content: formattedAnswer }]);
      } else {
        setMessages(prev => [...prev, { role: 'assistant', content: 'I encountered an error querying the vector search indexes.' }]);
      }
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Connection timed out or API offline.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="panel" style={{marginBottom: '1rem', padding: '1rem'}}>
        <label className="form-label" style={{marginBottom: '0.25rem'}}>RAG Scope Projects:</label>
        <div style={{display: 'flex', gap: '1rem', flexWrap: 'wrap'}}>
          {dbProjects.map(p => {
            const checked = selProjs.includes(p.project_code);
            return (
              <label key={p.project_code} style={{display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.85rem', cursor: 'pointer'}}>
                <input 
                  type="checkbox" 
                  checked={checked}
                  onChange={() => {
                    if (checked) setSelProjs(selProjs.filter(x => x !== p.project_code));
                    else setSelProjs([...selProjs, p.project_code]);
                  }}
                />
                <span>{p.project_code}</span>
              </label>
            );
          })}
        </div>
      </div>

      <div className="chat-container">
        <div className="chat-messages">
          {messages.map((m, idx) => (
            <div key={idx} className={`chat-bubble ${m.role}`}>
              <div style={{whiteSpace: 'pre-wrap'}}>{m.content}</div>
            </div>
          ))}
          {loading && (
            <div className="chat-bubble assistant" style={{fontStyle: 'italic'}}>
              Analyzing vector collections and generating response...
            </div>
          )}
        </div>
        <form onSubmit={handleSend} className="chat-input-area">
          <input 
            type="text" 
            placeholder="Ask about CycIF gating, SPACEStat, Novaseq sequencing runs..." 
            className="form-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
          />
          <button type="submit" className="btn btn-primary" disabled={loading}>Send</button>
        </form>
      </div>
    </div>
  );
}
