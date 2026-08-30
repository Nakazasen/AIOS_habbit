# Hợp đồng an toàn cho vòng vụ việc, Agent và dự đoán

## 1. Bất biến toàn hệ thống

1. Thiếu evidence, role, scope, digest, migration hoặc owner decision thì fail-closed.
2. `local_only` không đi Gemini Web/Nakazasen Router; C-AGENT chỉ theo policy và consent hiện có.
3. Không có API nào trong phạm vi này được điều khiển PLC, dừng line, chặn/xuất hàng, xóa hoặc ghi đè nguồn nhà máy.
4. AI output không tự trở thành `confirmed`, outcome label, bài học hoặc PASS.
5. Workspace Chat không import `studio` hoặc `case_cockpit`.
6. Mọi lỗi UI được đổi thành thông báo tiếng Việt an toàn, không traceback/secret/system path.

## 2. Hợp đồng migration

```text
migrate_store(database_path, target_version) -> MigrationResult
```

### Điều kiện trước

- Path nằm trong local runtime root được phép.
- Migration chain liên tục, checksum đúng, không có version lạ.
- Online backup thành công và `quick_check` của bản nguồn đạt.

### Kết quả

- Tất cả migration hoặc không migration nào được commit.
- `schema_migrations` và `PRAGMA user_version` khớp.
- `quick_check` sau migration đạt; nếu lỗi, restore snapshot và trả error code an toàn.

## 3. Hợp đồng tạo và đọc case

```text
create_case_from_trace_id(trace_id, expected_conversation_id) -> CaseRecord
list_cases(filter, actor) -> CaseSummary[]
get_case_detail(case_id, actor) -> CaseDetail
transition_case(case_id, expected_version, transition, actor, rationale) -> CaseRecord
attach_evidence_reference(case_id, expected_version, source_store, source_id, source_version, locator, content_digest, provenance_status, actor) -> EvidenceReference
```

### Chốt chặn

- Tạo từ trace cần citation/source locator/digest/`local_only`; không copy raw Q&A/excerpt.
- `list_cases` chỉ trả metadata đã scrub và case actor được phép xem.
- `get_case_detail` phân giải trace gốc ở read time; trace mất trả `missing`, không tái sinh nội dung.
- Transition kiểm state machine, role/scope, optimistic version và ghi `CaseActivity` cùng transaction.
- Gắn thêm evidence chỉ nhận locator đã làm sạch, digest và provenance từ kho nguồn được phép; không nhận raw bytes/raw excerpt và phải ghi activity cùng transaction.
- Actor được lấy từ local actor context đáng tin cậy do ứng dụng cấu hình, không nhận ID tự khai từ form UI. Case luôn có scope để đối chiếu grant; thiếu actor/grant/scope thì fail-closed.
- Mỗi activity có `event_digest`; case giữ `activity_head_digest` và service phải kiểm toàn chuỗi trước thao tác ghi.

## 4. Hợp đồng chuyên gia

```text
request_expert_review(case_id, claim_digest, question, assignee, scope, actor) -> ExpertRequest
record_expert_review(request_id, decision, rationale, confidence, actor) -> ExpertReview
resolve_review_conflict(case_id, review_ids, decision, rationale, actor) -> ExpertReview
```

### Chốt chặn

- Assignee/actor phải có `RoleGrant` còn hiệu lực và scope khớp.
- `confirmed`/`rejected` cần rationale không rỗng và evidence digest vẫn khớp case.
- Review append-only; sửa tạo record mới với `supersedes_review_id`.
- Hai review trái chiều chuyển case sang trạng thái xung đột; AI không chọn bên thắng.

## 5. Hợp đồng bài học

```text
create_learning_candidate(review_id, learning_text, actor) -> LearningRecord
promote_learning(learning_id, actor, rationale) -> LearningRecord
withdraw_learning(learning_id, actor, rationale) -> LearningRecord
search_promoted_learning(query, case_scope, actor) -> LearningHit[]
```

### Chốt chặn

- Candidate chỉ từ review `confirmed` có provenance đầy đủ.
- Promotion cần role `quality_manager`, digest không đổi và rationale.
- Search chỉ trả `promoted`, luôn kèm case/review/evidence refs và nhãn “Bài học đã xác nhận”.
- Không ghi `library.sqlite`, không train/re-embed tự động vào RAG library.

## 6. Hợp đồng điều tra line

```text
attach_line_events(case_id, event_ids, actor) -> EvidenceReference[]
build_investigation_timeline(case_id, actor) -> Timeline
propose_missing_evidence(case_id, actor) -> CaseChecklistItem[]
review_event_relevance(case_id, evidence_ref_id, decision, actor) -> EvidenceReference
```

### Chốt chặn

- Event phải tồn tại trong `line_events.sqlite`, có source digest/version và trạng thái `suspected`.
- Không match thì trả rỗng; cấm fallback năm event gần nhất.
- Timeline phân biệt fact, hypothesis và missing data.
- Mapping overlay chỉ dùng manifest có version/approver/scope khớp.
- CSV thô không đi `library.sqlite` hoặc external route.

## 7. Hợp đồng Agent artifact

```text
create_artifact_proposal(case_id, capability_id, instruction, actor) -> ArtifactProposal
generate_artifact_version(proposal_id, actor) -> ArtifactVersion
verify_artifact(artifact_version_id, verifier_id) -> VerificationResult
review_artifact(artifact_version_id, decision, actor, rationale) -> ApprovalRecord
export_approved_artifact(artifact_version_id, output_root, actor) -> ExportResult
```

### Chốt chặn

- Capability phải enabled, risk tier/inputs/outputs/template/verifier/approver đầy đủ.
- Case/evidence digest rỗng hoặc review chưa đạt theo capability thì từ chối.
- Mọi output là path tương đối nằm trong allowlisted root; file tồn tại thì tạo version/path mới.
- Chỉnh artifact sau approval làm approval cũ không còn hiệu lực.
- `process_design` không đồng nghĩa cho phép sửa file CAD/PLC gốc; adapter cụ thể phải có contract riêng.

## 8. Hợp đồng Agent lập trình

```text
create_code_task_case(task_pack, workspace, actor) -> CaseRecord
propose_code_change(case_id, proposal, actor) -> ArtifactVersion
approve_code_change(case_id, proposal_digest, actor) -> ApprovalRecord
run_approved_command(case_id, command_digest, actor) -> AgentExecutionRecord
record_observed_tests(case_id, evidence, auditor) -> AgentExecutionRecord
```

### Chốt chặn

- Workspace code đã xác nhận, nằm ngoài factory/local runtime data roots.
- Task pack xác định allowed/forbidden files, commands, tests, branch/head.
- `local_cases`, `.env`, factory source và system paths bị deny mặc định.
- Patch/command proposal bất biến; approval gắn đúng digest/version.
- Báo cáo PASS cần observed evidence do runner/auditor thu, không tin self-report.
- Không tự merge/push/commit nếu capability và approval riêng chưa được cấp.

## 9. Hợp đồng Data Gate dự đoán

```text
register_dataset_snapshot(manifest, actor) -> DatasetVersion
evaluate_prediction_readiness(dataset_id, protocol_id, actor) -> ReadinessResult
```

### Sáu điều kiện bắt buộc

1. Stable join keys và data dictionary được duyệt.
2. Measurement có unit, event time, ingest time, jig/process version.
3. Outcome labels có reviewer/evidence và đủ positive/negative theo protocol.
4. Data owner và quality owner được chỉ định.
5. Temporal/group split, replay và leakage checks đã định nghĩa.
6. Shadow reviewer, acceptance thresholds và rollback owner đã ký duyệt.

Thiếu bất kỳ điều kiện nào trả `blocked` cùng danh sách thiếu; không train model.

## 10. Hợp đồng huấn luyện và đánh giá

```text
build_feature_snapshot(dataset_id, as_of_time, feature_schema) -> FeatureSnapshot
train_candidate(dataset_id, protocol_id, algorithm_config) -> ModelVersion
evaluate_candidate(model_id, holdout_id, protocol_id) -> EvaluationReport
approve_model_for_shadow(model_id, actor, rationale) -> ModelVersion
```

### Chốt chặn

- Feature chỉ dùng event có thời gian không vượt `as_of_time`.
- Dataset/protocol/code/feature schema digest phải đóng băng.
- Evaluation bắt buộc có false alarm, missed detection, lead time, precision, recall, calibration và slice stability.
- Model không được tự chọn threshold; owner phê duyệt cost matrix/threshold.
- Chỉ status `approved_for_shadow`; không có production control state.

## 11. Hợp đồng shadow và case dự đoán

```text
run_shadow(model_id, input_window) -> PredictionRun
enqueue_prediction_case(risk_assessment, dedup_policy) -> PredictionCaseDispatch
reconcile_prediction_cases(limit, actor) -> ReconciliationResult
record_shadow_outcome(assessment_id, decision, observed_outcome, actor) -> ShadowOutcome
```

### Chốt chặn

- Model, feature schema và threshold version phải active/approved.
- Risk assessment có feature snapshot, horizon, uncertainty và factor digest.
- Dedup/cooldown ngăn tạo bão case.
- Ghi `RiskAssessment` và outbox dispatch trong cùng transaction của kho dự đoán; worker gọi case service bằng idempotency key rồi mới đánh dấu dispatched.
- Restart/lỗi nửa chừng phải reconcile được; không dựa vào transaction phân tán giữa `production_prediction.sqlite` và `workspace_cases.sqlite`.
- Shadow chỉ ghi DB/queue local; không gửi alert ngoài, không plant action.
- Outcome `true_positive`, `false_alarm`, `missed_detection`, `unknown` cần reviewer/evidence.

## 12. Hợp đồng cảnh báo có duyệt

```text
enable_in_app_alert_policy(policy, actor) -> AlertPolicy
create_preventive_action_proposal(case_id, action_id, actor) -> ArtifactProposal
record_action_outcome(proposal_id, outcome, actor, evidence) -> ActionOutcome
```

### Chốt chặn

- Chỉ mở sau shadow gate có owner approval, kill switch và rollback.
- Alert chỉ trong Workspace Chat cho role được phép.
- Hành động từ thư viện versioned, có evidence và human approval.
- Không có connector PLC/line control trong contract này.
