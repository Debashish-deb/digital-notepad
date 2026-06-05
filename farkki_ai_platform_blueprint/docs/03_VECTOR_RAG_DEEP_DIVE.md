# 03 — Vector and RAG Deep Dive

## What is a vector?

A vector is a list of numbers that represents meaning or feature similarity. In this platform, vectors can represent:

- protocol chunks
- project-note chunks
- script/function chunks
- publication chunks
- sample summaries
- numeric spatial feature profiles
- analysis-result summaries
- user queries

A vector is useful only when it has a source, model name, dimension, distance metric, metadata payload, access policy, and trace back to the original object.

## Minimum vector point contract

```yaml
point_id: stable unique ID
collection: qdrant collection name
vector:
  name: text
  values: [float]
  dimension: integer
  model: embedding model
  distance: cosine
payload:
  schema_version: 1
  source_type: protocol | script | project_note | publication | sample_summary | feature_profile
  source_uuid: uuid or stable code
  chunk_id: uuid or null
  title: text
  text_preview: text
  project_code: SPACE
  modality: [tcycif, geomx]
  sensitivity_level: public | internal | restricted | confidential
  allowed_project_codes: [SPACE]
  contains_patient_level_data: false
  contains_direct_identifier: false
  embedding_model: model name
  embedding_dimension: 384/768/1024/1536/etc
  created_at: timestamp
```

## What should be embedded?

### Documents

Embed cleaned chunks with title, section, and text.

Good:

```text
Title: EyeMT project log
Section: ROI and spatial-community integration
Text: Interaction hubs and GeoMx ROIs should be compared at similar biological/spatial scale...
```

Bad:

```text
random OCR text with no source, no title, no project, no permissions
```

### Scripts

Chunk by function/class/notebook section.

Each chunk should include:

- repository
- file path
- language
- function/class name
- input assumptions
- output assumptions
- pipeline stage
- project tag
- sensitivity level

### Publications

Embed:

- title
- abstract
- methods/result section summaries if available and allowed
- DOI/PMID/year/journal metadata

### Sample summaries

Use only approved de-identified summaries, not raw patient records.

Example:

```text
Sample SYNTH_SAMPLE_001, project SPACE, tCyCIF available.
Markers include CD4, CD8a, CD20, CD11c, CD163, TIM-3, HLA-DPB1.
Spatial profile: high CD8 density and high TIM-3 neighborhood score.
```

### Numeric feature vectors

For sample similarity, do not rely only on text. Use actual feature vectors:

```text
[z_cd8_density, z_tim3_cd8_fraction, z_hla_dpb1_mean, z_myeloid_density, z_tsi_distance, z_tls_score]
```

These belong in a dedicated `spatial_feature_profiles` collection.

## Recommended Qdrant collections

```text
doc_chunks
script_chunks
literature_chunks
sample_summaries
spatial_feature_profiles
```

## Payload fields to index

At minimum:

- source_type
- project_code
- modality
- sensitivity_level
- document_id/source_file_id
- sample_code/entity_code
- status
- created_at

Qdrant payload filters are essential because vector search alone does not understand project permissions.

## Chunking rules

### Protocols and project docs

- 500–900 tokens per chunk
- 80–150 token overlap
- keep headings and table rows intact
- do not split action-item tables randomly

### Scripts

- function/class-level chunks
- include local context
- do not chunk line-by-line unless necessary

### Meeting logs

- chunk by date, decision, caveat, action item
- keep sample caveats together

## Retrieval workflow

```text
question
 → normalize entities and aliases
 → check permissions
 → SQL lookup for structured facts
 → Qdrant vector/keyword retrieval
 → Neo4j graph retrieval if biological relation needed
 → rerank sources
 → tool execution if analysis is needed
 → answer with citations, counts, caveats
```

## Hybrid search

Use semantic + lexical.

Why:

- marker names are short exact terms: TIM-3, HLA-DPB1, CD11c, Iba1
- sample IDs are exact
- project codes are exact
- semantic embeddings may miss exact identifiers

## Security for vectors

Every vector point must include:

```yaml
sensitivity_level:
allowed_project_codes:
contains_patient_level_data:
contains_direct_identifier:
```

If a query is documentation-only, block restricted patient-level vectors.

## Vector lifecycle

```text
source file
 → checksum
 → parse
 → clean text
 → chunk
 → classify sensitivity
 → extract metadata/entities
 → embed
 → upsert Qdrant
 → register point in PostgreSQL
 → test retrieval
```

If the source changes:

```text
new document_version
new chunks
old points deprecated or revoked
new points active
```

## Vector quality checks

For every ingestion batch:

- no empty chunks
- required payload fields exist
- embedding dimension matches collection
- sensitivity level exists
- project filter exists
- source file resolves
- retrieval smoke test passes
- no direct identifiers in payload
