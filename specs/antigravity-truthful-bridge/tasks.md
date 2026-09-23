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

---

## Milestone 6: Dự phòng Tổng hợp Cục bộ có Trích dẫn (M6, làm giàu 2026-09-23)

**Mục tiêu**: Khi cả ba đường nhà cung cấp không tới được, người dùng vẫn có đường trả lời **có trích dẫn** bằng đáp án trích xuất đã tính sẵn trong máy, có nhãn trung thực, không gọi mạng.

**Đầu vào**: `spec.md` mục R6 (`FR-026..FR-032`, `SC-009..SC-013`), `plan.md` mục 9, `contracts/local-grounded-fallback.md`, `data-model.md`.

**Thứ tự**: hợp đồng dự phòng trước, rồi ghi đáp án, rồi nối giao diện, rồi nhãn, rồi xác minh.

### Phase A — Đường dự phòng trong hàm định tuyến

- [x] T037 [M6-FR-026] Thêm tham số tuỳ chọn `local_synthesis: Optional[Mapping[str, Any]] = None` vào `route_workspace_chat_submission` và hàm phụ `_local_fallback_available(...)` kiểm ba điều kiện `answer` khác rỗng, `grounded is True`, `abstained is False` trong `src/aios_habit/antigravity_bridge.py`. Giữ nguyên chữ ký trả về bốn phần tử.
- [x] T038 [M6-FR-026] Ở nhánh `unavailable`, khi dự phòng dùng được thì trả về cùng chuỗi lỗi cầu nối kèm `badge` kiểu `local_fallback_offered` đúng hợp đồng mục 2; khi không dùng được thì giữ nguyên hành vi cũ. Không ghi tin nhắn nào ở nhánh này.
- [x] T039 [M6-FR-027] Truyền `local_synthesis=ret_res.get("local_synthesis")` từ `_run_chat_turn_async` trong `src/aios_habit/workspace_chat_app.py`. Lưu `ret_res` vào phiên để nút dự phòng dùng lại được mà không truy xuất lần hai.

### Phase B — Ghi đáp án cục bộ

- [x] T040 [M6-FR-028] Viết `commit_local_grounded_answer(...)` trong `src/aios_habit/antigravity_bridge.py` dùng đúng bộ ba: `save_message` người dùng → `build_evidence_trace_from_citations` → `save_evidence_trace` → `save_message` trả lời. Trả `(ok, message_vi, badge)`; `badge["provider_used"]` luôn `False`.
- [x] T041 [M6-FR-029] Viết các nhánh từ chối theo hợp đồng mục 3: đáp án rỗng, không có trích dẫn, thiếu định danh hội thoại, lỗi dựng/lưu dấu vết. Mọi nhánh trả thông báo tiếng Việt và ghi 0 tin nhắn.
- [x] T042 [M6-FR-031] Kiểm bằng kiểm thử rằng suốt nhánh dự phòng có đúng 0 lời gọi ra nhà cung cấp (giám sát `call_cagent_prediction`, `generate_workspace_ai_answer`, `call_antigravity_bridge`).

### Phase C — Nối giao diện

- [x] T043 [M6-FR-026] Hiện nút `Xem tổng hợp cục bộ từ trích đoạn` khi huy hiệu là `local_fallback_offered`; bấm thì gọi `commit_local_grounded_answer` rồi làm mới trang trong `src/aios_habit/workspace_chat_app.py`.
- [x] T044 [M6-FR-030] Hiện nhãn `Tổng hợp cục bộ từ trích đoạn — chưa qua mô hình` cho đáp án cục bộ trong `src/aios_habit/workspace_chat_ui.py`, kèm lý do giới hạn khi có. Không gắn tên mô hình hay `Antigravity IDE`.

### Phase D — Nhãn và bản dịch

- [x] T045 [M6-FR-030] Thêm ba chuỗi `local_fallback_offer_button`, `local_fallback_note`, `local_fallback_empty_error` cho cả `vi`, `ja`, `zh-CN` trong `src/aios_habit/i18n.py` theo đúng hợp đồng mục 4.

### Phase E — Kiểm thử

- [x] T046 [M6-FR-026] `test_local_fallback_offered_only_when_grounded` trong `tests/test_antigravity_bridge.py`: bốn ca rỗng/abstained/không-grounded/không truyền tham số đều không mời; ca grounded thì mời và `ok is False`.
- [x] T047 [M6-FR-027] `test_chat_turn_passes_local_synthesis_to_router` trong `tests/test_antigravity_handoff_ui_flow.py`.
- [x] T048 [M6-FR-028] `test_commit_local_grounded_answer_writes_valid_trace` trong `tests/test_antigravity_handoff_ui_flow.py`: sau khi ghi, dấu vết có `status="valid"` và `cited_count` bằng số trích dẫn.
- [x] T049 [M6-FR-029] `test_commit_refuses_empty_or_abstained_answer` trong `tests/test_antigravity_bridge.py`: mọi nhánh từ chối ghi 0 tin nhắn.
- [x] T050 [M6-FR-030] `test_local_fallback_label_is_honest_and_vietnamese` trong `tests/test_workspace_chat_composer_ui.py`: nhãn đúng chữ, không chứa tên mô hình, ba ngôn ngữ đủ khoá.
- [x] T051 [M6-FR-031] `test_local_fallback_makes_zero_provider_calls` trong `tests/test_antigravity_bridge.py`.
- [x] T052 [M6-FR-032] Kiểm thử khẳng định chữ ký trả về của `route_workspace_chat_submission` vẫn bốn phần tử.

### Phase F — Xác minh và tài liệu

- [x] T053 Chạy `pytest` hai tệp liên quan, `compileall`, nhập module và `cli audit`; ghi số kiểm thử đạt và mã thoát.
- [x] T054 Chạy lại smoke 007 (`scripts/smoke_007_modern_chat_composer.py`) vì giao diện đổi; thêm kịch bản cho nhánh dự phòng nếu kiểm được không cần nhà cung cấp.
- [x] T055 Cập nhật `ARCHITECTURE.md` (đường trả lời có nhánh thứ tư), `ROADMAP.md` và `PROJECT_HANDOVER.md`.
- [ ] T056 Kiểm toán độc lập: người/vai kiểm toán khác xác nhận `SC-009..SC-013` bằng bằng chứng chạy thật, không dùng báo cáo của người thực thi.

### Phụ thuộc

```text
Phase A (T037-T039)  →  Phase B (T040-T042)
                              │
                              ▼
                       Phase C (T043-T044)  →  Phase D (T045)
                                                     │
                                                     ▼
                                             Phase E (T046-T052)  →  Phase F (T053-T056)
```

- Phase A phải xong trước B: `commit_local_grounded_answer` dùng cùng kiểu dữ liệu và cùng cách đối chiếu trích dẫn.
- Phase C phụ thuộc B vì nút gọi thẳng hàm ghi.
- Phase D độc lập về mã nhưng phải xong trước E để kiểm thử nhãn có khoá thật.
- Phase F cuối cùng; T056 bắt buộc tách khỏi người thực thi (`AGENT_RULES.md` mục 1 và `AGENTS.md` mục 4.3).

### Truy vết xác minh

| Nhiệm vụ | Lệnh / Cách kiểm | Kết quả mong đợi |
| --- | --- | --- |
| T037–T038, T046, T049, T051–T052 | `pytest tests/test_antigravity_bridge.py -q -k "local_fallback or commit_refuses or zero_provider"` | Toàn bộ đạt |
| T039, T047 | `pytest tests/test_antigravity_handoff_ui_flow.py -q -k "passes_local_synthesis"` | Đạt |
| T040–T041, T048 | `pytest tests/test_antigravity_handoff_ui_flow.py -q -k "commit_local_grounded"` | Đạt, dấu vết `status=valid` |
| T043–T045, T050 | `pytest tests/test_workspace_chat_composer_ui.py -q -k "local_fallback_label"` | Đạt, ba ngôn ngữ đủ khoá |
| T053 | `compileall` + `cli audit` + `import workspace_chat_app` | Sạch, `"status": "PASS"`, `IMPORT_OK` |
| T054 | `scripts/smoke_007_modern_chat_composer.py` | 12/12 PASS (không hồi quy) |
| T056 | Kiểm toán độc lập trên `local_runs/` và mã | `SC-009..SC-013` có bằng chứng chạy thật |
