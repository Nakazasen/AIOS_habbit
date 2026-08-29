# Tasks: Evidence-Based Chunking Evaluation — Commit E1

**Input**: Design documents from `/specs/006-chunking-evaluation/`

**Scope**: E1 only — baseline measurement. No chunker modifications, no overlap,
no default behavior changes. E2/E3/E4 tasks will be generated separately after
E1 results are reviewed.

**Gate**: E1 Prerequisite Gate CLEARED 2026-08-24 (Commit D conditional pass).

**Tests**: Included — E1 is a measurement harness; its own correctness must be
verified before trusting its output.

**Handoff status (2026-08-29)**: E1 measurement completed on the public
evaluation corpus via `StructureAwareChunker` + BGE-M3 hybrid. Two T019 runs
share identical corpus/question-set/model fingerprints and quality metrics.
Decision is `baseline`. This is **not** an owner `local_only` / `tailieugoc`
measurement. Synthetic identity fixtures remain fail-closed (`BLOCKED`,
exit 2). Do not generate E2/E3/E4 tasks until this report is reviewed.

**T019 evidence (venv Python 3.11.14, FlagEmbedding present)**:
- Corpus: `tests/fixtures/chunk_evaluation/corpus_public_v1.json`
  (`corpus_kind=public_evaluation`)
- Cases: `tests/fixtures/chunk_evaluation/cases_v1.json` (12 cases: vi/ja/zh-CN)
- Run 1: `local_runs/chunk_evaluation/e1_run1/chunk-eval-1788006856_report.json`
- Run 2: `local_runs/chunk_evaluation/e1_run2/chunk-eval-1788007041_report.json`
- Corpus fingerprint: `sha256:83d66e036ae8ffdcfe050dfaf326ed1610877208fc68c4a1465163edbf71d251`
- Question-set fingerprint: `sha256:9ee2b867b0cf195c5989e18ff5b1a155b24057c12a99bd2677da6348de612586`
- Model: `bge-m3:5617a9f61b02:b1d887e03f135476`
- Chunker: `StructureAwareChunker` (`legacy_chunkers_active=false`)
- Retrieval path: `hybrid`
- Recall@K / citation: **0.917** both runs (11/12 cases)
- Retrievable chunks: **127** both runs; index **1,859,584** bytes
- Warm p95: 417.1 ms (run 1) / 500.1 ms (run 2) — latency jitter only
- CJK boundary failures: ja 4/4, zh-CN 3/4; vi 0
- Missed case: `vi-002` (Vietnamese table / material standards)
- Privacy: `raw_local_only_text_exported=false`
- CLI on identity-only `corpus_manifest.json`: `BLOCKED` (not labelled baseline)

**E1 exit signal for review (no E2/E3 generated here)**:
- CJK mid-sentence / fallback splits are confirmed on ja and zh-CN.
- One Vietnamese table case missed expected evidence.
- Current chunking is **not** “good enough to stop” if CJK sentence integrity
  is a product requirement; promotion of any chunker change still needs a
  later candidate run against the same fingerprints.

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

- [x] T001 Create evaluation domain module at `src/aios_habit/rag_v2/chunk_evaluation.py` with `EvaluationCase`, `ChunkingStrategy`, `EvaluationRun`, `CaseOutcome`, and `StrategyMetrics` dataclasses matching `data-model.md`
- [x] T002 [P] Create evaluation test module at `tests/test_chunk_evaluation.py` with schema validation tests for all dataclasses (field types, required fields, controlled values)
- [x] T003 [P] Create evaluation fixture directory at `tests/fixtures/chunk_evaluation/` with a `README.md` explaining the fixture structure and privacy rules (no `local_only` text in committed fixtures)

---

## Phase 2: Foundational (Fixture Data + Schemas)

**Purpose**: Frozen corpus, question set, and report contract — MUST complete before measurement

**⚠️ CRITICAL**: No measurement code can run without frozen fixtures and validated schemas

- [x] T004 Create frozen multilingual question-evidence case set at `tests/fixtures/chunk_evaluation/cases_v1.json` with at least 3 Vietnamese, 3 Japanese, and 3 Simplified Chinese cases; each case has `case_id`, `question`, `language`, `source_ids`, `expected_chunk_hints`, and `challenge_labels` per `data-model.md`; include at least 1 boundary-challenge and 1 cross-source case per language
- [x] T005 [P] Create representative evaluation corpus fixture at `tests/fixtures/chunk_evaluation/corpus_manifest.json` listing source identities, language, document type (markdown, table, spreadsheet), and SHA-256 fingerprint; include at least one table-bearing and one multi-language document; do NOT embed raw `local_only` text — reference by path only
- [x] T006 [P] Create report schema validator in `src/aios_habit/rag_v2/chunk_evaluation.py` that validates a result dict against the `chunk-evaluation/v1` contract (`contracts/chunk-evaluation-v1.md`); enforce `raw_local_only_text_exported: false`, required fields, and decision enum
- [x] T007 Add fingerprinting utilities in `src/aios_habit/rag_v2/chunk_evaluation.py`: `corpus_fingerprint(manifest_path) -> str` and `question_set_fingerprint(cases_path) -> str` using SHA-256; these are used to ensure reproducibility across runs

**Checkpoint**: Frozen fixtures and schemas ready — measurement harness can now be built

---

## Phase 3: User Story 1 — Verify whether a chunking change is worthwhile (Priority: P1) 🎯 MVP

**Goal**: Capture current zero-overlap RAG v2 behavior as a reproducible baseline with full metrics

**Independent Test**: Run `python scripts/evaluate_chunking.py --strategy baseline` and verify the report contains corpus/question-set fingerprints, all case outcomes, and aggregate metrics (recall@K, citation support, p95 latency, index size, chunk count, length distribution)

### Tests for User Story 1

- [x] T008 [P] [US1] Test baseline runner produces valid `chunk-evaluation/v1` report in `tests/test_chunk_evaluation.py`: mock `LocalChunkIndex` and `StructureAwareChunker`, verify report schema, decision = `baseline`, all cases have outcomes, fingerprints present
- [x] T009 [P] [US1] Test `StrategyMetrics` aggregation in `tests/test_chunk_evaluation.py`: given known `CaseOutcome` list, verify `expected_evidence_recall_at_k`, `citation_support_rate`, `warm_query_p95_ms`, `index_size_bytes`, `retrievable_chunk_count`, and `length_distribution` compute correctly

### Implementation for User Story 1

- [x] T010 [US1] Implement `BaselineRunner` class in `src/aios_habit/rag_v2/chunk_evaluation.py`: accepts corpus manifest path, cases path, and strategy config; creates a dedicated local SQLite index (never mutates active Workspace Chat index); runs `StructureAwareChunker` + `LocalChunkIndex` ingestion; executes each case's question via `hybrid_search_with_summary`; records `CaseOutcome` for each case; computes `StrategyMetrics`; emits `chunk-evaluation/v1` JSON report
- [x] T011 [US1] Implement chunk-length distribution calculator in `src/aios_habit/rag_v2/chunk_evaluation.py`: count chunks in bands `[0-50]`, `[51-200]`, `[201-500]`, `[501-1000]`, `[1001+]` characters; include in `StrategyMetrics.length_distribution`; flag chunks under 50 chars as `short_chunk_warning`
- [x] T012 [US1] Create CLI runner script at `scripts/evaluate_chunking.py`: parse `--strategy`, `--corpus`, `--cases`, `--output-dir` args; call `BaselineRunner`; write JSON report + human-readable Markdown summary to `local_runs/chunk_evaluation/<run-id>/`; print pass/fail summary to stdout

**Checkpoint**: Baseline measurement can be run locally and produces a reproducible report

---

## Phase 4: User Story 2 — Preserve sentence meaning in Vietnamese, Japanese, and Chinese (Priority: P1)

**Goal**: E1 scope is measurement only — create multilingual boundary fixtures that will detect mid-sentence splits, without changing the chunker

**Independent Test**: Run baseline evaluation with the multilingual cases; inspect the report for `fallback_boundary_used` flags and verify boundary-challenge cases report whether the current chunker splits mid-sentence at CJK punctuation

### Tests for User Story 2

- [x] T013 [P] [US2] Test multilingual boundary detection in `tests/test_chunk_evaluation.py`: given a Japanese passage ending with `。` before the size limit, verify the boundary detector reports whether the split occurs at sentence punctuation or mid-sentence; this is a measurement test, not a fix

### Implementation for User Story 2

- [x] T014 [US2] Add boundary analysis to `CaseOutcome` in `src/aios_habit/rag_v2/chunk_evaluation.py`: for each boundary-challenge case, record `split_at_sentence_punctuation: bool`, `fallback_boundary_used: bool`, and `boundary_char_position: int`; analyze chunks produced by the current chunker against known CJK sentence-ending punctuation (`。`, `！`, `？`, `．`)
- [x] T015 [US2] Add language-partitioned metrics to `StrategyMetrics` in `src/aios_habit/rag_v2/chunk_evaluation.py`: `language_breakdown` dict keyed by `vi`/`ja`/`zh-CN` with per-language recall, citation support, boundary failure count, and average chunk length

**Checkpoint**: Multilingual boundary analysis produces data that will justify or reject E2 CJK boundary candidates

---

## Phase 5: User Story 4 — Avoid spending effort on inactive legacy paths (Priority: P3)

**Goal**: Record which chunking path is actually used by Workspace Chat RAG v2

**Independent Test**: Verify the baseline report includes a `supported_path` field identifying the active chunker class

- [x] T016 [US4] Add supported-path trace to `BaselineRunner` in `src/aios_habit/rag_v2/chunk_evaluation.py`: during ingestion, record which chunker class was invoked (`StructureAwareChunker` vs legacy); include `supported_path: str` and `legacy_chunkers_active: bool` in the report metadata
- [x] T017 [P] [US4] Test supported-path trace in `tests/test_chunk_evaluation.py`: verify baseline report identifies `StructureAwareChunker` as the active path and `legacy_chunkers_active` is `false` for the standard RAG v2 flow

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T018 [P] Add privacy validation to report writer in `src/aios_habit/rag_v2/chunk_evaluation.py`: scan output JSON for any string matching known `local_only` source content patterns; assert `raw_local_only_text_exported: false`; fail the run if raw text leaks into the report
- [x] T019 Run `quickstart.md` E1 validation: execute the baseline evaluation end-to-end, verify report completeness against all `data-model.md` fields, confirm reproducibility by running twice with identical fingerprints and comparing metrics

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

## Notes (E1)

- 19 total tasks, E1 scope only
- US1: 5 tasks (P1, baseline measurement)
- US2: 3 tasks (P1, multilingual boundary analysis — measurement only)
- US4: 2 tasks (P3, supported-path trace)
- Setup: 3 tasks, Foundational: 4 tasks, Polish: 2 tasks
- US3 (summary vs evidence): deferred to E3
- All evaluation uses dedicated local indexes; production index untouched

---

# Commit E2 — CJK / Vietnamese sentence-boundary candidate

**Opened**: 2026-08-29 after E1 review (CJK mid-sentence splits confirmed).

**Scope**: Opt-in candidate `cjk-sentence-punctuation-v1` on the same frozen
public corpus and cases as E1. Default `StructureAwareChunker()` (Workspace Chat)
stays on the legacy `. ` / newline / space splitter. No overlap. No E3. No E4
index promotion. Dedicated eval indexes only.

**Gates (SC-002 / SC-003)**: Candidate is `improved` only if it fixes the
confirmed CJK boundary cases (`ja-001`, `ja-004`, `zh-001`, `zh-004`) **or**
raises expected-evidence recall by ≥5pp, AND recall does not fall, AND warm p95
and index size stay ≤ +25% vs the frozen E1 report. Otherwise `neutral` or
`rejected`. Never label a candidate run `baseline`.

- [x] T020 [P] Add `boundary_policy` to `StructureAwareChunker` in `src/aios_habit/rag_v2/chunking.py`: default `legacy` preserves current `. `/newline/space split; `sentence_punctuation_v1` prefers Vietnamese/CJK sentence endings (`。！？．.!?`) in the existing min-window before character fallback; skip decimal dots
- [x] T021 [P] Tests in `tests/test_rag_v2_chunking.py`: default chunker still hard-cuts CJK without spaces; sentence policy splits at `。`/`！`/`？` when punctuation is inside the window; no-punctuation passage still falls back and stays within `max_chars`
- [x] T022 Register candidate strategy `cjk-sentence-punctuation-v1` (`baseline_of=baseline-structure-aware-v1`) in `src/aios_habit/rag_v2/chunk_evaluation.py`; `BaselineRunner` builds the matching chunker; candidate runs never emit `decision=baseline`
- [x] T023 Implement `classify_candidate_decision(candidate_report, baseline_report)` enforcing fingerprint match, no recall regression, SC-003 resource caps, and CJK boundary-case repair; tests in `tests/test_chunk_evaluation.py`
- [x] T024 Extend `scripts/evaluate_chunking.py` with `--strategy cjk-sentence-punctuation-v1` and `--compare-to <e1_report.json>`; synthetic corpus still fail-closes
- [x] T025 Run the candidate on `corpus_public_v1.json` / `cases_v1.json` with venv Python 3.11 against frozen E1 fingerprints; write report under `local_runs/chunk_evaluation/e2_run1/`; do not change Workspace Chat defaults regardless of `improved`/`neutral`/`rejected`

**T025 evidence (2026-08-29)**: Decision **`neutral`** (`no_sc003_gain`). Same fingerprints and model as E1. Recall@K 0.917 (unchanged), 127 chunks, index 1,859,584 bytes (identical), p95 498–523 ms. Workspace Chat default chunker **not** switched.

The public E1 corpus is mostly under 900 characters after ingest, so the 900-char splitter barely runs; E1 “CJK failures” were last-character scoring on unsplit documents. A diagnostic at `max_chars=200` on the same markdown fixtures shows the candidate does work when the window is hit: punct-ending children 5→53, true mid-sentence near-limit 42→7 (remaining 7 are the designed no-punctuation fallbacks). Promotion still requires an E1-comparable corpus that actually exceeds 900 chars, or an owner review to lengthen fixtures and re-baseline.

### E2 v2 — lengthened public corpus (same commit, after T025 review)

CJK markdown is now one paragraph per procedure/long-form section so ingest
exceeds `max_chars=900`. `corpus_public_v2.json` is the current file-backed
eval corpus; v1 fingerprints are historical and not comparable.

- [x] T026 Lengthen Japanese/Chinese public markdown (single paragraph, no
      trailing `(n)` after the sentence) and write `corpus_public_v2.json`
- [x] T027 Re-run E1 baseline on v2 (`local_runs/chunk_evaluation/e1_v2_run1/`)
- [x] T028 Re-run candidate vs frozen T027 report
      (`local_runs/chunk_evaluation/e2_v2_run1/`)
- [x] T029 If T028 is `improved` under SC-003: set default
      `StructureAwareChunker.boundary_policy` to `sentence_punctuation_v1` for
      **new** ingest only. Do not rebuild or mutate the active Workspace Chat
      index. Eval `--strategy baseline` still forces the legacy splitter.

**T027/T028 evidence (venv Python 3.11.14, FlagEmbedding present)**:
- Corpus: `tests/fixtures/chunk_evaluation/corpus_public_v2.json`
  fingerprint `sha256:0ab96b98a1c011514656bb474b06c18a8e236be5291bc3baf376679b537c9013`
- Cases fingerprint unchanged: `sha256:9ee2b867b0cf195c5989e18ff5b1a155b24057c12a99bd2677da6348de612586`
- Model: `bge-m3:5617a9f61b02:b1d887e03f135476`
- E1 v2: Decision `baseline`; Recall@K **0.917**; 96 retrievable chunks;
  index 2,252,800 bytes; warm p95 480.3 ms; CJK gate cases
  `ja-001`/`ja-004`/`zh-001`/`zh-004` all `split_at_sentence_punctuation=false`
  at position 899
- E2 v2: Decision **`improved`** (`cjk_boundary_fixed`); Recall@K **0.917**
  (no regression); 96 chunks; index 2,248,704 bytes; warm p95 476.7 ms;
  all four CJK gate cases `split_at_sentence_punctuation=true`
- Missed case on v2: `vi-002` (Vietnamese table). Fixed in corpus v3 below.
- Workspace Chat **index not rebuilt**. Production RAG profile remains
  `rolled_back`. Default chunker for new `RagV2DevPipeline` ingest is
  `sentence_punctuation_v1`.

### Table fixture `vi-002` (before E3)

E2 v2 retrieval for `vi-002` returned Chinese/Japanese tables, not
`src-material-standards.xlsx`. Cause: the Vietnamese table was ASCII
(`Ten nguyen lieu`) while the question uses diacritics (`nguyên liệu`);
dense hybrid preferred `原材料`. This is a fixture fidelity defect, not an
overlap/summary (E3) defect. E3 stays closed.

- [x] T030 Write Vietnamese material-standards table with diacritics and
      `nhập kho` in header/sheet; emit `corpus_public_v3.json`
- [x] T031 Re-run E1 then E2 candidate on v3; do not open overlap/summary

**T031 evidence (venv Python 3.11.14)**:
- Corpus: `tests/fixtures/chunk_evaluation/corpus_public_v3.json`
  fingerprint `sha256:3f993424380ba9e2c12ae4fc03d3259af90223d84287ce6c8f50a7996c6cd7e5`
- E1 v3: Decision `baseline`; Recall@K **1.000** (12/12); `vi-002` found
  `src-material-standards.xlsx`; p95 518.7 ms; CJK gate cases still fail
  under the legacy splitter
- E2 v3: Recall@K **1.000**; `vi-002` still found; CJK gate cases
  `ja-001`/`ja-004`/`zh-001`/`zh-004` split true; index 2,248,704 bytes
  (under +25%); Decision **`rejected`** (`warm_p95_over_budget`) because
  one cross-source query (`vi-003`) took 1006 ms (E1 p95 was 518.7 ms).
  Other E2 v3 latencies were 48–638 ms. Do **not** revert the E2 v2 default
  policy on this single noisy p95; do **not** treat v3 as a new promotion.
- E3 not opened.

### E2 prohibitions (still in force except default policy after T028)

- ❌ Adding overlap or neighbor-window expansion (E3)
- ❌ Rebuilding or mutating the active Workspace Chat index
- ❌ Labelling owner `local_only` / `tailieugoc` as measured
- ❌ Treating `corpus_public_v1.json` / v2 fingerprints as comparable to v3
