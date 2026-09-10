# Mô hình dữ liệu và vòng đời

## 1. Nguyên tắc lưu trữ

Không tạo cơ sở dữ liệu mới. `workspace_cases.sqlite` chỉ lưu metadata, digest, state và receipt đã làm sạch. Session chi tiết do runtime cục bộ giữ. Diff đầy đủ, transcript và stdout/stderr thô nằm trong vùng task `local_only` có retention hoặc bị xóa; hồ sơ Case chỉ giữ locator tương đối an toàn và digest khi cần truy vết.

Mọi record lịch sử quyền, action, verification và lỗi là append-only. Sửa một payload tạo version/ID mới; không cập nhật ngược artifact đã được duyệt.

## 2. `AgentTaskPack`

### Trường

- Định danh: `task_id`, `case_id`, `schema_version`, `protocol_version`, `task_pack_digest`.
- Workspace: `repo_logical_id`, `base_commit`, `workspace_status_digest`, `allowed_path_digests`.
- Phạm vi: `allowed_paths`, `forbidden_paths`, `allowed_tools`, `allowed_commands`, `required_checks`.
- Runtime: `required_capabilities`, `runtime_kind`, `minimum_adapter_version`.
- Ngân sách: `step_budget`, `time_budget_seconds`, `command_timeout_seconds`, `output_budget_bytes`.
- Privacy: `privacy_label`, `provider_route`, `retention_policy`, `consent_ref`.
- Trách nhiệm: `created_by`, `created_at`, `expires_at`.

### Quy tắc

- Task Pack bất biến sau khi được phát hành. Thay phạm vi, base, budget hoặc privacy tạo digest mới.
- `allowed_paths` là đường dẫn tương đối đã chuẩn hóa, không traversal, không symlink thoát root.
- Command thực thi phải khớp entry đã canonicalize; không chấp nhận so tiền tố chuỗi mơ hồ.
- Reader cũ vẫn đọc được `aios_agent_task_pack_v1`; đường runtime mới không âm thầm diễn giải field v1 theo nghĩa mới.

## 3. `WorkspaceSnapshot`

### Trường

- `snapshot_id`, `task_id`, `repo_logical_id`.
- `head_commit`, `status_digest`, `tracked_file_digests`, `untracked_manifest_digest`.
- `created_at`, `snapshot_kind` (`task_base`, `before_apply`, `after_apply`, `rollback_check`).

### Quy tắc

- Snapshot không chứa nội dung file trong SQLite.
- Task ghi chỉ được mở khi snapshot workspace đích đạt điều kiện sạch đã khóa.
- Apply yêu cầu HEAD, status digest và digest file đích khớp snapshot được approval bind.

## 4. `RuntimeSessionBinding`

### Trường

- `task_id`, `runtime_kind`, `runtime_version`, `adapter_version`.
- `runtime_session_id`, `capability_digest`, `worktree_id`.
- `status`, `last_aios_sequence`, `runtime_cursor`, `last_checkpoint_ref`.
- `created_at`, `updated_at`, `interruption_reason_code`.

### Trạng thái

```text
created → probing → planning → awaiting_plan_approval → executing
executing → awaiting_apply_approval → verifying → applying → completed
executing/verifying/applying → cancelling → cancelled
executing/verifying/applying → interrupted_unknown → resumable → executing
mọi trạng thái hoạt động → failed
awaiting_apply_approval → rejected | expired
```

### Quy tắc

- Mỗi Task Pack chỉ có một binding ghi hoạt động.
- `resumable` chỉ được gán sau khi đối chiếu session, process, worktree và receipt.
- Approval hết hạn không sống lại khi resume.

## 5. `AgentExecutionEvent`

### Trường

- `event_id`, `task_id`, `runtime_session_id`, `aios_sequence`.
- `upstream_event_id`, `event_kind`, `action_id`, `idempotency_key`.
- `safe_payload`, `payload_digest`, `previous_event_digest`.
- `observed_at`, `source` (`aios`, `runtime`, `verifier`, `git`).

### Quy tắc

- Append-only; `aios_sequence` tăng đơn điệu trong task.
- Duplicate upstream event với cùng digest không tạo action mới.
- Cùng idempotency key nhưng khác payload digest bị từ chối.
- `safe_payload` không chứa transcript, raw output, secret hoặc absolute path.

## 6. `ActionProposal`

### Trường

- `proposal_id`, `task_id`, `runtime_session_id`, `proposal_version`.
- `proposal_kind` (`patch`, `command`).
- `base_snapshot_id`, `payload_digest`, `policy_version`, `scope_digest`.
- `file_changes`: đường dẫn tương đối, loại thay đổi, before/after digest và danh sách hunk.
- `command_spec`: argv canonical, cwd logical, timeout và output budget; chỉ có với command.
- `risk_summary`, `payload_locator`, `created_by`, `created_at`, `expires_at`.

### `ProposalHunk`

- `hunk_id`, `relative_path`, `before_range`, `after_range`, `hunk_digest`.
- Không lưu raw hunk vào Case; UI lấy payload từ vùng task cục bộ rồi xác minh digest.

### Quy tắc

- Proposal bất biến. Payload đổi tạo proposal mới.
- Proposal không tự mang trạng thái approved; quyết định nằm ở record riêng.
- Rename/delete/create phải có before/after state rõ; symlink luôn được kiểm tra containment.

## 7. `ProposalDecision`

### Trường

- `decision_id`, `proposal_id`, `proposal_digest`, `task_id`, `runtime_session_id`.
- `decision` (`approved`, `rejected`, `cancelled`).
- `selected_hunk_ids`, `selection_digest`.
- `actor_id`, `scope_digest`, `policy_version`, `decided_at`, `expires_at`.
- `reason_summary`.

### Quy tắc

- Append-only; decision mới không sửa decision cũ.
- Approval hợp lệ khi task/session/proposal/actor/scope/policy/expiry cùng khớp.
- Với patch, `selection_digest` bind tập hunk có thứ tự chuẩn. Với command, bind toàn bộ command spec.
- Reuse decision sau expiry, base mismatch hoặc payload mismatch bị từ chối và tạo receipt.

## 8. `VerificationRun`

### Trường

- `verification_id`, `task_id`, `decision_id`, `selection_digest`.
- `verification_worktree_id`, `command_specs`, `started_at`, `finished_at`.
- `command_observations`: command digest, exit code, timeout/cancel state, output digest.
- `workspace_observation`: HEAD, status digest, changed path digest, forbidden path findings.
- `result` (`passed`, `failed`, `cancelled`, `interrupted_unknown`).
- `verifier_name`, `verifier_version`, `receipt_id`.

### Quy tắc

- Command lấy từ Task Pack/decision, không lấy từ model report.
- `passed` đòi mọi required check exit code 0, không timeout, không forbidden path và diff đúng selection.
- Output thô không vào SQLite; chỉ lưu digest, số byte, trạng thái truncation và locator local nếu retention cho phép.
- Partial hunk bắt buộc có VerificationRun riêng.

## 9. `ExecutionReceipt`

### Trường

- `receipt_id`, `task_id`, `runtime_session_id`, `action_id`, `idempotency_key`.
- `event_range`, `before_snapshot_id`, `after_snapshot_id`.
- `proposal_id`, `decision_id`, `verification_id`.
- `result_status`, `reason_codes`, `safe_summary`, `created_at`.
- `payload_digest`, `receipt_digest`, `previous_receipt_digest`.

### Quy tắc

- Append-only và có chuỗi digest.
- Không ghi `VERIFIED_PASS` nếu thiếu VerificationRun observed hoặc snapshot sau apply.
- Receipt runtime/model không thể tự nâng thành receipt verifier.

## 10. `AgentErrorReport`

Chi tiết trường và ví dụ nằm tại [contracts/agent-error-report-v1.md](contracts/agent-error-report-v1.md).

### Trường lõi

- `report_id`, `schema_version`, `task_id`, `session_id`, `status`, `failed_step`.
- `reason_code`, `message_vi`, `impact_vi`, `next_actions_vi`.
- `observed_facts`, `receipt_refs`, `can_resume`, `rollback_state`.
- `redaction_summary`, `created_at`, `report_digest`.

### Quy tắc

- `message_vi`, `impact_vi` và `next_actions_vi` là tiếng Việt dễ hiểu.
- Không chứa raw exception, traceback, absolute path, secret, prompt, transcript hoặc raw stdout/stderr.
- `status=failed` hoặc `interrupted` không được map thành success dù model report nói PASS.

## 11. `AgentWorkRecord`

### Trường

- `case_id`, `task_id`, `task_pack_digest`, `session_binding_ref`.
- `proposal_refs`, `decision_refs`, `verification_refs`, `receipt_refs`, `error_report_refs`.
- `current_status`, `created_at`, `updated_at`.

### Quy tắc

- Chỉ lưu liên kết và summary đã làm sạch; không sao chép payload raw.
- Kết quả rejected, failed, cancelled hoặc chưa verified không tạo lesson đã duyệt.
- Lesson candidate chỉ được tạo sau approval, observed verification và apply receipt khớp nhau.

## 12. Quan hệ

```text
AgentTaskPack 1 ── 1 WorkspaceSnapshot(task_base)
AgentTaskPack 1 ── 0..1 RuntimeSessionBinding hoạt động
RuntimeSessionBinding 1 ── N AgentExecutionEvent
RuntimeSessionBinding 1 ── N ActionProposal
ActionProposal 1 ── N ProposalDecision
ProposalDecision 1 ── 0..N VerificationRun
Action/Verification/Apply 1 ── N ExecutionReceipt
Task 1 ── N AgentErrorReport
AgentWorkRecord 1 ── N tham chiếu digest/receipt
```

## 13. Retention và cleanup

- Worktree task, raw output và runtime transcript có retention theo Task Pack; xóa idempotent sau khi không còn action/resume hợp lệ.
- Metadata/digest/receipt Case được giữ theo chính sách hồ sơ.
- Cleanup thất bại sinh error report và trạng thái `cancelled_with_residue`; không được nói rollback sạch.
- Không xóa worktree khi action còn `interrupted_unknown` trước khi owner quyết định điều tra hoặc hủy.
