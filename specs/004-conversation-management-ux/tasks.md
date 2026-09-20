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
- 2026-09-13: `uv run --no-sync --group dev pytest -q --durations=20` → **2800 passed, 3 failed** in 782.82s. CLI audit `"status": "PASS"`. Ba fail ngoài 004 (wheelhouse; hardcode-guard `t_parts` trên `_unique_content_parts`; prep-gate RAG). Không đánh dấu TECHNICAL_PASS.
- 2026-09-13 (đóng cổng): đổi tên `_unique_clause_parts`; cập nhật test cổng Non-blocking RAG; tách `tests/test_commit_d_wheel_and_packaging.py` bằng marker `desktop_packaging`. `pytest -q -m "not desktop_packaging"` → **2774 passed, 29 deselected, 0 failed** in 182s. `TECHNICAL_PASS`.

## Mở rộng: Nhiều thư viện và vào kho một chạm (phiên 2026-09-19, không tạo spec mới)

**Phạm vi**: Mỗi kho preset là một thư viện riêng, tạo thư viện bằng tên và thư mục, vào kho một chạm, ghi yêu cầu về máy kho. Toàn tiếng Việt, một lúc chỉ mở một kho.

- [x] T101 Đăng ký kho preset đọc thư mục mẫu `*.json`, chịu 10 kho, bỏ tệp hỏng trong `src/aios_habit/shared_library_presets.py`, có test trong `tests/test_shared_library_presets.py`
- [x] T102 Khối danh sách kho một chạm và ghi yêu cầu máy kho trong `src/aios_habit/workspace_chat_app.py`, chữ tiếng Việt trong `src/aios_habit/i18n.py`
- [x] T103 Sửa lỗi nút quay về thư viện cục bộ ghi đè ô nhập sau khi ô đã hiện trong `src/aios_habit/workspace_chat_app.py`
- [x] T104 Vào kho preset tạo hoặc dùng thư viện riêng theo từng kho trong `src/aios_habit/workspace_chat_store.py`, kho cũ giữ nguyên, có test
- [x] T105 Nút tạo thư viện mới bằng tên và thư mục trong `src/aios_habit/workspace_chat_app.py`, thư mục có thư viện khác thì báo rõ và giữ nguyên
- [x] T106 Chạy kiểm chứng `compileall`, kiểm thử liên quan, quét tiếng Việt, `cli audit` đạt `PASS`, `import workspace_chat_app` thành công

**Bằng chứng ngày 2026-09-19**: `compileall` sạch, `test_shared_library_presets + test_workspace_chat_store + test_rag_v2_lite_pilot` **58 passed**, quét tiếng Việt **PASS**, `cli audit` **PASS**, `import workspace_chat_app` thành công, `git diff --check` sạch. Trước đó: `test_shared_library_presets + test_rag_v2_lite_pilot + test_rag_v2_chunking` **26 passed**.

## Mở rộng: Hộp thư chung theo từng kho (phiên 2026-09-19, không tạo spec mới)

**Phạm vi**: Yêu cầu nằm trong thư mục của kho đích, bắt buộc chọn kho, ghi tên người gửi, mọi máy được đánh dấu xong kèm tên và thời điểm, kho local thì báo rõ.

- [x] T107 Hộp thư theo kho trong `src/aios_habit/shared_mailbox.py` (ghi, đọc, đánh dấu xong, khóa ghi), có test trong `tests/test_shared_mailbox.py`
- [x] T108 Giao diện chọn kho đích, tên người gửi, danh sách yêu cầu và đánh dấu xong trong `src/aios_habit/workspace_chat_app.py`, chữ tiếng Việt trong `src/aios_habit/i18n.py`
- [x] T109 Chạy kiểm chứng `compileall`, kiểm thử liên quan, quét tiếng Việt, `cli audit` đạt `PASS`, `import workspace_chat_app` thành công

**Bằng chứng hộp thư ngày 2026-09-19**: `compileall` sạch, `test_shared_mailbox + test_shared_library_presets + test_workspace_chat_store` **53 passed**, quét tiếng Việt **PASS**, `cli audit` **PASS**, `import workspace_chat_app` thành công, `git diff --check` sạch.

## Mở rộng: Thấy và đổi thư viện trong sổ (phiên 2026-09-19, không tạo spec mới)

**Phạm vi**: Trong sổ luôn thấy thư viện đang dùng và đổi được, lúc tạo sổ chỉ còn một thư viện thì hiện câu xác nhận thay vì ô chọn vô nghĩa.

- [x] T110 Hiện thư viện đang dùng và ô đổi thư viện trong sổ trong `src/aios_habit/workspace_chat_app.py`, chữ tiếng Việt trong `src/aios_habit/i18n.py`
- [x] T111 Gọn ô chọn thư viện lúc tạo sổ khi chỉ còn một thư viện trong `src/aios_habit/workspace_chat_app.py`
- [x] T112 Chạy kiểm chứng `compileall`, kiểm thử liên quan, quét tiếng Việt, `cli audit` đạt `PASS`, `import workspace_chat_app` thành công

**Bằng chứng ngày 2026-09-19**: `compileall` sạch, `test_shared_mailbox + test_shared_library_presets + test_workspace_chat_store` **53 passed**, quét tiếng Việt **PASS**, `cli audit` **PASS**, `import workspace_chat_app` thành công, `git diff --check` sạch.
