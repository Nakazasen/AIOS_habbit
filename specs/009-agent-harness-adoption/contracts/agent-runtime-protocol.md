# Hợp đồng giao tiếp runtime Agent

## 1. Nguyên tắc

- Protocol có version và capability handshake.
- AIOS quyết định quyền; runtime deny mặc định.
- Mọi request ghi/lệnh có `task_id`, `session_id`, `proposal_digest` và `idempotency_key`.
- Event có ID tăng đơn điệu trong phiên và đọc lại được sau reconnect.

## 2. Lệnh tối thiểu

```text
probe_runtime() -> RuntimeCapabilities
create_session(task_pack_digest) -> RuntimeSessionBinding
resume_session(session_id, last_event_id) -> EventStream
read_file(session_id, path, range) -> ReadReceipt
search_workspace(session_id, query) -> SearchReceipt
propose_patch(session_id, changes) -> ActionProposal
propose_command(session_id, command) -> ActionProposal
decide_proposal(proposal_id, payload_digest, actor, decision, expires_at) -> DecisionReceipt
execute_approved(proposal_id, payload_digest) -> EventStream
cancel_session(session_id) -> CancellationReceipt
snapshot(session_id) -> CheckpointReceipt
rollback(session_id, checkpoint_ref) -> RollbackReceipt
get_diff(session_id) -> ImmutableDiff
```

## 3. Capability bắt buộc ở G1

- Health và version.
- Tạo, đọc trạng thái, abort và resume session.
- SSE/event stream có cursor hoặc event ID.
- Read/search file trong root.
- Deny write và deny command có thể kiểm chứng trước khi tool chạy.

Thiếu một capability bắt buộc làm G1 `BLOCKED`; không giả lập PASS ở adapter.

## 4. Lỗi và fail-closed

- Runtime mất kết nối: task chuyển `interrupted`, không tự chạy lại action chưa xác định kết quả.
- Digest/base mismatch hoặc approval hết hạn: từ chối thực thi.
- Path thoát root, symlink thoát root hoặc command ngoài allowlist: từ chối và ghi receipt đã làm sạch.
- Output vượt giới hạn: cắt có đánh dấu, dừng job nếu policy yêu cầu; không đẩy raw output vào Case.

## 5. Ranh giới dữ liệu

Runtime chỉ nhận file trong workspace được tin cậy và context đã qua policy. Secret, thông tin xác thực và `local_only` không được gửi ra provider không được phép. Extension chỉ nhận dữ liệu hiển thị đã làm sạch từ Gateway.
