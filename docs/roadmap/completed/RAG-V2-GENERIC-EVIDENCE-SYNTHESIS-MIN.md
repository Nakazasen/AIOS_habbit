# RAG-V2-GENERIC-EVIDENCE-SYNTHESIS-MIN

Status: `DONE`

## Goal

Add generic evidence-grounded answer composition with citations and
insufficiency handling inside RAG v2, without creating a normal-user technical
UI or cloud-default path.

## Prerequisite

- `RAG-V2-HYBRID-RETRIEVAL-MIN` must be validated — `DONE`.

## Implemented scope

- New `rag_v2/evidence.py` module, independent of legacy `rag_evidence.py`,
  `rag_search.py`, and `query_intent.py`.
- Generic data types: `EvidencePackConfig`, `EvidenceConfidence` (enum),
  `EvidenceItem`, `PrivacySummary`, `EvidencePack`.
- `build_evidence_pack(query, response, config)`: converts `SearchResponse`
  into an `EvidencePack` with numbered citations `[1]`, `[2]`..., snippet
  clipping, configurable confidence assessment, per-document limits, and
  strictest-wins privacy summary.
- `format_evidence_for_prompt(pack)`: plain-text block with citations, source
  names/locations, scores, snippets, insufficient-evidence warnings, and
  privacy notice. Language-neutral (English) for generic core.
- `evidence_pack_to_dict(pack)`: JSON-compatible serialization with recursive
  tuple-to-list conversion.
- Confidence computed from retrieval `SearchSummary` insufficiency reasons
  plus configurable score/coverage thresholds (default: high ≥ 8.0,
  medium ≥ 3.0).
- Insufficiency reasons propagated from retrieval summary and augmented with
  evidence-level checks: `no_evidence_items`, `top_score_below_threshold`,
  `too_few_evidence_items`, `weak_term_coverage`.
- Privacy: strictest-wins across all items; `local_only`/`confidential` in any
  item makes the whole pack `local_only`.

## Acceptance evidence

- Focused evidence + hard-code guard tests: **15 passed** in 0.19s.
- Documentation contract: PASS.
- Compile: PASS.
- Full test suite: **921 passed** in 45.98s.
- CLI audit: PASS, no errors or warnings.
- Workspace Chat import: PASS (expected Streamlit bare-mode warnings only).
- `git diff --check`: PASS (LF→CRLF warnings only, expected on Windows).
- Hard-code guard (`test_rag_v2_hardcode_guard.py`): PASS; no protected terms
  in RAG v2 source or comments.

## Explicitly excluded

- No Workspace Chat UI or runtime migration.
- No cloud/provider/network call, credential, or new dependency.
- No import from legacy `rag_evidence.py`, `rag_search.py`, or
  `query_intent.py`.
- No domain-specific terms in source or comments.
- No answer composer / response generator — this gate produces evidence packs
  only.

## References

- Architecture: `docs/rag_v2/RAG_V2_DESIGN.md` sections 11–12.
- Design patterns: Haystack `DocumentJoiner`, LlamaIndex
  `QueryFusionRetriever`, legacy `rag_evidence.py` (consulted, not imported).
