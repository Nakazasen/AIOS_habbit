# Mô hình dữ liệu: Vòng vụ việc, Agent và dự đoán có kiểm soát

> **Ranh giới kích hoạt**: Tài liệu này giữ hướng dữ liệu cho toàn bộ US1–US11, không yêu cầu tạo tất cả bảng ngay. MVP chỉ mở rộng `workspace_cases.sqlite` cho xác nhận chuyên gia và chỉ tạo `production_prediction.sqlite` sau khi file Iris LSU thật vượt Data Gate. Các bảng Agent và mở rộng prediction còn lại là thiết kế dự phòng, không phải task hiện tại.

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

Tác tử hệ thống `system:rubric` không phải `RoleGrant` của con người. Nó chỉ được ghi quyết định Data Gate, chạy bóng đọc-only và cổng kỹ thuật kèm `rubric_version`/digest; không được xác nhận chuyên gia, cấp quyền hoặc phát lệnh máy.

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

## 5. Kho dữ liệu Iris LSU cho MVP

Kho này chỉ được tạo sau khi dữ liệu thật chứng minh có thể nối ổn định. Trước thời điểm đó, bộ nhập file chỉ trả báo cáo Data Gate và không ghi dữ liệu bền vững.

### 5.1. `ComponentLotMeasurement`

| Trường | Ràng buộc |
|---|---|
| `lot_measurement_id` | ID bất biến |
| `component_lot_id`, `component_code` | Khóa lot và loại linh kiện theo data dictionary |
| `metric_name`, `value`, `unit` | Thông số đầu vào; không bỏ giá trị thô |
| `event_time`, `ingested_at` | Tách thời điểm đo và thời điểm nhận dữ liệu |
| `source_digest`, `privacy_label` | Bắt buộc; mặc định `local_only` |

### 5.2. `UnitLotLink`

`link_id`, `unit_serial`, `component_lot_id`, `component_code`, `assembly_time`, `line_id`, `station_id`, `source_digest`, `ingested_at`.

Một Unit có thể dùng nhiều loại linh kiện. Cặp khóa hợp lệ phải do data dictionary quy định; không ghép bằng tên file hoặc vị trí dòng.

### 5.3. `JigMeasurementOutcome`

| Trường | Ràng buộc |
|---|---|
| `jig_result_id`, `unit_serial`, `jig_id`, `run_id` | Xác định đúng Unit, JIG và lần đo |
| `event_time`, `ingested_at` | Thời điểm đo và thời điểm dữ liệu đến |
| `metric_name`, `value`, `unit` | Phép đo JIG |
| `jig_version`, `process_version` | Có thể rỗng nhưng phải bị báo trong Data Gate |
| `target_label`, `failure_code`, `retest_outcome` | OK/NG và kết quả thực tế theo data dictionary |
| `review_state`, `confirmed_by`, `evidence_digest` | `machine_verified` hoặc `human_confirmed` mới dùng để đánh giá/model; mâu thuẫn là `unknown` |
| `source_digest`, `privacy_label` | Bắt buộc; mặc định `local_only` |

### 5.4. `DatasetVersion`

`dataset_id`, `domain_adapter`, `primary_jig`, `schema_version`, `mapping_digest`, `rubric_version`, `rubric_digest`, `gate_status`, `snapshot_started_at`, `snapshot_ended_at`, `row_count`, `joined_unit_count`, `missing_count`, `conflict_count`, `positive_count`, `negative_count`, `source_digest`, `quality_report_digest`, `created_by`, `created_at`.

MVP chỉ dùng `domain_adapter=lsu_iris` và `primary_jig=BOWSKEW_4_BEAM`. Giá trị target dùng hợp đồng mặc định có version hoặc cấu hình cục bộ ghi đè, không hard-code trong lõi chung.

### 5.5. `EvaluationRun`

`evaluation_id`, `dataset_id`, `method`, `protocol_digest`, `threshold_digest`, `rubric_version`, `rubric_digest`, `code_commit`, `true_alerts`, `false_alerts`, `missed_detections`, `lead_time_summary`, `report_digest`, `status`, `created_at`.

`status` gồm `evaluated`, `AUTO_SHADOW`, `LEARNING_SHADOW`, `BLOCKED_DATA`, `FAIL_TECHNICAL`. Quyết định đọc-only nằm ngay trên evaluation để không phải tạo thêm bảng phê duyệt và workflow thừa.

`method` trước hết là `no_alert` hoặc một baseline thống kê. Chỉ thêm một `model` khi Data Gate đạt; model artifact và feature schema được ghi cùng `report_digest`, không cần dựng registry model tổng quát trong MVP.

`protocol_digest` đại diện cho cấu hình nhỏ nhất gồm metric được phép, chiều rủi ro, hệ số EWMA, cửa sổ nền, `as_of_time`, khoảng dự báo, quy tắc ghép cảnh báo–outcome, danh sách feature cho phép và phép chia thời gian/Unit. Không có đủ cấu hình thì phương pháp là `not_applicable`, không tự điền giá trị dùng cho dữ liệu thật.

### 5.6. `RiskAssessment`

`assessment_id`, `evaluation_id`, `shadow_run_id`, `unit_serial`, `as_of_time`, `evaluation_window_start`, `evaluation_window_end`, `input_snapshot_digest`, `batch_digest`, `risk_score`, `threshold_digest`, `factor_summary`, `link_status`, `case_id`, `idempotency_key`, `created_at`.

- Chỉ dùng dữ liệu có `event_time <= as_of_time`.
- `link_status` chỉ gồm `pending_case_link`, `linked`, `retryable_error`; trạng thái này cho phép tiếp tục sau lỗi giữa hai kho mà không cần outbox.
- `factor_summary` là giải thích ngắn đã làm sạch; dữ liệu chi tiết vẫn ở nguồn cục bộ.
- UI phải nói “nguy cơ cần kiểm tra”, không nói “chắc chắn lỗi”.
- `idempotency_key` được tạo từ dataset, phương pháp, threshold, `batch_digest`, Unit và cửa sổ đánh giá bằng cách tuần tự hóa chuẩn. Không dùng thời điểm đồng hồ lúc chạy; chạy lại cùng lô phải ra cùng khóa và không tạo case trùng. MVP không cần outbox hay worker nền.

### 5.7. `ShadowOutcome`

`shadow_outcome_id`, `shadow_run_id`, `assessment_id`, `unit_serial`, `decision`, `observed_jig_result_id`, `reviewer_id`, `rationale`, `reviewed_at`.

`decision`: `true_positive`, `false_alarm`, `missed_detection`, `unknown`. Nguồn kết quả cuối cùng vượt rubric được ghi với `reviewer_id=system:rubric`; người dùng có thể bổ sung bản sửa append-only có lý do.

Với `missed_detection`, `assessment_id` được phép rỗng nhưng `shadow_run_id`, `unit_serial`, outcome đã xác nhận, nguồn xác nhận, rationale và evidence bắt buộc có. Outcome được nhập sau lượt dự báo; file đầu vào shadow không được mang outcome tương lai vào feature snapshot.

### 5.8. Phần chỉ mở sau MVP

Scheduler, outbox nhiều tiến trình, registry model tổng quát, calibration service, cảnh báo ngoài ứng dụng và adapter Drum/DLP chỉ được thiết kế chi tiết khi shadow thủ công chứng minh nhu cầu. Không tạo bảng rỗng cho các phần này trong MVP.

## 6. Quan hệ chính

```text
CaseRecord
 ├─ EvidenceReference
 ├─ CaseActivity
 ├─ CaseChecklistItem
 ├─ ExpertRequest ──> ExpertReview ──> LearningRecord
 ├─ ArtifactProposal ──> ArtifactVersion ──> ApprovalRecord
 └─ RiskAssessment ──> ShadowOutcome

ComponentLotMeasurement ──┐
UnitLotLink ───────────────┼─> DatasetVersion ─> EvaluationRun ─> RiskAssessment ─> CaseRecord(prediction)
JigMeasurementOutcome ────┘                                      └───────────────> ShadowOutcome
```

## 7. Quy tắc xóa, thu hồi và rollback

- Không hard-delete case/review/approval/prediction audit record qua UI thông thường.
- Thu hồi bài học/model/artifact bằng trạng thái và activity mới; model chỉ áp dụng nếu MVP thực sự tạo model.
- Xóa dữ liệu thật chỉ theo retention policy do chủ sở hữu phê duyệt và phải có audit/backup boundary.
- Rollback prediction chuyển threshold hoặc model được chọn về version trước; không xóa báo cáo đánh giá cũ.
- Artifact rollback tạo version thay thế, không ghi đè version đã phát hành.
