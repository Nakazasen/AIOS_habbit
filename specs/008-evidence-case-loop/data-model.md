# Mô hình dữ liệu: Vòng vụ việc, Agent và dự đoán có kiểm soát

> **Ranh giới kích hoạt**: Tài liệu này giữ hợp đồng dữ liệu cho toàn bộ US1–US11, không có nghĩa mọi bảng/kho phải được tạo ngay. Đợt hiện tại chỉ mở rộng `workspace_cases.sqlite` khi pilot cần. `production_prediction.sqlite` chỉ được tạo sau khi Data Gate LSU/Iris đạt; các bảng Agent/prediction còn lại là thiết kế dự phòng.

## 1. Nguyên tắc phân kho

| Kho | Mục đích | Nội dung bị cấm |
|---|---|---|
| `library.sqlite` | Chunk/citation của tài liệu quy chuẩn | Case, CSV log, model prediction, chat history |
| `line_events.sqlite` | Event Jam/C-call/LSU ở mức `suspected` | Bài học đã duyệt, model, nội dung RAG |
| `local_cases/workspace_cases.sqlite` | Case, activity, expert, learning, artifact và approval | Bản copy chat/excerpt thô, model binary |
| `local_cases/production_prediction.sqlite` | Dataset/model/prediction/shadow metadata | Tài liệu RAG, chat, plant-control command |

Liên kết giữa kho chỉ dùng ID/digest bất biến. Không join bằng tên file, câu chữ AI sinh hoặc đường dẫn tuyệt đối hiển thị cho người dùng.

## 2. Migration và tương thích

Mỗi SQLite store mới hoặc đang mở rộng phải có:

- `schema_migrations(version, name, applied_at, checksum)`.
- `PRAGMA user_version` đồng bộ với migration cuối.
- Online backup trước migration và `PRAGMA quick_check` sau migration.
- Migration chỉ tiến, transaction được; rollback bằng restore snapshot khi migration thất bại.
- Fixture schema Cổng 1 để chứng minh dữ liệu cũ đọc được sau upgrade.

Không được dùng `CREATE TABLE IF NOT EXISTS` như cơ chế migration duy nhất.

## 3. Kho hồ sơ vụ việc

### 3.1. `CaseRecord`

| Trường | Ràng buộc |
|---|---|
| `case_id` | ID bất biến, khóa chính |
| `case_type` | `investigation`, `prediction`, `agent_work` |
| `title` | Tiêu đề đã làm sạch, không chứa secret/excerpt thô |
| `status` | Theo state machine ở mục 3.9 |
| `priority` | `low`, `normal`, `high`, `urgent`; không tự suy ra từ LLM |
| `conversation_id`, `assistant_message_id`, `trace_id` | Con trỏ về Workspace Chat; có thể null với prediction tự mở |
| `evidence_digest` | Digest toàn tập evidence tại version hiện tại |
| `owner_id`, `assignee_id` | ID cục bộ; assignee phải có role hợp lệ |
| `created_by`, `created_at`, `updated_at` | Audit metadata |
| `version` | Optimistic concurrency; tăng khi transition hợp lệ |
| `activity_head_digest` | Digest đầu chuỗi activity hiện hành; phát hiện sửa/xóa event cuối |

### 3.2. `EvidenceReference`

| Trường | Ràng buộc |
|---|---|
| `evidence_ref_id`, `case_id` | ID và khóa ngoại |
| `source_store` | `workspace_trace`, `library`, `line_events`, `prediction`, `approved_artifact` |
| `source_id`, `source_version`, `locator` | Con trỏ bất biến/phiên bản; locator được làm sạch |
| `content_digest` | Bắt buộc |
| `provenance_status` | `suspected`, `approved`, `unknown`, `missing` |
| `privacy_label` | Mặc định `local_only` |
| `relevance_status` | `unreviewed`, `relevant`, `not_relevant`, `conflicted` |
| `added_by`, `added_at` | Audit metadata |

Tham chiếu có thể được tạo cùng case hoặc gắn thêm sau đó. Mọi lần gắn thêm phải qua service, kiểm tra optimistic version và tạo `CaseActivity`; không lưu nội dung ảnh, SOP, log hoặc đoạn trích thô trong kho case.

### 3.3. `CaseActivity`

Nhật ký append-only cho create, assignment, evidence added, status transition, expert request/review, learning promotion, artifact approval, prediction outcome và rollback. Mỗi activity có `event_id`, `case_id`, `event_type`, `actor_id`, `occurred_at`, `payload_digest`, `previous_event_digest`, `event_digest`. `CaseRecord.activity_head_digest` phải bằng digest event cuối để phát hiện cả việc sửa/xóa event cuối.

### 3.4. `CaseChecklistItem`

Biểu diễn phần còn thiếu mà hệ thống hoặc người dùng phát hiện: serial, ảnh, thời gian, SOP, log, retest. Trường chính gồm `item_id`, `case_id`, `kind`, `prompt_text`, `status`, `requested_from`, `resolved_by`, `resolution_evidence_ref_id`.

AI được tạo item `open`; chỉ evidence/human action hợp lệ mới chuyển `resolved`.

### 3.5. `RoleGrant`

| Trường | Ràng buộc |
|---|---|
| `actor_id` | ID người dùng cục bộ |
| `role` | `investigator`, `expert`, `quality_manager`, `artifact_approver`, `shadow_reviewer`, `admin` |
| `scope` | Miền/công đoạn/asset được phép; không dùng wildcard mặc định |
| `valid_from`, `valid_until`, `revoked_at` | Hiệu lực theo thời gian |
| `granted_by`, `reason` | Bắt buộc |

### 3.6. `ExpertRequest`

`request_id`, `case_id`, `claim_digest`, `question_text`, `requested_expert_id`, `required_scope`, `status`, `due_at`, `created_by`, `created_at`. Trạng thái: `open`, `answered`, `cancelled`, `expired`.

### 3.7. `ExpertReview`

`review_id`, `request_id`, `case_id`, `claim_digest`, `evidence_digest`, `decision`, `reviewer_id`, `reviewer_role`, `scope`, `rationale`, `confidence`, `supersedes_review_id`, `reviewed_at`.

`decision` chỉ gồm `confirmed`, `rejected`, `needs_more_evidence`, `conflicted`. Record append-only; không update nội dung cũ.

### 3.8. `LearningRecord`

| Trường | Ràng buộc |
|---|---|
| `learning_id` | ID bất biến |
| `source_review_id`, `case_id`, `evidence_digest` | Bắt buộc và truy vết được |
| `learning_text` | Văn bản đã scrub, dùng cho con người và retrieval |
| `status` | `candidate`, `promoted`, `withdrawn` |
| `promoted_by`, `promoted_at`, `promotion_reason` | Bắt buộc khi promoted |
| `withdrawn_by`, `withdrawn_at`, `withdrawal_reason` | Bắt buộc khi withdrawn |
| `search_document` | Bản chuẩn hóa để lập chỉ mục case-memory, không chứa excerpt thô |

### 3.9. State machine của case

```text
draft → triage → in_progress → awaiting_expert → resolved → archived
                    │              │
                    ├──────────────┴→ blocked
                    └───────────────→ rejected
```

- `prediction` bắt đầu ở `triage` khi signal hợp lệ.
- `resolved` cần outcome/review phù hợp loại case.
- `archived` không xóa record.
- Chỉ service được transition sau kiểm role, version và evidence digest.

## 4. Artifact và Agent

### 4.1. `ArtifactProposal`

`proposal_id`, `case_id`, `capability_id`, `artifact_type`, `risk_tier`, `evidence_digest`, `instruction_digest`, `status`, `created_by`, `created_at`.

Loại đầu ra ban đầu: `investigation_report`, `sop_draft`, `process_design`, `spreadsheet`, `diagram`, `code_change`.

### 4.2. `ArtifactVersion`

`artifact_version_id`, `proposal_id`, `version`, `content_digest`, `relative_output_path`, `mime_type`, `generator`, `template_version`, `verifier_result_digest`, `created_at`.

Mỗi version tạo file mới; `relative_output_path` phải nằm trong allowlisted output root.

### 4.3. `ApprovalRecord`

`approval_id`, `proposal_id`, `artifact_version_id`, `decision`, `approver_id`, `role`, `scope`, `rationale`, `approved_at`, `evidence_digest`.

`decision`: `approved`, `rejected`, `changes_requested`, `expired`. Approval gắn đúng version; chỉnh nội dung làm approval cũ hết hiệu lực.

### 4.4. `CapabilityDefinition`

`capability_id`, `artifact_type`, `risk_tier`, `allowed_inputs`, `allowed_outputs`, `template_id`, `verifier_id`, `required_role`, `allowed_commands`, `forbidden_paths`, `enabled`.

Capability được cấu hình, versioned và fail-closed; không tin loại task do prompt tự khai.

### 4.5. `AgentExecutionRecord`

Cho coding Agent: `execution_id`, `case_id`, `task_pack_digest`, `workspace_root_digest`, `proposal_digest`, `declared_commands_digest`, `observed_test_digest`, `result_status`, `rollback_ref`, `created_at`.

Không lưu secret, raw command output nhạy cảm hoặc đường dẫn hệ thống trong UI.

## 5. Kho dữ liệu dự đoán

### 5.1. `AssetRecord`

`asset_id`, `asset_type`, `line_id`, `station_id`, `effective_from`, `effective_to`, `source_digest`. `asset_type` hỗ trợ adapter `lsu_iris`, `drum`, `dlp` nhưng lõi không hard-code feature.

### 5.2. `MeasurementRecord`

`measurement_id`, `asset_id`, `unit_serial`, `event_time`, `ingested_at`, `metric_name`, `value`, `unit`, `jig_version`, `process_version`, `source_digest`, `privacy_label`.

Không làm tròn bỏ giá trị thô; thời gian sự kiện và ingest tách riêng.

### 5.3. `OutcomeLabel`

`outcome_id`, `asset_id`, `unit_serial`, `case_id`, `target_label`, `review_state`, `action_effectiveness`, `effective_time`, `confirmed_by`, `review_id`, `evidence_digest`, `created_at`.

- `target_label` biểu diễn sự thật cần học như `ok`, `ng` hoặc một failure class đã được data dictionary duyệt.
- `review_state` biểu diễn trạng thái thẩm định `confirmed`, `rejected`, `unknown`; không được dùng thay cho nhãn mục tiêu.
- `action_effectiveness` là `not_applicable`, `effective`, `ineffective` và chỉ dùng cho outcome hành động phòng ngừa.

Chỉ target label có review `confirmed` và provenance đầy đủ mới được dùng khi train/evaluate. `false_alarm` và `missed_detection` là kết quả đánh giá shadow, không phải target label nguồn.

### 5.4. `DatasetVersion`

`dataset_id`, `domain_adapter`, `schema_version`, `snapshot_started_at`, `snapshot_ended_at`, `row_count`, `positive_count`, `negative_count`, `unknown_count`, `source_digest`, `label_policy_digest`, `quality_report_digest`, `created_by`, `created_at`.

### 5.5. `FeatureSnapshot`

`feature_snapshot_id`, `dataset_id`, `asset_id`, `as_of_time`, `feature_schema_version`, `feature_values_digest`, `source_window_digest`, `created_at`.

Snapshot chỉ dùng dữ liệu có `event_time <= as_of_time`; đây là chốt chống outcome leakage.

### 5.6. `EvaluationProtocol`

`protocol_id`, `split_strategy`, `time_boundaries`, `group_keys`, `gap`, `metrics`, `cost_matrix`, `calibration_method`, `acceptance_thresholds`, `owner_approval_digest`.

### 5.7. `ModelVersion`

`model_id`, `algorithm`, `hyperparameters_digest`, `dataset_id`, `protocol_id`, `feature_schema_version`, `code_commit`, `artifact_digest`, `model_card_path`, `status`, `created_at`.

`status`: `candidate`, `evaluated`, `approved_for_shadow`, `retired`, `rejected`. Không có `production_control`.

### 5.8. `PredictionRun`

`run_id`, `model_id`, `started_at`, `ended_at`, `input_snapshot_digest`, `status`, `error_code`, `created_case_count`. Error lưu mã an toàn, không traceback thô.

### 5.9. `RiskAssessment`

`assessment_id`, `run_id`, `asset_id`, `feature_snapshot_id`, `horizon`, `risk_score`, `calibrated_probability`, `uncertainty`, `threshold_version`, `top_factor_digest`, `case_id`, `created_at`.

Không lưu câu “chắc chắn hỏng”; UI hiển thị đây là rủi ro cần kiểm tra.

### 5.10. `ShadowOutcome`

`shadow_outcome_id`, `assessment_id`, `case_id`, `decision`, `reviewer_id`, `review_id`, `observed_outcome_id`, `rationale`, `reviewed_at`.

`decision`: `true_positive`, `false_alarm`, `missed_detection`, `unknown`. Missed detection có thể được tạo từ outcome thực không có assessment trước đó.

### 5.11. `PredictionCaseDispatch`

`dispatch_id`, `assessment_id`, `idempotency_key`, `target_case_id`, `status`, `attempt_count`, `last_error_code`, `created_at`, `updated_at`.

Record outbox này nằm trong kho dự đoán và có unique key theo `assessment_id` cùng phiên bản policy. Worker chỉ gọi case service bằng idempotency key; sau lỗi hoặc restart có thể reconcile mà không tạo case trùng. Không có transaction phân tán trực tiếp giữa hai SQLite.

## 6. Quan hệ chính

```text
CaseRecord
 ├─ EvidenceReference
 ├─ CaseActivity
 ├─ CaseChecklistItem
 ├─ ExpertRequest ──> ExpertReview ──> LearningRecord
 ├─ ArtifactProposal ──> ArtifactVersion ──> ApprovalRecord
 └─ RiskAssessment ──> ShadowOutcome

DatasetVersion ──> FeatureSnapshot ──> ModelVersion
ModelVersion ──> PredictionRun ──> RiskAssessment ──> CaseRecord(prediction)
                                      └─ PredictionCaseDispatch ──> CaseRecord(prediction)
OutcomeLabel ───────────────────────────────────────> ShadowOutcome
```

## 7. Quy tắc xóa, thu hồi và rollback

- Không hard-delete case/review/approval/prediction audit record qua UI thông thường.
- Thu hồi bài học/model/artifact bằng trạng thái và activity mới.
- Xóa dữ liệu thật chỉ theo retention policy do chủ sở hữu phê duyệt và phải có audit/backup boundary.
- Model rollback chuyển threshold/model active pointer về version trước; không xóa model card/evaluation cũ.
- Artifact rollback tạo version thay thế, không ghi đè version đã phát hành.
