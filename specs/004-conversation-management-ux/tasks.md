# Tasks: Conversation Management UX

**Input**: Design documents in `specs/004-conversation-management-ux/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/conversation-management-ui.md`

## Phase 1: Setup

- [X] T001 Review the Graphify conversation-state trace and protect unrelated `.agents/` working-tree changes before editing `src/aios_habit/workspace_chat_app.py`.
- [X] T002 Define the completed selection, deletion, and stale-URL behavior in `specs/004-conversation-management-ux/quickstart.md` as implementation acceptance evidence.

## Phase 2: Foundational State Recovery

- [X] T003 Add focused navigation-state tests for deleted, missing, and wrong-notebook conversation IDs in `tests/test_workspace_chat_owner_flow.py`.
- [X] T004 Implement a single validated active-conversation resolution path in `src/aios_habit/workspace_chat_app.py` that keeps session state and the `conv` URL parameter consistent.

**Checkpoint**: Valid conversation navigation recovers without rendering an invalid content pane.

## Phase 3: User Story 1 - Delete the Intended Conversation Safely (Priority: P1)

**Goal**: Make destructive actions visibly target one named conversation and preserve all unrelated data.

**Independent Test**: Delete one of several conversations, cancel once, then confirm; only the named conversation and its conversation-scoped data change.

- [X] T005 [P] [US1] Add store cascade and isolation regression coverage in `tests/test_workspace_chat_store.py` for a named conversation deletion.
- [X] T006 [P] [US1] Add UI-state tests in `tests/test_workspace_chat_owner_flow.py` for explicit delete target, confirmation, and cancel behavior.
- [X] T007 [US1] Add target-scoped conversation management callbacks and confirmation-state cleanup in `src/aios_habit/workspace_chat_app.py`.
- [X] T008 [US1] Render a conversation-associated management entry and confirmation naming the deletion target in `src/aios_habit/workspace_chat_app.py`.

## Phase 4: User Story 2 - Continue Without a Blank Screen (Priority: P1)

**Goal**: Immediately open a valid remaining conversation after deletion, or show an actionable no-conversation state.

**Independent Test**: Delete the active conversation with and without a remaining conversation, then refresh a stale link.

- [X] T009 [P] [US2] Add regression coverage for active deletion fallback, last-conversation empty state, and stale URL refresh in `tests/test_workspace_chat_owner_flow.py`.
- [X] T010 [US2] Implement post-delete fallback selection and URL replacement in `src/aios_habit/workspace_chat_app.py`.
- [X] T011 [US2] Render an explicit Vietnamese no-conversation state with a create action in `src/aios_habit/workspace_chat_app.py`.

## Phase 5: User Story 3 - Manage the Selected Conversation with Confidence (Priority: P2)

**Goal**: Make selection and rename target identity obvious, including for similar titles.

**Independent Test**: Switch between similar titles, rename the selected conversation, and confirm the list and management labels agree.

- [X] T012 [P] [US3] Add selection and rename-target UI assertions in `tests/test_workspace_chat_owner_flow.py`.
- [X] T013 [US3] Update conversation-list selected styling/copy and management heading in `src/aios_habit/workspace_chat_app.py`.
- [X] T014 [US3] Ensure successful rename refreshes target-specific management state without affecting another conversation in `src/aios_habit/workspace_chat_app.py`.

## Phase 6: Verification and Documentation

- [X] T015 Refresh Graphify after source edits with `graphify update .` and inspect the conversation-state path.
- [X] T016 Run focused Workspace Chat tests and the full repository quality commands listed in `specs/004-conversation-management-ux/quickstart.md`.
- [X] T017 Update `specs/004-conversation-management-ux/tasks.md` with completed tasks and record any blocked validation truthfully.

## Dependencies & Execution Order

- T001-T004 establish the shared recovery behavior and block all user-story UI work.
- US1 and US2 share the resolved state path; complete US1 before wiring active deletion fallback in US2.
- US3 follows US1 because the management target and selected state use the same identity rules.
- T015-T017 run after all implementation tasks.

## Parallel Opportunities

- T005 and T006 can be authored in parallel because they cover store isolation and UI state respectively.
- T009 and T012 can be prepared in parallel after T004 because they assert separate journeys in the same test module.

## Implementation Strategy

1. Establish invalid-ID recovery first.
2. Make deletion target-scoped and test cancellation/isolation.
3. Add post-delete fallback and an explicit empty state.
4. Improve selected-state and rename clarity, then run full validation.

## Validation Record

- 2026-08-22: `py -3 -m pytest -q tests/test_workspace_chat_store.py tests/test_workspace_chat_owner_flow.py tests/test_workspace_chat_source_selection_owner_flow.py tests/test_workspace_chat_source_selection_ui_copy.py tests/test_workspace_chat_ai_answer.py` passed: **134 passed**.
- 2026-08-22: `py -3 -m compileall -q src tests` and the Workspace Chat module import passed (bare-mode Streamlit warnings expected).
- 2026-08-22: Full `py -3 -m pytest -q` completed: **1289 passed, 10 failed**. Failures are in the separately modified Antigravity bridge tests (9) and RAG v2 deployment checksum fixture (1), outside this feature's files.
- 2026-08-22: `$env:PYTHONPATH='src'; py -3 -m aios_habit.cli audit` did not complete within 64 seconds and left child processes; those test processes were stopped. Release-quality audit remains **BLOCKED** pending diagnosis of the CLI audit hang.
