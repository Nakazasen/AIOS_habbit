# Tasks: Resumable Stage A Preparation

**Input**: Design documents from `/specs/001-stage-a-resume-guard/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/stage-a-checkpoint.md, quickstart.md

## Phase 1: Setup

- [X] T001 Confirm ignored runtime artifacts remain excluded in `.gitignore` and do not add sealed evidence placeholders.

## Phase 2: Foundational

- [X] T002 Add a bounded per-source deadline option to `scripts/battle_notebooklm_rag_v2.py` and pass it only into local Stage A preparation.
- [X] T003 Add identity-bound checkpoint load/write validation helpers in `scripts/battle_notebooklm_rag_v2.py` using atomic JSON and opaque document IDs.

## Phase 3: User Story 1 - Resume an interrupted local preparation (Priority: P1)

**Goal**: Resume a matching Stage A run without re-preparing successfully committed sources.

**Independent Test**: A simulated failure after one commit produces a matching checkpoint; rerun invokes preparation only for remaining sources.

- [X] T004 [US1] Write adapter resume/progress tests in `tests/test_workspace_chat_rag_v2_adapter.py`.
- [X] T005 [US1] Extend `prepare_workspace_chat_sources` in `src/aios_habit/workspace_chat_rag_v2_adapter.py` with verified completed-document skipping and post-commit progress events.
- [X] T006 [US1] Write staging checkpoint/resume tests in `tests/test_battle_notebooklm_rag_v2.py`.
- [X] T007 [US1] Implement matching-checkpoint resume and atomic completion updates in `scripts/battle_notebooklm_rag_v2.py`.

## Phase 4: User Story 2 - Identify and bound a stalled source (Priority: P2)

**Goal**: Leave a safe restart point and deterministic failure when a local source stalls.

**Independent Test**: A synthetic deadline expiry marks the stage failed, records only a safe failure category, and creates no ready manifest.

- [X] T008 [US2] Write deadline and partial-ready registry tests in `tests/test_workspace_chat_rag_v2_adapter.py`.
- [X] T009 [US2] Enforce source-level time budget in `src/aios_habit/rag_v2/bge_subprocess_client.py` and wire it through `src/aios_habit/workspace_chat_rag_v2_adapter.py`.
- [X] T010 [US2] Write fail-closed staging deadline and content-free heartbeat tests in `tests/test_battle_notebooklm_rag_v2.py`.
- [X] T011 [US2] Persist failed checkpoint state and per-source heartbeat progress in `scripts/battle_notebooklm_rag_v2.py`.

## Phase 5: User Story 3 - Preserve diagnostic gate boundaries (Priority: P3)

**Goal**: Keep resumability distinct from sealed-artifact validity and live provider authorization.

**Independent Test**: Focused tests prove local Stage A does not initialize a provider and a missing immutable artifact remains blocked.

- [X] T012 [US3] Add local-only/no-provider and missing-artifact blocker coverage in `tests/test_battle_notebooklm_rag_v2.py`.
- [X] T013 [US3] Ensure Stage A result metadata in `scripts/battle_notebooklm_rag_v2.py` labels resumed and blocked states without a quality verdict.

## Phase 6: Validation and hygiene

- [X] T014 Run focused tests and the full relevant test suite from `specs/001-stage-a-resume-guard/quickstart.md`.
- [X] T015 Run `python -m compileall src scripts`, `git diff --check`, and `graphify update .` after implementation.
- [X] T016 Review the diff; report sealed-artifact recovery status separately from code validation and do not run BQ01/BQ02 until artifacts are present.
- [X] T017 Add a regression test for production Stage A adapter construction and remove unsupported lexical-fallback configuration from `scripts/battle_notebooklm_rag_v2.py`.

## Dependencies & Execution Order

- T001-T003 precede all story work.
- T004-T007 form the P1 MVP.
- T008-T011 depend on the P1 adapter and checkpoint behavior.
- T012-T013 depend on completed Stage A behavior.
- T014-T016 follow all implementation tasks.

## Implementation Strategy

Implement and validate P1 first, then add the deadline guard. The primary diagnostic remains unrun until sealed artifacts are independently restored; no task authorizes Stage B.
