# 08 — Documentation and Script Intake

## What to provide safely

Useful without data:

- project summaries
- protocols/SOPs
- marker panels/channel maps
- script files/notebooks
- README files
- dependency files
- folder structures
- QC templates
- column dictionaries
- meeting decision logs
- manuscript outlines
- public paper lists
- synthetic examples

## Intake workflow

```text
receive file
 → classify sensitivity
 → add manifest row
 → parse/clean
 → chunk
 → extract entities
 → embed
 → index in Qdrant
 → register vector point
 → run retrieval tests
 → approve
```

## Script audit fields

For each script, extract:

- file path
- language
- pipeline stage
- imports/dependencies
- CLI args
- input paths
- output paths
- hardcoded paths
- functions/classes
- expected outputs
- known issues
- project assumptions
- manifest support

## Script modernization target

Every script should ideally support:

```bash
python script.py \
  --input input_file \
  --output-dir output_dir \
  --sample-code SAMPLE \
  --project-code PROJECT \
  --config config.yaml \
  --manifest-out manifest.yaml \
  --log-file run.log
```

## Output manifest target

```yaml
script_name:
script_version:
git_commit:
started_at:
finished_at:
status:
inputs:
outputs:
parameters:
environment:
warnings:
errors:
```

## Redaction checklist

Remove before upload:

- patient names
- hospital IDs
- exact direct identifiers
- access tokens
- passwords
- SSH keys
- unapproved patient rows
- raw unredacted reports
