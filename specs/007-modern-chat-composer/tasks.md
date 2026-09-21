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
- [X] T011 Run compilation, import, CLI audit, and `git diff --check` for the modified Workspace Chat files (2026-09-12: `compileall` sạch, import Workspace Chat, CLI audit `"status": "PASS"`, smoke Playwright 6/6)
- [X] T012 Refresh the repository graph with `graphify update .` after code changes
- [X] T013 Move the AI bridge selector and its C-AGENT endpoint configuration into the composer toolbar in `src/aios_habit/workspace_chat_app.py`
- [X] T014 Add the compact attachment popover, clipboard-image thumbnail, and removal control in `src/aios_habit/workspace_chat_app.py`
- [X] T015 Pin the clipboard component and cover its UI/i18n behavior in `pyproject.toml`, `uv.lock`, `src/aios_habit/i18n.py`, and `tests/test_workspace_chat_composer_ui.py`

## Dependencies & Execution Order

- T001 → T002 → T003/T004/T005 → T006/T007 → T008/T009 → T010 → T011 → T012.
- T003 and T004 share the application file and must be completed together.
- T006 depends on the P1 composer structure; T008 depends on the final control layout.

## Implementation Strategy

Implement and validate the P1 composer first, then add progressive attachment, model selection, and keyboard/responsive refinements. Keep explicit send as the behavioral boundary throughout. For widget state management, adhere strictly to Streamlit's lifecycle: never mutate widget-associated keys after widget instantiation in the same run; use deferred reset flags evaluated prior to instantiation.

## Mở rộng: Gợi ý câu hỏi mở đầu và câu tiếp theo (phiên 2026-09-19, không tạo spec mới)

**Phạm vi**: Tối đa 3 gợi ý sinh từ tên tài liệu đang bật, bấm là gửi đúng chữ, sổ chưa có nguồn thì không hiện. Sau câu trả lời có trích dẫn thì gợi ý tiếp theo nhắc đúng nhãn trích dẫn.

- [x] T013 Hàm sinh gợi ý mở đầu và gợi ý tiếp theo trong `src/aios_habit/question_suggestions.py`, có test trong `tests/test_question_suggestions.py`
- [x] T014 Hiện nút gợi ý trên composer và sau câu trả lời trong `src/aios_habit/workspace_chat_app.py`
- [x] T015 Chạy kiểm chứng `compileall`, kiểm thử liên quan, quét tiếng Việt, `cli audit` đạt `PASS`, `import workspace_chat_app` thành công

**Bằng chứng ngày 2026-09-19**: `compileall` sạch, `test_question_suggestions + test_shared_mailbox + test_shared_library_presets` **12 passed**, quét tiếng Việt **PASS**, `cli audit` **PASS**, `import workspace_chat_app` thành công, `git diff --check` sạch.

## Mở rộng: Bộ đo 5 mạch bám mạch (phiên 2026-09-19, không tạo spec mới)

**Phạm vi**: 5 mạch từ NotebookLM chuyển thành 15 câu hỏi đóng băng kèm tệp kỳ vọng, cả 5 tệp đã đối chiếu có trong sổ. Đo gợi ý bám mạch, không đo BGE.

- [x] T016 Bộ đo đóng băng trong `tests/fixtures/suggestion_threads/v1.json`, 5 mạch 15 câu, cả 5 tệp kỳ vọng đã đối chiếu có trong sổ
- [x] T017 Chạy bộ đo sau mỗi lần đổi mã gợi ý, ghi đạt hoặc loại theo bám mạch câu 2 và 3

**Bằng chứng T017 ngày 2026-09-19**: `test_suggestion_threads + test_question_suggestions` **14 passed**. Vòng đo bắt được nút thứ ba thiếu nguồn nên đã sửa để cả 3 nút bám nguồn và tên đầy đủ khi gửi.

## Đo chất lượng trả lời 8 mạch (phiên 2026-09-19, không tạo spec mới)

**Phạm vi**: Hệ ta trả lời 24 câu trên văn bản thật trong sổ bằng đường nhẹ lexical, kiểm tra nguồn kỳ vọng có trong trích dẫn. Đo bám nguồn, chưa chấm đúng sai chuyên môn.

- [x] T018 Chạy 24 câu qua `local_runs/run_thread_answers.py`, ghi trúng nguồn và thời gian vào `local_runs/thread_answer_probe/report.json`

**Bằng chứng T018 ngày 2026-09-19**: trúng nguồn **20/24**, mỗi câu **0.05-0.14 giây**. 4 câu trượt đều là câu mở đầu chưa có mạch, các câu sau có mạch đều trúng. Đường lexical chỉ tìm chữ, câu hỏi tiếng Việt hỏi nội dung tiếng Nhật dễ trượt, ca BGE theo nghĩa để nhịp đêm.

## Mở rộng nontech US7/US8 (phiên 2026-09-21, không tạo spec mới)

**Phạm vi**: Câu chuyện 7 composer siêu thân thiện (P1) và Câu chuyện 8 thẻ JIG, biểu đồ, mail dễ hiểu (P2) theo `spec.md` FR-014 tới FR-020 và SC-007 tới SC-010. Dùng lại luồng gửi, mô đun `production_prediction` và gợi ý hiện có.

**Thứ tự**: US7 trước (MVP), US8 sau. US8 dùng được độc lập sau khi US7 xong.

- [x] T019 [US7] Bổ sung kiểm thử hợp đồng nhãn nhìn thấy, nút 44 px, lỗi cạnh trường trong `tests/test_workspace_chat_composer_ui.py`
- [x] T020 [US7] Hiện nhãn tiếng Việt, nút gửi/dừng trong composer và hướng dẫn cạnh trường trong `src/aios_habit/workspace_chat_app.py`
- [x] T021 [US7] Giữ tương đương bản dịch cho chuỗi mới trong `src/aios_habit/i18n.py` và kiểm thử trong `tests/test_workspace_chat_ui_i18n.py`
- [x] T022 [US8] Bổ sung kiểm thử thẻ JIG một câu kết luận, biểu đồ hình chữ bảng số trong `tests/test_jig_chat_wire.py`
- [x] T023 [US8] Vẽ thẻ JIG, điểm đánh dấu bất thường và bảng số thay thế trong `src/aios_habit/production_prediction/jig_chat_wire.py`
- [x] T024 [US8] Nối nút Tạm dừng/Tiếp tục và cô lập phiên trực ban trong `src/aios_habit/workspace_chat_app.py`
- [x] T025 [US8] Hiện màn hình duyệt mail trước khi gửi trong `src/aios_habit/production_prediction/alert_mailer.py`
- [x] T026 Chạy kiểm chứng tập trung, biên dịch, kiểm toán và smoke 007 theo `specs/007-modern-chat-composer/quickstart.md`

**Kiểm thử độc lập từng chuyện**:

- US7: người mới nhận ra chỗ nhập/gửi trong 5 giây, gửi trống thấy hướng dẫn cạnh nút, chờ tài liệu bấm dừng được, 360 px không chồng lấp.
- US8: dán log vượt ngưỡng ra thẻ Nguy cơ kèm JIG và đề xuất, biểu đồ có hình chữ bảng số, tạm dừng không mất dữ liệu ngầm, mail chỉ gửi sau khi duyệt.
