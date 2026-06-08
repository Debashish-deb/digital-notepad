import fs from 'fs';
import path from 'path';
import readline from 'readline';

// Using relative import for the projectsCatalog to access project_code and folder_path
// But since this is a script, we can just read the file and extract it
const projectsCode = fs.readFileSync(path.join(process.cwd(), 'src', 'data', 'projectsCatalog.js'), 'utf8');
const projectsMatch = projectsCode.match(/export const projectsCatalog = (\[[\s\S]+?\]);/);
let projects = [];
if (projectsMatch) {
  try {
    projects = new Function('return ' + projectsMatch[1])();
  } catch(e) { console.error('Error parsing projects catalog'); }
}

const INPUT_DIR = process.env.DATABASE_ROOT || path.join(__dirname, '../../../../DIGITIZED_OUTPUT_ULTRA/DIGITIZED_OUTPUT_ULTRA/00_DATABASE_LEVEL');
const OUTPUT_DIR = path.join(process.cwd(), 'public', 'database');
const DOCS_DIR = path.join(OUTPUT_DIR, 'docs');
const PROCESSED_DIR = path.join(process.cwd(), 'public', 'processed');

const CATALOG_FILE = path.join(INPUT_DIR, 'OMEIA_SEARCH_CATALOG.jsonl');
const CHUNKS_FILE = path.join(INPUT_DIR, 'OMEIA_ALL_CHUNKS.jsonl');
const DOCS_FILE = path.join(INPUT_DIR, 'OMEIA_ALL_DOCUMENTS.jsonl');

const WIKI_SECTIONS = new Set([
  '00_General_Knowledge',
  '01_Overview',
  '02_Orders',
  '03_Social',
  '04_Wet_Lab'
]);

// Hardcoded fallback mappings for edge cases
const MANUAL_PROJECT_MAPPINGS = {
  '36_36_metabolomics': 'Metabolomics',
  '21_36_metabolomics-20260602t172108z-3-001': 'Metabolomics',
  '07_2._methods_and_experiments-20260602t110526z-3-001': 'HaikalaCollab'
};

function getProjectCodeForSection(sec) {
  if (!sec) return null;
  if (WIKI_SECTIONS.has(sec)) return null;
  if (MANUAL_PROJECT_MAPPINGS[sec]) return MANUAL_PROJECT_MAPPINGS[sec];

  let matchedProject = null;
  projects.forEach(p => {
    const code = p.project_code.toLowerCase();
    const folder = (p.folder_path || '').toLowerCase();
    if (sec.toLowerCase().includes(code) || (folder && sec.toLowerCase().includes(folder.split('-')[0]))) {
      matchedProject = p.project_code;
    }
  });
  return matchedProject;
}

async function processDatabase() {
  console.log('Building OMEIA static database & updating Project Twins...');

  if (!fs.existsSync(OUTPUT_DIR)) fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  if (!fs.existsSync(DOCS_DIR)) fs.mkdirSync(DOCS_DIR, { recursive: true });

  const wikiCatalog = [];
  const projectDocsMap = {}; // projectCode -> list of docs
  
  console.log('Loading catalog...');
  const catalogStream = readline.createInterface({ input: fs.createReadStream(CATALOG_FILE), crlfDelay: Infinity });

  for await (const line of catalogStream) {
    if (!line.trim()) continue;
    try {
      const entry = JSON.parse(line);
      let sec = entry.section;
      if (!sec || sec.trim() === '') sec = '00_General_Knowledge';
      entry.section = sec;
      
      if (WIKI_SECTIONS.has(sec)) {
        wikiCatalog.push(entry);
      } else {
        const pCode = getProjectCodeForSection(sec);
        if (pCode) {
          if (!projectDocsMap[pCode]) projectDocsMap[pCode] = [];
          projectDocsMap[pCode].push(entry);
        } else {
          // If it didn't map, put it in wiki general knowledge to avoid losing it
          entry.section = '00_General_Knowledge';
          wikiCatalog.push(entry);
        }
      }
    } catch (e) {
      console.error('Error parsing catalog line:', e.message);
    }
  }

  // Build wiki sections
  const sections = {};
  wikiCatalog.forEach(doc => {
    if (!sections[doc.section]) sections[doc.section] = [];
    sections[doc.section].push({
      id: doc.document_id,
      title: doc.filename,
      path: doc.relative_path,
      hasText: doc.has_text
    });
  });

  const sortedSections = {};
  Object.keys(sections).sort().forEach(sec => {
    sortedSections[sec] = sections[sec].sort((a, b) => a.title.localeCompare(b.title));
  });

  // Load Metadata
  console.log('Loading full document metadata...');
  const metadataMap = {};
  if (fs.existsSync(DOCS_FILE)) {
    const docsStream = readline.createInterface({ input: fs.createReadStream(DOCS_FILE), crlfDelay: Infinity });
    for await (const line of docsStream) {
      if (!line.trim()) continue;
      try {
        const doc = JSON.parse(line);
        metadataMap[doc.document_id] = {
          source: doc.source,
          classification: doc.classification,
          extraction_metadata: doc.extraction_metadata,
          converted_at: doc.converted_at
        };
      } catch (e) {}
    }
  }

  // Load Chunks
  console.log('Aggregating full text from chunks...');
  const textMap = {}; // docId -> chunks
  const chunksStream = readline.createInterface({ input: fs.createReadStream(CHUNKS_FILE), crlfDelay: Infinity });

  for await (const line of chunksStream) {
    if (!line.trim()) continue;
    try {
      const chunk = JSON.parse(line);
      const docId = chunk.document_id;
      if (!textMap[docId]) textMap[docId] = [];
      textMap[docId].push(chunk);
    } catch (e) {}
  }

  // Write Wiki Docs
  console.log('Writing Wiki document files...');
  for (const doc of wikiCatalog) {
    const docId = doc.document_id;
    let fullText = '';
    if (textMap[docId]) {
      textMap[docId].sort((a, b) => (a.ordinal || 0) - (b.ordinal || 0));
      fullText = textMap[docId].map(c => c.text).join('\n\n');
    }
    const docOutput = { ...doc, full_text: fullText, metadata: metadataMap[docId] || null };
    fs.writeFileSync(path.join(DOCS_DIR, `${docId}.json`), JSON.stringify(docOutput));
  }

  // Write Wiki Catalog
  console.log('Writing Wiki catalog index...');
  fs.writeFileSync(
    path.join(OUTPUT_DIR, 'catalog.json'),
    JSON.stringify({
      generated_at: new Date().toISOString(),
      total_documents: wikiCatalog.length,
      sections: sortedSections
    })
  );

  // Update Project Twins
  console.log('Updating Project Twins in public/processed/ ...');
  for (const [pCode, docs] of Object.entries(projectDocsMap)) {
    const twinPath = path.join(PROCESSED_DIR, `${pCode}.json`);
    if (!fs.existsSync(twinPath)) {
      console.warn(`Twin for ${pCode} not found at ${twinPath}, skipping.`);
      continue;
    }
    
    let twin = null;
    try {
      twin = JSON.parse(fs.readFileSync(twinPath, 'utf8'));
    } catch (e) {
      console.error(`Error parsing twin for ${pCode}: ${e.message}`);
      continue;
    }

    const document_index = [];
    const vector_chunks = [];

    for (const doc of docs) {
      const docId = doc.document_id;
      const chunks = textMap[docId] || [];
      chunks.sort((a, b) => (a.ordinal || 0) - (b.ordinal || 0));

      const excerpt = chunks.length > 0 ? chunks[0].text.substring(0, 400) : '';

      document_index.push({
        document_id: docId,
        path: doc.relative_path,
        title: doc.filename,
        has_text: doc.has_text,
        excerpt: excerpt,
        metadata: metadataMap[docId] || null
      });

      chunks.forEach((c, idx) => {
        vector_chunks.push({
          document_id: docId,
          source_file: doc.relative_path,
          chunk_index: idx,
          text: c.text
        });
      });
    }

    twin.document_index = document_index;
    twin.vector_chunks = vector_chunks;
    
    // Auto-update metrics
    twin.metrics = twin.metrics || {};
    twin.metrics.knowledge_chunk_count = vector_chunks.length;
    twin.metrics.extracted_document_count = document_index.length;

    fs.writeFileSync(twinPath, JSON.stringify(twin, null, 2));
    console.log(`Updated twin for ${pCode}: ${document_index.length} docs, ${vector_chunks.length} chunks.`);
  }

  console.log('Build complete!');
}

processDatabase().catch(console.error);
