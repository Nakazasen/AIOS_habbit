# Kế hoạch triển khai: Agent lập trình và thao tác file có kiểm soát

**Mã tính năng**: `009-agent-harness-adoption` | **Ngày**: 2026-09-07 | **Đặc tả**: [spec.md](spec.md)

## 1. Tóm tắt

Tái sử dụng OpenCode qua server/adapter làm runtime ứng viên chính, Code-OSS làm mặt bàn chuyên dụng và Cline làm benchmark/fallback. AIOS không viết lại harness; chỉ giữ Task Pack, policy, approval, receipt, Case/Evidence và learning đã duyệt. Triển khai theo cổng G0–G8, trong đó G1 là cổng dừng sớm.

## 2. Bối cảnh kỹ thuật

- **Ngôn ngữ**: Python 3.11 cho AIOS; TypeScript chỉ cho extension Code-OSS mỏng.
- **Phụ thuộc chính**: runtime OpenCode chạy cục bộ qua HTTP/OpenAPI/SSE; Git worktree; API extension Code-OSS.
- **Lưu trữ**: tiếp tục dùng `workspace_cases.sqlite` cho metadata/digest/receipt; runtime tự giữ session trong vùng cục bộ của nó.
- **Kiểm thử**: `pytest`, contract test, fault injection, E2E Windows và benchmark cố định.
- **Nền tảng**: Windows 10/11, ưu tiên cục bộ, một người dùng.
- **Ràng buộc**: deny mặc định; không tự commit/push/deploy; không quyền admin; không ghi ngoài worktree; không tạo database thứ năm.
- **Quy mô bản đầu**: một task, một workspace và một runtime session tại một thời điểm; có command job foreground/background bị giới hạn.

## 3. Kiểm tra Hiến chương

| Cổng | Kết quả thiết kế |
|---|---|
| Bằng chứng trước tuyên bố | Mọi test và action tạo receipt; model không tự báo PASS |
| Local-first và đồng ý | Runtime bind `127.0.0.1`; provider route vẫn qua policy AIOS; không gửi `local_only` mặc định |
| Khả năng thay thế | Adapter có version; OpenCode không đạt G1 thì dừng và thử Cline theo cùng contract |
| Giao diện tiếng Việt | Extension và Workspace Chat dùng tiếng Việt dễ hiểu; chặn traceback/raw error |
| Kỷ luật thay đổi | Worktree tách biệt, proposal digest, verifier độc lập, rollback và cập nhật tài liệu canonical |

Không có ngoại lệ Hiến chương được yêu cầu. Kiểm tra sau thiết kế vẫn đạt.

## 4. Kiến trúc được chọn

```text
Workspace Chat / Code-OSS / CLI
             ↓ cùng protocol
AIOS Agent Gateway: Task Pack + policy + approval + receipt
             ↓ adapter cục bộ có version
OpenCode runtime/server
             ↓ tool và session trong phạm vi
Git worktree tách biệt
             ↓ diff + observed test
AIOS Case / Evidence / Learning đã duyệt
```

Ranh giới chi tiết nằm trong [ADR-0008](../../docs/adr/0008-inherited-agent-runtime-and-code-oss-companion.md). Không có đường trực tiếp từ RAG answer đến tool ghi.

## 5. Cấu trúc dự kiến

```text
src/aios_habit/
├── agent_task_pack.py
├── coding_assistant.py
├── agent_result_import.py
├── workspace_agent_policy.py
├── workspace_agent_orchestrator.py
├── workspace_agent_bridge_client.py
├── agent_runtime_protocol.py        # mới nếu G1 đạt
└── opencode_runtime_adapter.py      # mới nếu G1 đạt

extensions/aios-agent-companion/     # extension Code-OSS mỏng, chỉ mở từ G5
tests/fixtures/agent_harness/         # repo fixture không chứa dữ liệu thật
tests/test_agent_runtime_*.py
```

Ưu tiên nâng các module hiện có. Chỉ tạo hai module protocol/adapter khi G1 chứng minh cần thiết; không dựng framework song song.

## 6. Cổng triển khai

| Cổng | Phạm vi | Điều kiện ra |
|---|---|---|
| G0 | Đóng audit T057, đặc tả, ADR, Gate Card và kế hoạch | Tài liệu canonical đồng bộ; owner chấp thuận ranh giới |
| G1 | Pin OpenCode; health/version/session/SSE/read/search; negative write/command | Probe và contract test đạt; nếu không thì `BLOCKED` và thử Cline |
| G2 | Protocol, bind session, event append-only, cancel/resume/idempotency | Restart không lặp write; event đọc lại được |
| G3 | Worktree, patch nhiều file, command job, snapshot, diff/hunk, conflict | Main workspace không đổi trước duyệt; rollback sạch |
| G4 | Plan → edit → test → repair có ngân sách; verifier độc lập | Fixture Python và TypeScript đạt, không fake PASS |
| G5 | Extension Code-OSS và CLI/headless cùng protocol | Task hằng ngày không cần chỉnh JSON thủ công |
| G6 | Receipt vào `agent_work`, privacy route và learning có duyệt | Reject/revoke không thành bài học; truy ngược digest được |
| G7 | Threat model, secret scan, license/SBOM và clean-machine package | Gói Windows lặp lại được, không lộ secret |
| G8 | Benchmark mù với Cline/OpenCode | Đạt toàn bộ tiêu chí `spec.md` SC-001–SC-006 |

## 7. Thứ tự và ước lượng

- G0–G1: 2–4 ngày.
- G2: 4–6 ngày.
- G3: 5–7 ngày.
- G4: 5–8 ngày.
- G5–G6: 5–8 ngày.
- G7–G8: 4–7 ngày.

Tổng dự kiến 25–40 ngày làm việc nếu G1 đạt. Không bắt đầu G2 khi G1 chưa có bằng chứng.

## 8. Nghiên cứu và hợp đồng

- Quyết định nguồn và phương án thay thế: [research.md](research.md).
- Mô hình dữ liệu tối thiểu: [data-model.md](data-model.md).
- Hợp đồng adapter: [contracts/agent-runtime-protocol.md](contracts/agent-runtime-protocol.md).
- Kịch bản xác minh: [quickstart.md](quickstart.md).
- Danh sách việc thực thi: [tasks.md](tasks.md).

## 9. Hoàn tác

Tắt feature flag và gỡ adapter/extension; giữ nguyên US6 foundation, Case/Evidence và dữ liệu người dùng. Không sửa lịch sử Git của workspace đích. Nếu G1 thất bại, chỉ lưu receipt kỹ thuật và ADR bổ sung cho quyết định fallback; không fork runtime trong cùng cổng.
