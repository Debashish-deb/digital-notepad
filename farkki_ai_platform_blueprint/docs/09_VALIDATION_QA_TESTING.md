# 09 — Validation, QA, and Testing

## Validation layers

```text
data validation
file validation
pipeline validation
feature validation
statistical validation
retrieval validation
answer validation
security validation
```

## Data validation

Check:

- required columns
- allowed values
- duplicate IDs
- missingness
- impossible dates
- impossible survival times
- sample-patient linkage
- project-cohort linkage
- units

## File validation

Check:

- file exists
- checksum
- size
- extension/type
- sample/project linkage
- duplicate content
- storage accessibility

## Pipeline validation

Check:

- input count
- output count
- runtime
- memory
- logs
- warnings/errors
- QC metrics
- software version
- container/version metadata

## Feature validation

Every feature needs:

- definition
- input columns
- code version
- unit
- range expectations
- missingness policy
- validation plot/table

## Retrieval validation questions

1. What is the tCyCIF pipeline?
2. Which scripts perform segmentation?
3. Which projects combine tCyCIF and GeoMx?
4. What are the ROI/community matching caveats?
5. Which clinical columns are needed for PFS/PFI/OS?
6. What should the LLM never calculate by itself?

## Answer validation

Answers must show:

- sources
- cohort/sample counts when relevant
- filters
- limitations
- tool run ID for statistics
- no invented values
- no unauthorized data

## Security tests

- unauthorized project retrieval blocked
- restricted vector retrieval blocked in documentation mode
- audit written for every answer
- revoked docs not retrieved
- direct identifiers absent from vector payload
