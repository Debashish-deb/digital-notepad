# Retrieval Test Questions

Manual QA for unified platform search (`GET /api/platform/unified-search`) and copilot retrieval (`POST /ask`).

## Lab corpus (semantic / hybrid)

1. What is the current tCyCIF image-processing pipeline?
2. Which scripts perform segmentation?
3. Which projects combine tCyCIF and GeoMx?
4. What are the caveats around ROI-community matching?
5. Wet lab protocol for sample fixation or staining?

## Registry (keyword / hybrid)

6. Notebook entry about SPACE or EyeMT methodology
7. Wiki / SOP mentioning Gate normalization
8. Open decision about analysis strategy
9. Task assigned to a researcher with due date

## Vault & files

10. Vault asset with review_status pending or uncategorized
11. Processed twin file in overview documents (permits, guidelines)
12. Project workspace file in SPACE or EyeMT twins

## Copilot integration

13. `POST /ask` with `mode=search_only` returns `search_hits[]` without LLM (researcher role)
14. Editor `POST /ask` returns overlapping hits in `search_hits` and navigable `nav` on citations
15. Omnibox ⌘K query matches copilot retrieval for same `q` (lab bucket ordering)

## Suggestions & synonyms

16. Prefix `cyc` suggests tCyCIF / CycIF related seeds
17. Query `stardist` returns synonym hint `cell segmentation`
18. `GET /api/platform/search-suggestions` returns recent queries after logging

## Index & portable stub

19. `GET /api/platform/search-index-status` reports storage mode and lab index stats
20. Search works with `OMEIA_STORAGE_MODE=stub` when Qdrant is offline (Postgres/JSON fallback)

## Engineering contracts

21. Every hit includes `id`, `bucket`, `title`, `snippet`, `score`, optional `rank`, `highlights[]`, `nav`
22. Legacy `GET /platform/search` still returns `entry_id` / `wiki_id` / `task_id` aliases for old clients

## Expected acceptance

- Hybrid mode returns lab + file hits when Qdrant or fallback index has content
- Clicking a hit navigates to the correct module (overview, wet_lab, projects_data, etc.)
- Restricted notebook entries are omitted unless `include_restricted=true` (admin)
- Query log row written to `platform.search_query_log` when SQL migration applied
