# Mô hình dữ liệu và vòng đời

## 1. Nguyên tắc

- Mở rộng record `agent_work` và schema hiện có; không tạo database phiên mới.
- Hồ sơ chỉ lưu metadata, nguồn, digest, kết quả kiểm tra và locator cục bộ đã làm sạch.
- Transcript, stdout/stderr thô, `diff` đầy đủ và file nhạy cảm không đi vào hồ sơ Case.
- Bản ghi trạng thái và receipt là append-only; sửa nội dung tạo phiên bản mới.
- Cấu trúc chỉ phục vụ ba loại việc của MVP: `error_report`, `process_design_review`, `code_change`.

## 2. `AgentWorkItem`

Một việc trong hàng đợi.

### Trường

- `work_id`, `case_id` tùy chọn, `workspace_id`, `work_type`.
- `goal_vi`, `source_refs`, `allowed_roots`, `allowed_commands`.
- `privacy_route`, `status`, `queue_position`, `created_at`, `updated_at`.
- `runtime_binding_ref`, `checkpoint_ref`, `result_ref`, `error_report_ref`.
- `idempotency_key`, `record_digest`.

### Trạng thái

```text
queued → running → needs_input | verifying
verifying → completed | verification_failed
queued | running | needs_input → cancelling → cancelled
completed | verification_failed → rolled_back
running → interrupted_unknown → running | needs_input | cancelled
```

### Quy tắc

- Chỉ một item trạng thái `running` có quyền ghi trên cùng `workspace_id`.
- `completed` chỉ được đặt sau verifier của đúng `work_type`.
- `interrupted_unknown` không tự chạy lại thao tác ghi trước khi đối chiếu runtime, filesystem và checkpoint.
- Thứ tự hàng đợi có thể đổi, nhưng lịch sử chuyển trạng thái không bị ghi đè.

## 3. `AgentScopeGrant`

Phạm vi tự động duyệt cho một nhiệm vụ.

### Trường

- `work_id`, `root_paths`, `source_refs`, `allowed_actions`, `denied_actions`.
- `allowed_commands`, `privacy_route`, `expires_at`, `policy_version`, `scope_digest`.

### Quy tắc

- `read`, `search`, `create`, `edit` và `test` chỉ được tự động duyệt khi target nằm trong root và action có trong allowlist.
- Secret, path ngoài root, quyền admin, commit, push, merge và deploy luôn bị từ chối ở MVP.
- Prompt hoặc nội dung tài liệu không thể mở rộng grant.

## 4. `RuntimeSessionBinding`

Ánh xạ việc AIOS với phiên OpenCode.

### Trường

- `work_id`, `runtime_kind`, `runtime_version`, `runtime_session_id`.
- `scope_digest`, `workspace_checkpoint_digest`, `last_event_cursor`, `status`.

### Quy tắc

- Binding chỉ hợp lệ khi version và capability digest khớp bản đã probe.
- Resume phải đối chiếu session, scope và checkpoint.
- Binding của bridge NVIDIA cũ không được đổi thành binding OpenCode hợp lệ.

## 5. `WorkCheckpoint`

Điểm hoàn tác trước và sau nhiệm vụ.

### Trường

- `checkpoint_id`, `work_id`, `kind` (`git_worktree` hoặc `draft_snapshot`).
- `base_ref`, `before_manifest_digest`, `after_manifest_digest`.
- `local_locator`, `created_at`, `rollback_status`.

### Quy tắc

- Task mã dùng worktree; task artifact dùng snapshot thư mục bản nháp.
- Locator là cục bộ và không hiển thị đường dẫn tuyệt đối trên UI thường.
- Rollback không xóa hoặc ghi đè thay đổi có trước checkpoint.

## 6. `WorkArtifactDraft`

Bản nháp đầu ra của nhiệm vụ.

### Trường

- `artifact_id`, `work_id`, `artifact_type`, `title_vi`, `version`.
- `content_locator`, `source_claim_refs`, `visual_refs`, `status`.
- `created_at`, `artifact_digest`.

### Trạng thái

```text
draft → verified_draft → used
draft | verified_draft | used → rolled_back
```

`verified_draft` chỉ có nghĩa đã qua kiểm tra kỹ thuật của Goal 009; không có nghĩa báo cáo hay thiết kế công đoạn đã được ban hành chính thức.

## 7. `GroundedFinding`

Một phát hiện trong báo cáo hoặc rà soát công đoạn.

### Trường

- `finding_id`, `artifact_id`, `finding_type`.
- `statement_vi`, `source_refs`, `source_locations`.
- `evidence_status` (`supported`, `conflicting`, `insufficient`, `proposal`).
- `impact_vi`, `recommendation_vi`, `confidence`, `finding_digest`.

### Quy tắc

- `supported` phải có ít nhất một source location đọc lại được.
- `conflicting` giữ tất cả nguồn mâu thuẫn; không tự chọn một nguồn đúng.
- `proposal` không được trình bày như quy định hiện hành.
- Phát hiện ảnh hưởng an toàn/chất lượng phải tạo câu hỏi cần chuyên gia xác nhận.

## 8. `VisualArtifact`

Bảng, biểu đồ hoặc sơ đồ kèm provenance.

### Trường

- `visual_id`, `artifact_id`, `visual_type`, `title_vi`.
- `source_refs`, `source_columns`, `units`, `filters`, `aggregation`.
- `data_digest`, `rendered_locator`, `warning_vi` tùy chọn.

### Quy tắc

- Không có `source_refs` và `data_digest` thì không được render như biểu đồ có bằng chứng.
- Phép tổng hợp phải xác định và tái hiện được.
- Thiếu số liệu hoặc đơn vị thì tạo bảng/mô tả và cảnh báo thay vì biểu đồ.

## 9. `VerificationResult`

### Trường

- `verification_id`, `work_id`, `verifier_kind`, `status`.
- `checks`, `observed_facts`, `started_at`, `finished_at`, `result_digest`.

### Quy tắc theo loại việc

- `error_report`: section bắt buộc, nguồn cho claim, provenance cho bảng/biểu đồ.
- `process_design_review`: phát hiện có nguồn hoặc nhãn rõ; artifact vẫn là bản nháp.
- `code_change`: lệnh test, exit code, timeout, Git status và manifest file được hệ thống quan sát.
- Model report hoặc checkbox UI không tạo observed fact.

## 10. `WorkResultSummary`

Payload dành cho thẻ kết quả không chuyên.

### Trường

- `work_id`, `status_vi`, `what_changed_vi`, `evidence_summary_vi`.
- `verification_summary_vi`, `remaining_risks_vi`, `next_actions_vi`.
- `affected_file_names`, `artifact_ref`, `can_use`, `can_rollback`.
- `technical_detail_ref` tùy chọn.

### Quy tắc

- Không có traceback, secret, đường dẫn tuyệt đối, stdout thô hoặc nội dung `local_only`.
- `technical_detail_ref` đóng mặc định và không phải điều kiện để dùng kết quả.
- Mọi nhãn và câu giải thích cho người dùng là tiếng Việt.

## 11. Quan hệ

```text
AgentWorkItem 1 ── 1 AgentScopeGrant
AgentWorkItem 1 ── 0..1 RuntimeSessionBinding
AgentWorkItem 1 ── 1..n WorkCheckpoint
AgentWorkItem 1 ── 0..n WorkArtifactDraft
WorkArtifactDraft 1 ── 0..n GroundedFinding
WorkArtifactDraft 1 ── 0..n VisualArtifact
AgentWorkItem 1 ── 0..n VerificationResult
AgentWorkItem 1 ── 0..1 WorkResultSummary
```

## 12. Lưu trữ và dọn dẹp

- Metadata đã làm sạch theo retention của Case hiện có.
- Payload thô và worktree nằm trong vùng cục bộ theo task, có locator và digest.
- Chỉ dọn worktree khi task đã đóng/rollback và không ở `interrupted_unknown`.
- Dọn dẹp thất bại tạo báo cáo lỗi; không được báo hoàn tác sạch.
