# RAG-V2-HYBRID-RETRIEVAL-MIN

Status: `PLANNED`

## Goal

Improve generic local RAG v2 retrieval over the current deterministic lexical
index without UI, cloud, dependency or domain-tuning drift.

## Preconditions

- Documentation/legacy public-route cleanup is closed and validated.
- RAG v2 schema/converter/chunker/index foundations remain green.

## Intended scope

Generic lexical candidate retrieval, deterministic metadata/exact-match boosts,
privacy/fingerprint filtering, source diversity and focused tests. No vector DB,
provider/network call, source-specific hard-code or Workspace Chat UI change.

## Acceptance evidence

Focused RAG v2 tests, full test/audit, hard-code guard, privacy behavior, and a
local-only evaluation note. See `docs/rag_v2/RAG_V2_DESIGN.md` for architecture.
