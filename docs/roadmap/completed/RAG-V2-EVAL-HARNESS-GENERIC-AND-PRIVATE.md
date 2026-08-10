# RAG-V2-EVAL-HARNESS-GENERIC-AND-PRIVATE

Status: `DONE`

## Goal

Build a local-only, generic evaluation harness inside RAG v2 to measure
retrieval and evidence quality with concrete metrics.

## Prerequisite

- `RAG-V2-HYBRID-RETRIEVAL-MIN` must be validated — `DONE`.
- `RAG-V2-GENERIC-EVIDENCE-SYNTHESIS-MIN` must be validated — `DONE`.

## Implemented scope

- New `rag_v2/eval_harness.py` module, independent of legacy `rag_benchmark.py`,
  `rag_evaluator.py`, `rag_search.py`, and `query_intent.py`.
- Generic data types: `BenchmarkConfig`, `BenchmarkQuestion`,
  `BenchmarkResult`, `BenchmarkSummary`.
- `run_benchmark(index, questions, config)`: full pipeline runner exercising
  `LocalChunkIndex.search_with_summary()` → `build_evidence_pack()` → score.
- Metrics: retrieval hit rate, document hit rate, citation source hit rate,
  insufficiency detection rate, privacy pass rate, average latency.
- Forbidden term check in evidence snippets.
- Stable reproducible benchmark ID from hash of questions + config.
- `format_benchmark_summary(summary)`: human-readable text report.
- `benchmark_summary_to_dict(summary)`: JSON-compatible serialization.
- PASS / FAIL / PASS_WITH_WARNINGS verdict from configurable thresholds.

## Acceptance evidence

- Focused eval + hard-code guard tests: **11 passed** in 0.37s.
- Documentation contract: PASS.
- Compile: PASS.
- Full test suite: **931 passed** in 25.45s.
- CLI audit: PASS, no errors or warnings.
- Workspace Chat import: PASS (expected Streamlit bare-mode warnings only).
- Hard-code guard (`test_rag_v2_hardcode_guard.py`): PASS; no protected terms.

## Explicitly excluded

- No Workspace Chat UI or runtime migration.
- No cloud/provider/LLM call, credential, or new dependency.
- No import from legacy benchmark/evaluator/search/intent modules.
- No domain-specific terms in source or comments.
- No private dataset committed to Git.
- Answer faithfulness metric deferred (requires LLM judge — future gate).

## References

- Architecture: `docs/rag_v2/RAG_V2_DESIGN.md` section 13.
- Legacy pattern: `rag_benchmark.py` (consulted, not imported).
