# Tasks: Incremental Source Preparation and Truthful Chat Provenance

**Input**: Design documents in `specs/005-incremental-source-prep/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Required. The feature alters background data processing, retrieval scope, and user-visible AI provenance.

## Phase 1: Setup

**Purpose**: Establish shared names and executable test seams.

- [ ] T001 Define preparation-ledger schema/version constants and state names in `src/aios_habit/workspace_chat_rag_v2_adapter.py`.
- [ ] T002 [P] Add deterministic clock, worker, and SQLite-fixture helpers in `tests/test_workspace_chat_rag_v2_adapter.py`.
- [ ] T003 [P] Add a Streamlit session-state test harness for pending questions and progress rendering in `tests/test_workspace_chat_source_selection_owner_flow.py`.

## Phase 2: Foundational Durable Queue

**Purpose**: Persist index readiness and make a single CPU worker drain all eligible sources safely.

- [ ] T004 Add the `source_preparation_ledger` SQLite table, migration, model-identity validation, and stale-processing recovery in `src/aios_habit/workspace_chat_rag_v2_adapter.py`.
- [ ] T005 Add ledger CRUD and aggregate readiness-summary helpers in `src/aios_habit/workspace_chat_rag_v2_adapter.py`.
- [ ] T006 Add a priority claim operation (`interactive`, `normal`, `backfill`) that is atomic and permits only one active CPU source in `src/aios_habit/workspace_chat_rag_v2_adapter.py`.
- [ ] T007 Add a background drain loop that commits one source result then claims the next eligible source in `src/aios_habit/workspace_chat_rag_v2_adapter.py`.
- [ ] T008 Add source-change/delete/disable invalidation so stale ledger rows, materialized files, and BGE chunks cannot be reused in `src/aios_habit/workspace_chat_rag_v2_adapter.py` and `src/aios_habit/workspace_chat_app.py`.
- [ ] T009 Test SQLite recovery, duplicate scheduling, exact fingerprint reuse, stale processing recovery, priority ordering, and source deletion in `tests/test_workspace_chat_rag_v2_adapter.py`.

**Checkpoint**: Durable queue can run to completion and resume after restart before UI wiring begins.

## Phase 3: User Story 4 - Background preparation finishes the library (Priority: P1)

**Goal**: Uploading sources returns immediately while one worker continues through every pending source until ready or failed.

**Independent Test**: Upload three sources, observe all three become ready without another question; restart after one source and observe only remaining work resumes.

- [ ] T010 [P] [US4] Add a test for successful upload queuing every new/changed eligible source in `tests/test_workspace_chat_source_selection_owner_flow.py`.
- [ ] T011 [P] [US4] Add a test for notebook-open reconciliation and restart resumption without re-embedding a ready fingerprint in `tests/test_workspace_chat_rag_v2_adapter.py`.
- [ ] T012 [US4] Call reconciliation/enqueue after successful upload, restore, replacement, and notebook open in `src/aios_habit/workspace_chat_app.py`.
- [ ] T013 [US4] Start or continue the background drain only when BGE deployment/Local Pilot is genuinely available in `src/aios_habit/workspace_chat_app.py` and `src/aios_habit/workspace_chat_rag_v2_adapter.py`.
- [ ] T014 [US4] Render compact overall progress and the current source without putting the question composer below the fold in `src/aios_habit/workspace_chat_ui.py` and `src/aios_habit/workspace_chat_app.py`.
- [ ] T015 [US4] Render `failed` states with per-source retry and retry-failed actions in `src/aios_habit/workspace_chat_ui.py` and `src/aios_habit/workspace_chat_app.py`.
- [ ] T016 [US4] Add a UI flow test proving upload returns before embedding completes and progress reaches completion in `tests/test_workspace_chat_source_selection_owner_flow.py`.

## Phase 4: User Story 1 - Ask once about a newly added document (Priority: P1)

**Goal**: A question held solely for a relevant unready source is automatically answered once when that exact source becomes ready.

**Independent Test**: Submit one question for an unready document, complete preparation, and verify exactly one user/assistant exchange is saved without a second submit.

- [ ] T017 [P] [US1] Add tests for pending-question idempotency, cancellation, expiry, changed-selection invalidation, and exact-scope release in `tests/test_workspace_chat_source_selection_owner_flow.py`.
- [ ] T018 [US1] Add the session-only pending-question record and one-time continuation guard in `src/aios_habit/workspace_chat_app.py`.
- [ ] T019 [US1] Promote only the exact relevant unready source to `interactive` priority and retain the question with clear Vietnamese waiting text in `src/aios_habit/workspace_chat_app.py` and `src/aios_habit/workspace_chat_rag_v2_adapter.py`.
- [ ] T020 [US1] Poll readiness safely on Streamlit reruns, submit the retained question exactly once, and never re-expand retrieval beyond the checked scope in `src/aios_habit/workspace_chat_app.py`.

## Phase 5: User Story 2 - Continue using ready documents (Priority: P1)

**Goal**: A precise question about a ready document proceeds while unrelated sources continue preparing.

**Independent Test**: With one ready and one pending source, a ready-source question reaches retrieval immediately; a broad question does not enqueue a second full-library job.

- [ ] T021 [P] [US2] Add tests for ready-source bypass, interactive priority, broad-question rejection, and no scope re-expansion in `tests/test_workspace_chat_rag_v2_adapter.py`.
- [ ] T022 [US2] Return an explicit bounded query scope and a clear broad/ambiguous decision from `src/aios_habit/workspace_chat_rag_v2_adapter.py`.
- [ ] T023 [US2] Wire retrieval to use only the ready verified scope and show a source-choice prompt for unsafe broad requests in `src/aios_habit/workspace_chat_app.py`.

## Phase 6: User Story 3 - Understand document readiness (Priority: P2)

**Goal**: The operator can see why each source is ready, queued, being read, or failed and recover only the affected source.

**Independent Test**: Render all five states, retry a failure, and ensure BGE-unavailable state is never presented as active processing.

- [ ] T024 [P] [US3] Add localized render/callback tests for every readiness state and retry action in `tests/test_workspace_chat_source_selection_ui_copy.py` and `tests/test_workspace_chat_source_selection_owner_flow.py`.
- [ ] T025 [US3] Add source-row readiness badges, explanatory Vietnamese copy, and accessible retry controls in `src/aios_habit/workspace_chat_ui.py`.
- [ ] T026 [US3] Ensure unavailable BGE, cancelled sources, and changed fingerprints have truthful status and safe actions in `src/aios_habit/workspace_chat_app.py`.

## Phase 7: Truthful AI provenance and grouped evidence

**Purpose**: Remove false model claims and make retrieved chunks understandable.

- [ ] T027 [P] Add tests proving a bridge alias cannot be rendered as a verified model and provider metadata survives the direct flow in `tests/test_antigravity_bridge.py` and `tests/test_antigravity_handoff_ui_flow.py`.
- [ ] T028 [P] Add tests grouping three chunks of one source into one evidence row with a chunk count in `tests/test_workspace_chat_source_selection_ui_copy.py`.
- [ ] T029 Replace `antigravity-brain-pro` user-facing defaults with truthful bridge/provider/verified-model fields in `src/aios_habit/antigravity_bridge.py`, `scripts/antigravity_sidecar_daemon.py`, and `src/aios_habit/gemini_web_engine.py`.
- [ ] T030 Render bridge, Gemini Web provider, and unverified model state separately in `src/aios_habit/workspace_chat_ui.py`.
- [ ] T031 Group evidence by source id and render chunk count, EVD id, and page/section when available in `src/aios_habit/workspace_chat_ui.py` and `src/aios_habit/workspace_chat_app.py`.

## Phase 8: Polish and verification

- [ ] T032 [P] Update readiness/provenance architecture decisions in `ARCHITECTURE.md`, `ROADMAP.md`, and `PROJECT_HANDOVER.md`.
- [ ] T033 [P] Add the end-to-end manual scenarios from `specs/005-incremental-source-prep/quickstart.md` to the relevant test documentation.
- [ ] T034 Run focused queue, UI, bridge, and compression tests with `.venv\Scripts\python.exe -m pytest` and record results in the feature handover.
- [ ] T035 Run `py -3 -m compileall src tests`, `py -3 -m pytest -q`, `$env:PYTHONPATH="src"; py -3 -m aios_habit.cli audit`, and `graphify update .` before declaring completion.

## Dependencies and execution order

`T001–T009` block all feature work. Then complete US4 (`T010–T016`) first so uploads genuinely make progress. US1 and US2 can follow after the durable queue; US3 depends on the ledger summary; provenance/evidence can proceed in parallel with US3 after the bridge contract is agreed. Finish with T032–T035.

## MVP

The first usable delivery is `T001–T016`: upload returns immediately, every eligible source is queued to completion, progress is visible, and restarting does not lose unfinished work. Do not claim full completion until the provenance/evidence work also lands.
