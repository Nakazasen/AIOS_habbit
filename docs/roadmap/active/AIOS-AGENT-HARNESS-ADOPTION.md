# Thẻ cổng: Trợ lý thực thi công việc cho kỹ sư

Status: `ACTIVE`
Mã tính năng: `009-agent-harness-adoption`
Chủ sở hữu: Project owner / Software engineering reviewer
Cập nhật: 2026-09-11

## Mục tiêu

Đạt vòng giao việc đủ dùng hằng ngày bằng runtime kế thừa: tạo file/báo cáo lỗi có biểu đồ, rà soát thiết kế công đoạn có dẫn nguồn và sửa mã có test thật. AIOS giữ nguồn, policy theo vùng, checkpoint, verifier và hoàn tác. G1 phải probe đầy đủ đọc–sửa–test–resume–undo, không phải spike chỉ đọc.

## Phi mục tiêu

- Không fork OpenCode, dựng editor/terminal/model router, extension Code-OSS, scheduler đa Agent hoặc database session mới trong G1.
- Không tự commit, push, merge, deploy, dùng quyền admin hoặc ghi ngoài workspace.
- Không mở swarm, scheduler nhiều máy, browser automation hay điều khiển line/PLC/JIG.
- Không tự thay SOP, giới hạn sản xuất hoặc tài liệu công đoạn chính thức.

## Điều kiện tiên quyết

- T030–T057 đã commit tại `1d0749b` và remote cùng SHA.
- Kiểm toán 2026-09-07: 29 test US10/Workspace Chat trọng điểm đạt; `compileall`, CLI audit, import, tài liệu và UI tiếng Việt đạt.
- Chủ sở hữu đã chấp thuận năm điểm quyết định tại sổ LSU mục 30.14.

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
- Nếu thiếu một điều kiện: trạng thái `BLOCKED`, ghi bằng chứng và đánh giá Cline; không fork.

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
