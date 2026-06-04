# 02 — Mature Data Schema

## Why this schema is mature

A small MVP schema will break quickly because this platform must support many projects, many modalities, repeated samples, changing marker panels, reprocessing, clinical endpoint revisions, public validation data, model versions, vector retrieval, and audit logs.

The database should use PostgreSQL schemas as separate namespaces:

```text
core      projects, cohorts, patients, specimens, samples, markers, cell types
clinical  clinical dictionaries, summaries, observations, treatments, outcomes
assay     assay runs, panels, channel maps, sequencing/GeoMx/image metadata
files     file registry, checksums, dataset snapshots, file lineage
spatial   image processing, segmentation, quantification, cell table manifests, QC
features  feature definitions, feature matrices, analysis-ready datasets
omics     optional omics-specific summaries and manifests
ml        model registry, training runs, predictions, metrics
rag       documents, chunks, embedding jobs, vector registry, answer traces
kg        entity registry and evidence-backed assertions
security  users, roles, project access policies
audit     event logs and tool execution logs
ops       pipeline/task operations
```

## ID strategy

Use UUIDs internally and stable human-readable codes externally.

Examples:

```text
project_code: SPACE, EyeMT, KRAS
cohort_code: ONCOSYS_OVA_B1
patient_code: PSEUDO_001
sample_code: S253_iOme
assay_run_code: SPACE_TCYCIF_BATCH2_2025
pipeline_run_code: imageproc_2026_06_02_001
```

Never rely only on file names.

## Patient and sample model

A patient can have many specimens. A specimen can have many samples. A sample can have many assays.

```text
patient
 └─ specimen
     └─ sample
         ├─ tCyCIF assay
         ├─ GeoMx assay
         ├─ WES/WGS assay
         └─ RNA/scRNA/spatial transcriptomics assay
```

### Patient table

Stores pseudonymized research identity only.

Important fields:

- patient_code
- source_system
- diagnosis year or broad bin if approved
- disease ontology
- sensitivity level
- status
- metadata JSON

Direct hospital identity mapping, if ever needed, must be isolated under security-restricted tables, not normal research schema.

### Sample table

Important fields:

- sample_code
- patient_id
- specimen_id
- project_id
- cohort_id
- sample type
- anatomical site
- timepoint
- batch
- QC status
- sensitivity level
- metadata

## Clinical model

Use both summary and long-format observation tables.

### Clinical summary table

Optimized for common queries:

- histology
- stage
- grade
- diagnosis age
- BRCA status
- HRD/HRP status
- platinum response
- PARPi exposure
- PFS/PFI/OS
- progression event
- death event
- residual disease
- curation version

### Clinical observation table

Flexible future-proof table:

- patient_id
- sample_id optional
- variable_id
- value_text
- value_numeric
- value_date
- value_boolean
- unit
- source file
- source column
- curation status
- confidence

This allows new variables without database redesign.

## Clinical dictionary

Every clinical variable must have a dictionary row:

- variable name
- display name
- data type
- allowed values
- units
- missing value codes
- valid range
- definition
- curation rule
- source columns
- sensitivity level

Without this, the AI system should not run survival or response analysis.

## Assay model

Use one general `assay_run` table plus modality-specific tables/manifests.

Assay types:

- tcycif
- cycif
- geomx
- wes
- wgs
- bulk_rna
- scrna
- cosmx
- xenium
- he_wsi
- flow
- mass_spec

## Marker and channel model

Do not hardcode channel order only inside scripts.

Store:

- panel
- marker
- marker aliases
- channel map
- channel index
- DAPI/background/failed flags
- round/cycle
- antibody clone
- fluorophore
- exposure
- panel version

This prevents confusion when panels change across batches.

## File registry

Every file should have:

- file_id
- storage backend
- URI/path
- file name
- extension
- role
- size
- SHA256
- project
- sample optional
- assay optional
- sensitivity level
- status
- metadata

Storage backend examples:

- local
- pdrive
- lumi_scratch
- lumi_project
- s3
- minio
- google_drive_reference
- github
- external_url

## Pipeline lineage

Every processing run should have:

- pipeline name
- pipeline version
- git commit
- container image/digest
- executor
- started/finished timestamps
- status
- config JSON
- input file IDs
- output file IDs
- logs
- QC metrics

This matters because the same sample may be reprocessed with different segmentation methods or channel maps.

## Cell-level data scaling

Do not force all per-cell data into PostgreSQL.

Recommended production design:

```text
Large cell tables: Parquet / H5AD / Zarr / RDS in file/object store
PostgreSQL: cell_table_manifest + schema + row count + QC + feature summaries
```

Optional relational cell tables can exist for small/demo subsets, but not as the default for millions of cells.

## Feature model

Every feature must have a formal definition.

Feature definition fields:

- feature_name
- display name
- feature group
- entity level
- data type
- unit
- source modality
- calculation method
- required inputs
- parameters
- version
- owner
- status

Examples:

```text
cd8_tim3_neighbor_fraction_r50
tumor_stroma_interface_cd8_density
hla_dpb1_tumor_mean_intensity
myeloid_component_count
rcn7_fraction
tls_area_fraction
geomx_tcell_exhaustion_ssgsea
kras_amp_status
```

## Feature matrix model

Feature matrices should be snapshots:

- matrix code
- matrix version
- project
- entity level
- row count
- feature count
- file ID
- inclusion criteria
- exclusion criteria
- source pipeline runs
- QC status

## RAG metadata model

PostgreSQL stores vector traceability; Qdrant stores the vector.

Tables:

- document_source
- document_version
- document_chunk
- embedding_job
- vector_point_registry
- retrieval_trace
- answer_trace
- answer_citation

## Knowledge graph registry

Even if Neo4j stores graph data, PostgreSQL should keep an entity/assertion registry.

Entity types:

- Marker
- Gene
- Protein
- CellType
- CellState
- Disease
- Drug
- Pathway
- ClinicalOutcome
- SpatialFeature
- Project
- Publication
- Protocol

Assertions require evidence and confidence.

## ML model registry

Every model needs:

- model code
- model version
- algorithm
- training dataset
- feature set
- hyperparameters
- CV design
- metrics
- predictions
- feature importance
- validation cohort
- artifact file

No model output should be shown without sample count and validation context.

## Security and audit

Use:

- users
- roles
- user roles per project
- project access policy
- max sensitivity allowed
- event log
- tool execution log

Audit every answer, retrieval, export, and analysis run.
