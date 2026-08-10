# RAG-V2-HYBRID-RETRIEVAL-MIN

Status: `DONE`

## Goal

Improve generic local RAG v2 retrieval over the current deterministic lexical
index without UI, cloud, dependency or domain-tuning drift.

## Preconditions

- Documentation/legacy public-route cleanup is closed and validated.
- RAG v2 schema/converter/chunker/index foundations remain green.
- P0 AI Gateway real-route policy consolidation is `DONE`.

## Implemented scope

- Generic lexical candidate retrieval with Unicode tokenization.
- Deterministic metadata/exact-match boosts: exact text phrase, source
  name/path, section/sheet structure, table element type, optional generic
  confidence/freshness metadata.
- Pre-ranking privacy label filter, selected document/source path filter, and
  source fingerprint freshness check.
- Per-document source diversity cap (default: two chunks per document).
- Deterministic tie-breaking: score descending, then document ID / source path /
  chunk ID ascending.
- Transparent `SearchSummary` with indexed/eligible/candidate/result counts,
  filter breakdown, diversity-limited count, query coverage, and safe
  insufficiency reasons.
- New public types: `SearchOptions`, `SearchResult` (extended), `SearchSummary`,
  `SearchResponse`.
- Backward-compatible `search(query, limit=...)` list API preserved.
- Focused tests: 18 passed covering phrase ranking, metadata signals, table
  signal, privacy/source/stale filtering, diversity, determinism, and tokenless
  query handling.

## Acceptance evidence

- Focused RAG v2 index/chunking/hard-code tests: **18 passed** in 0.55s.
- Documentation contract: PASS.
- Compile (`py -3 -m compileall src tests`): PASS.
- Full test suite: **907 passed** in 12.94s.
- CLI audit (`py -3 -m aios_habit.cli audit`): PASS, no errors or warnings.
- Workspace Chat import: PASS (expected Streamlit bare-mode warnings only).
- `git diff --check` and `git diff --cached --check`: PASS.
- Hard-code guard (`test_rag_v2_hardcode_guard.py`): PASS; no protected terms
  in RAG v2 source or comments.

## Explicitly excluded

- No vector database, embedding, or cloud/provider/network call.
- No new dependency added.
- No Workspace Chat UI or runtime migration; legacy `rag_search.py` path
  remains the active Workspace Chat retrieval.
- No project-specific routing, intent, or domain hard-code in RAG v2.
- No roadmap/changelog status change within this implementation gate; status
  sync is a separate docs-only operation.

## References

- Architecture: `docs/rag_v2/RAG_V2_DESIGN.md`
- External patterns consulted: Haystack `DocumentJoiner`, LlamaIndex
  `QueryFusionRetriever`, Vespa hybrid-search tutorial, SQLite FTS5.
