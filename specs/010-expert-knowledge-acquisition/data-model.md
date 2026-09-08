# Mô hình dữ liệu: Vòng phỏng vấn và xuất bản tri thức

## 1. Nguyên tắc

- Workflow, nội dung thô và tri thức xuất bản là ba lớp khác nhau.
- Mọi thực thể thay đổi trạng thái bằng sự kiện append-only; projection có thể dựng lại.
- Actor lấy từ `IdentityProvider`; trường hiển thị không tạo quyền.
- Nội dung AI tạo mặc định là `candidate`.
- Audio/transcript chỉ tham chiếu bằng locator cục bộ + digest trong workflow DB.

## 2. Quan hệ

```text
VerifiedPrincipal 1─1 ExpertProfile 1─* ScopeGrant
KnowledgeCoverageMap 1─* KnowledgeGapCandidate
KnowledgeGapCandidate *─* InterviewPlan
InterviewPlan 1─* InterviewSession 1─* InterviewTurn
InterviewSession 1─* TranscriptSegment
InterviewTurn/TranscriptSegment *─* KnowledgeClaim
KnowledgeClaim *─* KnowledgeArtifactCandidate
KnowledgeArtifactCandidate 1─* ApprovalDecision
KnowledgeArtifactCandidate 1─* PublicationPackage 1─1 PublicationReceipt
```

## 3. Thực thể và trường tối thiểu

### 3.1 VerifiedPrincipal

| Trường | Ý nghĩa |
|---|---|
| `provider_id` | Adapter identity có version |
| `subject_id` | ID ổn định từ provider, không phải tên tự khai |
| `display_name` | Chỉ để hiển thị |
| `assurance_level` | Mức đảm bảo xác thực |
| `authenticated_at` | Thời điểm xác thực |
| `session_digest` | Liên kết phiên đã làm sạch |

Không lưu password/token dài hạn trong kho feature.

### 3.2 ExpertProfile

| Trường | Ý nghĩa |
|---|---|
| `expert_id` | ID nội bộ bất biến |
| `subject_id` | Liên kết principal xác thực |
| `competency_scopes` | Các công đoạn/năng lực đã xác nhận |
| `status` | `active`, `suspended`, `revoked` |
| `valid_from`, `valid_until` | Thời hạn hiệu lực |
| `evidence_refs` | Bằng chứng cấp hồ sơ |

### 3.3 ScopeGrant

| Trường | Ý nghĩa |
|---|---|
| `grant_id` | ID append-only |
| `expert_id` | Người nhận quyền |
| `action` | `interview.answer`, `claim.confirm`, `artifact.approve`, `publication.publish`, `publication.revoke` |
| `scope_type`, `scope_id` | Miền/công đoạn/collection |
| `granted_by`, `reason` | Người cấp và lý do |
| `valid_from`, `valid_until`, `revoked_at` | Vòng đời |

### 3.4 KnowledgeCoverageMap

| Trường | Ý nghĩa |
|---|---|
| `coverage_id`, `version` | Bản đồ bất biến theo phiên bản |
| `collection_id` | Thư viện được đánh giá |
| `scope` | Công đoạn/thiết bị/lỗi |
| `source_inventory_digest` | Digest inventory đầu vào |
| `question_set_digest` | Digest bộ câu hỏi kiểm tra |
| `coverage_metrics` | Số câu đủ/thiếu/xung đột/lỗi thời |
| `created_by`, `created_at` | Audit |

### 3.5 KnowledgeGapCandidate

| Trường | Ý nghĩa |
|---|---|
| `gap_id` | ID ổn định |
| `coverage_id` | Bản đồ sinh gap |
| `gap_type` | `missing`, `ambiguous`, `conflicted`, `stale`, `uncited` |
| `question`, `scope` | Điều cần làm rõ |
| `evidence_refs` | Query/source/case chứng minh |
| `priority`, `confidence` | Xếp hạng, không phải truth |
| `status` | `candidate`, `accepted`, `merged`, `deferred`, `rejected`, `resolved` |
| `decision_actor`, `decision_reason` | Quyết định của người có quyền |

### 3.6 InterviewPlan

| Trường | Ý nghĩa |
|---|---|
| `plan_id`, `version` | Phiên bản kế hoạch |
| `gap_ids` | Khoảng trống được giao |
| `required_scope` | Năng lực tối thiểu |
| `eligible_expert_ids` | Danh sách từ quyền, không do model tự phong |
| `seed_questions` | Câu hỏi nền |
| `max_turns`, `max_minutes`, `token_budget` | Ngân sách |
| `completion_rubric` | Điều kiện đủ/dừng/escalate |
| `status` | `draft`, `approved`, `scheduled`, `closed`, `cancelled` |

### 3.7 InterviewSession

| Trường | Ý nghĩa |
|---|---|
| `session_id` | ID resume |
| `plan_id`, `expert_id`, `principal_subject_id` | Bind kế hoạch/người |
| `state` | `ready`, `active`, `paused`, `awaiting_confirmation`, `completed`, `stopped`, `blocked` |
| `consent_state` | `not_requested`, `declined`, `granted`, `withdrawn` |
| `checkpoint_seq`, `last_turn_digest` | Resume/idempotency |
| `started_at`, `updated_at`, `ended_at` | Thời gian |
| `stop_reason` | Lý do kết thúc |

### 3.8 InterviewTurn

| Trường | Ý nghĩa |
|---|---|
| `turn_id`, `sequence` | Thứ tự bất biến |
| `question_text`, `answer_text` | Văn bản UTF-8 |
| `question_reason` | Lý do follow-up được phép |
| `trigger_refs` | Gap/turn/claim gây ra câu hỏi |
| `answer_confidence` | Tự đánh giá của chuyên gia |
| `answer_state` | `answered`, `unknown`, `uncertain`, `skipped`, `corrected` |
| `payload_digest`, `created_at` | Chống ghi lặp/audit |

### 3.9 TranscriptSegment

| Trường | Ý nghĩa |
|---|---|
| `segment_id`, `session_id` | Liên kết phiên |
| `start_ms`, `end_ms` | Mốc thời gian |
| `machine_text`, `corrected_text` | Bản máy và bản sửa |
| `critical_tokens` | Mã máy/số/đơn vị cần xác nhận |
| `confirmation_state`, `confirmed_by` | Trạng thái duyệt |
| `audio_locator`, `audio_digest` | Chỉ trỏ local-only |
| `engine_receipt` | Engine/model/version/config digest |

### 3.10 KnowledgeClaim

| Trường | Ý nghĩa |
|---|---|
| `claim_id`, `version` | Phát biểu nguyên tử |
| `statement` | Nội dung chuẩn hóa |
| `scope`, `validity_conditions` | Điều kiện áp dụng |
| `source_refs` | Turn/segment/document/case |
| `confidence`, `uncertainty_note` | Độ chắc chắn có giải thích |
| `status` | `candidate`, `confirmed`, `conflicted`, `rejected`, `superseded` |
| `confirmed_by`, `confirmed_at` | Người xác nhận |

### 3.11 KnowledgeArtifactCandidate

| Trường | Ý nghĩa |
|---|---|
| `artifact_id`, `artifact_type`, `version` | `sop` hoặc `lesson` |
| `title`, `content_locator`, `content_digest` | Artifact versioned |
| `claim_ids` | Nguồn claim |
| `diff_from_version` | Bản so sánh |
| `status` | `candidate`, `in_review`, `approved`, `rejected`, `revoked`, `superseded` |
| `required_approvals` | Ma trận vai trò/scope |

### 3.12 ApprovalDecision

| Trường | Ý nghĩa |
|---|---|
| `decision_id` | ID append-only |
| `subject_type`, `subject_id`, `subject_digest` | Nội dung được duyệt chính xác |
| `actor_id`, `scope_snapshot` | Người duyệt và quyền lúc duyệt |
| `decision` | `approve`, `reject`, `request_change`, `revoke` |
| `rationale`, `created_at` | Lý do/thời điểm |

### 3.13 PublicationPackage và PublicationReceipt

| Trường | Ý nghĩa |
|---|---|
| `package_id`, `artifact_id`, `artifact_digest` | Payload bất biến |
| `collection_id`, `source_name`, `source_digest` | Đích ingest |
| `approval_decision_ids` | Bằng chứng quyền |
| `acceptance_question_set` | Câu hỏi sau ingest |
| `status` | `sealed`, `publishing`, `published`, `failed`, `revoked`, `superseded` |
| `backup_id`, `index_digest_before/after` | Receipt an toàn |
| `retrieval_receipts`, `rollback_receipt` | Bằng chứng dùng/hoàn tác |

## 4. Chuyển trạng thái chính

```text
Gap: candidate -> accepted -> resolved
                 \-> deferred/rejected/merged

Session: ready -> active -> paused -> active -> awaiting_confirmation -> completed
                           \-> stopped/blocked

Claim: candidate -> confirmed -> superseded
                  \-> conflicted/rejected

Artifact: candidate -> in_review -> approved -> published -> superseded/revoked
                      \-> rejected/request_change
```

Mọi transition phải kiểm tra state hiện tại, exact digest, actor/scope và idempotency key. Transition không hợp lệ bị từ chối, không tự sửa projection.

## 5. Lưu giữ và xóa

Mặc định kỹ thuật là không tự xóa audio/bản chép lời và chỉ lưu ở vùng `local_only`; người có quyền có thể xóa thủ công theo consent. Thu hồi tri thức khỏi retrieval không đồng nghĩa xóa audit trail. Tự động xóa theo ngày chỉ được bổ sung bằng Goal cấu hình riêng khi doanh nghiệp có chính sách pháp lý cụ thể.
