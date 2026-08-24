# Tasks: Modern Chat Composer

**Input**: Design documents from `/specs/007-modern-chat-composer/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/composer-ui-contract.md, quickstart.md

**Tests**: Required by FR-003, SC-004, and the project constitution.

## Phase 1: Setup

- [X] T001 Review the existing composer contract and current focused test guards in `src/aios_habit/workspace_chat_app.py` and `tests/test_workspace_chat_source_selection_owner_flow.py`

## Phase 2: Foundational

- [X] T002 Add a focused UI-contract test module in `tests/test_workspace_chat_composer_ui.py` covering compact structure, progressive image attachment, retained image allowlist, shortcut declaration, and 360 px responsive rule

## Phase 3: User Story 1 - Soạn và gửi câu hỏi gọn gàng (Priority: P1)

**Goal**: Deliver a compact modern composer while preserving explicit submit behavior.

**Independent Test**: Enter and submit a text-only question by button and keyboard shortcut; the explicit send contract remains present without a tall form shell.

- [X] T003 [US1] Refactor the question form into a bounded, rounded primary composer with collapsed label, explicit send action, and compact secondary controls in `src/aios_habit/workspace_chat_app.py`
- [X] T004 [US1] Add scoped responsive styling that keeps composer controls visible at 360 px in `src/aios_habit/workspace_chat_app.py`
- [X] T005 [US1] Extend explicit-submit regression coverage for the composer send button and keyboard shortcut in `tests/test_workspace_chat_source_selection_owner_flow.py`

## Phase 4: User Story 2 - Đính kèm ảnh không làm rối luồng hỏi (Priority: P2)

**Goal**: Make image attachment progressive without changing image processing.

**Independent Test**: Expand attachment, choose a supported image, and submit image-only while preserving current ingestion behavior.

- [X] T006 [US2] Add progressive attachment disclosure and render the existing image picker inside the collapsed attachment section in `src/aios_habit/workspace_chat_app.py`
- [X] T007 [US2] Verify existing image-only and upload-version behavior through focused tests in `tests/test_workspace_chat_composer_ui.py` and `tests/test_workspace_chat_multi_file_uploader.py`

## Phase 5: User Story 3 - Dùng được bằng bàn phím và màn hình hẹp (Priority: P3)

**Goal**: Keep native accessibility and ensure the composer adapts to narrow windows.

**Independent Test**: Submit using Ctrl+Enter and inspect the composer at 360 px without overlapping controls.

- [X] T008 [US3] Add a locale-neutral shortcut hint and reuse existing localized labels for the composer controls in `src/aios_habit/workspace_chat_app.py`
- [X] T009 [US3] Verify existing translation-parity coverage remains green because no new composer translation keys are introduced in `tests/test_workspace_chat_ui_i18n.py`

## Phase 6: Polish and Validation

- [X] T010 Run focused composer, owner-flow, image-upload, and UI-i18n tests from `specs/007-modern-chat-composer/quickstart.md`
- [ ] T011 Run compilation, import, CLI audit, and `git diff --check` for the modified Workspace Chat files
- [X] T012 Refresh the repository graph with `graphify update .` after code changes
- [X] T013 Move the AI bridge selector and its C-AGENT endpoint configuration into the composer toolbar in `src/aios_habit/workspace_chat_app.py`
- [X] T014 Add the compact attachment popover, clipboard-image thumbnail, and removal control in `src/aios_habit/workspace_chat_app.py`
- [X] T015 Pin the clipboard component and cover its UI/i18n behavior in `pyproject.toml`, `uv.lock`, `src/aios_habit/i18n.py`, and `tests/test_workspace_chat_composer_ui.py`

## Dependencies & Execution Order

- T001 → T002 → T003/T004/T005 → T006/T007 → T008/T009 → T010 → T011 → T012.
- T003 and T004 share the application file and must be completed together.
- T006 depends on the P1 composer structure; T008 depends on the final control layout.

## Implementation Strategy

Implement and validate the P1 composer first, then add progressive attachment, model selection, and keyboard/responsive refinements. Keep explicit send as the behavioral boundary throughout.
