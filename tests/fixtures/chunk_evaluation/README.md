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
├── README.md                 # This file
├── cases_v1.json             # Frozen question-evidence case set
├── corpus_manifest.json      # Identity-only fixture (never a baseline)
├── corpus_public_v1.json     # Historical short public corpus
├── corpus_public_v2.json     # Historical CJK-lengthened corpus (ASCII Vietnamese table)
├── corpus_public_v3.json     # Current file-backed public evaluation corpus
├── docs/                     # Invented multilingual markdown sources (current = v3)
└── tables/                   # JSON tables materialized to xlsx at eval time
```

## Versioning

- `cases_v1.json` and `corpus_manifest.json` are frozen once created.
- Any change to the case set or corpus requires a new version suffix.
- `corpus_public_v1.json` is historical: CJK markdown was mostly under 900
  characters, so the 900-char splitter barely ran. Do not re-run v1 against
  the current `docs/` files (checksums will fail closed).
- `corpus_public_v2.json` lengthened Japanese/Chinese procedure paragraphs
  above 900 characters. The Vietnamese material-standards table was still
  ASCII (`nguyen lieu`) while `vi-002` asks `nguyên liệu`, so hybrid retrieval
  preferred the Chinese raw-material table. Fingerprints are not comparable
  to v1.
- `corpus_public_v3.json` keeps the v2 CJK documents and writes the Vietnamese
  table with diacritics and `nhập kho` in the header/sheet so `vi-002` shares
  terms with its source. Fingerprints are not comparable to v1 or v2.
- All evaluation runs must record the fingerprint of the case set and corpus
  used, to ensure reproducibility.
