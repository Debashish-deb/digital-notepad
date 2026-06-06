# Refresh Schedule

Recommended schedule:

- Färkkilä website crawl: weekly
- Publication metadata search: weekly
- Dataset registry update: monthly
- Internal documents: on upload or folder refresh
- Qdrant index health: daily
- Evaluation tests: after every ingestion batch

Example cron-style jobs:

```txt
0 3 * * MON  crawl_farkkila_public_site
30 3 * * MON discover_publications
0 4 1 * *   update_dataset_registry
0 2 * * *   check_qdrant_index_health
```

Every refresh job should produce:

- job_id
- status
- records discovered
- records indexed
- errors
- evaluation summary
