# Tasks: Evidence-Based Chunking Evaluation — Commit E1

**Input**: Design documents from `/specs/006-chunking-evaluation/`

**Scope**: E1 only — baseline measurement. No chunker modifications, no overlap,
no default behavior changes. E2/E3/E4 tasks will be generated separately after
E1 results are reviewed.

**Gate**: E1 Prerequisite Gate CLEARED 2026-08-24 (Commit D conditional pass).

**Tests**: Included — E1 is a measurement harness; its own correctness must be
verified before trusting its output.

**Handoff status (2026-08-24)**: A draft scaffold exists in the worktree and
its unit tests pass, but **E1 is blocked**. It currently uses synthetic source
identities and deterministic test embeddings, not the real BGE-M3 hybrid
Workspace Chat path. Do not mark any task complete or treat a generated report
as a baseline until the corrective tasks below are completed.

### Required corrective work before T019

- Add an ignored local corpus manifest that maps owner-approved real documents
  and question cases to exact opaque source identities and file fingerprints.
- Route the runner through the same extraction, `StructureAwareChunker`,
  BGE-M3 hybrid retrieval, and evidence metadata path that Workspace Chat uses.
- Fail closed as `blocked` when a corpus, model, case, or query fails; never
  label a synthetic or incomplete run as `baseline`.
- Measure warm latency only after warm-up, distinguish summaries from detailed
  evidence using index metadata, and inspect every CJK chunk boundary.
- Add T008 as a true integration test with `DocumentElement` fixtures, then
  rerun the focused suite and `git diff --check`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US4)
- US3 (summary vs evidence) is deferred to E3; not in E1 scope

---

## Phase 1: Setup (Evaluation Domain Module)

**Purpose**: Create the isolated evaluation domain without touching production code

- [ ] T001 Create evaluation domain module at `src/aios_habit/rag_v2/chunk_evaluation.py` with `EvaluationCase`, `ChunkingStrategy`, `EvaluationRun`, `CaseOutcome`, and `StrategyMetrics` dataclasses matching `data-model.md`
- [ ] T002 [P] Create evaluation test module at `tests/test_chunk_evaluation.py` with schema validation tests for all dataclasses (field types, required fields, controlled values)
- [ ] T003 [P] Create evaluation fixture directory at `tests/fixtures/chunk_evaluation/` with a `README.md` explaining the fixture structure and privacy rules (no `local_only` text in committed fixtures)

---

## Phase 2: Foundational (Fixture Data + Schemas)

**Purpose**: Frozen corpus, question set, and report contract — MUST complete before measurement

**⚠️ CRITICAL**: No measurement code can run without frozen fixtures and validated schemas

- [ ] T004 Create frozen multilingual question-evidence case set at `tests/fixtures/chunk_evaluation/cases_v1.json` with at least 3 Vietnamese, 3 Japanese, and 3 Simplified Chinese cases; each case has `case_id`, `question`, `language`, `source_ids`, `expected_chunk_hints`, and `challenge_labels` per `data-model.md`; include at least 1 boundary-challenge and 1 cross-source case per language
- [ ] T005 [P] Create representative evaluation corpus fixture at `tests/fixtures/chunk_evaluation/corpus_manifest.json` listing source identities, language, document type (markdown, table, spreadsheet), and SHA-256 fingerprint; include at least one table-bearing and one multi-language document; do NOT embed raw `local_only` text — reference by path only
- [ ] T006 [P] Create report schema validator in `src/aios_habit/rag_v2/chunk_evaluation.py` that validates a result dict against the `chunk-evaluation/v1` contract (`contracts/chunk-evaluation-v1.md`); enforce `raw_local_only_text_exported: false`, required fields, and decision enum
- [ ] T007 Add fingerprinting utilities in `src/aios_habit/rag_v2/chunk_evaluation.py`: `corpus_fingerprint(manifest_path) -> str` and `question_set_fingerprint(cases_path) -> str` using SHA-256; these are used to ensure reproducibility across runs

**Checkpoint**: Frozen fixtures and schemas ready — measurement harness can now be built

---

## Phase 3: User Story 1 — Verify whether a chunking change is worthwhile (Priority: P1) 🎯 MVP

**Goal**: Capture current zero-overlap RAG v2 behavior as a reproducible baseline with full metrics

**Independent Test**: Run `python scripts/evaluate_chunking.py --strategy baseline` and verify the report contains corpus/question-set fingerprints, all case outcomes, and aggregate metrics (recall@K, citation support, p95 latency, index size, chunk count, length distribution)

### Tests for User Story 1

- [ ] T008 [P] [US1] Test baseline runner produces valid `chunk-evaluation/v1` report in `tests/test_chunk_evaluation.py`: mock `LocalChunkIndex` and `StructureAwareChunker`, verify report schema, decision = `baseline`, all cases have outcomes, fingerprints present
- [ ] T009 [P] [US1] Test `StrategyMetrics` aggregation in `tests/test_chunk_evaluation.py`: given known `CaseOutcome` list, verify `expected_evidence_recall_at_k`, `citation_support_rate`, `warm_query_p95_ms`, `index_size_bytes`, `retrievable_chunk_count`, and `length_distribution` compute correctly

### Implementation for User Story 1

- [ ] T010 [US1] Implement `BaselineRunner` class in `src/aios_habit/rag_v2/chunk_evaluation.py`: accepts corpus manifest path, cases path, and strategy config; creates a dedicated local SQLite index (never mutates active Workspace Chat index); runs `StructureAwareChunker` + `LocalChunkIndex` ingestion; executes each case's question via `hybrid_search_with_summary`; records `CaseOutcome` for each case; computes `StrategyMetrics`; emits `chunk-evaluation/v1` JSON report
- [ ] T011 [US1] Implement chunk-length distribution calculator in `src/aios_habit/rag_v2/chunk_evaluation.py`: count chunks in bands `[0-50]`, `[51-200]`, `[201-500]`, `[501-1000]`, `[1001+]` characters; include in `StrategyMetrics.length_distribution`; flag chunks under 50 chars as `short_chunk_warning`
- [ ] T012 [US1] Create CLI runner script at `scripts/evaluate_chunking.py`: parse `--strategy`, `--corpus`, `--cases`, `--output-dir` args; call `BaselineRunner`; write JSON report + human-readable Markdown summary to `local_runs/chunk_evaluation/<run-id>/`; print pass/fail summary to stdout

**Checkpoint**: Baseline measurement can be run locally and produces a reproducible report

---

## Phase 4: User Story 2 — Preserve sentence meaning in Vietnamese, Japanese, and Chinese (Priority: P1)

**Goal**: E1 scope is measurement only — create multilingual boundary fixtures that will detect mid-sentence splits, without changing the chunker

**Independent Test**: Run baseline evaluation with the multilingual cases; inspect the report for `fallback_boundary_used` flags and verify boundary-challenge cases report whether the current chunker splits mid-sentence at CJK punctuation

### Tests for User Story 2

- [ ] T013 [P] [US2] Test multilingual boundary detection in `tests/test_chunk_evaluation.py`: given a Japanese passage ending with `。` before the size limit, verify the boundary detector reports whether the split occurs at sentence punctuation or mid-sentence; this is a measurement test, not a fix

### Implementation for User Story 2

- [ ] T014 [US2] Add boundary analysis to `CaseOutcome` in `src/aios_habit/rag_v2/chunk_evaluation.py`: for each boundary-challenge case, record `split_at_sentence_punctuation: bool`, `fallback_boundary_used: bool`, and `boundary_char_position: int`; analyze chunks produced by the current chunker against known CJK sentence-ending punctuation (`。`, `！`, `？`, `．`)
- [ ] T015 [US2] Add language-partitioned metrics to `StrategyMetrics` in `src/aios_habit/rag_v2/chunk_evaluation.py`: `language_breakdown` dict keyed by `vi`/`ja`/`zh-CN` with per-language recall, citation support, boundary failure count, and average chunk length

**Checkpoint**: Multilingual boundary analysis produces data that will justify or reject E2 CJK boundary candidates

---

## Phase 5: User Story 4 — Avoid spending effort on inactive legacy paths (Priority: P3)

**Goal**: Record which chunking path is actually used by Workspace Chat RAG v2

**Independent Test**: Verify the baseline report includes a `supported_path` field identifying the active chunker class

- [ ] T016 [US4] Add supported-path trace to `BaselineRunner` in `src/aios_habit/rag_v2/chunk_evaluation.py`: during ingestion, record which chunker class was invoked (`StructureAwareChunker` vs legacy); include `supported_path: str` and `legacy_chunkers_active: bool` in the report metadata
- [ ] T017 [P] [US4] Test supported-path trace in `tests/test_chunk_evaluation.py`: verify baseline report identifies `StructureAwareChunker` as the active path and `legacy_chunkers_active` is `false` for the standard RAG v2 flow

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T018 [P] Add privacy validation to report writer in `src/aios_habit/rag_v2/chunk_evaluation.py`: scan output JSON for any string matching known `local_only` source content patterns; assert `raw_local_only_text_exported: false`; fail the run if raw text leaks into the report
- [ ] T019 Run `quickstart.md` E1 validation: execute the baseline evaluation end-to-end, verify report completeness against all `data-model.md` fields, confirm reproducibility by running twice with identical fingerprints and comparing metrics

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on T001 (dataclasses must exist for fixtures to reference)
- **US1 (Phase 3)**: Depends on Phase 2 completion (fixtures + schemas)
- **US2 (Phase 4)**: Depends on T010 (BaselineRunner must exist to add boundary analysis)
- **US4 (Phase 5)**: Depends on T010 (BaselineRunner must exist to add path trace)
- **Polish (Phase 6)**: Depends on all story phases

### Parallel Opportunities

```text
Phase 1:  T001 ─────────────────────────┐
          T002 [P] ─────────────────────┤
          T003 [P] ─────────────────────┘
                                        │
Phase 2:  T004 ─────────────────────────┐
          T005 [P] ─────────────────────┤
          T006 [P] ─────────────────────┤
          T007 [P] ─────────────────────┘
                                        │
Phase 3:  T008 [P] ─────┐              │
          T009 [P] ─────┤ (tests)      │
                        ↓               │
          T010 ──────── T011 ── T012    │
                                        │
Phase 4:  T013 [P] ─── T014 ── T015    │ (after T010)
                                        │
Phase 5:  T016 ──────── T017 [P]        │ (after T010)
                                        │
Phase 6:  T018 [P] ──── T019           │ (after all)
```

---

## Implementation Strategy

### MVP First (US1 Only — Phases 1-3)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Fixtures + schemas (T004–T007)
3. Complete Phase 3: Baseline runner + CLI (T008–T012)
4. **STOP and VALIDATE**: Run baseline, verify report completeness
5. Review output: if baseline shows no CJK issues → E2 may be unnecessary

### E1 Exit Decision

After T019 completes, the baseline report determines:
- **"Current chunking is good enough"** → Stop. No E2/E3/E4 needed.
- **"CJK boundary failures confirmed"** → Proceed to E2 task generation.
- **"Summary crowds evidence"** → Proceed to E3 task generation.
- **"Both issues confirmed"** → Generate E2+E3 tasks.

---

## Prohibitions (E1 Scope)

These actions are **explicitly forbidden** in E1 tasks:

- ❌ Modifying `StructureAwareChunker` or any chunking logic
- ❌ Adding overlap, context windows, or sentence-aware splitting
- ❌ Changing retrieval defaults, document summaries, or legacy chunkers
- ❌ Mutating the active Workspace Chat index
- ❌ Exporting raw `local_only` document text outside the workspace
- ❌ Generating E2/E3/E4 tasks before E1 results are reviewed

---

## Notes

- 19 total tasks, E1 scope only
- US1: 5 tasks (P1, baseline measurement)
- US2: 3 tasks (P1, multilingual boundary analysis — measurement only)
- US4: 2 tasks (P3, supported-path trace)
- Setup: 3 tasks, Foundational: 4 tasks, Polish: 2 tasks
- US3 (summary vs evidence): deferred to E3
- All evaluation uses dedicated local indexes; production index untouched
