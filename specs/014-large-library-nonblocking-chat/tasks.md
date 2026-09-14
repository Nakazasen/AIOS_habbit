# Danh mục Công việc: 014-large-library-nonblocking-chat

**Branch**: `014-large-library-nonblocking-chat` | **Đặc tả**: [specs/014-large-library-nonblocking-chat/spec.md](file:///d:/Sandbox/AIOS_habbit/specs/014-large-library-nonblocking-chat/spec.md) | **Kế hoạch**: [specs/014-large-library-nonblocking-chat/plan.md](file:///d:/Sandbox/AIOS_habbit/specs/014-large-library-nonblocking-chat/plan.md)

---

## Phase 1: Tạo Đặc tả SpecKit & Cấu Trúc Đề Án

- [x] **T01-SPECKIT-DOCS**: Khởi tạo thư mục `specs/014-large-library-nonblocking-chat/` gồm `spec.md`, `plan.md`, `tasks.md` theo quy chuẩn SpecKit của dự án.

---

## Phase 2: Thực thi Chỉnh sửa Mã Nguồn (Code Implementation)

- [x] **T02-REMOVE-EAGER-ENQUEUE**: Chỉnh sửa L2180-2183 và L3464-3467 trong `src/aios_habit/workspace_chat_app.py`.
  - Gỡ bỏ lệnh `reconcile_and_enqueue_workspace_chat_sources(prep_context_sources)` trên toàn bộ 988 nguồn trong sidebar và biến `prep_status_map` không dùng.
  - Thay thế `schedule_workspace_chat_source_preparation(ctx_all_sources)` tại L3466 bằng việc chỉ enqueue các nguồn đang bật (`enabled_ctx_sources`).
- [x] **T03-GRACEFUL-DEGRADATION-PENDING**: Sửa hàm `_pending_source_submission_state` (L758-765) trong `src/aios_habit/workspace_chat_app.py`.
  - Không trả về `failed` nếu có nguồn bị lỗi nhưng vẫn còn nguồn sẵn sàng hoặc còn nội dung văn bản nguồn để trả lời fallback.
- [x] **T04-SUBMIT-GATE-REMEDIATION**: Nâng cấp cổng kiểm tra nguồn khi gửi câu hỏi (L2957-3062) trong `src/aios_habit/workspace_chat_app.py`.
  - Khi có nguồn `failed`, không hủy câu hỏi; tiếp tục tra cứu trên tập `ready_sources`.
  - Xử lý Broad Query tuân thủ FR-006 & FR-011: Không enqueue hàng loạt 171 nguồn; yêu cầu thu hẹp câu hỏi nếu có nhiều nguồn unready, hoặc chỉ chuẩn bị tối đa 1 nguồn nếu chỉ có 1 nguồn.
  - Hỗ trợ chế độ fallback nội dung văn bản nguồn (`retrieval_applied = False`) khi không có nguồn vector sẵn sàng.
- [x] **T05-OPTIMIZE-UI-POLLING**: Tối ưu hóa polling giao diện tại L3499 trong `src/aios_habit/workspace_chat_app.py`.
  - Giãn chu kỳ polling từ 2.5s lên 4.0s.
  - Chỉ theo dõi tiến độ của `enabled_ctx_sources` (thay vì toàn bộ 988 nguồn thư viện).
- [x] **T06-BRIDGE-FALLBACK-CONTEXT**: Cập nhật hàm `route_workspace_chat_submission` trong `src/aios_habit/antigravity_bridge.py`.
  - Bổ sung trích đoạn văn bản từ `packed_sources` vào `context_blocks` khi `evidence_items` rỗng để Gemini Web Bridge có đủ ngữ cảnh trả lời.

---

## Phase 3: Kiểm thử & Nghiệm thu Chất lượng

- [x] **T07-UNIT-TESTS**: Viết bài kiểm tra tự động xác nhận cơ chế Graceful Degradation, gỡ bỏ eager enqueue và tuân thủ FR-006 & FR-011 trong `tests/test_large_library_nonblocking_chat.py`.
- [x] **T08-REGRESSION-SUITE**: Chạy bộ kiểm thử hiện có của Workspace Chat:
  - `tests/test_workspace_chat_source_selection_owner_flow.py`
  - `tests/test_workspace_chat_app_smoke.py`
  - `tests/test_large_library_nonblocking_chat.py`
- [x] **T09-QUALITY-GATES**: Xác nhận toàn bộ các cổng kiểm tra chất lượng đạt chuẩn:
  - `python -m compileall src tests`
  - `python -m aios_habit.cli audit` -> `"status": "PASS"`
  - `python -c "import aios_habit.workspace_chat_app; print('Import OK')"`
