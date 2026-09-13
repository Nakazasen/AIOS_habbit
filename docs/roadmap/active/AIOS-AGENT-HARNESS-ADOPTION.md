# Thẻ cổng: Trợ lý thực thi công việc cho kỹ sư

Status: `PARTIAL` (US1+US2 Đạt / Proven)
Mã tính năng: `009-agent-harness-adoption`
Chủ sở hữu: Project owner / Software engineering reviewer
Cập nhật: 2026-09-13

## Mục tiêu

Đạt vòng giao việc đủ dùng hằng ngày bằng runtime kế thừa: tạo file/báo cáo lỗi có biểu đồ, rà soát thiết kế công đoạn có dẫn nguồn và sửa mã có test thật. AIOS giữ nguồn, policy theo vùng, checkpoint, verifier và hoàn tác. G1 probe đầy đủ đọc–sửa–test–resume–undo.

## Trạng thái hoàn thành thực tế

Status: `PARTIAL` — US1 và US2 cùng nền tảng bảo mật/chính sách cục bộ đã kiểm chứng đạt 100%:
- **US1 (Báo cáo lỗi xưởng - T011–T015)**: Tự động tổng hợp số liệu từ tệp Excel/nguồn được chọn, tạo báo cáo tiếng Việt và trực quan hóa Mermaid có provenance, tự hoàn tất không cần duyệt. ĐÃ ĐẠT.
- **US2 (Rà soát thiết kế công đoạn - T016–T019)**: Phân định rõ vai trò Guideline/Thiết kế, đánh giá pass/violate/insufficient, đối chiếu dung sai thực tế, bảo lưu SOP/JIG gốc. ĐÃ ĐẠT.
- **Nền an toàn thực thi (T006–T010)**: Task root scope grant, adapter OpenCode tuân thủ `aios_agent_runtime_v1`, chặn cứng path traversal / secret / command cấm, SQLite store version 9 (`agent_work_items`) kèm migration an toàn. ĐÃ ĐẠT.
- **US3 (Sửa mã nguồn & kiểm thử - T020–T023)**: `TẠM HOÃN / IN-PROGRESS` — Chưa kích hoạt chính thức trên UI vì chờ runtime OpenCode thực tế có chứng minh deny/event/undo; không dùng nút sửa mẫu cố định.
- **US4 (Hàng đợi nhiều việc bền vững - T024–T026)**: `IN-PROGRESS` — Unit test hàng đợi đã hoàn tất (T024); đang tiến hành chuẩn hóa UI i18n không dùng từ kỹ thuật và nối trực tiếp luồng enqueue/process thực tế vào ứng dụng.
- **Đóng cổng & kiểm toán (T027–T030)**: `CHƯA ĐÓNG` — Giữ trạng thái PARTIAL cho đến khi US3/US4 đạt trọn vẹn các tiêu chí nghiệm thu nghiêm ngặt.

## Phi mục tiêu

- Không fork OpenCode, dựng editor/terminal/model router, extension Code-OSS, scheduler đa Agent hoặc database session mới trong G1.
- Không tự commit, push, merge, deploy, dùng quyền admin hoặc ghi ngoài workspace.
- Không mở swarm, scheduler nhiều máy, browser automation hay điều khiển line/PLC/JIG.
- Không tự thay SOP, giới hạn sản xuất hoặc tài liệu công đoạn chính thức.

## Điều kiện tiên quyết

- T030–T057 đã commit tại `1d0749b` và remote cùng SHA.
- Kiểm toán 2026-09-07: 29 test US10/Workspace Chat trọng điểm đạt; `compileall`, CLI audit, import, tài liệu và UI tiếng Việt đạt.
- Chủ sở hữu đã chấp thuận năm điểm quyết định tại sổ LSU mục 30.14.

## Bản môi trường thực thi khóa cho G1

Ghi nhận cục bộ ngày 2026-09-13. Đây là bản phải dùng cho kiểm tra G1; việc ghi nhận này **không** có nghĩa G1 đã đạt.

- Gói cài cục bộ: `opencode-ai` phiên bản `1.14.33`.
- Máy G1 không có AVX2, vì vậy lệnh khởi chạy chọn biến thể `opencode-windows-x64-baseline` phiên bản `1.14.33`.
- Tệp thực thi đã kiểm chứng: `opencode.exe`, 183187336 byte, SHA-256 `C37DD78F32F9636D4D79D0B23FF43E37FCFB5A418602074587B7CB280F8774E4`.
- Giấy phép: MIT; tệp `LICENSE` đi kèm gói có SHA-256 `625F0F619133F89BBBB2ABE37369613DFA1885EBA1E50D02170DEB62BB42CB6B`.
- Lệnh khởi động thử nghiệm: `opencode.cmd serve --hostname 127.0.0.1 --port 4096 --pure`. Không dùng `--mdns`; tiến trình chỉ được gắn vào vòng lặp cục bộ và dừng bằng `Ctrl+C` sau kiểm tra.

Trước mỗi kiểm tra, chạy `opencode.cmd --version` và đối chiếu SHA-256 của tệp thực thi biến thể không AVX2 với giá trị trên. Nếu phiên bản, giá trị băm hoặc biến thể phần cứng khác, dừng G1 và ghi lỗi môi trường thực thi; không tạo cầu nối dựa trên bản chưa kiểm chứng.

## Quyết định G1

Status: `PARTIAL` — chỉ ràng US3 (sửa mã). **Goal 009 không BLOCKED.** Cập nhật 2026-09-13 (owner).

Probe OpenCode: đọc / tìm / tạo / sửa / test / resume / hủy **đạt**. Thiếu event/receipt đọc lại, deny-trước-chạy, và hoàn tác chưa sạch digest. Những thiếu đó **chỉ hoãn adapter OpenCode và US3**. Không được dùng để dừng US1/US2.

Cline chưa auth → **bỏ qua**, không cấu hình khóa, không fork.

**Việc tiếp theo bắt buộc: T011 US1** (file báo cáo lỗi trên Workspace Chat, extractors hiện có). Rồi T012–T019 US2. Cấm tạo `opencode_runtime_adapter.py` trước khi US1+US2 có test xanh. Cấm ghi Goal = BLOCKED.

## Danh sách cho phép G1

- `specs/009-agent-harness-adoption/`
- `src/aios_habit/agent_task_pack.py`
- `src/aios_habit/workspace_agent_policy.py`
- `src/aios_habit/workspace_agent_bridge_client.py`
- `src/aios_habit/workspace_agent_orchestrator.py`
- `src/aios_habit/opencode_runtime_adapter.py`
- `scripts/probe_opencode_runtime.py`
- `tests/fixtures/agent_harness/`
- `tests/test_agent_runtime_capabilities.py`
- Tài liệu canonical liên quan trực tiếp.

Mở rộng ngoài allowlist cần cập nhật thẻ cổng trước khi sửa.

## Tiêu chí ra G1

- Pin version, checksum, license và notices.
- Health/version/session/event/read/search/create/edit/test/resume/undo probe đạt trên Windows.
- Read/search/create/edit/test trong task root chạy tự động, không hỏi từng action.
- Path ngoài root, secret, quyền admin, commit, push, merge và deploy bị deny trước thực thi.
- Checkpoint hoàn tác fixture về đúng digest ban đầu; session/event đủ để lập receipt và không lặp action.
- Thiếu undo/deny/event: ghi `PARTIAL`, **vẫn làm US1/US2**. Không `BLOCKED` cả Goal. Không fork.

## Quyền riêng tư

Chỉ dùng fixture giả lập. Server bind `127.0.0.1`, có xác thực cục bộ. Không đưa `local_cases/`, `local_runs/`, `.env`, secret, nguồn nhà máy hoặc dữ liệu `local_only` vào runtime/provider ngoài policy.

## Xác minh

Theo [quickstart](../../../specs/009-agent-harness-adoption/quickstart.md) và [tasks](../../../specs/009-agent-harness-adoption/tasks.md). Full quality gate bắt buộc trước khi đóng toàn feature; kết quả trọng điểm không thay thế tuyên bố phát hành.

## Hoàn tác

Dừng server, dọn worktree fixture tạm sau khi xác minh checkpoint và gỡ adapter/feature flag chưa phát hành. Giữ `antigravity_bridge.py`, nền US6 và receipt đã ghi; không xóa thay đổi có trước của người dùng.

## Liên kết trạng thái

- [ADR-0008](../../adr/0008-inherited-agent-runtime-and-code-oss-companion.md)
- [Đặc tả](../../../specs/009-agent-harness-adoption/spec.md)
- [Kế hoạch](../../../specs/009-agent-harness-adoption/plan.md)
