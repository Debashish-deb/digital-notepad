# Data Digitalization Pipeline

## Overview
The Data Digitalization Pipeline is a professional, end-to-end system for converting raw laboratory documents (PDFs, Word docs, Spreadsheets, Text) into structured, canonical JSON and vector-search-ready chunks. 

Unlike the Raw Asset Vault (which primarily tracks file paths, metadata, and handles discovery), the Digitalization Pipeline actually **extracts, normalizes, and stores the real text content** in PostgreSQL.

## Architecture

1. **Manifest Scan** (`source_file_manifest`)
   Discovers files on DataCloud WebDAV, P-drive, or local disk. Records logical path and checksum. Does not extract text.

2. **Extraction** (`extracted_document`)
   Reads actual contents using `document_extraction.py`. Preserves raw text, tables, and extractor warnings.

3. **Canonicalization** (`canonical_document`)
   Converts raw text into a standard `schema_version: 1.0` JSON. Includes:
   - Document type & domain classification
   - Regex-based entity extraction (emails, URLs, order numbers)
   - Secret redaction (passwords, API keys replaced with `[REDACTED: vault_ref_xxx]`)

4. **Validation**
   Ensures the document is not a "path-only fake" (where the content is just the file path). Enforces length constraints.

5. **Chunking** (`document_chunk`)
   Splits validated canonical text into RAG-ready overlapping chunks. Embeds metadata (document ID, section heading) into each chunk.

## Database Tables
All tables are in the `platform` schema:
- `source_file_manifest`
- `digitalization_job`
- `extracted_document`
- `canonical_document`
- `document_chunk`
- `digitalization_event_log`

## Running the Pipeline

**Via CLI:**
```bash
python scripts/digitalization/run_digitalization.py --provider local --root ../OMEIA-database --max-files 100
```

**Via UI:**
Navigate to **Data & Storage > Data Digitalization** in the FARKkI Lab Assistant.

## Security & Secrets
Secrets (passwords, AWS keys, bearer tokens) are intercepted before Canonicalization. They are entirely removed from `canonical_text` and RAG `document_chunk` records to prevent accidental exposure to LLMs.
