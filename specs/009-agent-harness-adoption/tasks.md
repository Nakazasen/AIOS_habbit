# Danh sách việc: Trợ lý thực thi công việc cho kỹ sư

## Giai đoạn 1 — Khóa phạm vi và runtime

- [ ] T001 Ghi phiên bản, checksum, giấy phép và cách khởi động OpenCode cục bộ vào `docs/roadmap/active/AIOS-AGENT-HARNESS-ADOPTION.md`
- [ ] T002 Tạo fixture Windows không có dữ liệu thật cho báo cáo, tài liệu công đoạn và repo lỗi mẫu trong `tests/fixtures/agent_harness/`
- [ ] T003 Viết kiểm thử probe read/search/create/edit/test/resume/undo và deny ngoài vùng trong `tests/test_agent_runtime_capabilities.py`
- [ ] T004 Viết probe OpenCode theo đúng bản đã pin trong `scripts/probe_opencode_runtime.py`
- [ ] T005 Ghi quyết định G1 dựa trên output thật vào `docs/roadmap/active/AIOS-AGENT-HARNESS-ADOPTION.md`; chỉ tạo adapter nếu probe đạt

## Giai đoạn 2 — Nền dùng chung tối thiểu

- [ ] T006 Mở rộng policy theo task root, loại nhiệm vụ, lệnh test và vùng cấm trong `src/aios_habit/workspace_agent_policy.py`
- [ ] T007 Tạo adapter OpenCode mỏng cho session, event, file và command trong `src/aios_habit/opencode_runtime_adapter.py`
- [ ] T008 Mở rộng orchestrator cho checkpoint, resume, rollback và một writer theo workspace trong `src/aios_habit/workspace_agent_orchestrator.py`
- [ ] T009 Mở rộng record `agent_work` bằng migration nhỏ, có backup và rollback trong `src/aios_habit/workspace_case_repository.py`
- [ ] T010 Kiểm thử chung về path traversal, secret, Unicode, idempotency và restart trong `tests/test_agent_work_foundation.py`

## Giai đoạn 3 — US1: Báo cáo lỗi có biểu đồ

**Mục tiêu**: kỹ sư giao hồ sơ lỗi và nhận bản nháp báo cáo tiếng Việt có bảng/biểu đồ đúng nguồn.

**Kiểm thử độc lập**: fixture có log và số liệu tạo được báo cáo; mọi điểm trên biểu đồ truy ngược được, còn fixture thiếu số liệu không sinh biểu đồ giả.

- [ ] T011 [US1] Viết kiểm thử hợp đồng báo cáo, nguồn số liệu và fallback không vẽ biểu đồ trong `tests/test_agent_error_report_artifact.py`
- [ ] T012 [P] [US1] Dùng lại bộ đọc tài liệu và metadata Excel để tạo bảng dữ liệu biểu đồ trong `src/aios_habit/agent_work_artifact.py`
- [ ] T013 [P] [US1] Dùng lại khả năng Mermaid/visual hiện có để tạo biểu đồ hoặc sơ đồ kèm provenance trong `src/aios_habit/agent_work_artifact.py`
- [ ] T014 [US1] Tạo hoặc cập nhật bản nháp báo cáo lỗi và checkpoint hoàn tác trong `src/aios_habit/agent_work_artifact.py`
- [ ] T015 [US1] Thêm hành động “Tạo báo cáo lỗi” và thẻ kết quả đời thường trong `src/aios_habit/workspace_chat_app.py`

## Giai đoạn 4 — US2: Rà soát thiết kế công đoạn

**Mục tiêu**: chỉ ra điểm sai, mâu thuẫn, thiếu kiểm soát và cải tiến nên làm từ tài liệu đã chọn.

**Kiểm thử độc lập**: fixture có mâu thuẫn giới hạn, bước thiếu điểm kiểm tra và khoảng trống bằng chứng được phân loại đúng, dẫn đúng nguồn và chỉ tạo bản nháp.

- [ ] T016 [US2] Viết kiểm thử phát hiện có nguồn, suy luận, đề xuất và câu hỏi cần xác nhận trong `tests/test_agent_process_design_review.py`
- [ ] T017 [US2] Ghép evidence pack theo phạm vi tài liệu người dùng chọn trong `src/aios_habit/agent_work_artifact.py`
- [ ] T018 [US2] Tạo bản rà soát năm phần và sơ đồ hiện tại/đề xuất trong `src/aios_habit/agent_work_artifact.py`
- [ ] T019 [US2] Thêm hành động “Rà soát thiết kế công đoạn” và cảnh báo đây là bản nháp trong `src/aios_habit/workspace_chat_app.py`

## Giai đoạn 5 — US3: Sửa mã và chạy test

**Mục tiêu**: Agent tự đọc, sửa và chạy test trong worktree rồi cho dùng kết quả hoặc hoàn tác.

**Kiểm thử độc lập**: bug fixture được sửa sau một vòng test lỗi–sửa lại–test đạt; workspace chính không mất thay đổi có trước và thao tác cấm bị chặn.

- [ ] T020 [US3] Viết E2E cho vòng sửa–test–sửa lại–dùng kết quả–hoàn tác trong `tests/test_agent_code_worktree.py`
- [ ] T021 [US3] Nối OpenCode adapter vào orchestrator cho tác vụ mã nguồn trong `src/aios_habit/workspace_agent_orchestrator.py`
- [ ] T022 [US3] Xác minh exit code, trạng thái Git và xung đột trước khi dùng kết quả trong `src/aios_habit/agent_result_import.py`
- [ ] T023 [US3] Thêm thẻ tóm tắt “đã làm gì, test ra sao, file bị tác động, rủi ro” và thu gọn `diff` trong `src/aios_habit/workspace_chat_app.py`

## Giai đoạn 6 — US4: Hàng đợi nhiều việc

**Mục tiêu**: người dùng tiếp tục giao việc và theo dõi nhiều nhiệm vụ mà không cần cấu hình kỹ thuật.

**Kiểm thử độc lập**: ba việc thuộc ba loại giữ đúng thứ tự/trạng thái qua restart; hai việc ghi cùng workspace không chạy đồng thời.

- [ ] T024 [US4] Viết kiểm thử hàng đợi, writer lock theo workspace, hủy và resume trong `tests/test_agent_work_queue.py`
- [ ] T025 [US4] Mở rộng orchestrator bằng hàng đợi bền vững tối thiểu dùng record hiện có trong `src/aios_habit/workspace_agent_orchestrator.py`
- [ ] T026 [US4] Hiển thị các trạng thái tiếng Việt và hành động mở/hủy/hoàn tác trong `src/aios_habit/workspace_chat_app.py`

## Giai đoạn 7 — Hoàn thiện và kiểm toán độc lập

- [ ] T027 Chạy kiểm thử privacy, secret, prompt injection, đường dẫn Windows, mojibake và hồi quy cầu nối Antigravity trong `tests/test_agent_work_foundation.py`
- [ ] T028 Cập nhật threat model và đánh giá riêng tư đúng phần thay đổi trong `docs/security/THREAT_MODEL.md` và `docs/security/PRIVACY_IMPACT_ASSESSMENT.md`
- [ ] T029 Cập nhật trạng thái thực tế và bằng chứng vào `ARCHITECTURE.md`, `ROADMAP.md`, `PROJECT_HANDOVER.md` và `docs/roadmap/active/AIOS-AGENT-HARNESS-ADOPTION.md`
- [ ] T030 Chạy các cổng chất lượng trong `specs/009-agent-harness-adoption/quickstart.md`; reviewer độc lập mới quyết định `DONE` hoặc `BLOCKED`

## Phụ thuộc và chiến lược triển khai

- T001–T005 là cổng dừng sớm. Nếu OpenCode không chứng minh được đọc–sửa–test–hoàn tác đúng phạm vi, dừng và đánh giá Cline theo cùng fixture; không fork sâu.
- T006–T010 là nền chung nhỏ nhất. Không mở thêm abstraction nếu chưa có task nghiệm thu cần nó.
- US1 là MVP và phải hoàn tất trước: nó chứng minh giá trị tạo file/báo cáo và khả năng trực quan hóa.
- US2 dùng lại nền nguồn và artifact của US1; US3 dùng lại policy/checkpoint; US4 chỉ bắt đầu sau khi ít nhất US1 và US3 chạy được đơn nhiệm.
- T012 và T013 có thể làm song song sau T011. Các story khác thực hiện tuần tự để giữ diff nhỏ và dễ hoàn tác.
- Extension Code-OSS, partial-hunk approval, scheduler nhiều máy và multi-agent swarm không thuộc danh sách này.
