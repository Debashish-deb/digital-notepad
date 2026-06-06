# Privacy and Copyright Policy

## Public sources

Allowed:

- public website pages
- metadata from PubMed/Crossref/OpenAlex
- abstracts
- open-access full text when license permits
- public dataset metadata

Restricted:

- closed-access full text unless user has rights and the document is stored internally
- full copyrighted articles from publisher pages without license

## Internal sources

Internal SOPs, protocols, project folders, notebooks, and clinical metadata must be marked `internal` or `restricted`.

## Patient identifiers

Before sending any text to an external LLM:

- run privacy guardrail
- redact patient IDs, emails, phone numbers, dates of birth, MRNs, and other direct identifiers
- prefer local LLM for sensitive/internal data

## Answering policy

- research support only
- not medical advice
- cite sources for claims
- refuse or qualify unsupported answers
