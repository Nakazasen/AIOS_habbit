# Mô hình dữ liệu tối thiểu

Không tạo cơ sở dữ liệu mới. Các record dưới đây mở rộng hợp đồng US6 và lưu siêu dữ liệu trong `workspace_cases.sqlite`; session chi tiết thuộc runtime cục bộ.

## AgentTaskPack

- `task_id`, `case_id`, `protocol_version`.
- `workspace_root_digest`, `base_commit`, `allowed_paths`, `allowed_commands`.
- `step_budget`, `time_budget_seconds`, `output_budget_bytes`.
- `privacy_label`, `acceptance_checks`, `created_by`, `created_at`.

Task Pack bất biến sau khi duyệt. Thay đổi phạm vi tạo phiên bản/digest mới.

## RuntimeSessionBinding

- `task_id`, `runtime_kind`, `runtime_version`, `runtime_session_id`.
- `status`, `last_event_id`, `created_at`, `updated_at`.

Trạng thái: `created → planning → awaiting_plan_approval → executing → awaiting_apply_approval → verifying → completed`; nhánh lỗi gồm `rejected`, `failed`, `cancelled`, `interrupted → resumable`.

## ActionProposal

- `proposal_id`, `task_id`, `proposal_kind` (`patch` hoặc `command`).
- `payload_digest`, `base_commit`, `file_digests`, `policy_version`.
- `actor_id`, `scope`, `decision`, `expires_at`, `decided_at`.

Approval chỉ hợp lệ với đúng payload, base, actor, scope và thời hạn.

## ExecutionReceipt

- `receipt_id`, `task_id`, `runtime_session_id`, `event_ids`.
- `before_digest`, `after_digest`, `command_digest`, `exit_code`.
- `observed_test_digest`, `checkpoint_ref`, `result_status`, `created_at`.

Receipt append-only. `result_status=PASS` chỉ khi verifier quan sát được lệnh và trạng thái workspace tương ứng.

## Quan hệ

Một `AgentTaskPack` có một binding hoạt động, nhiều proposal và nhiều receipt. `AgentWorkRecord` trong Case chỉ trỏ các ID/digest này; không sao chép transcript hoặc output thô.
