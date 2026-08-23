# Chunk Evaluation Fixtures

This directory contains frozen local evaluation fixtures for the
evidence-based chunking evaluation (Feature 006).

## Privacy Rules

- **DO NOT** embed raw `local_only` document text in any committed fixture.
- Reference documents by source identity and path only.
- Anonymize any user-identifiable content in question text.
- All fixtures must remain local; they must not be transmitted to cloud services.

## Structure

```
chunk_evaluation/
├── README.md               # This file
├── cases_v1.json           # Frozen question-evidence case set
└── corpus_manifest.json    # Source identity and fingerprint manifest
```

## Versioning

- `cases_v1.json` and `corpus_manifest.json` are frozen once created.
- Any change to the case set or corpus requires a new version suffix.
- All evaluation runs must record the fingerprint of the case set and corpus
  used, to ensure reproducibility.
