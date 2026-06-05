# 04 — Knowledge Graph Design

## Why a knowledge graph?

Vector search finds similar content. A graph helps answer relationship questions.

Example:

```text
TIM-3 → HAVCR2 → T-cell exhaustion → immune escape → platinum resistance → HGSC
```

A graph should not replace statistics. It helps retrieve biological context and evidence.

## Node types

```text
Project
Cohort
Patient
Sample
Specimen
AssayRun
FileObject
PipelineRun
Marker
Gene
Protein
CellType
CellState
Pathway
SpatialFeature
ClinicalVariable
ClinicalOutcome
Drug
Disease
Publication
Protocol
DocumentChunk
AnalysisResult
Model
Assertion
```

## Relationship types

```text
HAS_COHORT
CONTAINS_PATIENT
HAS_SAMPLE
DERIVED_FROM
MEASURED_BY
PRODUCED_FILE
CONSUMED
PRODUCED
ALIAS_OF
ENCODES
MEASURES
EXPRESSES
CHARACTERIZED_BY
INVOLVES
ASSOCIATED_WITH
COMPUTED_FROM
RELATES_MARKER
RELATES_CELLTYPE
SUPPORTS
MENTIONS
```

## Assertion pattern

Do not make unsupported biological edges. Use assertion nodes.

```text
(:Marker {name:"TIM-3"})
  -[:SUBJECT_OF]->
(:Assertion {predicate:"ASSOCIATED_WITH", confidence:0.8})
  -[:OBJECT_OF]->
(:CellState {name:"T-cell exhaustion"})
```

Evidence connects to assertion:

```text
(:Publication)-[:SUPPORTS]->(:Assertion)
(:ProjectNote)-[:SUGGESTS]->(:Assertion)
(:AnalysisResult)-[:SUPPORTS]->(:Assertion)
```

## Alias examples

```text
TIM-3 = TIM3 = HAVCR2 protein marker
HLA-DPB1 = MHCII-related antigen-presentation marker
CD8a = CD8 T-cell marker depending panel
Iba1 = AIF1-related myeloid/macrophage marker
```

## GraphRAG workflow

1. Extract entities from question.
2. Canonicalize aliases.
3. Query graph for related entities and evidence.
4. Retrieve text chunks from Qdrant.
5. Query structured values from PostgreSQL.
6. Run tools if needed.
7. Generate answer with evidence.

## What goes where?

| Content | PostgreSQL | Qdrant | Neo4j |
|---|---|---|---|
| Patient outcome values | yes | only approved summaries | limited relation metadata |
| SOP text | metadata | yes | mentioned entities |
| Marker aliases | yes | optional | yes |
| Biological relationships | assertion registry | source chunks | yes |
| Sample similarity | feature metadata | yes | optional |
| Pipeline lineage | yes | no | optional |
