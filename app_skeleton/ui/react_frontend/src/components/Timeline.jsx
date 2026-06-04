import React from 'react';

export default function Timeline({ timeline }) {
  if (!timeline || timeline.length === 0) {
    return <p style={{color: 'var(--text-muted)', fontSize: '0.9rem'}}>No log entries parsed from project logbooks.</p>;
  }

  return (
    <div className="timeline-container">
      {timeline.map((entry, idx) => {
        const isMeeting = entry.title.toLowerCase().includes('meeting') || entry.title.toLowerCase().includes('anniina');
        const isTodo = entry.title.toLowerCase().includes('to do') || entry.title.toLowerCase().includes('task');
        let badgeClass = '';
        if (isMeeting) badgeClass = 'meeting';
        else if (isTodo) badgeClass = 'todo';
        
        return (
          <div key={idx} className="timeline-item">
            <div className={`timeline-badge ${badgeClass}`}></div>
            <div className="timeline-date">{entry.date}</div>
            <div className="timeline-card">
              <div className="timeline-title">{entry.title}</div>
              <div className="timeline-content">{entry.content}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
