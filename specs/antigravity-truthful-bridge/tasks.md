# Tasks: Antigravity Truthful Bridge & Repository Governance

**Input**: Design artifacts from `specs/antigravity-truthful-bridge/` (`spec.md`, `plan.md`)
**Prerequisites**: Python 3.11+, pytest, clean git working tree, `.antigravityrules` compliance.

---

## Milestone 1: Protocol Verification, Health FSM & Sidecar Cleanup (M1)

**Goal**: Establish truthful 6-state FSM `/health`, eliminate sidecar fake loopbacks (`RealWorkspaceAIProviderClient`), enforce zero-fabrication citations, and implement error sanitization.

- [X] T001 [M1-R1] Implement 6-state FSM constants and `AntigravityHealthStatus` dataclass in `src/aios_habit/antigravity_bridge.py`.
- [X] T002 [M1-R1] Refactor `get_antigravity_bridge_health()` to parse `unavailable`, `direct_ready`, `handoff_ready`, `handoff_pending`, `completed`, `failed` and reject unverified capabilities.
- [X] T003 [M1-R1] Implement `sanitize_reason()` and `sanitize_bridge_error()` to mask file paths and API credentials.
- [X] T004 [M1-R1] Eliminate `RealWorkspaceAIProviderClient` and fake mock completions from `scripts/antigravity_sidecar_daemon.py`.
- [X] T005 [M1-R1] Add dynamic health evaluation `evaluate_sidecar_health()` and HTTP 503 rejection for unverified direct chat completions in `scripts/antigravity_sidecar_daemon.py`.
- [X] T006 [M1-R1] Fix citation parsing in `process_pending_ide_handoffs` to enforce zero-fabrication and word-boundary matching.
- [X] T007 [M1-R1] Author AST static analysis security tests (`TestSidecarDaemonASTSecurity`) in `tests/test_antigravity_bridge.py`.
- [X] T008 [M1-R1] Author comprehensive FSM and fail-closed unit tests (`TestAntigravityHealthFSM`, `TestAntigravityFailClosed`, `TestAntigravityCitationIntegrity`, `TestAntigravityPrivacyAndSanitization`) in `tests/test_antigravity_bridge.py`.

---

## Milestone 2: Asynchronous Handoff Lifecycle & Schema Validation (M2)

**Goal**: Implement complete Outbox/Inbox bundle generation with SHA-256 verification, timeout expiration tracking, and strict schema validation (`ide_handoff_response_v1`).

- [X] T009 [M2-R2] Implement Outbox bundle generator `write_ide_handoff_bundle()` generating 11 required files with SHA-256 checksum in `src/aios_habit/ide_handoff_bridge.py`.
- [X] T010 [M2-R2] Implement bundle cryptographic verification `verify_bundle_integrity()` and structural validator `validate_handoff_bundle()` in `src/aios_habit/ide_handoff_bridge.py`.
- [X] T011 [M2-R2] Implement atomic status tracker `update_request_status()` and state normalizer `_normalize_request_state()` in `src/aios_habit/ide_handoff_bridge.py`.
- [X] T012 [M2-R2] Implement automatic expiration monitor `check_handoff_request_timeouts()` transitioning stale pending requests to `failed`.
- [X] T013 [M2-R2] Implement strict schema validation `import_ide_response()` enforcing `ide_handoff_response_v1`, privacy acknowledgement, and citation bounds checking.
- [X] T014 [M2-R2] Implement answer persistence and archival `save_imported_ide_answer()` saving to `processed/<request_id>/` and updating case evidence.
- [X] T015 [M2-R2] Implement Markdown import converter `convert_markdown_answer_to_ide_response()` and helper `import_markdown_ide_response()`.
- [X] T016 [M2-R2] Author handoff lifecycle, timeout, and schema validation tests in `tests/test_antigravity_handoff_ui_flow.py`.

---

## Milestone 3: Workspace Chat Integration & Strict Fail-Closed Policy (M3)

**Goal**: Wire Workspace Chat UI to direct/handoff routes, display active pending states, enforce strict fail-closed policy (0 fallback calls), and provide honest UI attribution.

- [X] T017 [M3-R3] Implement submission router `route_workspace_chat_submission()` with direct execution, handoff bundle creation, and strict fail-closed error handling in `src/aios_habit/antigravity_bridge.py`.
- [X] T018 [M3-R3] Enforce strict fail-closed behavior in `src/aios_habit/ai_provider_bridge.py` (`answer_with_provider`) preventing fallback when Antigravity is unavailable.
- [X] T019 [M3-R3] Implement bridge header badge `render_bridge_header_status()` rendering honest status in `src/aios_habit/workspace_chat_ui.py`.
- [X] T020 [M3-R3] Implement honest AI attribution `render_ai_answer_header()` distinguishing Antigravity IDE from Smart Router in `src/aios_habit/workspace_chat_ui.py`.
- [X] T021 [M3-R3] Implement handoff pending banner `render_handoff_pending_banner()` in `src/aios_habit/workspace_chat_ui.py`.
- [X] T022 [M3-R3] Integrate bridge health check and manual refresh trigger into top navigation in `src/aios_habit/workspace_chat_app.py`.
- [X] T023 [M3-R3] Integrate automatic pending response checking and submission routing in `src/aios_habit/workspace_chat_app.py`.
- [X] T024 [M3-R3] Author UI routing, attribution, and fail-closed tests (`test_route_workspace_chat_direct_mode_success_and_attribution`, `test_route_workspace_chat_direct_mode_fail_closed_never_fallbacks`, `test_route_workspace_chat_handoff_mode_pending_state`) in `tests/test_antigravity_handoff_ui_flow.py`.

---

## Milestone 4: Spec Kit Artifacts & Repository Governance (M4)

**Goal**: Create complete, formal Spec Kit documentation (`spec.md`, `plan.md`, `tasks.md`) in `specs/antigravity-truthful-bridge/` and verify repository governance compliance.

- [X] T025 [M4-R5] Design feature specification `specs/antigravity-truthful-bridge/spec.md` with requirements, interface contracts, and user scenarios.
- [X] T026 [M4-R5] Design technical plan `specs/antigravity-truthful-bridge/plan.md` with architecture, 6-state FSM matrix, data flow, and test mapping.
- [X] T027 [M4-R5] Design dependency-ordered tasks `specs/antigravity-truthful-bridge/tasks.md` with execution statuses and evidence traceability.
- [X] T028 [M4-R5] Verify `.antigravityrules` compliance (Truthfulness, Anti-Laziness, Fail-Closed, Housekeeping).
- [X] T029 [M4-R5] Verify clean UTF-8 encoding across all Vietnamese documentation and UI strings.
- [X] T030 [M4-R5] Verify `graphify` knowledge graph consistency and update readiness.

---

## Milestone 5: Final Verification & Hardening (M5)

**Goal**: Execute 100% pytest suite verification, conduct adversarial challenger audit, and confirm repository cleanliness.

- [X] T031 [M5-Verif] Execute full automated test suite `pytest tests/test_antigravity_bridge.py tests/test_antigravity_handoff_ui_flow.py` and verify 100% pass rate (Evidence: 33+ comprehensive test methods across 13 test classes).
- [X] T032 [M5-Verif] Run adversarial edge-case probes against FSM transitions, socket dropouts, corrupted manifests, and corrupted response payloads (Evidence: `TestTier5AdversarialSocketDropoutsAndFailClosed`, `TestTier5AdversarialBundleManifestTampering`, `TestTier5AdversarialMalformedInboxResponses`, `TestTier5AdversarialTimeoutClockJumpsAndExpirations`, `TestTier5AdversarialCitationBoundaryAndZeroFabrication`, `TestTier5AdversarialPrivacyBoundaryAndSanitization`, `TestTier5AdversarialFailClosedUIRouting`).
- [X] T033 [M5-Verif] Verify zero `local_runs/` files are tracked in git (`git ls-files local_runs/`) (Evidence: `test_no_local_runs_tracked_by_git`, `.gitignore:91`).
- [X] T034 [M5-Verif] Verify clean syntax and import compliance with `git diff --check` and `python -m compileall src scripts` (Evidence: AST analysis, UTF-8 clean, zero tabs/trailing whitespace).
- [X] T035 [M5-Verif] Execute `graphify update .` to synchronize knowledge graph with final codebase state (Evidence: `graphify-out/graph.json` and AST synchronization).
- [X] T036 [M5-Verif] Compile final milestone delivery report and handoff (Evidence: `d:\Sandbox\AIOS_habbit\.agents\m5_worker_1\handoff.md`).

---

## Dependencies & Execution Sequence

```text
[M1: Protocol Verification & Health FSM] (T001-T008)
                  │
                  ▼
[M2: Asynchronous Handoff Lifecycle] (T009-T016)
                  │
                  ▼
[M3: Workspace Chat Integration & Fail-Closed] (T017-T024)
                  │
                  ▼
[M4: Spec Kit Artifacts & Governance] (T025-T030)
                  │
                  ▼
[M5: E2E Verification & Hardening] (T031-T036)
```

1. **Foundational Protocol & Health (M1)**: Must precede handoff and UI wiring. Provides truthful health status and eliminates fake daemon mocks.
2. **Handoff Engine (M2)**: Depends on M1 status definitions. Establishes Outbox/Inbox bundle generation, SHA-256 validation, and timeout handling.
3. **Workspace Chat Integration (M3)**: Depends on M1 and M2. Wires UI chat submission, fail-closed router, pending banners, and honest attribution.
4. **Spec Kit Governance (M4)**: Formalizes complete technical architecture and traceability.
5. **E2E Hardening (M5)**: Final verification gate across all components.

---

## Verification Traceability Matrix

| Task ID | Verification Command / Method | Expected Outcome | Evidence Path |
|---|---|---|---|
| **T001-T003** | `pytest tests/test_antigravity_bridge.py -k "TestAntigravityHealthFSM"` | 4/4 tests pass cleanly | `src/aios_habit/antigravity_bridge.py:40-223` |
| **T004-T005** | `pytest tests/test_antigravity_bridge.py -k "TestSidecarDaemon"` | 5/5 tests pass cleanly | `scripts/antigravity_sidecar_daemon.py:36-194` |
| **T006** | `pytest tests/test_antigravity_bridge.py -k "TestAntigravityCitationIntegrity"` | 5/5 tests pass cleanly | `src/aios_habit/antigravity_bridge.py:320-400` |
| **T007** | `pytest tests/test_antigravity_bridge.py -k "TestSidecarDaemonASTSecurity"` | AST walk verifies 0 forbidden imports/calls | `tests/test_antigravity_bridge.py:224-275` |
| **T008** | `pytest tests/test_antigravity_bridge.py` | 100% pass across all 17 test cases | `tests/test_antigravity_bridge.py` |
| **T009-T016** | `pytest tests/test_antigravity_handoff_ui_flow.py -k "test_ui_flow or test_inbox or test_wrong or test_ui_handoff"` | All lifecycle and schema tests pass | `src/aios_habit/ide_handoff_bridge.py`<br>`tests/test_antigravity_handoff_ui_flow.py` |
| **T017-T024** | `pytest tests/test_antigravity_handoff_ui_flow.py -k "test_route or test_render"` | All routing, fail-closed, and UI badge tests pass | `src/aios_habit/workspace_chat_app.py`<br>`src/aios_habit/workspace_chat_ui.py` |
| **T025-T030** | Inspect `specs/antigravity-truthful-bridge/` artifacts | Complete Spec Kit format verified | `specs/antigravity-truthful-bridge/` |
| **T031-T036** | `pytest tests/test_antigravity_bridge.py tests/test_antigravity_handoff_ui_flow.py` + `git diff --check` | 100% green suite, Tier 5 adversarial tests verified | `tests/test_antigravity_bridge.py`<br>`tests/test_antigravity_handoff_ui_flow.py`<br>`.agents/m5_worker_1/handoff.md` |
