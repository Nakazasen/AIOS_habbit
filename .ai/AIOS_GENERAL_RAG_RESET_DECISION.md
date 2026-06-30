# AIOS General RAG Reset Decision

## Decision

AIOS must become a general RAG core plus optional domain playbooks.

The manufacturing/MOM/WMS playbook is useful, but it must not be hidden as core
intelligence and must not be used to imply general NotebookLM replacement.

## Why

The MOM/WMS benchmark helped expose retrieval and synthesis weaknesses, but it
cannot prove general replacement across the owner's whole work. Optimizing the
system for that benchmark would create a deceptive product: answers could sound
strong because they are tuned to one domain, while failing on HR, accounting,
Japanese learning, contracts, IT logs, and normal manuals.

## NotebookLM Comparison Discipline

Every comparison must distinguish:

- deterministic local evidence engine
- AI-assisted answer synthesis

NotebookLM uses model synthesis. A fair NotebookLM comparison requires AIOS to
use a privacy-safe model bridge or clearly label the comparison as deterministic
AIOS evidence synthesis versus NotebookLM model synthesis.

## Claims

- General NotebookLM replacement: NO / NOT YET.
- Daily replacement: NO / NOT YET.
- MOM-only replacement: NO / NOT YET.
- Global NotebookLM parity: NO.
- P1.0 opened: NO.

No replacement claim is allowed until multi-domain benchmarks and human review
prove it.

## Implementation Direction

- Keep ingestion, search, evidence packs, citations, privacy, and evaluation in
  the generic core.
- Move domain vocabulary and domain-specific next-action text into explicit
  playbooks.
- Default domain mode is `general`.
- Default answer mode is deterministic and bounded.
- Model-assisted mode is a separate bridge with privacy and citation checks.
- Claim guard blocks overclaims before reports or UI can present them.
