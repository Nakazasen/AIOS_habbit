# Hợp đồng giao tiếp runtime Agent

## 1. Phạm vi và vai trò

Hợp đồng này là biên duy nhất giữa client, Gateway AIOS và runtime kế thừa. Code-OSS, CLI/headless và Workspace Chat không gọi runtime trực tiếp.

- AIOS quyết định Task Pack, policy, approval, worktree, idempotency, verifier, receipt, apply và rollback.
- Runtime thực hiện session, vòng model–tool, event stream và cancel/resume trong worktree đã cấp.
- Runtime permission là lớp chặn bổ sung, không thay quyền AIOS.
- Bridge NVIDIA hiện hữu không đáp ứng contract này và không được nối tắt vào đường G1–G4.

## 2. Version và capability handshake

Mỗi request có `protocol_version`; mỗi adapter khai `adapter_version`, `runtime_kind`, `runtime_version`, `runtime_checksum` và `capability_digest`.

### Capability bắt buộc ở G1

- health/version và xác thực loopback.
- tạo session, đọc trạng thái, abort và attach/resume bằng ID ổn định.
- event stream có upstream ID hoặc cursor đủ để adapter phát hiện duplicate/gap.
- read/search file chỉ trong worktree root.
- deny write và deny command trước tool execution.
- lấy diff/session state để đối chiếu sau reconnect.

Thiếu một capability làm G1 `BLOCKED`. Adapter không giả lập capability để báo đạt. Toàn bộ G2 trở đi bị khóa cho đến khi G1 có receipt.

## 3. Envelope chung

### Request

```json
{
  "protocol_version": "aios_agent_runtime_v1",
  "request_id": "REQ-...",
  "task_id": "TASK-...",
  "session_id": "SESSION-...",
  "action": "read_file",
  "payload_digest": "sha256:...",
  "idempotency_key": "IDEMP-...",
  "sent_at": "2026-09-10T00:00:00Z"
}
```

### Event

```json
{
  "protocol_version": "aios_agent_runtime_v1",
  "event_id": "EVT-...",
  "task_id": "TASK-...",
  "session_id": "SESSION-...",
  "aios_sequence": 12,
  "upstream_event_id": "runtime-event-id",
  "event_kind": "tool_finished",
  "action_id": "ACT-...",
  "safe_payload": {},
  "payload_digest": "sha256:...",
  "previous_event_digest": "sha256:...",
  "observed_at": "2026-09-10T00:00:01Z"
}
```

`safe_payload` phải qua redaction trước khi persistence/UI. Tool result, environment và lỗi upstream không được chuyển thẳng. Adapter không được truyền toàn bộ `os.environ`; chỉ tạo allowlist biến môi trường tối thiểu và loại secret trước khi khởi động runtime.

## 4. Thao tác tối thiểu

```text
probe_runtime() -> RuntimeCapabilities
create_session(task_pack_digest, worktree_ref) -> RuntimeSessionBinding
get_session(session_id) -> RuntimeSessionState
resume_session(session_id, runtime_cursor, last_aios_sequence) -> EventStream
read_file(session_id, relative_path, range) -> ReadReceipt
search_workspace(session_id, query) -> SearchReceipt
start_agent_run(session_id, objective_digest) -> EventStream
propose_patch(session_id) -> ActionProposalRef
propose_command(session_id, command_spec_digest) -> ActionProposalRef
record_decision(proposal_id, proposal_digest, selection_digest, decision_ref) -> DecisionReceipt
execute_approved(decision_ref, idempotency_key) -> EventStream
cancel_session(session_id, reason_code) -> CancellationReceipt
snapshot(session_id) -> CheckpointReceipt
get_diff(session_id) -> ImmutableDiffRef
get_process_state(session_id) -> ProcessObservation
close_session(session_id) -> CloseReceipt
```

Runtime không có thao tác apply trực tiếp vào main workspace. `rollback` main workspace và apply thuộc orchestrator AIOS.

## 5. Tiền điều kiện ghi và chạy lệnh

Mọi patch/command phải khớp đồng thời:

1. Task Pack và capability digest còn hiệu lực.
2. Session bind đúng worktree và base snapshot.
3. Proposal digest/policy version/scope digest còn khớp.
4. Decision do app context cấp, đúng actor và chưa hết hạn.
5. `selection_digest` khớp đúng tập hunk hoặc command spec.
6. Idempotency key chưa được dùng với payload khác.

Sai một điều kiện phải từ chối trước thực thi, ghi receipt đã làm sạch và sinh báo cáo lỗi theo [agent-error-report-v1.md](agent-error-report-v1.md).

## 6. Patch nhiều file và partial hunk

- Adapter chỉ trả diff/session state; AIOS tự đọc worktree và tính manifest/hunk digest.
- Hunk ID được tính tất định từ relative path, range và nội dung canonical.
- Decision chứa danh sách hunk được chọn và selection digest; proposal gốc không đổi.
- AIOS tạo verification worktree sạch, áp đúng selection và chạy required checks.
- Test của full diff không chứng minh partial diff.
- Rename/delete/create phải kiểm before/after digest; symlink target phải nằm trong root.

## 7. Command job

- Command được biểu diễn bằng argv/cwd logical/env allowlist/timeout/output budget canonical; không dùng raw shell string làm khóa quyền.
- Command chỉ chạy trong task/verification worktree.
- Adapter không kế thừa toàn bộ environment của host; credential và biến chưa allowlist bị loại.
- Stdout/stderr thô không đi vào event/UI/Case. Adapter ghi spool local nếu policy cho phép và chỉ trả digest, byte count, truncation state cùng safe summary.
- Cancel phải dừng cả process tree. Không xác minh được thì trạng thái là `cancelled_with_residue`, không phải `completed`.

## 8. Event ordering, resume và idempotency

- AIOS gán `aios_sequence` tăng đơn điệu và `previous_event_digest` trước persistence.
- Duplicate upstream event cùng digest được bỏ qua; cùng ID khác digest là lỗi integrity.
- Gap event làm session `interrupted_unknown` cho đến khi đối chiếu runtime/session/worktree.
- Write/command không tự replay sau reconnect.
- Cùng idempotency key/cùng payload trả receipt cũ; cùng key/khác payload bị từ chối.
- Resume không làm sống lại approval hết hạn hoặc proposal mismatch.

## 9. Observed verification

Runtime có thể gửi kết quả tự khai nhưng không tạo `VERIFIED_PASS`. Verifier AIOS phải:

1. dựng worktree sạch từ base;
2. áp đúng selection digest;
3. lấy command từ Task Pack/decision;
4. quan sát exit code, timeout, process residue và Git state;
5. so changed paths/digest với proposal;
6. tạo `VerificationRun` và `ExecutionReceipt` append-only.

UI không được tự tạo observed evidence, không được dùng checkbox để đặt `tests_passed=True` hoặc `worktree_clean=True`, và không được copy changed files từ model report làm quan sát.

## 10. Apply và rollback

- Trước apply, AIOS so snapshot main workspace hiện tại với snapshot đã bind approval.
- Mismatch HEAD/status/file digest hoặc approval hết hạn làm apply bị từ chối.
- Apply dùng đúng payload đã verified; lỗi giữa chừng phục hồi snapshot trước apply và xác minh lại digest.
- Không gọi `git reset --hard`, không rewrite history và không xóa thay đổi đã có của người dùng.
- Xóa task worktree chỉ sau close/cancel/rollback receipt và không còn trạng thái `interrupted_unknown`.

## 11. Lỗi và ánh xạ fail-closed

| Điều kiện | Trạng thái | Reason code gợi ý |
|---|---|---|
| Runtime mất kết nối khi chưa biết action đã chạy | `interrupted_unknown` | `RUNTIME_CONNECTION_LOST` |
| Base/file/proposal digest lệch | `failed` | `BASELINE_CHANGED` hoặc `PROPOSAL_MISMATCH` |
| Approval hết hạn/replay | `failed` | `APPROVAL_EXPIRED` hoặc `APPROVAL_REPLAYED` |
| Path/symlink thoát root | `failed` | `PATH_OUTSIDE_WORKTREE` |
| Command ngoài allowlist | `failed` | `COMMAND_NOT_ALLOWED` |
| Test exit code khác 0 | `failed` | `VERIFICATION_FAILED` |
| Cancel còn process/file residue | `cancelled_with_residue` | `CANCEL_RESIDUE_DETECTED` |
| Output vượt budget | `failed` hoặc `cancelled` theo policy | `OUTPUT_BUDGET_EXCEEDED` |

Mỗi điều kiện tạo receipt và error report tiếng Việt; không hiện raw exception hoặc traceback.

## 12. Ranh giới dữ liệu và transport

- Server chỉ bind `127.0.0.1`, mDNS tắt, CORS không mở nếu không có nhu cầu được duyệt và có xác thực cục bộ.
- Runtime chỉ nhận worktree cùng context đã qua policy; không nhận `local_cases/`, `local_runs/` ngoài vùng task, `.env`, secret hoặc dữ liệu `local_only` khi provider route không cho phép.
- Extension chỉ nhận state, diff và error payload đã làm sạch từ Gateway.
- Event/receipt persistence không chứa absolute path, raw prompt/transcript, raw output hoặc provider credential.

## 13. Tương thích

- `aios_agent_task_pack_v1` và `aios_agent_report_v1` tiếp tục được reader lịch sử chấp nhận theo semantics cũ.
- Protocol runtime mới dùng version riêng; adapter phải từ chối version/capability không hỗ trợ.
- Report v1 nhập thủ công không tự biến thành VerificationRun. Muốn đạt verified phải có verifier receipt mới liên kết đúng task/proposal/decision.
- Pending action từ bridge RAM cũ hết hiệu lực khi restart và không được migration thành approval.
