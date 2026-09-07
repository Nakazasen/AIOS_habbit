# Thẻ cổng: Nâng US6 thành Agent lập trình có kiểm soát

Status: `ACTIVE`
Mã tính năng: `009-agent-harness-adoption`
Chủ sở hữu: Project owner / Software engineering reviewer
Cập nhật: 2026-09-07

## Mục tiêu

Đạt vòng lập trình và thao tác file đủ dùng hằng ngày bằng runtime kế thừa, trong khi AIOS giữ quyền, bằng chứng và phê duyệt. G1 chỉ là spike chỉ đọc và là cổng dừng sớm.

## Phi mục tiêu

- Không fork OpenCode, dựng editor/terminal/model router hoặc tạo database session mới trong G1.
- Không tự commit, push, merge, deploy, dùng quyền admin hoặc ghi ngoài workspace.
- Không mở swarm, scheduler nhiều máy, browser automation hay điều khiển line/PLC/JIG.

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
- `src/aios_habit/agent_runtime_protocol.py`
- `src/aios_habit/opencode_runtime_adapter.py`
- `scripts/probe_opencode_runtime.py`
- `tests/fixtures/agent_harness/`
- `tests/test_agent_runtime_capabilities.py`
- Tài liệu canonical liên quan trực tiếp.

Mở rộng ngoài allowlist cần cập nhật thẻ cổng trước khi sửa.

## Tiêu chí ra G1

- Pin version, checksum, license và notices.
- Health/version/session/SSE/read/search probe đạt trên Windows.
- Write và command bị deny trước khi thực thi; digest fixture không đổi.
- Session ID/resume và event ordering đủ để lập receipt.
- Nếu thiếu một điều kiện: trạng thái `BLOCKED`, ghi bằng chứng và đánh giá Cline; không fork.

## Quyền riêng tư

Chỉ dùng fixture giả lập. Server bind `127.0.0.1`, có xác thực cục bộ. Không đưa `local_cases/`, `local_runs/`, `.env`, secret, nguồn nhà máy hoặc dữ liệu `local_only` vào runtime/provider ngoài policy.

## Xác minh

Theo [quickstart](../../../specs/009-agent-harness-adoption/quickstart.md) và [tasks](../../../specs/009-agent-harness-adoption/tasks.md). Full quality gate bắt buộc trước khi đóng toàn feature; kết quả trọng điểm không thay thế tuyên bố phát hành.

## Hoàn tác

Dừng server, xóa worktree fixture tạm và gỡ adapter/feature flag chưa phát hành. Giữ nguyên US6 foundation và không xóa receipt đã ghi.

## Liên kết trạng thái

- [ADR-0008](../../adr/0008-inherited-agent-runtime-and-code-oss-companion.md)
- [Đặc tả](../../../specs/009-agent-harness-adoption/spec.md)
- [Kế hoạch](../../../specs/009-agent-harness-adoption/plan.md)
