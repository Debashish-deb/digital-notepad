# 06 — Security and Governance

## Sensitivity levels

```text
public              public papers, public GitHub docs
internal            lab docs, SOPs, scripts without patient data
restricted          pseudonymized clinical/sample/feature tables
confidential        linked multi-modal patient-level records
direct_identifier   hospital IDs, names, direct identity maps
```

The platform should begin in `documentation_only` mode.

## Access roles

```text
platform_admin
data_steward
project_pi
project_researcher
analyst
viewer
external_collaborator
```

## Permissions

```text
read_project_docs
read_project_metadata
read_pseudonymized_clinical
read_spatial_features
run_analysis
export_results
manage_project
manage_users
view_audit
```

## Vector access control

Every vector payload must include:

```yaml
sensitivity_level:
allowed_project_codes:
contains_patient_level_data:
contains_direct_identifier:
```

Never rely on the UI only. Retrieval filters must enforce permissions.

## Audit events

Log:

- login/session
- document retrieval
- patient/sample query
- vector retrieval
- graph query
- tool execution
- answer generation
- export/download
- permission failure

## External LLM use

Use cloud/frontier models for public or non-sensitive planning and code help only unless institutionally approved.

For restricted patient-level data, use:

- local model
- institution-approved API
- secure environment
- no unapproved external data transfer

## Redaction before ingestion

Remove:

- names
- hospital IDs
- exact direct identifiers
- birth dates
- private keys
- API tokens
- passwords
- unapproved pathology free text
- unapproved patient rows

## AI answer safety

The copilot must:

- cite sources
- show sample counts
- show filters
- state missing data
- call tools for statistics
- refuse unsupported clinical claims
- separate hypothesis from result
- avoid direct clinical decision support
