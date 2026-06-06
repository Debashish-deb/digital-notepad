# Manual QA Checklist

## Ingestion

- [ ] Färkkilä website crawl runs without errors.
- [ ] Crawler respects allowlist and rate limit.
- [ ] Publication discovery returns lab-relevant publications.
- [ ] Dataset registry includes GSE211956, EGA phs002262, TCGA-OV, CPTAC references.
- [ ] Closed-access papers are stored as metadata/abstract/snippets only.
- [ ] Internal documents are marked internal/restricted.

## Indexing

- [ ] Qdrant collection `research_knowledge` exists.
- [ ] Named vector `text` exists.
- [ ] Chunks upsert successfully.
- [ ] Chunks are retrievable by query.
- [ ] No flat/named vector schema conflict.

## Search

- [ ] Search `MHC class II HGSC` returns the MHC class II spatial atlas.
- [ ] Search `tertiary lymphoid structures ovarian cancer` returns TLS sources.
- [ ] Search `GSE211956` returns the dataset.
- [ ] Search results include title, snippet, source URL, score, and navigation action.
- [ ] Restricted/internal results are hidden from unauthorized users.

## AI answers

- [ ] Assistant cites sources.
- [ ] Assistant does not invent DOI/PMID/URLs.
- [ ] Assistant admits uncertainty when no indexed source exists.
- [ ] Assistant distinguishes public literature from internal lab documents.
- [ ] Assistant redacts patient identifiers before external LLM calls.

## UI

- [ ] Research Knowledge Admin screen loads.
- [ ] Status panel shows index health.
- [ ] Ingestion actions show progress/errors.
- [ ] Search result cards are clickable.
- [ ] Dark, light, and academic themes look good.
- [ ] Mobile layout works.

## Build/tests

- [ ] `python -m compileall app_skeleton/api` passes.
- [ ] `pytest` passes or failures are documented.
- [ ] `npm run build` passes.
