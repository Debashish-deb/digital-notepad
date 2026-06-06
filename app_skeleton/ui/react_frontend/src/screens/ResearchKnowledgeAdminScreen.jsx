import React, { useEffect, useState } from 'react';
import { BookOpen, Database, Loader2, RefreshCw, Search, Sparkles } from 'lucide-react';
import {
  crawlFarkkilaSite,
  getResearchKnowledgeStatus,
  ingestPublications,
  searchResearchKnowledge,
  seedResearchDatasets,
} from '../api/researchKnowledgeClient.js';
import './ResearchKnowledge.css';

export default function ResearchKnowledgeAdminScreen() {
  const [status, setStatus] = useState(null);
  const [query, setQuery] = useState('MHC class II HGSC');
  const [hits, setHits] = useState([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');

  async function refreshStatus() {
    setBusy(true);
    try {
      setStatus(await getResearchKnowledgeStatus());
    } catch (error) {
      setMessage(error?.message || 'Failed to load status.');
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    refreshStatus();
  }, []);

  async function runCrawl() {
    setBusy(true);
    setMessage('Crawling Färkkilä public seed pages...');
    try {
      const result = await crawlFarkkilaSite({ maxPages: 50 });
      setMessage(`Crawl finished: ${result.page_count || 0} pages discovered.`);
      await refreshStatus();
    } catch (error) {
      setMessage(error?.message || 'Crawl failed.');
    } finally {
      setBusy(false);
    }
  }

  async function runPublicationIngest() {
    setBusy(true);
    setMessage('Discovering publication metadata...');
    try {
      const result = await ingestPublications();
      const ingested = result.ingested ?? result.count ?? 0;
      const total = result.count ?? ingested;
      setMessage(`Publication ingest finished: ${ingested}/${total} records indexed.`);
      await refreshStatus();
    } catch (error) {
      setMessage(error?.message || 'Publication ingest failed.');
    } finally {
      setBusy(false);
    }
  }

  async function runSeedDatasets() {
    setBusy(true);
    setMessage('Seeding public dataset registry...');
    try {
      const result = await seedResearchDatasets();
      setMessage(`Dataset seed finished: ${result.count ?? 0} records.`);
      await refreshStatus();
    } catch (error) {
      setMessage(error?.message || 'Dataset seed failed.');
    } finally {
      setBusy(false);
    }
  }

  async function runSearch(event) {
    event.preventDefault();
    setBusy(true);
    try {
      const result = await searchResearchKnowledge({ q: query, limit: 20 });
      setHits(result.hits || []);
      setMessage(result.warning || `${result.count || 0} results.`);
    } catch (error) {
      setMessage(error?.message || 'Search failed.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="research-kb-screen">
      <header className="research-kb-hero">
        <div>
          <span className="research-kb-eyebrow"><Sparkles size={14} /> Research AI Brain</span>
          <h1>Färkkilä Lab Knowledge Base</h1>
          <p>Ingest public research, publications, datasets, and internal lab knowledge into a source-grounded AI assistant.</p>
        </div>
        <button className="btn btn-secondary" onClick={refreshStatus} disabled={busy}>
          {busy ? <Loader2 className="spin" size={16} /> : <RefreshCw size={16} />}
          Refresh
        </button>
      </header>

      <div className="research-kb-grid">
        <article className="panel research-kb-card">
          <h2><Database size={18} /> Index Status</h2>
          <pre>{JSON.stringify(status, null, 2)}</pre>
        </article>

        <article className="panel research-kb-card">
          <h2><BookOpen size={18} /> Ingestion Actions</h2>
          <div className="research-kb-actions">
            <button className="btn btn-primary" onClick={runCrawl} disabled={busy}>Crawl Färkkilä Website</button>
            <button className="btn btn-secondary" onClick={runPublicationIngest} disabled={busy}>Discover Publications</button>
            <button className="btn btn-secondary" onClick={runSeedDatasets} disabled={busy}>Seed Datasets</button>
          </div>
          {status?.warnings?.length ? (
            <p className="research-kb-message research-kb-message--warn">
              {status.warnings.join(' ')}
            </p>
          ) : null}
          {message && <p className="research-kb-message">{message}</p>}
        </article>
      </div>

      <article className="panel research-kb-card">
        <h2><Search size={18} /> Research Knowledge Search</h2>
        <form className="research-kb-search" onSubmit={runSearch}>
          <input className="form-input" value={query} onChange={(e) => setQuery(e.target.value)} />
          <button className="btn btn-primary" disabled={busy}>Search</button>
        </form>
        <div className="research-kb-results">
          {hits.map((hit) => (
            <div key={`${hit.bucket}-${hit.id}`} className="research-kb-hit">
              <span>{hit.source_type || hit.bucket}</span>
              <h3>{hit.title}</h3>
              <p>{hit.snippet}</p>
              {hit.source_url && <a href={hit.source_url} target="_blank" rel="noreferrer">Open source</a>}
            </div>
          ))}
        </div>
      </article>
    </section>
  );
}
