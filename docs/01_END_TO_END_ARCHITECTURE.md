# 01 — End-to-End Architecture

## Main layers

```text
1. Source layer
2. Ingestion and registry layer
3. Storage layer
4. Pipeline and feature-extraction layer
5. Statistics/ML/tool layer
6. Retrieval layer
7. LLM/copilot layer
8. Security/audit layer
```

## 1. Source layer

Sources can include:

- raw or processed tCyCIF/CycIF images
- masks and quantification files
- GeoMx DCC/PKC/annotation files
- WES/WGS/RNA/scRNA/CosMx/Xenium outputs
- clinical Excel/CSV schemas and curated exports
- SOPs, protocols, project logs, meeting notes
- script repositories and notebooks
- public literature and dataset metadata

At this stage, no real patient data is required. You can start with only schemas, scripts, folder trees, and synthetic placeholders.

## 2. Ingestion and registry layer

The ingestion layer does not “analyze”. It records what exists.

It should create:

- project registry
- cohort registry
- sample registry
- file registry
- assay registry
- clinical variable dictionary
- document manifest
- pipeline run manifest
- feature definition registry

Every object should have:

- stable ID
- source path/URI
- version
- checksum if a file
- project link
- sensitivity level
- status
- owner/contact
- created/updated timestamp

## 3. Storage layer

### PostgreSQL

Stores truth and metadata:

- projects, cohorts, patients, samples
- clinical summary and clinical observations
- assays, panels, channels, pipeline runs
- file registry and checksums
- feature definitions and feature matrices
- model registry
- RAG metadata and audit logs

### File/object storage

Stores large artifacts:

- OME-TIFFs
- masks
- Parquet/H5AD/Zarr/RDS
- large expression matrices
- analysis report bundles
- figures

### Qdrant

Stores vectors for similarity search:

- document chunks
- script chunks
- literature chunks
- sample summaries
- spatial feature profiles

### Neo4j

Stores relationships:

- marker aliases
- cell type relationships
- disease/drug/pathway relations
- evidence-backed biological assertions
- project/sample/assay lineage where useful

## 4. Pipeline layer

Existing image-processing should be treated as production pipeline components:

```text
BaSiC illumination correction
Ashlar stitching/registration
Mesmer or StarDist segmentation
Quantification
Filtered-image workflow
Phenotyping
SPACEstat / Scimap / spatial feature extraction
Cylinter or QC review
```

Each pipeline stage should produce a manifest:

```yaml
stage_name:
sample_code:
input_files:
output_files:
software_version:
git_commit:
container_image:
parameters:
qc_metrics:
status:
logs:
```

## 5. Feature layer

The feature layer converts raw outputs into analysis-ready tables.

Feature levels:

- patient
- sample
- specimen
- image
- ROI
- spatial community
- cell
- cell-pair/neighborhood

Feature groups:

- marker intensity
- morphology
- cell abundance
- cell density
- nearest-neighbor distance
- hotspot
- spatial co-occurrence
- tumor-stroma interface
- TLS/milky spot
- recurrent cellular neighborhood
- pathway score
- clinical/genomic status

## 6. Statistics and tool layer

Tools should be callable by the copilot but versioned and logged.

Examples:

- Kaplan-Meier
- Cox proportional hazards
- log-rank
- Wilcoxon/Mann-Whitney
- mixed models
- DESeq2/limma
- pathway enrichment
- Random Forest / XGBoost / elastic net
- feature importance
- external validation

LLM answers must reference stored tool outputs, not guess them.

## 7. Retrieval layer

A research question may require:

- SQL retrieval for structured clinical/sample/feature values
- vector retrieval for docs/scripts/literature
- graph retrieval for biological relationships
- tool execution for statistics

The final answer should include:

- cohort definition
- sample/patient count
- data sources
- pipeline/feature versions
- statistical method if used
- citations/evidence
- limitations

## 8. Security and audit layer

Every query and answer should be logged.

Audit:

- who asked
- what was retrieved
- which projects were accessed
- what sensitivity level was used
- which tools ran
- which answer was produced
- whether anything was exported

## Request lifecycle

```text
User asks question
 → authenticate user
 → classify intent
 → check project permissions
 → extract markers/cell types/outcomes/projects
 → query PostgreSQL
 → retrieve vectors from Qdrant with access filters
 → query Neo4j if biological relation needed
 → run Python/R tools if calculation needed
 → assemble evidence
 → generate answer
 → log retrieval, tool, and answer trace
```
