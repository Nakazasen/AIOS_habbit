# P1 Advanced Retrieval Decision

## Decision summary

- Vector DB before P1.0: `DEFERRED_NOT_P1_BLOCKER`
- Graph DB before P1.0: `DEFERRED_NOT_P1_BLOCKER`
- NotebookLM parity: `NOT_CLAIMED`

## Is Vector DB required before P1.0?

No current evidence proves that a vector DB is required before P1.0. The existing local SQLite FTS/BM25 foundation, evidence pack, and benchmark harness are enough to continue owner workflow validation.

A vector DB should be reconsidered only if a benchmark shows that keyword/BM25 retrieval cannot find relevant evidence for owner-critical tasks that are phrased differently from the source text.

## Is Graph DB required before P1.0?

No current evidence proves that a graph DB is required before P1.0. P1.0 should first prove the daily Case → Evidence → Action workflow.

A graph DB should be reconsidered only if cross-case relationship queries become P1-critical and cannot be represented with lightweight local metadata.

## What failure would justify advanced retrieval?

- Repeated benchmark misses on semantically equivalent questions.
- Owner cannot find known evidence through reasonable Vietnamese/English queries.
- Evidence packs include too many irrelevant chunks for daily use.
- Cross-case relation questions become required for P1.0 decisions.

## Benchmark needed to prove need

- Fake-data and real-local-only question sets.
- Expected chunks, documents, and citation labels.
- Insufficient-evidence questions.
- Privacy pass-rate checks.
- Before/after comparison against current BM25 baseline.

## NotebookLM wording policy

Allowed wording:

- "NotebookLM-safe export"
- "local evidence workflow"
- "limited retrieval benchmark"
- "NotebookLM-style benchmark criteria"

Forbidden wording unless proven by benchmark and owner acceptance:

- "NotebookLM parity"
- "NotebookLM replacement"
- "better than NotebookLM"

## Why deferring is safe

Deferring Vector DB and Graph DB keeps P1 focused on owner usability, privacy, evidence traceability, and validation. Adding advanced storage before owner acceptance would increase scope and risk without proving that it solves the current blocker.
