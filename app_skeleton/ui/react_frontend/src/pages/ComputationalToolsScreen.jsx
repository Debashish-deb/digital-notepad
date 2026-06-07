
import React from 'react';
import { computationalToolsData } from '@/data/labData';

export default function ComputationalToolsScreen() {
  const { tools = [], intro, conclusion } = computationalToolsData;

  return (
    <div className="stack-lg">
      <p className="text-body-secondary">{intro}</p>
      <div className="overview-theme-grid">
        {tools.map((tool) => (
          <article key={tool.id} className="panel overview-theme-card">
            <h3 className="text-title-3">{tool.name}</h3>
            <p className="text-caption">{tool.fullName}</p>
            <p style={{ marginTop: '0.75rem', lineHeight: 1.55 }}>{tool.description}</p>
            {tool.link && (
              <a
                href={tool.link}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-secondary"
                style={{ marginTop: '1rem', display: 'inline-flex' }}
              >
                View publication
              </a>
            )}
          </article>
        ))}
      </div>
      {conclusion && (
        <p className="text-body-secondary" style={{ fontStyle: 'italic' }}>{conclusion}</p>
      )}
    </div>
  );
}
